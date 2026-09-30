"""Integration test for ViVy 1B Student Model end-to-end training pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.train_vivy_1b import run_training


def test_vivy_1b_full_pipeline(tmp_path: Path) -> None:
    res = run_training()

    assert res["status"] == "SUCCESS"
    assert res["estimated_parameters"] > 1_000_000_000
    assert Path(res["checkpoint_path"]).exists()

    ckpt_data = json.loads(Path(res["checkpoint_path"]).read_text(encoding="utf-8"))
    assert ckpt_data["model_name"] == "ViVy-1B-Student"
    assert len(ckpt_data["training_state"]["metrics_history"]) == 10
    assert res["latency_sla_ms"]["max_latency_ms"] < 200.0
