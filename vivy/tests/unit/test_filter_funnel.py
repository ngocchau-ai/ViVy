"""Unit tests for Phễu lọc Tự kiểm chứng (Self-Verification Filter Funnel)."""

import math

import pytest

from nps_core.filter_funnel import (
    AmplitudeAnalyzer,
    ExtractedThoughtPattern,
    FilterFunnel,
    FunnelResult,
    FunnelSignal,
    LogicFilter,
    SVDDecomposer,
    ThoughtStream,
)


def test_amplitude_analyzer_entropy_and_normalization():
    # Vector trạng thái đồng đều 4 chiều
    state = [1.0, 1.0, 1.0, 1.0]
    report = AmplitudeAnalyzer.analyze(state, top_k=4)

    assert len(report.probabilities) == 4
    # Với 4 trạng thái đồng đều, p = 0.25 -> Entropy = -4 * 0.25 * log2(0.25) = 2.0
    assert pytest.approx(report.entropy, abs=1e-3) == 2.0
    assert not report.phase_conflict_detected


def test_amplitude_analyzer_destructive_interference():
    # Hai trạng thái có biên độ lớn nhưng lệch pha pi (1 và -1 = exp(i*pi))
    state = [1.0, -1.0, 0.05, 0.05]
    report = AmplitudeAnalyzer.analyze(state, top_k=4, phase_conflict_threshold=0.8 * math.pi)

    assert report.phase_conflict_detected
    assert len(report.destructive_pairs) >= 1


def test_svd_decomposer_stream_extraction():
    # State 4 chiều (2^1 x 2^1)
    state = [1.0, 0.0, 0.0, 1.0]
    streams = SVDDecomposer.decompose(state_vector=state, partition=(1, 1), threshold=0.01)

    assert len(streams) >= 1
    top_stream = streams[0]
    assert isinstance(top_stream, ThoughtStream)
    assert top_stream.singular_value > 0
    assert len(top_stream.state_a) == 2
    assert len(top_stream.state_b) == 2


def test_logic_filter_evaluation():
    stream1 = ThoughtStream(
        stream_index=0,
        singular_value=1.0,
        amplitude_ratio=0.8,
        state_a=(complex(1, 0), complex(0, 0)),
        state_b=(complex(1, 0), complex(0, 0)),
    )
    stream2 = ThoughtStream(
        stream_index=1,
        singular_value=0.2,
        amplitude_ratio=0.1,
        state_a=(complex(0, 0), complex(1, 0)),
        state_b=(complex(0, 0), complex(1, 0)),
    )

    filter_report = LogicFilter.filter_streams([stream1, stream2], step_count=1)

    assert len(filter_report.evaluated_streams) == 2
    assert len(filter_report.accepted_streams) >= 1
    assert filter_report.accepted_streams[0].stream.stream_index == 0


def test_filter_funnel_full_pipeline_halt_signal():
    # Vector tập trung vào 1 trạng thái -> Entropy thấp -> HALT
    state = [1.0, 0.01, 0.01, 0.01]
    funnel = FilterFunnel(entropy_halt_threshold=0.6, confidence_halt_threshold=0.5)

    result = funnel.evaluate_state(state, partition=(1, 1))

    assert isinstance(result, FunnelResult)
    assert result.signal == FunnelSignal.MEASURE_AND_HALT
    assert result.extracted_pattern is not None
    assert isinstance(result.extracted_pattern, ExtractedThoughtPattern)


def test_filter_funnel_backtrack_signal():
    # Vector rỗng -> BACKTRACK
    funnel = FilterFunnel()
    result = funnel.evaluate_state([], partition=(1, 1))

    assert result.signal == FunnelSignal.BACKTRACK
    assert result.overall_confidence == 0.0
