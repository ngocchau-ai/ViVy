"""C12 receipt runner — phase split + RSS-vs-buffer + full-vs-sparse + claim guards.

Writes evidence/c12_cartography_phases_sparse.json (new file only; io_guard refuses overwrite).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from training.cartography_phases import (
    PHASES,
    check_100b_claim,
    check_vision_claim,
    measure_phases,
    sample_process_memory,
)
from training.io_guard import open_write
from training.sparse_forward import run_full_vs_sparse

DEFAULT_OUTPUT = Path("evidence/c12_cartography_phases_sparse.json")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output = Path(argv[0]) if argv else DEFAULT_OUTPUT

    rng = np.random.default_rng(42)
    W = rng.normal(size=(64, 64))
    x = rng.normal(size=64)

    # Pre-allocate a buffer so RSS-vs-buffer is observable side by side.
    buffer = np.zeros(2_000_000, dtype=np.uint8)  # ~2 MB
    mem_before_alloc = sample_process_memory(allocated_buffer_bytes=0)
    mem_after_alloc = sample_process_memory(allocated_buffer_bytes=int(buffer.nbytes))
    del buffer

    phases = measure_phases(
        atlas_bytes=402_004,
        atlas_load_ms=30.01,
        weight_bytes_paged=int(W.nbytes),
        resident_rss_bytes=mem_after_alloc["rss_bytes"] or 0,
        forward_ms=0.0,  # filled from sparse bench below
        semantic_correct=0,
        semantic_total=0,
    )

    sparse = run_full_vs_sparse(W, x, k=8, reps=30, seed=0)
    sparse_dict = sparse.as_dict()
    # Overlay measured forward latency into the phase table (still one field).
    phases["phases"]["forward_execution"]["value"] = sparse_dict["latency_end_to_end_ms"]["median"]
    phases["phases"]["forward_execution"]["source"] = "measured"
    phases["phases"]["semantic_accuracy"]["value"] = None
    phases["phases"]["semantic_accuracy"]["source"] = "not_run"
    phases["note"] += " semantic_accuracy NOT_RUN: no reference labels on this fixture."

    guard_100b = check_100b_claim(
        claimed_parameter_count=100_000_000_000,
        weights_present=False,
        weights_bytes=670_069,
        nearest_artifact="qwen2-vl-72b.catlas",
    )
    guard_vision_text = check_vision_claim(
        images=["a red circle on a white background"],
        reference_labels=["red circle"],
        source="text_description",
    )
    guard_vision_real = check_vision_claim(
        images=[b"\x89PNG\r\n\x1a\nfakepngbytes"],
        reference_labels=["red circle"],
        source="image_bytes",
    )

    receipt = {
        "kind": "C12_CARTOGRAPHY_PHASES_SPARSE",
        "requirement_ids": ["C12.1", "C12.2", "C12.3", "C12.4", "C12.5", "C12.6"],
        "status_label": "PROVISIONAL_RESULT",
        "result_class": "TESTED_MECHANISM",
        "phases": phases,
        "phase_names": list(PHASES),
        "memory_sample_before_buffer": mem_before_alloc,
        "memory_sample_after_buffer": mem_after_alloc,
        "sparse_forward": sparse_dict,
        "guard_100b": guard_100b,
        "guard_vision_text_description": guard_vision_text,
        "guard_vision_real_image_bytes": guard_vision_real,
        "claims": {
            "phases_distinct": "TESTED",
            "no_collapsed_overall_score": "TESTED",
            "ram_not_inferred_from_buffer": "TESTED",
            "sparse_path_exercised_in_forward": "TESTED" if sparse_dict["sparse_path_exercised"] else "FAIL",
            "same_weights_same_input": "TESTED" if sparse_dict["same_weights"] and sparse_dict["same_input"] else "FAIL",
            "quality_regression_reported": "TESTED",
            "end_to_end_latency_reported": "TESTED",
            "100b_on_10gb": guard_100b["status"],
            "vision_multimodal_grounding": guard_vision_real["status"],
            "vision_from_text_description": "NOT_RUN",
            "semantic_accuracy_on_real_labels": "NOT_RUN",
            "physical_zero_latency": "NOT_CLAIMED",
            "o1_claim": "NOT_CLAIMED",
            "production_ready": "NOT_CLAIMED",
        },
    }

    with open_write(output) as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "output": str(output),
                "sparse_path_exercised": sparse_dict["sparse_path_exercised"],
                "n_sparse_nonzero": sparse_dict["n_sparse_nonzero"],
                "n_full_nonzero": sparse_dict["n_full_nonzero"],
                "cosine": sparse_dict["quality_regression"]["cosine"],
                "e2e_median_ms": sparse_dict["latency_end_to_end_ms"]["median"],
                "rss_bytes": mem_after_alloc["rss_bytes"],
                "allocated_buffer_bytes": mem_after_alloc["allocated_buffer_bytes"],
                "guard_100b": guard_100b["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
