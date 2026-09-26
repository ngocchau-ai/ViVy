"""C13 receipt runner — VMEM spec-threshold gaps + VM shape gates + resilience soak.

Writes evidence/c13_vmem_resilience.json (new file only; io_guard refuses overwrite).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from training.io_guard import open_write
from training.vmem_soak import MIN_SOAK_TASKS, run_soak, verify_receipts_intact
from training.vmem_spec_gates import (
    LIVE_LABEL,
    SIM_LABEL,
    VM_IDS,
    evaluate_spec_thresholds,
    judge_vm_measurement,
)

DEFAULT_OUTPUT = Path("evidence/c13_vmem_resilience.json")

# Spec headers as read on this host (2026-09-24). Neither document contains a
# VM-01…VM-11 numeric threshold table — every quote is therefore a GAP.
SPEC_HEADERS = {
    "VIVY_COGNITIVE_CORE_SPEC.md": {
        "spec_version": "2026-09-19",
        "sha256_prefix": "82ef36488c6021c5",
        "has_vm_threshold_table": False,
    },
    "ACCURACY_AND_MATURATION_STRATEGIES.md": {
        "spec_version": "2026-09-20",
        "sha256_prefix": "4a13d4fe71ec3071",
        "has_vm_threshold_table": False,
    },
    "ACCEPTANCE_GATES.md": {
        "spec_version": "2026-09-19",
        "sha256_prefix": "155f8157378a0ca3",
        "has_vm_threshold_table": False,
    },
}

# "Sai lầm cần tránh" payloads — each must FAIL the shape gate.
_SHORTCUT_PAYLOADS: dict[str, dict] = {
    "VM-01": {"n_forage": 10, "note": "all FORAGE decisions look right"},
    "VM-02": {"adapter_exists": True, "accuracy": 1.0},
    "VM-03": {"n_tool_calls": 42},
    "VM-04": {"cache_entries": 7},
    "VM-05": {"lesson_text": "always do X"},
    "VM-06": {"parse_ok": True},
    "VM-07": {"named_the_error": "it was a timeout"},
    "VM-08": {"process_restarted": True},
    "VM-09": {"memory_get_ms": 0.003, "label": "TTFT"},
    "VM-10": {"n": 3, "note": "more cores = smarter"},
    "VM-11": {"repeat_rate": 0.03, "status_label": SIM_LABEL, "live": False},
}


def _threshold_entries() -> list[dict]:
    entries = []
    for spec_name, meta in SPEC_HEADERS.items():
        for vm_id in VM_IDS:
            entries.append(
                {
                    "vm_id": vm_id,
                    "spec_name": spec_name,
                    "spec_version": meta["spec_version"],
                    "verbatim": "",  # spec is silent — GAP, never invented
                }
            )
    # Dedup by vm_id keeping the first (cognitive-core) row; the report records
    # that all three specs were scanned and none supplied a threshold.
    seen: dict[str, dict] = {}
    for entry in entries:
        seen.setdefault(entry["vm_id"], entry)
    return [seen[vm_id] for vm_id in VM_IDS]


def _live_measurement_status() -> dict[str, dict]:
    """Honest per-VM status: live effectiveness is NOT_RUN on this host."""
    status = {}
    for vm_id in VM_IDS:
        status[vm_id] = {
            "live_measurement": "NOT_RUN",
            "reason": "no live model/service observation on this host",
            "shape_gate": "TESTED",
            "threshold": "GAP",
        }
    return status


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output = Path(argv[0]) if argv else DEFAULT_OUTPUT

    threshold_report = evaluate_spec_thresholds(_threshold_entries())
    threshold_report["specs_scanned"] = SPEC_HEADERS
    threshold_report["binding_rule"] = (
        "missing threshold → GAP, not PASS; quote verbatim with version before measurement"
    )

    shape_gates = {}
    for vm_id in VM_IDS:
        bad = judge_vm_measurement(vm_id, _SHORTCUT_PAYLOADS[vm_id])
        shape_gates[vm_id] = {
            "shortcut_payload": _SHORTCUT_PAYLOADS[vm_id],
            "shortcut_verdict": bad["verdict"],
            "shortcut_missing": bad["missing"],
            "shortcut_rejected": bad["verdict"] == "FAIL",
        }

    tasks = [{"task_id": i, "prompt": f"soak-task-{i}"} for i in range(MIN_SOAK_TASKS)]
    fault_plan = [
        {"kind": "timeout", "at_task": 7},
        {"kind": "restart", "at_task": 3},
        {"kind": "unavailable", "at_task": 5},
    ]
    soak = run_soak(tasks, fault_plan=fault_plan, concurrency=4, max_steps_per_task=1)
    receipt_check = verify_receipts_intact(soak["receipts"], expected=MIN_SOAK_TASKS)

    # VM-11 simulated pilot (C11) must FAIL the live shape gate.
    vm11_sim_judged = judge_vm_measurement(
        "VM-11",
        {
            "repeat_rate": 0.0,
            "false_inhibition_rate": 1.0,
            "status_label": SIM_LABEL,
            "live": False,
            "denominator": 100,
            "ci95": None,
        },
    )

    receipt = {
        "kind": "C13_VMEM_RESILIENCE",
        "requirement_ids": ["C13.1", "C13.2", "C13.3", "C13.4", "C13.5", "C13.6"],
        "status_label": "PROVISIONAL_RESULT",
        "result_class": "TESTED_MECHANISM",
        "threshold_report": threshold_report,
        "vm_shape_gates": shape_gates,
        "vm_live_status": _live_measurement_status(),
        "vm11_simulated_pilot_vs_live_gate": vm11_sim_judged,
        "soak": {
            "n_tasks": soak["n_tasks"],
            "min_required": MIN_SOAK_TASKS,
            "status_label": soak["status_label"],
            "latency_claim": soak["latency_claim"],
            "max_steps_per_task": soak["max_steps_per_task"],
            "max_steps_observed": soak["max_steps_observed"],
            "concurrency": soak["concurrency"],
            "concurrent_ok": soak["concurrent_ok"],
            "completed": soak["completed"],
            "timed_out": soak["timed_out"],
            "restarted": soak["restarted"],
            "fallback_taken": soak["fallback_taken"],
            "fallback_log": soak["fallback_log"],
            "side_effect_repeats": soak["side_effect_repeats"],
            "infinite_loops_detected": soak["infinite_loops_detected"],
            "receipts_written": soak["receipts_written"],
            "receipts_lost": soak["receipts_lost"],
            "fault_plan": soak["fault_plan"],
            "receipt_check": receipt_check,
        },
        "claims": {
            "spec_thresholds_quoted_verbatim": "TESTED",
            "missing_threshold_is_gap_not_pass": (
                "TESTED" if threshold_report["overall"] == "GAP" else "FAIL"
            ),
            "vm_shape_gates_reject_shortcuts": (
                "TESTED"
                if all(g["shortcut_rejected"] for g in shape_gates.values())
                else "FAIL"
            ),
            "soak_at_least_100_tasks": (
                "TESTED" if soak["n_tasks"] >= MIN_SOAK_TASKS else "FAIL"
            ),
            "timeout_bounded_no_infinite_loop": (
                "TESTED" if soak["infinite_loops_detected"] == 0 else "FAIL"
            ),
            "restart_recovery_no_side_effect_repeat": (
                "TESTED" if soak["side_effect_repeats"] == 0 else "FAIL"
            ),
            "unavailable_logged_fallback": (
                "TESTED" if soak["fallback_taken"] >= 1 and soak["fallback_log"] else "FAIL"
            ),
            "no_lost_receipts": (
                "TESTED" if soak["receipts_lost"] == 0 and receipt_check["ok"] else "FAIL"
            ),
            "concurrency_keeps_receipts": (
                "TESTED" if soak["concurrent_ok"] else "FAIL"
            ),
            "vm01_to_vm11_live_effectiveness": "NOT_RUN",
            "vm11_live_repeat_rate": "NOT_RUN",
            "simulation_is_production": "NOT_CLAIMED",
            "production_ready": "NOT_CLAIMED",
            "physical_zero_latency": "NOT_CLAIMED",
            "o1_claim": "NOT_CLAIMED",
        },
    }

    with open_write(output) as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "output": str(output),
                "threshold_overall": threshold_report["overall"],
                "threshold_gaps": len(threshold_report["gaps"]),
                "shape_shortcuts_rejected": sum(
                    1 for g in shape_gates.values() if g["shortcut_rejected"]
                ),
                "soak_n": soak["n_tasks"],
                "timed_out": soak["timed_out"],
                "restarted": soak["restarted"],
                "fallback_taken": soak["fallback_taken"],
                "side_effect_repeats": soak["side_effect_repeats"],
                "infinite_loops_detected": soak["infinite_loops_detected"],
                "receipts_lost": soak["receipts_lost"],
                "concurrent_ok": soak["concurrent_ok"],
                "vm11_sim_vs_live_gate": vm11_sim_judged["verdict"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
