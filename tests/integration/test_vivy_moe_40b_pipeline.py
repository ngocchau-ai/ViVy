"""Integration test for ViVy 40B Sparse MoE training pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.train_vivy_moe_40b import run_training


def test_vivy_moe_40b_full_pipeline() -> None:
    res = run_training()

    assert res["status"] == "SUCCESS"
    assert res["total_parameters"] == 40_000_000_000
    assert res["active_parameters"] == 7_000_000_000
    assert Path(res["checkpoint_path"]).exists()

    ckpt = json.loads(Path(res["checkpoint_path"]).read_text(encoding="utf-8"))
    assert ckpt["model_name"] == "ViVy-40B-Sparse-MoE"
    assert ckpt["compute_reduction_ratio"] == 0.825
    assert len(ckpt["training_state"]["metrics_history"]) == 10
    assert res["latency_sla_ms"]["max_latency_ms"] < 200.0
