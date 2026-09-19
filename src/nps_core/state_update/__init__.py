"""Atomic state update package.

Public API re-exports the state-update error taxonomy, the evidence update
record model, and the deterministic ``apply_evidence`` entry point.
"""

from nps_core.state_update.engine import EvidenceUpdateRecord, apply_evidence
from nps_core.state_update.errors import (
    InvalidRecordError,
    ReplacementValidationError,
    StateUpdateError,
    TargetMismatchError,
)

__all__ = [
    # errors
    "StateUpdateError",
    "ReplacementValidationError",
    "TargetMismatchError",
    "InvalidRecordError",
    # models / functions
    "EvidenceUpdateRecord",
    "apply_evidence",
]
