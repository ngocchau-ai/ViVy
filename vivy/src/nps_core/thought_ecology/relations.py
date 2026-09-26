"""Frozen typed relations for the thought ecology graph.

All relations are immutable, slotted, and carry deterministic metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from nps_core.thought_ecology.errors import (
    EcologyValidationError,
    SelfReferenceError,
)

__all__ = [
    "DependencyEdge",
    "ContradictionEdge",
    "OverlapEdge",
    "SharedAssumptionLink",
    "EvidencePlacement",
]

_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")
_VALID_BUCKETS = frozenset({"supporting", "opposing", "unresolved"})


def _validate_thought_id(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise EcologyValidationError(
            f"{field} must be a string",
            path=field,
        )
    if not _THOUGHT_ID_RE.match(value):
        raise EcologyValidationError(
            f"{field} must match THOUGHT-* pattern",
            path=field,
        )
    return value


def _validate_non_empty_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise EcologyValidationError(
            f"{field} must be a string",
            path=field,
        )
    if not value or value.isspace():
        raise EcologyValidationError(
            f"{field} must be non-empty",
            path=field,
        )
    return value


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    """Return the canonical undirected endpoint order."""
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """Directed dependency edge: source depends on target."""

    source_id: str
    target_id: str

    def __post_init__(self) -> None:
        src = _validate_thought_id(self.source_id, field="source_id")
        tgt = _validate_thought_id(self.target_id, field="target_id")
        if src == tgt:
            raise SelfReferenceError(
                "DependencyEdge cannot reference the same thought",
                thought_id=src,
                relation_type="DependencyEdge",
            )
        object.__setattr__(self, "source_id", src)
        object.__setattr__(self, "target_id", tgt)

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "target_id": self.target_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencyEdge:
        if not isinstance(data, dict):
            raise EcologyValidationError("DependencyEdge.from_dict requires a dict")
        if set(data.keys()) != {"source_id", "target_id"}:
            raise EcologyValidationError(
                "DependencyEdge.from_dict requires exactly 'source_id' and 'target_id' keys"
            )
        return cls(source_id=data["source_id"], target_id=data["target_id"])


@dataclass(frozen=True, slots=True)
class ContradictionEdge:
    """Undirected contradiction edge between two thoughts."""

    first_id: str
    second_id: str

    def __post_init__(self) -> None:
        a = _validate_thought_id(self.first_id, field="first_id")
        b = _validate_thought_id(self.second_id, field="second_id")
        if a == b:
            raise SelfReferenceError(
                "ContradictionEdge cannot reference the same thought",
                thought_id=a,
                relation_type="ContradictionEdge",
            )
        canon = _canonical_pair(a, b)
        object.__setattr__(self, "first_id", canon[0])
        object.__setattr__(self, "second_id", canon[1])

    def to_dict(self) -> dict[str, Any]:
        return {"first_id": self.first_id, "second_id": self.second_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContradictionEdge:
        if not isinstance(data, dict):
            raise EcologyValidationError("ContradictionEdge.from_dict requires a dict")
        if set(data.keys()) != {"first_id", "second_id"}:
            raise EcologyValidationError(
                "ContradictionEdge.from_dict requires exactly 'first_id' and 'second_id' keys"
            )
        return cls(first_id=data["first_id"], second_id=data["second_id"])


@dataclass(frozen=True, slots=True)
class OverlapEdge:
    """Undirected overlap edge between two thoughts."""

    first_id: str
    second_id: str

    def __post_init__(self) -> None:
        a = _validate_thought_id(self.first_id, field="first_id")
        b = _validate_thought_id(self.second_id, field="second_id")
        if a == b:
            raise SelfReferenceError(
                "OverlapEdge cannot reference the same thought",
                thought_id=a,
                relation_type="OverlapEdge",
            )
        canon = _canonical_pair(a, b)
        object.__setattr__(self, "first_id", canon[0])
        object.__setattr__(self, "second_id", canon[1])

    def to_dict(self) -> dict[str, Any]:
        return {"first_id": self.first_id, "second_id": self.second_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OverlapEdge:
        if not isinstance(data, dict):
            raise EcologyValidationError("OverlapEdge.from_dict requires a dict")
        if set(data.keys()) != {"first_id", "second_id"}:
            raise EcologyValidationError(
                "OverlapEdge.from_dict requires exactly 'first_id' and 'second_id' keys"
            )
        return cls(first_id=data["first_id"], second_id=data["second_id"])


@dataclass(frozen=True, slots=True)
class SharedAssumptionLink:
    """Link between two thoughts sharing an assumption with identical payload."""

    assumption_id: str
    first_thought_id: str
    second_thought_id: str

    def __post_init__(self) -> None:
        aid = _validate_non_empty_str(self.assumption_id, field="assumption_id")
        a = _validate_thought_id(self.first_thought_id, field="first_thought_id")
        b = _validate_thought_id(self.second_thought_id, field="second_thought_id")
        if a == b:
            raise SelfReferenceError(
                "SharedAssumptionLink cannot reference the same thought",
                thought_id=a,
                relation_type="SharedAssumptionLink",
            )
        canon = _canonical_pair(a, b)
        object.__setattr__(self, "assumption_id", aid)
        object.__setattr__(self, "first_thought_id", canon[0])
        object.__setattr__(self, "second_thought_id", canon[1])

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "first_thought_id": self.first_thought_id,
            "second_thought_id": self.second_thought_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SharedAssumptionLink:
        if not isinstance(data, dict):
            raise EcologyValidationError("SharedAssumptionLink.from_dict requires a dict")
        if set(data.keys()) != {"assumption_id", "first_thought_id", "second_thought_id"}:
            raise EcologyValidationError(
                "SharedAssumptionLink.from_dict requires exactly 'assumption_id', 'first_thought_id', and 'second_thought_id' keys"
            )
        return cls(
            assumption_id=data["assumption_id"],
            first_thought_id=data["first_thought_id"],
            second_thought_id=data["second_thought_id"],
        )


@dataclass(frozen=True, slots=True)
class EvidencePlacement:
    """Placement of an evidence ID into a bucket for a thought."""

    evidence_id: str
    thought_id: str
    bucket: str

    def __post_init__(self) -> None:
        eid = _validate_non_empty_str(self.evidence_id, field="evidence_id")
        tid = _validate_thought_id(self.thought_id, field="thought_id")
        if not isinstance(self.bucket, str):
            raise EcologyValidationError(
                "bucket must be a string",
                path="bucket",
            )
        if self.bucket not in _VALID_BUCKETS:
            raise EcologyValidationError(
                f"bucket must be one of {sorted(_VALID_BUCKETS)}",
                path="bucket",
            )
        object.__setattr__(self, "evidence_id", eid)
        object.__setattr__(self, "thought_id", tid)
        object.__setattr__(self, "bucket", self.bucket)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "thought_id": self.thought_id,
            "bucket": self.bucket,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidencePlacement:
        if not isinstance(data, dict):
            raise EcologyValidationError("EvidencePlacement.from_dict requires a dict")
        if set(data.keys()) != {"evidence_id", "thought_id", "bucket"}:
            raise EcologyValidationError(
                "EvidencePlacement.from_dict requires exactly 'evidence_id', 'thought_id', and 'bucket' keys"
            )
        return cls(
            evidence_id=data["evidence_id"],
            thought_id=data["thought_id"],
            bucket=data["bucket"],
        )
