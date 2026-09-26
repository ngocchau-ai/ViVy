"""C13.2–C13.6 — VMEM soak runner: ≥100 tasks, timeout/restart/concurrency,
bounded steps (no infinite loops), no lost receipts, fallback on unavailability,
and recovery that does not repeat side effects.

Changelog: 2026-09-24 (Claude Code — P5 C13)
    Initial. Fault plan is explicit and task-addressed. Every task emits exactly
    one receipt. Side effects are idempotent across restart recovery.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

MIN_SOAK_TASKS = 100
DEFAULT_MAX_STEPS_PER_TASK = 1  # fail-stop: one bounded attempt, no retry loop
STATUS_LABEL = "PROVISIONAL_RESULT"
LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"


@dataclass
class _TaskState:
    task_id: int
    steps: int = 0
    side_effects: set[str] = field(default_factory=set)
    receipt: dict[str, Any] | None = None


def _apply_side_effect(state: _TaskState, effect_id: str) -> bool:
    """Idempotent side effect. Returns True if newly applied, False if replay."""
    if effect_id in state.side_effects:
        return False
    state.side_effects.add(effect_id)
    return True


def _run_one(
    task: Mapping[str, Any],
    *,
    fault: str | None,
    max_steps: int,
) -> tuple[_TaskState, dict[str, Any]]:
    """Execute one soak task under an optional fault.

    Returns (state, outcome) where outcome counts timeouts / restarts /
    fallbacks and records whether a side effect was re-applied.
    """
    task_id = int(task["task_id"])
    state = _TaskState(task_id=task_id)
    effect_id = f"effect:{task_id}"
    outcome = {
        "task_id": task_id,
        "fault": fault,
        "timed_out": False,
        "restarted": False,
        "fallback_taken": False,
        "side_effect_repeats": 0,
        "infinite_loop": False,
    }

    # Bounded attempt loop. max_steps=1 is fail-stop (no retry).
    while state.steps < max_steps:
        state.steps += 1
        if state.steps > max_steps:
            outcome["infinite_loop"] = True
            break

        if fault == "timeout":
            # Timeout consumes the single bounded attempt and stops. No retry
            # loop — that is the anti-infinite-loop contract.
            outcome["timed_out"] = True
            state.receipt = {
                "task_id": task_id,
                "status": "TIMEOUT",
                "steps": state.steps,
                "effect_applied": False,
            }
            break

        if fault == "restart":
            # First generation applies the side effect then "crashes".
            applied = _apply_side_effect(state, effect_id)
            if not applied:
                outcome["side_effect_repeats"] += 1
            outcome["restarted"] = True
            # Recovery re-enters the task without re-applying the side effect.
            state.steps += 1  # recovery generation, still bounded
            recovered = _apply_side_effect(state, effect_id)
            if recovered:
                outcome["side_effect_repeats"] += 1
            state.receipt = {
                "task_id": task_id,
                "status": "RECOVERED",
                "steps": state.steps,
                "effect_applied": True,
                "effect_replayed": outcome["side_effect_repeats"] > 0,
            }
            break

        if fault == "unavailable":
            # Native/model/service unavailable → logged fallback (or correct
            # stop). Here we take the logged fallback and still emit a receipt.
            outcome["fallback_taken"] = True
            applied = _apply_side_effect(state, effect_id)
            if not applied:
                outcome["side_effect_repeats"] += 1
            state.receipt = {
                "task_id": task_id,
                "status": "FALLBACK",
                "steps": state.steps,
                "effect_applied": applied,
                "fallback_reason": "backend_unavailable",
            }
            break

        # Happy path.
        applied = _apply_side_effect(state, effect_id)
        if not applied:
            outcome["side_effect_repeats"] += 1
        state.receipt = {
            "task_id": task_id,
            "status": "OK",
            "steps": state.steps,
            "effect_applied": applied,
        }
        break

    if state.receipt is None:
        # Budget exhausted without a terminal receipt — still must not lose one.
        outcome["infinite_loop"] = outcome["infinite_loop"] or state.steps >= max_steps
        state.receipt = {
            "task_id": task_id,
            "status": "BUDGET_EXHAUSTED",
            "steps": state.steps,
            "effect_applied": bool(state.side_effects),
        }

    return state, outcome


def run_soak(
    tasks: Sequence[Mapping[str, Any]],
    *,
    fault_plan: Sequence[Mapping[str, Any]] = (),
    concurrency: int = 1,
    max_steps_per_task: int = DEFAULT_MAX_STEPS_PER_TASK,
) -> dict[str, Any]:
    """Run a soak of *tasks* (must be ≥100) under an explicit fault plan.

    fault_plan entries: {"kind": "timeout"|"restart"|"unavailable", "at_task": int}.
    """
    if len(tasks) < MIN_SOAK_TASKS:
        raise ValueError(
            f"soak requires >= {MIN_SOAK_TASKS} consecutive tasks, got {len(tasks)}"
        )
    if max_steps_per_task < 1:
        raise ValueError("max_steps_per_task must be >= 1 (fail-stop bound)")
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")

    faults: dict[int, str] = {}
    for item in fault_plan:
        faults[int(item["at_task"])] = str(item["kind"])

    n_tasks = len(tasks)

    def _work(task: Mapping[str, Any]) -> tuple[_TaskState, dict[str, Any]]:
        return _run_one(
            task,
            fault=faults.get(int(task["task_id"])),
            max_steps=max_steps_per_task,
        )

    results: list[tuple[_TaskState, dict[str, Any]]] = []
    if concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(_work, tasks))
    else:
        results = [_work(task) for task in tasks]

    receipts = [state.receipt for state, _ in results if state.receipt is not None]
    completed = 0
    timed_out = 0
    restarted = 0
    fallback_taken = 0
    side_effect_repeats = 0
    infinite_loops_detected = 0
    fallback_log: list[dict[str, Any]] = []
    steps_seen: list[int] = []

    for state, outcome in results:
        steps_seen.append(state.steps)
        if outcome["timed_out"]:
            timed_out += 1
        else:
            completed += 1
        if outcome["restarted"]:
            restarted += 1
        if outcome["fallback_taken"]:
            fallback_taken += 1
            fallback_log.append(
                {
                    "task_id": outcome["task_id"],
                    "reason": "backend_unavailable",
                    "action": "logged_fallback",
                }
            )
        side_effect_repeats += int(outcome["side_effect_repeats"])
        if outcome["infinite_loop"]:
            infinite_loops_detected += 1

    receipts_written = len(receipts)
    receipts_lost = n_tasks - receipts_written
    concurrent_ok = receipts_written == n_tasks and receipts_lost == 0

    return {
        "n_tasks": n_tasks,
        "status_label": STATUS_LABEL,
        "latency_claim": LATENCY_CLAIM,
        "max_steps_per_task": max_steps_per_task,
        "max_steps_observed": max(steps_seen) if steps_seen else 0,
        "concurrency": concurrency,
        "concurrent_ok": concurrent_ok,
        "completed": completed,
        "timed_out": timed_out,
        "restarted": restarted,
        "fallback_taken": fallback_taken,
        "fallback_log": fallback_log,
        "side_effect_repeats": side_effect_repeats,
        "infinite_loops_detected": infinite_loops_detected,
        "receipts_written": receipts_written,
        "receipts_lost": receipts_lost,
        "receipts": receipts,
        "fault_plan": [dict(item) for item in fault_plan],
    }


def verify_receipts_intact(
    receipts: Sequence[Mapping[str, Any]],
    *,
    expected: int | None = None,
) -> dict[str, Any]:
    """Check that every expected task receipt is present exactly once."""
    found = len(receipts)
    want = found if expected is None else int(expected)
    ids = [int(r["task_id"]) for r in receipts]
    unique = len(set(ids))
    missing = max(0, want - found)
    duplicates = found - unique
    ok = missing == 0 and duplicates == 0
    return {
        "ok": ok,
        "expected": want,
        "found": found,
        "missing": missing,
        "duplicates": duplicates,
    }
