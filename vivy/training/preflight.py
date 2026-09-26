"""Preflight gates that must pass before any ViVy training run.

Changelog: 2026-09-24 (Antigravity/Claude Code — P0 CORRECTIONS §2.8, §2.9)
    Fail-closed gates: empty gold no longer vacuously passes provenance;
    a missing shadow receipt file is FAIL, not PASS. CLI exits non-zero when
    promotion is BLOCKED so a trainer cannot ignore preflight. Added
    require_promotion_ready() for in-process enforcement.
Changelog: 2026-09-24 (Claude Code — P1 C01)
    Contract-test list includes backend_baseline / gate_negative / backend_registry.
Changelog: 2026-09-24 (Claude Code — P2 C02/C03)
    Contract-test list includes decision_contract / dataset_c03.
Changelog: 2026-09-24 (Claude Code — P2 C04)
    Contract-test list includes outcome_capture.
Changelog: 2026-09-24 (Claude Code — P3 C05)
    Contract-test list includes independent_baselines.
Changelog: 2026-09-24 (Claude Code — P3 C06)
    Contract-test list includes smoke_train.
Changelog: 2026-09-24 (Claude Code — P4 C07/C08/C09)
    Contract-test list includes shadow_integration / token_ledger / thinking_budget.
Changelog: 2026-09-24 (Claude Code — P5 C10)
    Contract-test list includes session_memory / abi_layout / hebbian_bench /
    memory_retrieval_ab.
Changelog: 2026-09-24 (Claude Code — P5 C11)
    Contract-test list includes error_classifier / dream_lesson_gate /
    lesson_persistence / brain_sync / vm11_pilot.
Changelog: 2026-09-24 (Claude Code — P5 C12)
    Contract-test list includes cartography_phases / sparse_forward.
Changelog: 2026-09-24 (Claude Code — P5 C13)
    Contract-test list includes vmem_spec_gates / vmem_soak.
Changelog: 2026-09-24 (Claude Code — Plan 1 D2/D3/D4/D5/D6)
    Contract-test list includes verify_receipt / sandbox_capture /
    check_known_limits / run_w2_live / receipt_shape.
Changelog: 2026-09-24 (Claude Code — Plan 2 A/C)
    Contract-test list includes native_parity_decision / learned_router.
Changelog: 2026-09-25 (Claude Code — Wave 1A/1B)
    Contract-test list includes cautreo_weight_map / cautreo_session_log.
Changelog: 2026-09-25 (Claude Code — Wave 2A/2B)
    Contract-test list includes weight_pager / cross_model_adapter.
Changelog: 2026-09-25 (Claude Code — Wave 3A)
    Contract-test list includes scored_mindmap_dag.
Changelog: 2026-09-25 (Claude Code — Wave 4A)
    Contract-test list includes model_upgrade_protocol.
Changelog: 2026-09-25 (Claude Code — AWL-4/5 + TD-6 integration)
    Contract-test list includes cautreo_resource_monitor / load_governor /
    cross_model_awl (previously omitted) and the new mindmap_planner /
    load_receipt.
Changelog: 2026-09-25 (Claude Code — TD-6 live evidence)
    Contract-test list includes run_reroute_live.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class PreflightBlocked(RuntimeError):
    """Raised when preflight gates are not all PASS."""


def run(root: str | Path = ".", *, run_contract_tests: bool = True) -> dict[str, Any]:
    root = Path(root)
    # Contract tests deliberately exclude training.test_preflight: those tests
    # call run(), which would recurse through this subprocess forever.
    test_modules = [
        "training.test_typed_decision", "training.test_audit_dataset",
        "training.test_baseline", "training.test_receipt",
        "training.test_shadow_router", "training.test_shadow_run",
        "training.test_perturbation", "training.test_legacy_to_typed",
        "training.test_gold_review_queue", "training.test_promote_reviewed",
        "training.test_gold_oracle", "training.test_triage_gold",
        "training.test_confirm_gold", "training.test_typed_decision_metrics",
        "training.test_io_guard", "training.test_backend_baseline",
        "training.test_gate_negative", "training.test_backend_registry",
        "training.test_decision_contract", "training.test_dataset_c03",
        "training.test_outcome_capture", "training.test_independent_baselines",
        "training.test_smoke_train", "training.test_shadow_integration",
        "training.test_token_ledger", "training.test_thinking_budget",
        "training.test_session_memory", "training.test_abi_layout",
        "training.test_hebbian_bench", "training.test_memory_retrieval_ab",
        "training.test_error_classifier", "training.test_dream_lesson_gate",
        "training.test_lesson_persistence", "training.test_brain_sync",
        "training.test_vm11_pilot", "training.test_cartography_phases",
        "training.test_sparse_forward", "training.test_vmem_spec_gates",
        "training.test_vmem_soak",
        "training.test_verify_receipt", "training.test_sandbox_capture",
        "training.test_check_known_limits", "training.test_run_w2_live",
        "training.test_receipt_shape",
        "training.test_native_parity_decision", "training.test_learned_router",
        "training.test_cautreo_weight_map", "training.test_cautreo_session_log",
        "training.test_weight_pager", "training.test_cross_model_adapter",
        "training.test_scored_mindmap_dag",
        "training.test_model_upgrade_protocol",
        "training.test_cautreo_resource_monitor", "training.test_load_governor",
        "training.test_cross_model_awl", "training.test_mindmap_planner",
        "training.test_load_receipt", "training.test_run_reroute_live",
        "training.test_cautreo_91sh_tool",
    ]
    test_exit_code = 0
    test_stdout = ""
    test_stderr = ""
    if run_contract_tests:
        test = subprocess.run(
            [sys.executable, "-m", "unittest", *test_modules],
            cwd=root, capture_output=True, text=True, check=False,
        )
        test_exit_code = test.returncode
        test_stdout = test.stdout or ""
        test_stderr = test.stderr or ""
    report_path = root / "evidence" / "gold_train.jsonl"
    shadow_path = root / "evidence" / "shadow_receipts.jsonl"
    gold_rows = []
    if report_path.exists():
        gold_rows = [json.loads(line) for line in report_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    shadow_exists = shadow_path.exists()
    actuated = 0
    if shadow_exists:
        actuated = sum(1 for line in shadow_path.read_text(encoding="utf-8").splitlines() if '"actuated": true' in line.lower())
    # §2.8: empty set must not vacuously pass (`all([]) is True`).
    provenance_ok = bool(gold_rows) and all(
        r.get("label_quality") == "independently_reviewed"
        and r.get("provenance", {}).get("review_receipt_id")
        for r in gold_rows
    )
    # §2.8: a missing shadow file cannot prove non-actuation.
    shadow_ok = shadow_exists and actuated == 0
    gates: dict[str, str] = {}
    if run_contract_tests:
        gates["contract_tests"] = "PASS" if test_exit_code == 0 else "FAIL"
    gates.update({
        "gold_dataset_nonempty": "PASS" if gold_rows else "FAIL",
        "gold_review_provenance": "PASS" if provenance_ok else "FAIL",
        "shadow_receipts_present": "PASS" if shadow_exists else "FAIL",
        "shadow_non_actuating": "PASS" if shadow_ok else "FAIL",
    })
    promotion = "READY_FOR_SMOKE" if gates and all(v == "PASS" for v in gates.values()) else "BLOCKED"
    return {
        "gates": gates,
        "promotion": promotion,
        "gold_rows": len(gold_rows),
        "shadow_actuated": actuated,
        "shadow_receipts_present": shadow_exists,
        "test_exit_code": test_exit_code,
        "test_output_tail": (test_stdout or "")[-1000:] + (test_stderr or "")[-1000:],
    }


def require_promotion_ready(root: str | Path = ".", *, run_contract_tests: bool = True) -> dict[str, Any]:
    """Raise PreflightBlocked unless every gate PASSes. Trainers must call this
    (or check the returned report) and exit non-zero on BLOCKED — a printed
    BLOCKED line is not enforcement (§2.9).
    """
    report = run(root, run_contract_tests=run_contract_tests)
    if report.get("promotion") != "READY_FOR_SMOKE":
        failed = [k for k, v in report.get("gates", {}).items() if v != "PASS"]
        raise PreflightBlocked(f"preflight BLOCKED; failing gates: {failed}")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("promotion") == "READY_FOR_SMOKE" else 2)
