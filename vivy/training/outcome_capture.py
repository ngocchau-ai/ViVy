"""C04 observed-outcome capture store.

Rule (C04 / §2.2): an *expected* postcondition written by the acting model is a
prediction. It must never be promoted to `gold_outcome`. Only an independent
checker plus real tool result + before/after captures may produce an observed
outcome.

Sandbox only. A tool failure is a negative outcome about the action attempt —
it is not proof the candidate selection was wrong.

Changelog:
    24/09/2026 (Claude Code — P2 C04): Initial.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from training.io_guard import open_write

OUTCOME_SUCCESS = "success"
OUTCOME_WRONG_STATE = "tool_success_wrong_state"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_FOCUS_CHANGE = "focus_change"
OUTCOME_STALE_CAPTURE = "stale_capture"
OUTCOME_PARTIAL = "partial"
OUTCOME_RETRY = "retry"
OUTCOME_ROLLBACK = "rollback"
OUTCOME_ACTION_FAILURE = "action_failure"
OUTCOME_UNKNOWN = "unknown"

KNOWN_OUTCOMES = frozenset({
    OUTCOME_SUCCESS,
    OUTCOME_WRONG_STATE,
    OUTCOME_TIMEOUT,
    OUTCOME_FOCUS_CHANGE,
    OUTCOME_STALE_CAPTURE,
    OUTCOME_PARTIAL,
    OUTCOME_RETRY,
    OUTCOME_ROLLBACK,
    OUTCOME_ACTION_FAILURE,
    OUTCOME_UNKNOWN,
})

# checker.verdict → gold_outcome. Deliberately excludes anything derived from
# `expected_postcondition`.
_CHECKER_MAP = {
    "met": OUTCOME_SUCCESS,
    "not_met": OUTCOME_WRONG_STATE,
    "timeout": OUTCOME_TIMEOUT,
    "focus_change": OUTCOME_FOCUS_CHANGE,
    "stale": OUTCOME_STALE_CAPTURE,
    "partial": OUTCOME_PARTIAL,
    "retry": OUTCOME_RETRY,
    "rolled_back": OUTCOME_ROLLBACK,
    "tool_error": OUTCOME_ACTION_FAILURE,
}

PERMISSION_SANDBOX = "sandbox"
PERMISSION_APPROVED = "approved-sandbox"


class CaptureError(ValueError):
    """Raised when a capture record violates the observed-outcome contract."""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_capture_id(
    *,
    task_id: str,
    chosen_action: str,
    capture_before_id: str,
    tool_result_hash: str,
) -> str:
    """Content-addressed capture id. Changes whenever the action or captures change."""
    payload = json.dumps(
        {
            "task_id": task_id,
            "chosen_action": chosen_action,
            "capture_before_id": capture_before_id,
            "tool_result_hash": tool_result_hash,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "outcome-" + _sha256_text(payload)[:16]


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CaptureError(f"{name} must be a mapping")
    return value


def _validate_snapshot(snapshot: Any, name: str) -> Mapping[str, Any]:
    snap = _require_mapping(snapshot, name)
    for key in ("capture_id", "captured_at", "state_fingerprint"):
        if not snap.get(key):
            raise CaptureError(f"{name}.{key} is required")
    return snap


def _checker_is_independent(checker: Mapping[str, Any]) -> bool:
    if checker.get("is_acting_model"):
        return False
    checker_id = str(checker.get("checker_id", "")).lower()
    if checker_id in {"the-acting-model", "acting-model", "self", "the_model", "vivy-self"}:
        return False
    if "acting-model" in checker_id or checker_id.endswith("-self"):
        return False
    return True


def derive_outcome(record: Mapping[str, Any]) -> str:
    """Map an observed capture to `gold_outcome`. Never reads `expected_postcondition`."""
    checker = record.get("independent_checker")
    if not isinstance(checker, Mapping) or not checker.get("verdict"):
        return OUTCOME_UNKNOWN
    verdict = str(checker["verdict"]).strip().lower()
    if verdict == "met":
        # success is only real when something was actually observed after the action
        observed = record.get("observed_postcondition") or []
        after = record.get("capture_after")
        if not observed or not after:
            return OUTCOME_WRONG_STATE
        return OUTCOME_SUCCESS
    return _CHECKER_MAP.get(verdict, OUTCOME_UNKNOWN)


def record_capture(
    record: Mapping[str, Any],
    *,
    approved_task_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Validate and stamp an observed-outcome record.

    - Expected postconditions are stored but flagged `expected_used_as_outcome=False`.
    - Non-sandbox permission is refused unless `permission == approved-sandbox`
      *and* `approval_token` names an approved task.
    - An acting-model self-claim is not an independent checker.
    """
    data = dict(record)
    task_id = str(data.get("task_id") or "")
    if not task_id:
        raise CaptureError("task_id is required")
    if not data.get("goal"):
        raise CaptureError("goal is required")
    chosen = data.get("chosen_action")
    if not chosen:
        raise CaptureError("chosen_action is required")
    candidates = data.get("candidate_set") or []
    if chosen not in candidates:
        raise CaptureError("chosen_action must be a member of candidate_set")

    permission = str(data.get("permission") or "")
    if permission == PERMISSION_APPROVED:
        token = str(data.get("approval_token") or "")
        if not token.startswith(f"{task_id}:"):
            raise CaptureError("approved-sandbox requires approval_token bound to task_id")
        if task_id not in set(approved_task_ids):
            raise CaptureError("approved-sandbox requires the task id in approved_task_ids")
    elif permission != PERMISSION_SANDBOX:
        raise CaptureError("only sandbox or approved-sandbox captures may be recorded")

    before = _validate_snapshot(data.get("capture_before"), "capture_before")
    after_raw = data.get("capture_after")
    after = _validate_snapshot(after_raw, "capture_after") if after_raw else None

    checker = data.get("independent_checker")
    if checker is not None:
        checker = _require_mapping(checker, "independent_checker")
        if not checker.get("checker_id") or not checker.get("verdict"):
            raise CaptureError("independent_checker needs checker_id and verdict")
        if not _checker_is_independent(checker):
            raise CaptureError("acting-model self-claim is not an independent checker")

    tool_result = data.get("tool_result")
    if tool_result is not None:
        tool_result = _require_mapping(tool_result, "tool_result")

    expected = list(data.get("expected_postcondition") or [])
    observed = list(data.get("observed_postcondition") or [])

    tool_result_hash = _sha256_text(
        json.dumps(tool_result or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )
    capture_id = data.get("capture_id") or make_capture_id(
        task_id=task_id,
        chosen_action=str(chosen),
        capture_before_id=str(before["capture_id"]),
        tool_result_hash=tool_result_hash,
    )

    gold_outcome = derive_outcome({
        "observed_postcondition": observed,
        "capture_after": after,
        "independent_checker": checker,
        "tool_result": tool_result,
    })

    stamped = {
        "capture_id": capture_id,
        "task_id": task_id,
        "goal": str(data["goal"]),
        "candidate_set": list(candidates),
        "chosen_action": chosen,
        "permission": permission,
        "approval_token": data.get("approval_token"),
        "tool_result": tool_result,
        "tool_result_sha256": tool_result_hash,
        "capture_before": dict(before),
        "capture_after": dict(after) if after else None,
        "expected_postcondition": expected,
        "observed_postcondition": observed,
        "expected_used_as_outcome": False,
        "independent_checker": dict(checker) if checker else None,
        "gold_outcome": gold_outcome,
        "outcome_known": gold_outcome != OUTCOME_UNKNOWN,
        # C04: a failed action is a negative outcome about the attempt.
        "outcome_indicts_selection": False,
        "action_observed_at": (after or before).get("captured_at"),
        "timestamp_kind": "observation",
        "contract_version": "vivy-outcome-capture-v1",
    }
    return stamped


def write_capture(
    path: str | Path,
    record: Mapping[str, Any],
    *,
    protected: Sequence[str | Path] = (),
    allow_replace: bool = False,
) -> None:
    with open_write(path, protected=protected, allow_replace=allow_replace) as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
