"""P5 FINAL rollup receipt — collates C01–C13 scoped verdicts + limitation counts.

Writes evidence/p5_final_acceptance.json (new file only; io_guard refuses overwrite).
This is an index to the packets, not a substitute for their raw evidence.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from training.io_guard import open_write

DEFAULT_OUTPUT = Path("evidence/p5_final_acceptance.json")

PACKETS = {
    "P0": "docs/plans/P0_INVENTORY_TRACEABILITY_CORRECTIONS.md",
    "P1": "docs/plans/P1_BACKEND_BASELINE_GATE_NEGATIVE_TESTS.md",
    "P2": "docs/plans/P2_DATASET_CONTRACT_AND_PROVENANCE.md",
    "P3": "docs/plans/P3_INDEPENDENT_BASELINES_C05.md",
    "P4": "docs/plans/P4_SHADOW_TOKEN_THINKING_C07_C09.md",
    "P5_C10": "docs/plans/P5_C10_MEMORY_C_ABI_HEBBIAN.md",
    "P5_C11": "docs/plans/P5_C11_VM11_DREAM_PROMOTION.md",
    "P5_C12": "docs/plans/P5_C12_CARTOGRAPHY_PHASES_SPARSE.md",
    "P5_C13": "docs/plans/P5_C13_VMEM_RESILIENCE.md",
    "P5_FINAL": "docs/plans/P5_FINAL_ACCEPTANCE.md",
    "KNOWN_LIMITATIONS": "docs/plans/KNOWN_LIMITATIONS.md",
}

# Scoped verdicts only. "PASS" here always means PASS at the named scope.
REQUIREMENTS = {
    "C01": {"verdict": "PASS", "scope": "harness"},
    "C01_live_accuracy": {"verdict": "NOT_RUN", "scope": "live"},
    "C02": {"verdict": "PASS", "scope": "contract"},
    "C03": {"verdict": "PASS", "scope": "contract"},
    "C04": {"verdict": "PASS", "scope": "contract"},
    "C05": {"verdict": "PASS", "scope": "harness"},
    "C06": {"verdict": "PASS", "scope": "harness"},
    "C07": {"verdict": "PASS", "scope": "harness"},
    "C08": {"verdict": "PASS", "scope": "contract"},
    "C09": {"verdict": "PASS", "scope": "harness"},
    "C09_live": {"verdict": "NOT_RUN", "scope": "live"},
    "C10": {"verdict": "PASS", "scope": "harness"},
    "C10_native_memory_path": {"verdict": "NOT_RUN", "scope": "live"},
    "C11": {"verdict": "PASS", "scope": "harness"},
    "C11_7_live_repeat_rate": {"verdict": "NOT_RUN", "scope": "live"},
    "C12": {"verdict": "PASS", "scope": "mechanism"},
    "C12_os_rss_probe": {"verdict": "NOT_RUN", "scope": "host"},
    "C12_6_real_model_inference": {"verdict": "NOT_RUN", "scope": "live"},
    "C13_shape_and_soak": {"verdict": "PASS", "scope": "harness"},
    "C13_vm_numeric_thresholds": {"verdict": "GAP", "scope": "spec"},
    "C13_vm_live_effectiveness": {"verdict": "NOT_RUN", "scope": "live"},
    "S2_12_laya_verdict_schema_pin": {"verdict": "NOT_RUN", "scope": "upstream"},
    "native_cautreo_parity": {"verdict": "FAIL", "scope": "isolated"},
}

IMMUTABLES = {
    "vivy_train_dataset.jsonl": "8d1e68421572708324248ff8a06326e77449c292d2214498759f231a82b4531b",
    "evidence/gold_train.jsonl": "630a2ee442f20d942be210d219ca40eca4e2905cb83247c2d1e0d1e589ec44c7",
    "evidence/gold_review_queue.jsonl": "93cdcf3675facc0bf7dbaf2baef5f35cff1c5c47c0c13968ac176d97f8ca2ef7",
    "evidence/shadow_receipts.jsonl": "695a224b16b82baeeeac499cb3e50fb74ceb2036e439ee8d92fbed51efbd0576",
}


def _counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in REQUIREMENTS.values():
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output = Path(argv[0]) if argv else DEFAULT_OUTPUT

    receipt = {
        "kind": "P5_FINAL_ACCEPTANCE_ROLLUP",
        "status_label": "PROPOSED_ACCEPTANCE_AT_HARNESS_LEVEL",
        "production_ready": "NOT_CLAIMED",
        "result_class": "TESTED_MECHANISM",
        "whole_goal_handoff": "NOT_CLAIMED",
        "requirements": REQUIREMENTS,
        "counts": _counts(),
        "packets": PACKETS,
        "immutables": IMMUTABLES,
        "claim_bans": [
            "PRODUCTION-READY",
            "0%",
            "O(1)",
            "latency_SLA",
            "EXECUTE_DIRECTLY_before_Evidence_Gate",
            "fabricated_gold",
            "LLM_critique_as_ground_truth",
            "simulation_as_production",
            "test_count_or_checkpoint_as_quality_evidence",
        ],
        "latency_claim": "NOT_A_PHYSICAL_ZERO",
        "notes": [
            "PASS always means PASS at the named scope only.",
            "See docs/plans/KNOWN_LIMITATIONS.md for every GAP/NOT_RUN/FAIL.",
            "This receipt is an index; recompute metrics from the per-component raw evidence.",
        ],
    }

    with open_write(output) as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "output": str(output),
                "counts": receipt["counts"],
                "production_ready": receipt["production_ready"],
                "whole_goal_handoff": receipt["whole_goal_handoff"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
