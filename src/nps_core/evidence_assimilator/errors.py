"""Domain exceptions for evidence assimilation.

All exceptions are deterministic and carry no nondeterministic data.
"""

from __future__ import annotations

__all__ = [
    "EvidenceError",
    "PacketValidationError",
    "ImpactValidationError",
    "PlanValidationError",
]


class EvidenceError(ValueError):
    """Stable base domain exception for evidence assimilation errors."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        evidence_id: str | None = None,
        thought_id: str | None = None,
    ) -> None:
        self.message = message
        self.path = path
        self.evidence_id = evidence_id
        self.thought_id = thought_id
        rendered = message
        if evidence_id is not None:
            rendered = f"evidence_id={evidence_id}: {rendered}"
        if thought_id is not None:
            rendered = f"thought_id={thought_id}: {rendered}"
        if path is not None:
            rendered = f"path={path}: {rendered}"
        super().__init__(rendered)


class PacketValidationError(EvidenceError):
    """EvidencePacket fails structural or value validation."""


class ImpactValidationError(EvidenceError):
    """EvidenceImpact classification or target set is invalid."""


class PlanValidationError(EvidenceError):
    """Assimilation plan fails structural or value validation."""
