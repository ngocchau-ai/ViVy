#!/usr/bin/env python3
"""P4 Dream → 2brain durable-lesson e2e tests (Gate 7).

Proves the full learning-safety path:
  LessonStore.promote (Gate 7 accept/reject) → sync_2brain → durable_decisions.md
  plus Dream cycle → 2brain hot-memory journal.

Gate 7 binding: "Unverified output cannot become durable knowledge. Promotion
records provenance, scope, confidence, and validation."

Gate 9: these tests assert mechanism and receipt schema only. They do NOT
claim live-model accuracy, latency, or production readiness.

Changelog:
    23/09/2026 (Claude Code — P4 Dream → 2brain durable-lesson e2e): Initial.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _complete_evidence(**overrides):
    base = {
        "claim": "P4 e2e: durable lesson path records provenance",
        "evidence_ids": ["ev_p4_1"],
        "source": "dream_lesson_e2e",
        "expected_evidence": "lesson present in 2brain durable_decisions.md",
        "actual_observation": "lesson_id listed under VERIFIED_RESULT section",
        "acceptance": "ACCEPTED",
        "confidence": 0.9,
        "limits": "mechanism TESTED on temp brain path; not live-model",
        "task_id": "p4_e2e",
        "session_id": "sess_p4_e2e",
        "state_hash": "hash_p4_abc",
    }
    base.update(overrides)
    return base


def _provenance(evidence=None):
    return {
        "evidence": evidence if evidence is not None else _complete_evidence(),
        "node_ids": ["hyp_p4_1"],
        "rounds": 1,
    }


class Gate7PromotionFixtureTests(unittest.TestCase):
    """Gate 7: rejected promotion and accepted promotion fixtures."""

    def test_verified_result_with_full_evidence_is_accepted(self):
        from integration.lesson_store import LessonStore
        from orchestrator.graph_bridge import EvidenceClass

        with tempfile.TemporaryDirectory() as td:
            store = LessonStore(Path(td) / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_p4_e2e",
                content="Durable lesson body",
                evidence_class=EvidenceClass.VERIFIED_RESULT,
                confidence=0.9,
                provenance=_provenance(),
                scope="p4_e2e",
            )
            self.assertIsNotNone(lesson)
            self.assertEqual(lesson.evidence_class, "VERIFIED_RESULT")
            self.assertEqual(lesson.scope, "p4_e2e")
            self.assertAlmostEqual(lesson.confidence, 0.9)
            self.assertIn("evidence", lesson.provenance)

    def test_fast_signal_is_rejected(self):
        from integration.lesson_store import LessonStore
        from orchestrator.graph_bridge import EvidenceClass

        with tempfile.TemporaryDirectory() as td:
            store = LessonStore(Path(td) / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_p4_e2e",
                content="fast claim",
                evidence_class=EvidenceClass.FAST_SIGNAL,
                confidence=0.5,
                provenance=_provenance(),
            )
            self.assertIsNone(lesson)
            self.assertEqual(store.count()["total"], 0)

    def test_provisional_result_is_rejected(self):
        from integration.lesson_store import LessonStore
        from orchestrator.graph_bridge import EvidenceClass

        with tempfile.TemporaryDirectory() as td:
            store = LessonStore(Path(td) / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_p4_e2e",
                content="provisional claim",
                evidence_class=EvidenceClass.PROVISIONAL_RESULT,
                confidence=0.7,
                provenance=_provenance(),
            )
            self.assertIsNone(lesson)
            self.assertEqual(store.count()["total"], 0)

    def test_incomplete_evidence_packet_is_rejected(self):
        from integration.lesson_store import LessonStore
        from orchestrator.graph_bridge import EvidenceClass

        with tempfile.TemporaryDirectory() as td:
            store = LessonStore(Path(td) / "lessons.jsonl")
            bad = _complete_evidence(claim="", actual_observation="")
            lesson = store.promote(
                session_id="sess_p4_e2e",
                content="half-baked claim",
                evidence_class=EvidenceClass.VERIFIED_RESULT,
                confidence=0.9,
                provenance=_provenance(bad),
            )
            self.assertIsNone(lesson)
            self.assertEqual(store.count()["total"], 0)

    def test_all_rejected_batch_creates_no_durable_lesson(self):
        from integration.lesson_store import LessonStore
        from orchestrator.graph_bridge import EvidenceClass

        with tempfile.TemporaryDirectory() as td:
            store = LessonStore(Path(td) / "lessons.jsonl")
            for cls in (
                EvidenceClass.FAST_SIGNAL,
                EvidenceClass.PROVISIONAL_RESULT,
                EvidenceClass.VERIFIED_RESULT,
            ):
                # All-rejected batch: even VERIFIED_RESULT must fail on an
                # incomplete evidence packet (Gate 7 dual-key).
                ev = _complete_evidence(claim="", actual_observation="")
                store.promote(
                    session_id="sess_p4_e2e",
                    content=f"batch-{cls.name}",
                    evidence_class=cls,
                    confidence=0.4,
                    provenance=_provenance(ev),
                )
            counts = store.count()
            self.assertEqual(counts["total"], 0)
            self.assertEqual(counts["active"], 0)


class DreamTo2BrainSyncTests(unittest.TestCase):
    """Accepted lesson and Dream journal land on the 2brain path."""

    def test_sync_writes_durable_decisions_and_lessons(self):
        from integration.lesson_store import LessonStore
        from orchestrator.dream_lesson_e2e import run_e2e
        from orchestrator.graph_bridge import EvidenceClass

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store_path = root / "lessons.jsonl"
            brain = root / "brain"
            store = LessonStore(store_path)
            lesson = store.promote(
                session_id="sess_p4_e2e",
                content="Lesson that must appear in durable_decisions.md",
                evidence_class=EvidenceClass.VERIFIED_RESULT,
                confidence=0.9,
                provenance=_provenance(),
                scope="p4_sync",
            )
            self.assertIsNotNone(lesson)

            result = run_e2e(
                store_path=store_path,
                brain_path=brain,
                skip_promotion=True,  # already promoted above
            )
            self.assertTrue(result.synced_2brain)
            self.assertIn(lesson.lesson_id, result.synced_lesson_ids)

            decisions = brain / "projects" / "vivy-v5" / "durable_decisions.md"
            self.assertTrue(decisions.exists(), "durable_decisions.md missing")
            text = decisions.read_text(encoding="utf-8")
            self.assertIn(lesson.lesson_id, text)
            self.assertIn("Lesson that must appear", text)

            lessons_dir = brain / "projects" / "vivy-v5" / "lessons"
            self.assertTrue(lessons_dir.exists())
            self.assertTrue(any(lessons_dir.glob("lessons_*.jsonl")))

            hot = brain / "hot-memory" / "vivy_sync_receipts.jsonl"
            self.assertTrue(hot.exists())

    def test_dream_cycle_writes_hot_memory_journal(self):
        from engine.dream_engine import VivyDreamEngine
        from integration.cautreo_binding import CautreoContextMemory, CautreoScoreGraph
        from memory.cognitive_graph import CognitiveStateGraph

        with tempfile.TemporaryDirectory() as td:
            brain = Path(td) / "brain"
            engine = VivyDreamEngine(
                cognitive_graph=CognitiveStateGraph(),
                context_memory=CautreoContextMemory(max_items=16),
                score_graph=CautreoScoreGraph(),
                brain_path=str(brain),
            )
            try:
                result = engine.run_dream_cycle(task_id="p4_e2e")
                self.assertTrue(result.success)
                self.assertEqual(result.status, "LUCID_STANDBY")
                self.assertTrue(result.synced_2brain)
                journal = brain / "hot-memory" / "durable-learning-dream-cycle-latest.md"
                self.assertTrue(journal.exists(), "dream journal missing")
                text = journal.read_text(encoding="utf-8")
                self.assertIn("LUCID_STANDBY", text)
                self.assertIn("p4_e2e", text)
            finally:
                engine.context_memory.close()
                engine.score_graph.destroy()


class E2EReceiptSchemaTests(unittest.TestCase):
    """Receipt must carry Gate 7 fields and Gate 9 labels."""

    def test_receipt_records_provenance_scope_confidence_validation(self):
        from orchestrator.dream_lesson_e2e import run_e2e

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = run_e2e(
                store_path=root / "lessons.jsonl",
                brain_path=root / "brain",
            )
            self.assertTrue(result.gate7_pass, result.to_dict())
            self.assertEqual(result.n_accepted, 1)
            self.assertGreaterEqual(result.n_rejected, 3)

            accepted = result.accepted[0]
            for field in ("lesson_id", "scope", "confidence", "provenance", "validation"):
                self.assertIn(field, accepted)
            self.assertEqual(accepted["scope"], "p4_e2e")
            self.assertAlmostEqual(accepted["confidence"], 0.9)
            self.assertTrue(accepted["validation"]["valid_for_promotion"])
            self.assertIn("evidence", accepted["provenance"])

            rejected_reasons = {r["reject_reason"] for r in result.rejected}
            self.assertIn("evidence_class", rejected_reasons)
            self.assertIn("evidence_packet", rejected_reasons)

    def test_receipt_status_label_is_gate9_honest(self):
        from orchestrator.dream_lesson_e2e import run_e2e

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = run_e2e(
                store_path=root / "lessons.jsonl",
                brain_path=root / "brain",
            )
            self.assertEqual(result.status_label, "TESTED_MECHANISM")
            self.assertNotEqual(result.status_label, "VERIFIED_RESULT")
            self.assertNotEqual(result.status_label, "PRODUCTION_READY")
            low = result.protocol.lower()
            self.assertNotIn("0ms", low)
            self.assertNotIn("production-ready", low)
            self.assertIn("gate 7", low)

    def test_receipt_is_json_serializable(self):
        from orchestrator.dream_lesson_e2e import run_e2e

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = run_e2e(
                store_path=root / "lessons.jsonl",
                brain_path=root / "brain",
            )
            payload = result.to_dict()
            text = json.dumps(payload, ensure_ascii=False)
            self.assertIn("gate7_verdict", text)
            self.assertIn("accepted", text)
            self.assertIn("rejected", text)

    def test_write_receipt_emits_json_file(self):
        from orchestrator.dream_lesson_e2e import run_e2e, write_receipt

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = run_e2e(
                store_path=root / "lessons.jsonl",
                brain_path=root / "brain",
            )
            out = root / "receipt.json"
            path = write_receipt(result, str(out))
            self.assertTrue(os.path.exists(path))
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(data["status_label"], "TESTED_MECHANISM")
            self.assertEqual(data["n_accepted"], 1)


class FailClosedTests(unittest.TestCase):
    def test_missing_brain_root_fails_closed(self):
        from orchestrator.dream_lesson_e2e import run_e2e

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Point at a path whose parent is a file → mkdir must fail closed.
            blocker = root / "blocker"
            blocker.write_text("x", encoding="utf-8")
            result = run_e2e(
                store_path=root / "lessons.jsonl",
                brain_path=blocker / "nested" / "brain",
            )
            self.assertFalse(result.synced_2brain)
            self.assertFalse(result.gate7_pass or result.synced_2brain)
            self.assertEqual(result.gate7_verdict, "FAIL")


if __name__ == "__main__":
    unittest.main()
