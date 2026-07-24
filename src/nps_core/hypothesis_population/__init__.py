"""Hypothesis population core: lifecycle, lineage, and serialization.

Re-exports all intended public constants, immutable value types, domain errors,
serialization helpers, LineageIndex, TransitionEvent, PopulationSnapshot, and
the create/branch/merge/prune lifecycle operations.
"""

from __future__ import annotations

from nps_core.hypothesis_population.errors import (
    CycleDetectedError,
    DuplicateEventError,
    DuplicateIdError,
    InvalidDispositionError,
    InvalidTransitionError,
    MergeSourceError,
    SelfReferenceError,
    TerminalStateError,
    ThoughtStateError,
    UnknownReferenceError,
    ValidationError,
)
from nps_core.hypothesis_population.lifecycle import (
    PopulationSnapshot,
    TransitionEvent,
    branch,
    create,
    merge,
    prune,
)
from nps_core.hypothesis_population.lineage import LineageIndex
from nps_core.hypothesis_population.serialization import (
    CANONICAL_SEPARATORS,
    canonical_json,
    parse_json,
    thought_state_from_dict,
    thought_state_from_json,
    thought_state_to_dict,
)
from nps_core.hypothesis_population.thought_state import (
    PRUNE_DISPOSITIONS,
    TERMINAL_STATES,
    VALID_STATES,
    VALID_STATE_SET,
    Assumption,
    Evidence,
    ExecutorProfile,
    Graph,
    Hypothesis,
    Interpretation,
    Metrics,
    Status,
    ThoughtState,
    VerificationPlan,
)

__all__ = [
    # errors
    "CycleDetectedError",
    "DuplicateEventError",
    "DuplicateIdError",
    "InvalidDispositionError",
    "InvalidTransitionError",
    "MergeSourceError",
    "SelfReferenceError",
    "TerminalStateError",
    "ThoughtStateError",
    "UnknownReferenceError",
    "ValidationError",
    # lifecycle
    "PopulationSnapshot",
    "TransitionEvent",
    "branch",
    "create",
    "merge",
    "prune",
    # lineage
    "LineageIndex",
    # serialization
    "CANONICAL_SEPARATORS",
    "canonical_json",
    "parse_json",
    "thought_state_from_dict",
    "thought_state_from_json",
    "thought_state_to_dict",
    # thought_state constants
    "PRUNE_DISPOSITIONS",
    "TERMINAL_STATES",
    "VALID_STATES",
    "VALID_STATE_SET",
    # thought_state value types
    "Assumption",
    "Evidence",
    "ExecutorProfile",
    "Graph",
    "Hypothesis",
    "Interpretation",
    "Metrics",
    "Status",
    "ThoughtState",
    "VerificationPlan",
]
