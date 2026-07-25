"""Domain exceptions for the thought ecology graph.

All exceptions are deterministic and carry no nondeterministic data.
"""

from __future__ import annotations

__all__ = [
    "ThoughtEcologyError",
    "EcologyValidationError",
    "UnknownThoughtError",
    "SelfReferenceError",
    "DependencyCycleError",
    "ConflictingAssumptionError",
    "AmbiguousEvidenceBucketError",
    "SnapshotMismatchError",
]


class ThoughtEcologyError(ValueError):
    """Stable base domain exception for thought ecology errors."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
    ) -> None:
        self.message = message
        self.path = path
        rendered = message
        if path is not None:
            rendered = f"path={path}: {rendered}"
        super().__init__(rendered)


class EcologyValidationError(ThoughtEcologyError):
    """A field or relation fails structural or value validation."""


class UnknownThoughtError(ThoughtEcologyError):
    """A thought ID is not present in the snapshot."""

    def __init__(
        self,
        message: str,
        *,
        thought_id: str,
        reference_source: str,
        path: str | None = None,
    ) -> None:
        super().__init__(message, path=path)
        self.thought_id = thought_id
        self.reference_source = reference_source


class SelfReferenceError(ThoughtEcologyError):
    """A relation references the same thought at both endpoints."""

    def __init__(
        self,
        message: str,
        *,
        thought_id: str,
        relation_type: str,
        path: str | None = None,
    ) -> None:
        super().__init__(message, path=path)
        self.thought_id = thought_id
        self.relation_type = relation_type


class DependencyCycleError(ThoughtEcologyError):
    """A dependency cycle is detected in the ecology graph."""

    def __init__(
        self,
        message: str,
        *,
        cycle: tuple[str, ...] = (),
        path: str | None = None,
    ) -> None:
        super().__init__(message, path=path)
        self.cycle = cycle


class ConflictingAssumptionError(ThoughtEcologyError):
    """The same assumption ID maps to different payloads."""

    def __init__(
        self,
        message: str,
        *,
        assumption_id: str,
        thoughts: tuple[str, ...] = (),
        path: str | None = None,
    ) -> None:
        super().__init__(message, path=path)
        self.assumption_id = assumption_id
        self.thoughts = thoughts


class AmbiguousEvidenceBucketError(ThoughtEcologyError):
    """The same evidence ID appears in multiple buckets for one thought."""

    def __init__(
        self,
        message: str,
        *,
        evidence_id: str,
        thought_id: str,
        buckets: tuple[str, ...] = (),
        path: str | None = None,
    ) -> None:
        super().__init__(message, path=path)
        self.evidence_id = evidence_id
        self.thought_id = thought_id
        self.buckets = buckets


class SnapshotMismatchError(ThoughtEcologyError):
    """The supplied snapshot does not match the stored digest."""

    def __init__(
        self,
        message: str,
        *,
        expected_digest: str,
        actual_digest: str,
        path: str | None = None,
    ) -> None:
        super().__init__(message, path=path)
        self.expected_digest = expected_digest
        self.actual_digest = actual_digest
