"""C11.2 — repeated-error taxonomy (root cause / action / outcome).

Splits a trial into new_error / repeat_error / valid_reattempt / recovered so a
dampener can be scored on repeat rate AND false inhibition. Inherits the VM-11
"falsified_count > 0" notion of a logged failure without treating every
re-encounter of an action as a repeat: condition-changed retries are valid.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorSignature:
    """Identity of a failure on three axes. Same action ≠ same error."""

    root_cause: str
    action: str
    outcome: str


@dataclass(frozen=True)
class ErrorRecord:
    signature: ErrorSignature
    task_id: int


@dataclass(frozen=True)
class TrialContext:
    signature: ErrorSignature
    failed: bool
    condition_changed: bool


def record_error(signature: ErrorSignature, *, task_id: int) -> ErrorRecord:
    return ErrorRecord(signature=signature, task_id=task_id)


def _seen(history, signature: ErrorSignature) -> bool:
    return any(r.signature == signature for r in history)


def classify_trial(history, ctx: TrialContext) -> str:
    """Return one of: new_error | repeat_error | valid_reattempt | recovered."""
    if not ctx.failed:
        return "recovered"
    if ctx.condition_changed:
        # Conditions moved since the logged failure — a retry is legitimate.
        return "valid_reattempt"
    if _seen(history, ctx.signature):
        return "repeat_error"
    return "new_error"


def is_false_inhibition(history, ctx: TrialContext, *, action_blocked_by_dampener: bool) -> bool:
    """True when a dampener blocked a reattempt that conditions made legitimate."""
    if not action_blocked_by_dampener:
        return False
    if not ctx.condition_changed:
        return False
    return _seen(history, ctx.signature)
