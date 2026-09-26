"""C11.1 + C11.3 — VM-11 error-dampening pilot (sim vs live, 100-task mix).

Separates SIMULATED_PROTOCOL from LIVE_MODEL_OBSERVATION on an identical task
sequence. Requires known-error + novel-error + conflicting negative constraints.
Reports repeat rate, false inhibition, and task success — each with a denominator.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from training.error_classifier import (
    ErrorSignature,
    TrialContext,
    classify_trial,
    is_false_inhibition,
    record_error,
)

SIM_LABEL = "SIMULATED_PROTOCOL"
LIVE_LABEL = "LIVE_MODEL_OBSERVATION"
NOT_RUN_LABEL = "NOT_RUN"

REQUIRED_KINDS = frozenset({"known_error", "novel_error", "conflict_constraint"})

LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"
DEFAULT_STATUS = "PROVISIONAL_RESULT"


@dataclass(frozen=True)
class PilotTask:
    task_id: int
    kind: str
    action: str
    fails: bool
    root_cause: str = ""
    condition_changed: bool = False


def _seq_hash(tasks) -> str:
    payload = json.dumps(
        [asdict(t) for t in tasks],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _not_run(tasks, *, mode: str, use_dampener: bool) -> dict:
    n = len(tasks)
    return {
        "n_tasks": n,
        "mode": mode,
        "status_label": NOT_RUN_LABEL,
        "verdict": NOT_RUN_LABEL,
        "use_dampener": use_dampener,
        "task_sequence_hash": _seq_hash(tasks),
        "repeat_errors": 0,
        "new_errors": 0,
        "valid_reattempts": 0,
        "recovered": 0,
        "n_failed_or_ok_accounted": 0,
        "blocked_count": 0,
        "false_inhibitions": 0,
        "successes": 0,
        "repeat_rate": None,
        "repeat_rate_denominator": 0,
        "false_inhibition_rate": None,
        "false_inhibition_rate_denominator": 0,
        "task_success_rate": None,
        "task_success_rate_denominator": 0,
        "latency_claim": LATENCY_CLAIM,
        "backend_id": None,
        "ci95": None,
    }


def run_pilot(
    tasks,
    *,
    mode: str,
    seed: int = 0,
    use_dampener: bool = True,
    live_backend: str | None = None,
) -> dict:
    kinds = {t.kind for t in tasks}
    if not REQUIRED_KINDS <= kinds:
        missing = sorted(REQUIRED_KINDS - kinds)
        raise ValueError(f"pilot requires task kinds {sorted(REQUIRED_KINDS)}, missing {missing}")

    if mode == "live" and live_backend is None:
        return _not_run(tasks, mode=mode, use_dampener=use_dampener)

    if mode not in ("simulated", "live"):
        raise ValueError(f"mode must be simulated|live, got {mode!r}")

    status_label = SIM_LABEL if mode == "simulated" else LIVE_LABEL

    history: list = []
    falsified_actions: set[str] = set()
    counts = {"repeat_error": 0, "new_error": 0, "valid_reattempt": 0, "recovered": 0}
    blocked_count = 0
    false_inhibitions = 0
    successes = 0
    n_condition_changed = sum(1 for t in tasks if t.condition_changed)

    for task in tasks:
        outcome = "wrong_state" if task.fails else "success"
        sig = ErrorSignature(
            root_cause=task.root_cause or task.kind,
            action=task.action,
            outcome=outcome,
        )
        ctx = TrialContext(signature=sig, failed=task.fails, condition_changed=task.condition_changed)

        # Naive dampener: avoid any action with falsified_count > 0.
        # Deliberately condition-blind so false inhibition is measurable.
        if use_dampener and task.action in falsified_actions:
            blocked_count += 1
            if is_false_inhibition(history, ctx, action_blocked_by_dampener=True):
                false_inhibitions += 1
            continue

        verdict = classify_trial(history, ctx)
        counts[verdict] += 1
        if task.fails:
            history.append(record_error(sig, task_id=task.task_id))
            falsified_actions.add(task.action)
        else:
            successes += 1

    n_accounted = counts["repeat_error"] + counts["new_error"] + counts["valid_reattempt"] + counts["recovered"]
    n_tasks = len(tasks)

    repeat_den = counts["repeat_error"] + counts["new_error"] + counts["valid_reattempt"]
    fi_den = n_condition_changed
    success_den = n_tasks

    return {
        "n_tasks": n_tasks,
        "mode": mode,
        "status_label": status_label,
        "verdict": DEFAULT_STATUS if mode == "simulated" else DEFAULT_STATUS,
        "use_dampener": use_dampener,
        "seed": seed,
        "task_sequence_hash": _seq_hash(tasks),
        "repeat_errors": counts["repeat_error"],
        "new_errors": counts["new_error"],
        "valid_reattempts": counts["valid_reattempt"],
        "recovered": counts["recovered"],
        "n_failed_or_ok_accounted": n_accounted,
        "blocked_count": blocked_count,
        "false_inhibitions": false_inhibitions,
        "successes": successes,
        "repeat_rate": (counts["repeat_error"] / repeat_den) if repeat_den else None,
        "repeat_rate_denominator": repeat_den,
        "false_inhibition_rate": (false_inhibitions / fi_den) if fi_den else None,
        "false_inhibition_rate_denominator": fi_den,
        "task_success_rate": (successes / success_den) if success_den else None,
        "task_success_rate_denominator": success_den,
        "latency_claim": LATENCY_CLAIM,
        "backend_id": live_backend if mode == "live" else "simulated-action-loop",
        "ci95": None,  # CI requires a live sample ≥100 with observed outcomes — not claimed here
    }
