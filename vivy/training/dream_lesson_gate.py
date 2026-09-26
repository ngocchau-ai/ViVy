"""C11.4 — Dream accepts only verified, in-scope evidence.

Rejects incomplete packets, FAST_SIGNAL / PROVISIONAL_RESULT, duplicates,
stale versions, poisoned text, and contradictory lessons in the same scope.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Sequence


REQUIRED_EVIDENCE_CLASS = "VERIFIED_RESULT"

REQUIRED_PACKET_FIELDS = (
    "claim",
    "evidence_ids",
    "source",
    "expected_evidence",
    "actual_observation",
    "acceptance",
    "limits",
    "task_id",
    "session_id",
    "state_hash",
)

_POISON_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "ignore prior instructions",
    "disregard previous",
    "disregard prior",
    "grant execute_directly",
    "execute_directly",
    "override safety",
    "disable evidence gate",
    "you are now",
    "<|system|>",
    "### system",
)

_POLARITY_PAIRS = (
    ("always", "never"),
    ("must not", "must"),
    ("should not", "should"),
    ("prefer", "avoid"),
    ("allow", "forbid"),
)


@dataclass(frozen=True)
class LessonCandidate:
    lesson_id: str
    evidence_class: str
    scope: str
    confidence: float
    claim: str
    evidence_ids: Sequence[str]
    source: str
    expected_evidence: str
    actual_observation: str
    acceptance: str
    limits: str
    task_id: str
    session_id: str
    state_hash: str
    created_at_ms: int
    content_hash: str


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    return False


def _packet_complete(lesson: LessonCandidate) -> bool:
    for name in REQUIRED_PACKET_FIELDS:
        if _is_blank(getattr(lesson, name, None)):
            return False
    return True


def _poisoned(lesson: LessonCandidate) -> bool:
    blob = " ".join(
        str(getattr(lesson, name, "") or "")
        for name in ("claim", "expected_evidence", "actual_observation", "limits", "source")
    ).lower()
    return any(marker in blob for marker in _POISON_MARKERS)


def _polarity_core(text: str) -> tuple[str, str]:
    t = " " + text.lower().strip() + " "
    for pos, neg in _POLARITY_PAIRS:
        for first, second in ((pos, neg), (neg, pos)):
            if f" {first} " in t and f" {second} " not in t.replace(f" {first} ", " "):
                core = t
                for word in (pos, neg):
                    core = core.replace(f" {word} ", " ")
                return first, " ".join(core.split())
    return "", " ".join(t.split())


def _contradictory(a: LessonCandidate, b: LessonCandidate) -> bool:
    if a.scope != b.scope or not a.scope:
        return False
    pol_a, core_a = _polarity_core(a.claim)
    pol_b, core_b = _polarity_core(b.claim)
    if not pol_a or not pol_b or pol_a == pol_b:
        return False
    return bool(core_a) and core_a == core_b


def evaluate_lesson(lesson: LessonCandidate, *, existing: Sequence[LessonCandidate], now_ms: int) -> dict:
    """Return {"decision": "accept"|"reject", "reason": <gate name> | "ok"}."""
    del now_ms  # reserved for future TTL-on-lessons; gate is content-based today

    if _is_blank(lesson.scope):
        return {"decision": "reject", "reason": "scope"}
    if lesson.evidence_class != REQUIRED_EVIDENCE_CLASS:
        return {"decision": "reject", "reason": "evidence_class"}
    if not _packet_complete(lesson):
        return {"decision": "reject", "reason": "evidence_packet"}
    if _poisoned(lesson):
        return {"decision": "reject", "reason": "poisoned_text"}

    for prior in existing:
        if prior.content_hash and prior.content_hash == lesson.content_hash:
            return {"decision": "reject", "reason": "duplicate"}

    for prior in existing:
        if prior.lesson_id == lesson.lesson_id and prior.created_at_ms > lesson.created_at_ms:
            return {"decision": "reject", "reason": "stale"}

    for prior in existing:
        if _contradictory(prior, lesson):
            return {"decision": "reject", "reason": "contradictory"}

    return {"decision": "accept", "reason": "ok"}
