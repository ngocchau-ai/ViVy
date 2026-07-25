"""Domain exceptions for the atomic state update engine.

All exceptions are deterministic and carry no nondeterministic data.
"""

from __future__ import annotations

__all__ = [
    "StateUpdateError",
    "ReplacementValidationError",
    "TargetMismatchError",
    "InvalidRecordError",
]


class StateUpdateError(ValueError):
    """Stable base domain exception for state update errors."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        thought_id: str | None = None,
    ) -> None:
        self.message = message
        self.path = path
        self.thought_id = thought_id
        rendered = message
        if thought_id is not None:
            rendered = f"thought_id={thought_id}: {rendered}"
        if path is not None:
            rendered = f"path={path}: {rendered}"
        super().__init__(rendered)


class ReplacementValidationError(StateUpdateError):
    """A replacement ThoughtState fails validation."""


class TargetMismatchError(StateUpdateError):
    """The replacement key set does not match the plan targets."""


class InvalidRecordError(StateUpdateError):
    """The EvidenceUpdateRecord metadata is invalid."""
