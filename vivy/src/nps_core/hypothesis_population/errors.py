"""Domain exceptions for the hypothesis population lifecycle.

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
    """A ThoughtState field or relation fails structural or value validation."""


class DuplicateIdError(ThoughtStateError):
    """A duplicate thought_id or event_id was detected."""


class UnknownReferenceError(ThoughtStateError):
    """A referenced thought_id does not exist."""


class SelfReferenceError(ThoughtStateError):
    """A relation references the same thought at both endpoints."""

    def __init__(
        self,
        message: str,
        *,
        thought_id: str | None = None,
        relation_type: str | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message, thought_id=thought_id, path=path)
        self.relation_type = relation_type


class CycleDetectedError(ThoughtStateError):
    """A cycle was detected in the lineage graph."""


class InvalidTransitionError(ThoughtStateError):
    """A lifecycle transition violates the state machine rules."""


class InvalidDispositionError(ThoughtStateError):
    """An invalid prune disposition was supplied."""


class TerminalStateError(ThoughtStateError):
    """The target thought is in a terminal state."""


class MergeSourceError(ThoughtStateError):
    """The merge source_ids are invalid."""


class DuplicateEventError(ThoughtStateError):
    """A duplicate event_id was detected."""
