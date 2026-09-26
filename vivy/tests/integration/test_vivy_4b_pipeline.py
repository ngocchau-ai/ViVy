"""Integration test for ViVy 40B -> 4B Distillation & Compression Pipeline."""


from scripts.compress_vivy_40b_to_4b import generate_sample_dataset

from nps_core.model_training.compressor import ModelCompressor


def test_full_compression_pipeline_integration():
    dataset = generate_sample_dataset()
    assert len(dataset) > 0

    metrics, curated = ModelCompressor.compress_40b_to_4b(dataset)

    assert metrics.original_parameters == 40_000_000_000
    assert metrics.compressed_parameters == 4_000_000_000
    assert metrics.flops_reduction_ratio >= 0.8
    assert metrics.distillation_loss > 0.0
    assert metrics.student_proposal_latency_ms < 100.0
    assert len(curated) < len(dataset)  # Noise and duplicates pruned
