"""Unit tests for ViVy 40B Sparse MoE training pipeline and configuration."""

from __future__ import annotations

from nps_core.model_training import MODEL_MOE_40B, MoEConfig, MoERouter


def test_vivy_moe_40b_configuration() -> None:
    model_cfg = MODEL_MOE_40B.model
    assert model_cfg.num_layers == 32
    assert model_cfg.hidden_size == 4096
    assert model_cfg.num_attention_heads == 32

    moe_cfg = MoEConfig(total_parameters=40_000_000_000, active_parameters=7_000_000_000)
    assert moe_cfg.total_parameters == 40_000_000_000
    assert moe_cfg.active_parameters == 7_000_000_000
    assert round(moe_cfg.compute_reduction_ratio, 4) == 0.825


def test_vivy_moe_expert_routing_multidomain() -> None:
    experts_vision = MoERouter.route_task("multimodal_vision")
    assert "Multimodal_Vision" in experts_vision

    experts_nlp = MoERouter.route_task("bilingual_nlp")
    assert "Bilingual_NLP_EN_VI" in experts_nlp
