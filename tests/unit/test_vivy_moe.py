"""Unit tests for ViVy MoE (Mixture-of-Experts) 40B/7B configuration and router."""

from __future__ import annotations

import pytest

from nps_core.model_training import ConfigError, MoEConfig, MoERouter


def test_moe_config_compute_reduction() -> None:
    cfg = MoEConfig(total_parameters=40_000_000_000, active_parameters=7_000_000_000)
    assert cfg.num_total_experts == 8
    assert cfg.num_active_experts == 2
    assert round(cfg.compute_reduction_ratio, 4) == 0.825

    with pytest.raises(ConfigError, match="num_active_experts invalid"):
        MoEConfig(num_total_experts=4, num_active_experts=5)


def test_moe_router_expert_selection() -> None:
    vision_experts = MoERouter.route_task("vision_analysis")
    assert len(vision_experts) == 2
    assert "Multimodal_Vision" in vision_experts

    code_experts = MoERouter.route_task("code_ast")
    assert "Code_AST_Analysis" in code_experts
