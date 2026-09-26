"""Dream → 2brain durable-lesson e2e harness (Gate 7).

Proves the learning-safety path end to end on a real filesystem:

  1. Gate 7 promotion fixtures through LessonStore.promote():
       - VERIFIED_RESULT + complete evidence packet  → ACCEPTED
       - FAST_SIGNAL / PROVISIONAL_RESULT            → REJECTED (evidence_class)
       - incomplete evidence packet                  → REJECTED (evidence_packet)
  2. Sync accepted lesson to a brain root (2brain layout):
       <brain>/projects/vivy-v5/lessons/lessons_<ts>.jsonl
       <brain>/projects/vivy-v5/durable_decisions.md
       <brain>/hot-memory/vivy_sync_receipts.jsonl
  3. Optional Dream cycle journal to <brain>/hot-memory/.

Gate 7 (vivyChatGPT ACCEPTANCE_GATES.md):
    "Unverified output cannot become durable knowledge. Promotion records
    provenance, scope, confidence, and validation."

Gate 9: receipts are labelled TESTED_MECHANISM. This is a filesystem e2e on a
temp (or explicit) brain path — it is NOT a live-model accuracy claim, NOT a
latency claim, and NOT a production-readiness claim.

Changelog:
    23/09/2026 (Claude Code — P4 Dream → 2brain durable-lesson e2e): Initial.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from integration.evidence import evidence_from_mapping
from integration.lesson_store import LessonStore
from orchestrator.graph_bridge import EvidenceClass

GATE7_STATUS_LABEL = "TESTED_MECHANISM"
GATE7_PROTOCOL = (
    "Gate 7 learning-safety e2e: LessonStore.promote accept/reject fixtures "
    "+ sync_2brain durable-lesson layout (mechanism, not live-model)"
)


def _complete_evidence(session_id: str = "sess_p4_e2e", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "claim": "P4 e2e: durable lesson path records provenance",
        "evidence_ids": ["ev_p4_1"],
        "source": "dream_lesson_e2e",
        "expected_evidence": "lesson present in 2brain durable_decisions.md",
        "actual_observation": "lesson_id listed under VERIFIED_RESULT section",
        "acceptance": "ACCEPTED",
        "confidence": 0.9,
        "limits": "mechanism TESTED on temp brain path; not live-model",
        "task_id": "p4_e2e",
        "session_id": session_id,
        "state_hash": "hash_p4_abc",
    }
    base.update(overrides)
    return base


def _provenance(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "evidence": evidence if evidence is not None else _complete_evidence(),
        "node_ids": ["hyp_p4_1"],
        "rounds": 1,
    }


@dataclass
class Gate7CaseRecord:
    """One promotion attempt in the e2e."""

    name: str
    evidence_class: str
    accepted: bool
    lesson_id: str | None = None
    reject_reason: str | None = None
    scope: str = ""
    confidence: float = 0.0


@dataclass
class DreamLessonE2EReceipt:
    """Receipt for a Dream → 2brain durable-lesson e2e run."""

    gate7_verdict: str
    n_accepted: int
    n_rejected: int
    protocol: str
    generated_at: str
    status_label: str
    synced_2brain: bool
    synced_lesson_ids: list[str] = field(default_factory=list)
    accepted: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    cases: list[dict[str, Any]] = field(default_factory=list)
    brain_path: str = ""
    store_path: str = ""
    synced_files: list[str] = field(default_factory=list)

    @property
    def gate7_pass(self) -> bool:
        return self.gate7_verdict == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_e2e(
    store_path: str | Path,
    brain_path: str | Path,
    *,
    skip_promotion: bool = False,
    with_dream_cycle: bool = False,
) -> DreamLessonE2EReceipt:
    """Run the Gate 7 e2e: promote fixtures (unless skipped), sync, build receipt.

    Parameters
    ----------
    store_path:
        JSONL lesson store path (created on first promote).
    brain_path:
        2brain root to sync into (temp dir in tests, ``D:\\2brain`` in ops).
    skip_promotion:
        When True, do not run the built-in fixtures — sync whatever is already
        in ``store_path`` (used by callers that promoted their own lessons).
    with_dream_cycle:
        When True, also run a VivyDreamCycle against ``brain_path`` so the
        hot-memory dream journal is part of the same e2e receipt.
    """
    store_path = Path(store_path)
    brain_path = Path(brain_path)
    store = LessonStore(store_path)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    cases: list[Gate7CaseRecord] = []

    if not skip_promotion:
        # --- Gate 7 fixture matrix ---
        # 1. ACCEPT: VERIFIED_RESULT + complete evidence packet
        ev_ok = _complete_evidence()
        packet_ok = evidence_from_mapping(ev_ok)
        lesson = store.promote(
            session_id="sess_p4_e2e",
            content="Durable lesson body",
            evidence_class=EvidenceClass.VERIFIED_RESULT,
            confidence=0.9,
            provenance=_provenance(ev_ok),
            scope="p4_e2e",
        )
        if lesson is not None:
            accepted.append(
                {
                    "lesson_id": lesson.lesson_id,
                    "scope": lesson.scope,
                    "confidence": lesson.confidence,
                    "provenance": lesson.provenance,
                    "validation": {
                        "valid_for_promotion": packet_ok.valid_for_promotion(),
                        "evidence_class": lesson.evidence_class,
                        "has_evidence_packet": "evidence" in lesson.provenance,
                    },
                }
            )
            cases.append(
                Gate7CaseRecord(
                    name="verified_full_evidence",
                    evidence_class="VERIFIED_RESULT",
                    accepted=True,
                    lesson_id=lesson.lesson_id,
                    scope=lesson.scope,
                    confidence=lesson.confidence,
                )
            )
        else:
            cases.append(
                Gate7CaseRecord(
                    name="verified_full_evidence",
                    evidence_class="VERIFIED_RESULT",
                    accepted=False,
                    reject_reason="unexpected_reject",
                )
            )
            rejected.append(
                {"name": "verified_full_evidence", "reject_reason": "unexpected_reject"}
            )

        # 2-3. REJECT by evidence_class
        for name, cls, reason in (
            ("fast_signal", EvidenceClass.FAST_SIGNAL, "evidence_class"),
            ("provisional_result", EvidenceClass.PROVISIONAL_RESULT, "evidence_class"),
        ):
            before = store.count()["total"]
            out = store.promote(
                session_id="sess_p4_e2e",
                content=f"claim-{name}",
                evidence_class=cls,
                confidence=0.5,
                provenance=_provenance(_complete_evidence()),
            )
            after = store.count()["total"]
            ok_reject = out is None and after == before
            cases.append(
                Gate7CaseRecord(
                    name=name,
                    evidence_class=cls.name,
                    accepted=out is not None,
                    lesson_id=out.lesson_id if out else None,
                    reject_reason=None if out else reason,
                )
            )
            rejected.append(
                {
                    "name": name,
                    "reject_reason": reason if ok_reject else "unexpected_accept",
                }
            )

        # 4. REJECT by incomplete evidence packet (even with VERIFIED_RESULT)
        bad_ev = _complete_evidence(claim="", actual_observation="")
        before = store.count()["total"]
        out = store.promote(
            session_id="sess_p4_e2e",
            content="half-baked claim",
            evidence_class=EvidenceClass.VERIFIED_RESULT,
            confidence=0.9,
            provenance=_provenance(bad_ev),
        )
        after = store.count()["total"]
        ok_reject = out is None and after == before
        cases.append(
            Gate7CaseRecord(
                name="verified_incomplete_evidence",
                evidence_class="VERIFIED_RESULT",
                accepted=out is not None,
                lesson_id=out.lesson_id if out else None,
                reject_reason=None if out else "evidence_packet",
            )
        )
        rejected.append(
            {
                "name": "verified_incomplete_evidence",
                "reject_reason": "evidence_packet" if ok_reject else "unexpected_accept",
            }
        )
    else:
        # Caller already promoted — harvest what is in the store.
        for lesson in store.list_active():
            accepted.append(
                {
                    "lesson_id": lesson.lesson_id,
                    "scope": lesson.scope,
                    "confidence": lesson.confidence,
                    "provenance": lesson.provenance,
                    "validation": {
                        "valid_for_promotion": evidence_from_mapping(
                            lesson.provenance.get("evidence", {})
                        ).valid_for_promotion()
                        if "evidence" in lesson.provenance
                        else False,
                        "evidence_class": lesson.evidence_class,
                        "has_evidence_packet": "evidence" in lesson.provenance,
                    },
                }
            )
            cases.append(
                Gate7CaseRecord(
                    name="pre_promoted",
                    evidence_class=lesson.evidence_class,
                    accepted=True,
                    lesson_id=lesson.lesson_id,
                    scope=lesson.scope,
                    confidence=lesson.confidence,
                )
            )

    # --- Sync to 2brain layout ---
    synced_2brain = False
    synced_files: list[str] = []
    synced_lesson_ids = [a["lesson_id"] for a in accepted]
    try:
        # Import lazily so the harness stays importable without scripts/ on path.
        import sys

        core_root = Path(__file__).resolve().parent.parent
        if str(core_root) not in sys.path:
            sys.path.insert(0, str(core_root))
        from scripts.sync_2brain import (
            sync_lessons,
            update_hot_memory,
            write_durable_decisions,
        )

        vivy_v5 = brain_path / "projects" / "vivy-v5"
        lessons_dst = vivy_v5 / "lessons"
        hot_memory = brain_path / "hot-memory"

        brain_path.mkdir(parents=True, exist_ok=True)
        n_synced = sync_lessons(store_path, lessons_dst) if store_path.exists() else 0
        write_durable_decisions(store_path, vivy_v5)
        # Point hot-memory receipt at the requested brain root.
        update_hot_memory(n_synced, hot_memory_dir=hot_memory)

        for p in (
            vivy_v5 / "durable_decisions.md",
            hot_memory / "vivy_sync_receipts.jsonl",
        ):
            if p.exists():
                synced_files.append(str(p))
        if lessons_dst.exists():
            for p in sorted(lessons_dst.glob("lessons_*.jsonl")):
                synced_files.append(str(p))

        synced_2brain = (vivy_v5 / "durable_decisions.md").exists()
    except Exception as e:  # fail-closed: never report a false sync
        synced_2brain = False
        synced_files.append(f"SYNC_ERROR: {e}")

    # --- Optional Dream journal ---
    if with_dream_cycle:
        try:
            from engine.dream_engine import VivyDreamEngine

            engine = VivyDreamEngine(brain_path=str(brain_path))
            try:
                dream = engine.run_dream_cycle(task_id="p4_e2e")
                if dream.synced_2brain:
                    journal = brain_path / "hot-memory" / "durable-learning-dream-cycle-latest.md"
                    if journal.exists():
                        synced_files.append(str(journal))
            finally:
                engine.context_memory.close()
                engine.score_graph.destroy()
        except Exception as e:  # pragma: no cover - dream is optional in e2e
            synced_files.append(f"DREAM_ERROR: {e}")

    # --- Verdict ---
    # E2E spans Gate 7 (promotion safety) AND the 2brain landing. If either
    # side fails the verdict is FAIL — fail-closed, no partial credit.
    expected_accept = 1 if not skip_promotion else len(accepted)
    n_accepted = len(accepted)
    n_rejected = len(rejected)
    reject_ok = all(r.get("reject_reason") in {"evidence_class", "evidence_packet"} for r in rejected)
    accept_ok = n_accepted == expected_accept and all(a["lesson_id"] for a in accepted)
    if skip_promotion:
        promotion_ok = accept_ok
    else:
        promotion_ok = accept_ok and reject_ok
    gate7_pass = promotion_ok and synced_2brain
    gate7_verdict = "PASS" if gate7_pass else "FAIL"

    return DreamLessonE2EReceipt(
        gate7_verdict=gate7_verdict,
        n_accepted=n_accepted,
        n_rejected=n_rejected,
        protocol=GATE7_PROTOCOL,
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        status_label=GATE7_STATUS_LABEL,
        synced_2brain=synced_2brain,
        synced_lesson_ids=synced_lesson_ids,
        accepted=accepted,
        rejected=rejected,
        cases=[asdict(c) for c in cases],
        brain_path=str(brain_path),
        store_path=str(store_path),
        synced_files=synced_files,
    )


def write_receipt(receipt: DreamLessonE2EReceipt, path: str | Path) -> str:
    """Write receipt JSON to path. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return str(path)


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Dream → 2brain durable-lesson e2e (Gate 7)"
    )
    parser.add_argument("--store", default="vivy_lessons.jsonl")
    parser.add_argument("--brain", default=r"D:\2brain")
    parser.add_argument("--output", default="", help="Write receipt JSON to this path")
    parser.add_argument("--with-dream-cycle", action="store_true")
    args = parser.parse_args()

    receipt = run_e2e(
        store_path=args.store,
        brain_path=args.brain,
        with_dream_cycle=args.with_dream_cycle,
    )
    print(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
    print(
        f"\nGate 7 verdict={receipt.gate7_verdict} "
        f"accepted={receipt.n_accepted} rejected={receipt.n_rejected} "
        f"synced_2brain={receipt.synced_2brain}"
    )
    print(f"status_label={receipt.status_label}")
    if args.output:
        write_receipt(receipt, args.output)
        print(f"receipt → {args.output}")
    return 0 if receipt.gate7_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
