"""Module for thought relationship graph in NPS Core."""

from nps_core.thought_ecology.errors import (
    AmbiguousEvidenceBucketError,
    ConflictingAssumptionError,
    DependencyCycleError,
    EcologyValidationError,
    SelfReferenceError,
    SnapshotMismatchError,
    ThoughtEcologyError,
    UnknownThoughtError,
)
from nps_core.thought_ecology.index import ThoughtEcology, build
from nps_core.thought_ecology.relations import (
    ContradictionEdge,
    DependencyEdge,
    EvidencePlacement,
    OverlapEdge,
    SharedAssumptionLink,
)

__all__ = [
    # Errors
    "ThoughtEcologyError",
    "AmbiguousEvidenceBucketError",
    "ConflictingAssumptionError",
    "DependencyCycleError",
    "EcologyValidationError",
    "SelfReferenceError",
    "SnapshotMismatchError",
    "UnknownThoughtError",
    # Relations
    "ContradictionEdge",
    "DependencyEdge",
    "EvidencePlacement",
    "OverlapEdge",
    "SharedAssumptionLink",
    # Index
    "ThoughtEcology",
    "build",
]
