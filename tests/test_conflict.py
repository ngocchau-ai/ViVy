"""Unit tests for funnel/conflict.py — detect_conflict and has_conflict."""

import numpy as np

from funnel._types import make_stream
from funnel.conflict import detect_conflict, has_conflict


def _stream(sv: float, a: np.ndarray) -> dict:
    return make_stream(
        singular_value=sv,
        amplitude_ratio=sv,
        state_A=a,
        state_B=np.array([0.0, 1.0], dtype=np.complex128),
    )


class TestDetectConflict:
    def test_empty_streams(self):
        result = detect_conflict([])
        assert not result["conflict"]
        assert result["n_conflicts"] == 0
        assert result["strong_indices"] == []

    def test_single_stream_no_conflict(self):
        s = [_stream(0.5, np.array([1.0, 0.0], dtype=np.complex128))]
        result = detect_conflict(s)
        assert not result["conflict"]

    def test_two_strong_orthogonal_streams_conflict(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.7, np.array([0.0, 1.0], dtype=np.complex128)),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert result["conflict"]
        assert result["n_conflicts"] == 1

    def test_two_strong_aligned_streams_no_conflict(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.7, np.array([1.0, 0.0], dtype=np.complex128)),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert not result["conflict"]

    def test_weak_streams_no_conflict(self):
        streams = [
            _stream(0.01, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.01, np.array([0.0, 1.0], dtype=np.complex128)),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert not result["conflict"]

    def test_mixed_strong_weak(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.01, np.array([0.0, 1.0], dtype=np.complex128)),
            _stream(0.7, np.array([0.0, 1.0], dtype=np.complex128)),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert result["conflict"]
        assert len(result["strong_indices"]) == 2  # only indices 0 and 2

    def test_three_streams_multiple_conflicts(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.7, np.array([0.0, 1.0], dtype=np.complex128)),
            _stream(0.6, np.array([0.0, -1.0], dtype=np.complex128)),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert result["conflict"]
        assert result["n_conflicts"] >= 1

    def test_custom_thresholds(self):
        streams = [
            _stream(0.3, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.2, np.array([0.0, 1.0], dtype=np.complex128)),
        ]
        # With min_amplitude=0.25, only stream 0 is strong => no conflict.
        result = detect_conflict(streams, min_amplitude=0.25, overlap_threshold=0.5)
        assert not result["conflict"]

    def test_identical_vectors_no_conflict(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.7, np.array([1.0, 0.0], dtype=np.complex128)),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert not result["conflict"]

    def test_complex_state_vectors(self):
        a = np.array([1.0 + 1.0j, 0.0], dtype=np.complex128)
        b = np.array([0.0, 1.0 - 1.0j], dtype=np.complex128)
        streams = [
            _stream(0.8, a),
            _stream(0.7, b),
        ]
        result = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert result["conflict"]

    def test_different_dimensions(self):
        """Streams with different-dim state_A should not crash."""
        streams = [
            make_stream(
                singular_value=0.8,
                amplitude_ratio=0.8,
                state_A=np.array([1.0, 0.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.7,
                amplitude_ratio=0.7,
                state_A=np.array([0.0, 1.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        result = detect_conflict(streams)
        assert isinstance(result["conflict"], bool)


class TestHasConflict:
    def test_wrapper_true(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.7, np.array([0.0, 1.0], dtype=np.complex128)),
        ]
        assert has_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)

    def test_wrapper_false(self):
        streams = [
            _stream(0.8, np.array([1.0, 0.0], dtype=np.complex128)),
            _stream(0.7, np.array([1.0, 0.0], dtype=np.complex128)),
        ]
        assert not has_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)

    def test_wrapper_empty(self):
        assert not has_conflict([])
