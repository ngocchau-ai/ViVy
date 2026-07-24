"""Domain exceptions for the ThoughtState lifecycle.

All exceptions are deterministic and carry no nondeterministic data.
"""

from __future__ import annotations

__all__ = [
    "ThoughtStateError",
    "ValidationError",
    "DuplicateIdError",
    "UnknownReferenceError",
    "SelfReferenceError",
    "CycleDetectedError",
    "InvalidTransitionError",
    "InvalidDispositionError",
    "TerminalStateError",
    "MergeSourceError",
    "DuplicateEventError",
]


class ThoughtStateError(ValueError):
    """Stable base domain exception for ThoughtState lifecycle errors."""

    def __init__(
        self,
        message: str,
        *,
        thought_id: str | None = None,
        path: str | None = None,
    ) -> None:
        self.message = message
        self.thought_id = thought_id
        self.path = path
        rendered = message
        if thought_id is not None:
            rendered = f"thought_id={thought_id}: {rendered}"
        if path is not None:
            rendered = f"path={path}: {rendered}"
        super().__init__(rendered)


class ValidationError(ThoughtStateError):
    """Input fails structural or value validation."""


class DuplicateIdError(ThoughtStateError):
    """A thought ID already exists in the population."""


class UnknownReferenceError(ThoughtStateError):
    """A referenced thought ID does not exist in the population."""


class SelfReferenceError(ThoughtStateError):
    """A thought references itself in its lineage."""


class CycleDetectedError(ThoughtStateError):
    """Adding a lineage edge would create a cycle."""


class InvalidTransitionError(ThoughtStateError):
    """The requested status transition is not allowed."""


class InvalidDispositionError(ThoughtStateError):
    """The prune disposition is not ``rejected`` or ``dormant``."""


class TerminalStateError(ThoughtStateError):
    """The target thought is already in a terminal state."""


class MergeSourceError(ThoughtStateError):
    """Merge sources are duplicate, terminal, or insufficient."""


class DuplicateEventError(ThoughtStateError):
    """An audit event ID has already been recorded."""
