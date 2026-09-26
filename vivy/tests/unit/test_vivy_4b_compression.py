"""Unit tests for ViVy 4B Model Compression & Domain-Prioritized Filter Funnel."""

import pytest

from nps_core.model_training.bridge import TrainingExample
from nps_core.model_training.compressor import (
    MODEL_COMPACT_4B,
    CompressionMetrics,
    DomainFilterFunnel,
    DomainPriority,
    ModelCompressor,
)


def make_ex(inp: str, out: str, thought_id: str, conf: float) -> TrainingExample:
    return TrainingExample(
        task="reasoning",
        system="sys",
        input=inp,
        output=out,
        metadata={"thought_id": thought_id, "confidence": conf},
        content_hash="",
    )


def test_model_compact_4b_config():
    assert MODEL_COMPACT_4B.num_layers == 28
    assert MODEL_COMPACT_4B.hidden_size == 3072
    assert MODEL_COMPACT_4B.num_attention_heads == 24
    assert MODEL_COMPACT_4B.num_kv_heads == 8


def test_domain_priority_weights():
    dp = DomainPriority(
        logic_reasoning_weight=0.35,
        matrix_algebra_weight=0.25,
        geometry_spatial_weight=0.20,
        bilingual_nlp_weight=0.20,
    )
    total = (
        dp.logic_reasoning_weight
        + dp.matrix_algebra_weight
        + dp.geometry_spatial_weight
        + dp.bilingual_nlp_weight
    )
    assert pytest.approx(total) == 1.0


def test_domain_filter_funnel_classification_and_deduplication():
    ex1 = make_ex(
        inp="Prove singular value decomposition of matrix A.",
        out="SVD matrix decomposition completed.",
        thought_id="T-1",
        conf=0.9,
    )
    ex2 = make_ex(
        inp="Tính diện tích tam giác vuông góc a, b.",
        out="Diện tích tam giác hình học.",
        thought_id="T-2",
        conf=0.85,
    )
    ex_duplicate = make_ex(
        inp="Prove singular value decomposition of matrix A.",
        out="SVD matrix decomposition completed.",
        thought_id="T-1",
        conf=0.9,
    )
    ex_noise = make_ex(
        inp="Noise prompt",
        out="Noise completion",
        thought_id="T-3",
        conf=0.1,  # Low confidence < 0.35
    )

    examples = [ex1, ex2, ex_duplicate, ex_noise]
    curated, counts = DomainFilterFunnel.filter_and_prioritize(examples)

    assert len(curated) == 2  # Duplicate and noise removed
    assert counts["matrix_algebra"] == 1
    assert counts["geometry_spatial"] == 1


def test_model_compressor_40b_to_4b():
    ex = make_ex(
        inp="Chain of thought logic reasoning.",
        out="Hypothesis verified.",
        thought_id="T-1",
        conf=0.9,
    )
    metrics, curated = ModelCompressor.compress_40b_to_4b([ex])

    assert isinstance(metrics, CompressionMetrics)
    assert metrics.original_parameters == 40_000_000_000
    assert metrics.compressed_parameters == 4_000_000_000
    assert metrics.parameter_reduction_ratio > 0.85
    assert metrics.student_proposal_latency_ms < 100.0
    assert len(curated) == 1
