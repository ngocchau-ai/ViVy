"""Unit tests for ViVy 1B Student Model training configuration and parameter estimation."""

from __future__ import annotations

import json
from pathlib import Path

from nps_core.model_training import MODEL_1B, TrainingState, get_learning_rate


def test_vivy_1b_parameter_count() -> None:
    model_cfg = MODEL_1B.model
    est_params = model_cfg.estimate_params()

    assert model_cfg.num_layers == 24
    assert model_cfg.hidden_size == 2048
    assert model_cfg.num_attention_heads == 16
    assert 1_000_000_000 <= est_params <= 1_300_000_000, f"Expected ~1B params, got {est_params:,}"


def test_vivy_1b_learning_rate_schedule() -> None:
    training_cfg = MODEL_1B.training
    lr_step1 = get_learning_rate(1, training_cfg)
    lr_step100 = get_learning_rate(100, training_cfg)

    assert lr_step1 > 0.0
    assert lr_step100 >= lr_step1


def test_vivy_1b_training_state_checkpoint(tmp_path: Path) -> None:
    state = TrainingState(config=MODEL_1B.to_dict())
    metrics = state.update_step(
        loss=1.85,
        learning_rate=3e-4,
        grad_norm=0.5,
        num_tokens=4096,
        elapsed=0.02,
    )
    assert metrics.step == 1
    assert state.best_loss == 1.85

    ckpt_file = tmp_path / "checkpoint.json"
    ckpt_file.write_text(json.dumps(state.to_dict()), encoding="utf-8")
    assert ckpt_file.exists()
