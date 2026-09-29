"""
LessonStore -- ViVy Sprint 4 (Gate 5+7: Durability + Learning Safety).

Durable lesson storage voi epistemic gate:
    CHI co EvidenceClass.VERIFIED_RESULT moi duoc phep promote thanh durable lesson.
    PROVISIONAL va FAST_SIGNAL bi reject tai promote gate.

Mirrors vivyChatGPT Gate 7 (Learning Safety):
    "Unverified output cannot become durable knowledge."
    "Promotion records provenance, scope, confidence, and validation."

Storage format: JSONL, one lesson per line.
    Append-only (immutable lessons -- consistent with Document Immutability Rule).
    No deletion -- only ISOLATED/DEPRECATED marking.

Changelog:
    21/09/2026 (Antigravity IDE, Sprint 4 -- Gate 5+7): Initial.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from integration.evidence import evidence_from_mapping
from orchestrator.graph_bridge import EvidenceClass

logger = logging.getLogger(__name__)


@dataclass
class Lesson:
    """A durable, verified piece of knowledge.

    Attributes
    ----------
    lesson_id : Unique ID.
    session_id : Session that produced this lesson.
    content : Human-readable lesson text.
    evidence_class : MUST be VERIFIED_RESULT to be stored.
    confidence : Float [0, 1] from multi-stream calibration.
    provenance : Source: node_id(s), task context, inference round.
    created_at : Unix timestamp.
    scope : Topic/domain tag for search.
    is_isolated : True if deprecated (never deleted -- Document Immutability).
    isolation_reason : Why it was isolated.
    """

    lesson_id: str
    session_id: str
    content: str
    evidence_class: str          # EvidenceClass.name
    confidence: float
    provenance: dict[str, Any]
    created_at: float
    scope: str = "general"
    is_isolated: bool = False
    isolation_reason: str = ""


class LessonStore:
    """Append-only durable lesson store with VERIFIED_RESULT gate.

    Gate 7 enforcement:
        promote() rejects any lesson with evidence_class != VERIFIED_RESULT.
        This is NOT a soft warning -- it's a hard reject with receipt.

    Document Immutability:
        Lessons are never deleted. To deprecate, call isolate().
        The JSONL file is append-only.

    Parameters
    ----------
    store_path : Path to the JSONL lesson store file.
    """

    def __init__(
        self,
        store_path: Path | str = Path("vivy_lessons.jsonl"),
    ) -> None:
        self._path = Path(store_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("LessonStore: path=%s", self._path)

    def promote(
        self,
        session_id: str,
        content: str,
        evidence_class: EvidenceClass,
        confidence: float,
        provenance: dict[str, Any],
        scope: str = "general",
    ) -> Lesson | None:
        """Promote a result to durable lesson storage.

        Gate 7 (Learning Safety) hard enforcement:
            Only EvidenceClass.VERIFIED_RESULT is accepted.
            FAST_SIGNAL and PROVISIONAL_RESULT are rejected with a log receipt.

        CRITICAL: This boundary mirrors vivyChatGPT Gate 7:
            "Unverified output cannot become durable knowledge."
            Process success (tool returned 200) != semantic correctness != durable knowledge.

        Parameters
        ----------
        session_id : Session that produced this result.
        content : What was learned (human-readable).
        evidence_class : Epistemic weight -- MUST be VERIFIED_RESULT.
        confidence : Min-stream confidence (from calibrate_multi_stream_confidence).
        provenance : Dict with node_ids, task_context, rounds, etc.
        scope : Topic tag.

        Returns
        -------
        Lesson if promoted, None if rejected.
        """
        if evidence_class != EvidenceClass.VERIFIED_RESULT:
            logger.warning(
                "LessonStore.promote: REJECTED -- evidence_class=%s (need VERIFIED_RESULT). "
                "session=%s content=%.60s",
                evidence_class.name,
                session_id[:8],
                content,
            )
            return None

        # [REPLACED 29/09/2026] WP-8.  The old body validated ``provenance["evidence"]``
        # only *when that key was present*, so ``promote(..., provenance={})``
        # sailed through.  That is a wrong promotion: Gate 7 requires the
        # promotion to record provenance and validation, and T8 asks for zero
        # wrong promotions on replay.  Missing evidence is now the same reject
        # as incomplete evidence -- fail-closed, not fail-open.
        if "evidence" not in provenance:
            logger.warning(
                "LessonStore.promote: REJECTED -- provenance carries no evidence "
                "(Gate 7 requires provenance + validation on every promotion). "
                "session=%s content=%.60s",
                session_id[:8],
                content,
            )
            return None
        packet = evidence_from_mapping(provenance.get("evidence", {}))
        if not packet.valid_for_promotion():
            logger.warning("LessonStore.promote: REJECTED -- incomplete independent evidence")
            return None

        lesson = Lesson(
            lesson_id=uuid.uuid4().hex[:16],
            session_id=session_id,
            content=content,
            evidence_class=evidence_class.name,
            confidence=confidence,
            provenance=provenance,
            created_at=time.time(),
            scope=scope,
        )

        self._append(lesson)
        logger.info(
            "LessonStore.promote: ACCEPTED lesson=%s conf=%.3f scope=%s session=%s",
            lesson.lesson_id, confidence, scope, session_id[:8],
        )
        return lesson

    def isolate(
        self,
        lesson_id: str,
        reason: str,
    ) -> bool:
        """Mark a lesson as isolated (deprecated) -- never deleted.

        Document Immutability Rule: lessons are append-only.
        Isolation appends a new record with is_isolated=True.

        Returns True if the original lesson was found and isolation record written.
        """
        original = self.get(lesson_id)
        if original is None:
            logger.warning("LessonStore.isolate: lesson %s not found", lesson_id)
            return False

        isolated = Lesson(
            lesson_id=original.lesson_id,
            session_id=original.session_id,
            content=original.content,
            evidence_class=original.evidence_class,
            confidence=original.confidence,
            provenance=original.provenance,
            created_at=original.created_at,
            scope=original.scope,
            is_isolated=True,
            isolation_reason=f"[ISOLATED] {reason}",
        )
        self._append(isolated)
        logger.info("LessonStore.isolate: lesson=%s reason=%s", lesson_id, reason[:60])
        return True

    def get(self, lesson_id: str) -> Lesson | None:
        """Retrieve a lesson by ID (latest version -- may be isolated)."""
        result: Lesson | None = None
        if not self._path.exists():
            return None
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if d.get("lesson_id") == lesson_id:
                        result = Lesson(**d)
                except Exception:  # noqa: BLE001
                    continue
        return result

    def list_active(self, scope: str | None = None) -> list[Lesson]:
        """List all active (non-isolated) lessons, optionally filtered by scope."""
        seen: dict[str, Lesson] = {}
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    lesson = Lesson(**d)
                    seen[lesson.lesson_id] = lesson  # last write wins
                except Exception:  # noqa: BLE001
                    continue
        active = [x for x in seen.values() if not x.is_isolated]
        if scope:
            active = [x for x in active if x.scope == scope]
        return sorted(active, key=lambda x: x.created_at, reverse=True)

    def count(self) -> dict[str, int]:
        """Return counts: total, active, isolated."""
        seen: dict[str, Lesson] = {}
        if not self._path.exists():
            return {"total": 0, "active": 0, "isolated": 0}
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    seen[d["lesson_id"]] = Lesson(**d)
                except Exception:  # noqa: BLE001
                    continue
        active = sum(1 for x in seen.values() if not x.is_isolated)
        isolated = sum(1 for x in seen.values() if x.is_isolated)
        return {"total": len(seen), "active": active, "isolated": isolated}

    def _append(self, lesson: Lesson) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(lesson)) + "\n")
