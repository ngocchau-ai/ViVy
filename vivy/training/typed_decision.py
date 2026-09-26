"""Minimal, provenance-aware typed decisions for ViVy training records.

Change log: Codex, 2026-09-23 — initial Laya/Verdict contract; no runtime or
model behavior is changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping


DECISION_TYPES = frozenset({"choice", "score", "noul"})
SPLITS = frozenset({"train", "dev", "test"})
_PROVENANCE_FIELDS = ("source", "producer", "receipt_id", "timestamp")


@dataclass(frozen=True)
class TypedDecision:
    """Validated JSON-shaped record used by the dataset/evaluation boundary."""

    decision_type: str
    candidates: tuple[Mapping[str, Any], ...]
    selected_candidate: str | None
    score: float | None
    confidence: float
    evidence_required: tuple[str, ...]
    provenance: Mapping[str, Any]
    split: str


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    value = float(value)
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{field} must be in [0, 1]")
    return value


def validate_typed_decision(record: Mapping[str, Any]) -> TypedDecision:
    """Validate and normalize one Laya/Verdict-style decision record."""
    if not isinstance(record, Mapping):
        raise ValueError("record must be a mapping")

    decision_type = record.get("decision_type")
    if decision_type not in DECISION_TYPES:
        raise ValueError("decision_type must be one of choice, score, noul")

    raw_candidates = record.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("candidates must be a non-empty list")
    candidates: list[Mapping[str, Any]] = []
    candidate_ids: list[str] = []
    for candidate in raw_candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("each candidate must be a mapping")
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("each candidate must have a non-empty string id")
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.append(candidate_id)
        candidates.append(candidate)

    selected = record.get("selected_candidate")
    if selected is not None and (
        not isinstance(selected, str) or selected not in candidate_ids
    ):
        raise ValueError("selected_candidate must identify a candidate or be null")

    raw_score = record.get("score")
    score = None if raw_score is None else _number(raw_score, "score")
    if decision_type == "choice" and (selected is None or score is not None):
        raise ValueError("choice requires selected_candidate and no score")
    if decision_type == "score" and (selected is None or score is None):
        raise ValueError("score requires selected_candidate and score")
    if decision_type == "noul" and (selected is not None or score is not None):
        raise ValueError("noul requires selected_candidate and score to be null")

    confidence = _number(record.get("confidence"), "confidence")

    evidence = record.get("evidence_required")
    if not isinstance(evidence, list) or any(
        not isinstance(item, str) or not item.strip() for item in evidence
    ):
        raise ValueError("evidence_required must be a list of non-empty strings")

    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping) or any(
        not isinstance(provenance.get(field), str) or not provenance[field].strip()
        for field in _PROVENANCE_FIELDS
    ):
        raise ValueError(
            "provenance must contain non-empty source, producer, receipt_id, timestamp"
        )

    split = record.get("split")
    if split not in SPLITS:
        raise ValueError("split must be one of train, dev, test")

    return TypedDecision(
        decision_type=decision_type,
        candidates=tuple(candidates),
        selected_candidate=selected,
        score=score,
        confidence=confidence,
        evidence_required=tuple(evidence),
        provenance=provenance,
        split=split,
    )


def _self_check() -> None:
    base = {
        "decision_type": "choice",
        "candidates": [{"id": "execute"}, {"id": "noul"}],
        "selected_candidate": "execute",
        "confidence": 0.8,
        "evidence_required": ["postcondition"],
        "provenance": {
            "source": "gold",
            "producer": "human",
            "receipt_id": "r-1",
            "timestamp": "2026-09-23T00:00:00Z",
        },
        "split": "dev",
    }
    assert validate_typed_decision(base).selected_candidate == "execute"
    invalid = {**base, "confidence": 1.1}
    try:
        validate_typed_decision(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range confidence must be rejected")


if __name__ == "__main__":
    _self_check()
    print("typed_decision self-check: PASS")
