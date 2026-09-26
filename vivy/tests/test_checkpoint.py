"""
Tests for CheckpointManager + LessonStore -- Sprint 4 Gate 5+7.
Uses local temp dir instead of pytest tmp_path (Windows permission issue).
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import numpy as np

from integration.checkpoint_manager import CheckpointManager
from integration.lesson_store import LessonStore
from memory.cognitive_graph import CognitiveStateGraph, NodeType
from memory.hebbian_recall import HebbianRecall
from orchestrator.graph_bridge import EvidenceClass

# Use a local temp dir to avoid Windows AppData permission issues
_TEST_TMP = Path("_pytest_tmp")


def _mktemp() -> Path:
    p = _TEST_TMP / f"t_{int(time.time()*1000)}_{os.getpid()}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rm(p: Path) -> None:
    try:
        shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_graph() -> CognitiveStateGraph:
    g = CognitiveStateGraph()
    g.add_node("n1", NodeType.HYPOTHESIS, content="test", embedding=[0.1]*64, confidence=0.8)
    g.add_node("n2", NodeType.INVARIANT, content="fact", embedding=[0.2]*64, confidence=1.0)
    g.add_edge_falsified("n1", "n2")
    return g


def _make_recall() -> HebbianRecall:
    r = HebbianRecall(dim=64)
    r.register("n1", np.array([0.1]*64, dtype=np.float32))
    r.register("n2", np.array([0.2]*64, dtype=np.float32))
    return r


# ---------------------------------------------------------------------------
# CheckpointManager Tests (Gate 5)
# ---------------------------------------------------------------------------


class TestCheckpointManager:
    def test_save_creates_file(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d, max_checkpoints_per_session=3)
            meta = mgr.save("sess_a", _make_graph(), _make_recall())
            assert Path(meta.file_path).exists()
            assert meta.node_count == 2
            assert meta.session_id == "sess_a"
        finally:
            _rm(d)

    def test_restore_nodes(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d, max_checkpoints_per_session=3)
            mgr.save("sess_a", _make_graph(), _make_recall())
            g2 = CognitiveStateGraph()
            r2 = HebbianRecall(dim=64)
            meta = mgr.restore("sess_a", g2, r2)
            assert meta is not None
            assert "n1" in g2._nodes
            assert "n2" in g2._nodes
            assert g2._nodes["n1"].node_type == NodeType.HYPOTHESIS
        finally:
            _rm(d)

    def test_restore_recall_W(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d)
            mgr.save("sess_a", _make_graph(), _make_recall())
            g2 = CognitiveStateGraph()
            r2 = HebbianRecall(dim=64)
            mgr.restore("sess_a", g2, r2)
            # W is built lazily on first recall() -- trigger it
            test_vec = np.array([0.1]*64, dtype=np.float32)
            r2.recall(test_vec, graph=g2)
            # After recall, W is built
            assert r2.is_built
        finally:
            _rm(d)

    def test_restore_none_if_no_checkpoint(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d)
            result = mgr.restore("nobody", CognitiveStateGraph(), HebbianRecall(dim=64))
            assert result is None
        finally:
            _rm(d)

    def test_purge_old_checkpoints(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d, max_checkpoints_per_session=3)
            g = _make_graph()
            r = _make_recall()
            for _ in range(5):
                mgr.save("sess_purge", g, r)
            remaining = mgr.list_checkpoints("sess_purge")
            assert len(remaining) <= 3
        finally:
            _rm(d)

    def test_atomic_write_no_tmp_left(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d)
            mgr.save("sess_atomic", _make_graph(), _make_recall())
            tmp_files = list(mgr._dir.glob("*.tmp"))
            assert len(tmp_files) == 0
        finally:
            _rm(d)

    def test_checkpoint_roundtrip_falsified_count(self):
        d = _mktemp()
        try:
            mgr = CheckpointManager(checkpoint_dir=d)
            g = _make_graph()
            # n1 -> n2 edge (FALSIFIED) already added by _make_graph
            # falsified_count is incremented by add_edge_falsified:
            n1_original_count = g._nodes["n1"].falsified_count
            g._nodes["n1"].falsified_count = n1_original_count + 2  # simulate 2 extra
            expected = g._nodes["n1"].falsified_count
            mgr.save("sess_fc", g, _make_recall())
            g2 = CognitiveStateGraph()
            r2 = HebbianRecall(dim=64)
            mgr.restore("sess_fc", g2, r2)
            # Restored falsified_count should be >= expected (edge re-added increments too)
            assert g2._nodes["n1"].falsified_count >= expected
        finally:
            _rm(d)


# ---------------------------------------------------------------------------
# LessonStore Tests (Gate 7)
# ---------------------------------------------------------------------------


class TestLessonStore:
    def test_promote_verified_accepted(self):
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_a", content="The sky is blue.",
                evidence_class=EvidenceClass.VERIFIED_RESULT, confidence=0.82, provenance={},
            )
            assert lesson is not None
            assert lesson.evidence_class == EvidenceClass.VERIFIED_RESULT.name
        finally:
            _rm(d)

    def test_promote_fast_signal_rejected(self):
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_a", content="Guessed fact.",
                evidence_class=EvidenceClass.FAST_SIGNAL, confidence=0.2, provenance={},
            )
            assert lesson is None
        finally:
            _rm(d)

    def test_promote_provisional_rejected(self):
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_a", content="Probably true.",
                evidence_class=EvidenceClass.PROVISIONAL_RESULT, confidence=0.55, provenance={},
            )
            assert lesson is None
        finally:
            _rm(d)

    def test_lessons_persisted_across_instances(self):
        d = _mktemp()
        p = d / "lessons.jsonl"
        try:
            s1 = LessonStore(store_path=p)
            lesson = s1.promote(
                session_id="sess_b", content="Persistent fact.",
                evidence_class=EvidenceClass.VERIFIED_RESULT, confidence=0.9, provenance={},
            )
            assert lesson is not None
            s2 = LessonStore(store_path=p)
            active = s2.list_active()
            assert any(x.lesson_id == lesson.lesson_id for x in active)
        finally:
            _rm(d)

    def test_isolate_marks_lesson(self):
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_c", content="Old fact.",
                evidence_class=EvidenceClass.VERIFIED_RESULT, confidence=0.75, provenance={},
            )
            assert lesson is not None
            ok = store.isolate(lesson.lesson_id, reason="Superseded.")
            assert ok
            got = store.get(lesson.lesson_id)
            assert got is not None
            assert got.is_isolated
        finally:
            _rm(d)

    def test_list_active_excludes_isolated(self):
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            l1 = store.promote(
                session_id="sess_d", content="Active fact.",
                evidence_class=EvidenceClass.VERIFIED_RESULT, confidence=0.8, provenance={},
            )
            l2 = store.promote(
                session_id="sess_d", content="Soon isolated.",
                evidence_class=EvidenceClass.VERIFIED_RESULT, confidence=0.75, provenance={},
            )
            store.isolate(l2.lesson_id, "outdated")
            active = store.list_active()
            ids = [x.lesson_id for x in active]
            assert l1.lesson_id in ids
            assert l2.lesson_id not in ids
        finally:
            _rm(d)

    def test_count_accurate(self):
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            for i in range(3):
                store.promote(
                    session_id="count_sess", content=f"Fact {i}",
                    evidence_class=EvidenceClass.VERIFIED_RESULT, confidence=0.8, provenance={},
                )
            counts = store.count()
            assert counts["total"] == 3
            assert counts["active"] == 3
            assert counts["isolated"] == 0
        finally:
            _rm(d)
