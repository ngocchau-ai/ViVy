"""Unit tests for funnel/analysis.py — amplitude/phase, entropy, interference."""

import math

import numpy as np

from funnel._types import make_stream
from funnel.analysis import (
    amplitude_phase_analysis,
    entropy_analysis,
    interference_detection,
)


def _streams_2d(n: int = 3) -> list:
    """Helper: produce ``n`` streams with 2-D state vectors."""
    streams = []
    for i in range(n):
        theta = 2.0 * math.pi * i / max(1, n)
        a = np.array([math.cos(theta), math.sin(theta)], dtype=np.complex128)
        b = np.array([math.sin(theta), math.cos(theta)], dtype=np.complex128)
        streams.append(
            make_stream(
                singular_value=1.0 - 0.2 * i,
                amplitude_ratio=0.5 - 0.1 * i,
                state_A=a,
                state_B=b,
                interpretation=f"stream_{i}",
            )
        )
    return streams


class TestAmplitudePhaseAnalysis:
    def test_empty_streams(self):
        result = amplitude_phase_analysis([])
        assert result["n_streams"] == 0
        assert result["total_amplitude"] == 0.0
        assert result["max_amplitude"] == 0.0
        assert result["mean_amplitude"] == 0.0
        assert result["dominant"] == []
        assert result["phase_spread"] == 0.0

    def test_single_stream(self):
        s = [
            make_stream(
                singular_value=0.8,
                amplitude_ratio=1.0,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            )
        ]
        result = amplitude_phase_analysis(s)
        assert result["n_streams"] == 1
        assert abs(result["total_amplitude"] - 0.8) < 1e-12
        assert abs(result["max_amplitude"] - 0.8) < 1e-12
        assert len(result["dominant"]) == 1

    def test_multiple_streams(self):
        streams = _streams_2d(4)
        result = amplitude_phase_analysis(streams, top_k=2)
        assert result["n_streams"] == 4
        assert result["total_amplitude"] > 0.0
        assert len(result["dominant"]) == 2

    def test_dominant_sorted(self):
        streams = _streams_2d(5)
        result = amplitude_phase_analysis(streams, top_k=5)
        amps = [a for _, a, _ in result["dominant"]]
        assert all(amps[i] >= amps[i + 1] for i in range(len(amps) - 1))

    def test_phase_spread_single(self):
        s = [
            make_stream(
                singular_value=0.5,
                amplitude_ratio=1.0,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            )
        ]
        result = amplitude_phase_analysis(s)
        assert result["phase_spread"] == 0.0

    def test_top_k_larger_than_n(self):
        streams = _streams_2d(2)
        result = amplitude_phase_analysis(streams, top_k=10)
        assert len(result["dominant"]) == 2


class TestEntropyAnalysis:
    def test_empty_streams(self):
        result = entropy_analysis([])
        assert result["n_streams"] == 0
        assert result["entropy"] == 0.0

    def test_single_stream_zero_entropy(self):
        s = [
            make_stream(
                singular_value=1.0,
                amplitude_ratio=1.0,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            )
        ]
        result = entropy_analysis(s)
        assert result["n_streams"] == 1
        assert result["entropy"] == 0.0
        assert result["normalized_entropy"] == 0.0

    def test_uniform_amplitudes_max_entropy(self):
        streams = [
            make_stream(
                singular_value=1.0,
                amplitude_ratio=0.5,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=1.0,
                amplitude_ratio=0.5,
                state_A=np.array([0.0, 1.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = entropy_analysis(streams)
        assert result["n_streams"] == 2
        # Uniform distribution => entropy = log(2).
        assert abs(result["entropy"] - math.log(2)) < 1e-12
        assert abs(result["normalized_entropy"] - 1.0) < 1e-12

    def test_skewed_amplitudes_low_entropy(self):
        streams = [
            make_stream(
                singular_value=0.99,
                amplitude_ratio=0.99,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.01,
                amplitude_ratio=0.01,
                state_A=np.array([0.0, 1.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = entropy_analysis(streams)
        assert result["entropy"] < math.log(2) * 0.5  # significantly lower than max

    def test_all_zero_amplitudes(self):
        streams = [
            make_stream(
                singular_value=0.0,
                amplitude_ratio=0.0,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.0,
                amplitude_ratio=0.0,
                state_A=np.array([0.0, 1.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = entropy_analysis(streams)
        assert result["entropy"] == 0.0


class TestInterferenceDetection:
    def test_empty_streams(self):
        result = interference_detection([])
        assert not result["interference"]
        assert result["n_interfering_pairs"] == 0

    def test_single_stream_no_interference(self):
        s = [
            make_stream(
                singular_value=0.5,
                amplitude_ratio=1.0,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            )
        ]
        result = interference_detection(s)
        assert not result["interference"]

    def test_constructive_interference(self):
        """Two streams with same phase => constructive."""
        streams = [
            make_stream(
                singular_value=0.5,
                amplitude_ratio=0.5,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.5,
                amplitude_ratio=0.5,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = interference_detection(streams, phase_tol=0.5, amp_ratio_tol=0.1)
        assert result["interference"]
        assert any(kind == "constructive" for _, _, kind, _, _ in result["pairs"])

    def test_destructive_interference(self):
        """Two streams with opposite phase => destructive."""
        streams = [
            make_stream(
                singular_value=0.5,
                amplitude_ratio=0.5,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.5,
                amplitude_ratio=0.5,
                state_A=np.array([-1.0, 0.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = interference_detection(streams, phase_tol=0.5, amp_ratio_tol=0.1)
        assert result["interference"]
        assert any(kind == "destructive" for _, _, kind, _, _ in result["pairs"])

    def test_no_interference_weak_streams(self):
        streams = [
            make_stream(
                singular_value=0.01,
                amplitude_ratio=0.01,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.01,
                amplitude_ratio=0.01,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = interference_detection(streams, amp_ratio_tol=0.5)
        assert not result["interference"]

    def test_no_interference_different_phases(self):
        streams = [
            make_stream(
                singular_value=0.5,
                amplitude_ratio=0.5,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.5,
                amplitude_ratio=0.5,
                state_A=np.array([0.0, 1.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        # Phase diff = pi/2, outside tolerance.
        result = interference_detection(streams, phase_tol=0.1)
        assert not result["interference"]
