"""Tests for core.svd_streams — extract_thought_streams."""

import numpy as np

from core.state import QuantumState
from core.svd_streams import ThoughtStream, dominant_stream, extract_thought_streams


def test_product_state_single_stream():
    """A product state |00⟩ should yield exactly one stream."""
    state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
    streams = extract_thought_streams(state, partition=[0], threshold=0.05)
    assert len(streams) == 1
    assert abs(streams[0].singular_value - 1.0) < 1e-10
    assert abs(streams[0].amplitude_ratio - 1.0) < 1e-10


def test_bell_state_two_streams():
    """A Bell state (|00⟩ + |11⟩)/√2 has two equal streams."""
    vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
    state = QuantumState(vec)
    streams = extract_thought_streams(state, partition=[0], threshold=0.01)
    assert len(streams) == 2
    # Both singular values ≈ 1/√2
    assert np.allclose([s.singular_value for s in streams], [1 / np.sqrt(2)] * 2)


def test_stream_amplitude_ratios_sum_to_one():
    """Amplitude ratios of all streams should sum to 1."""
    vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
    state = QuantumState(vec)
    streams = extract_thought_streams(state, partition=[0], threshold=0.0)
    total = sum(s.amplitude_ratio for s in streams)
    assert abs(total - 1.0) < 1e-10


def test_stream_substates():
    """Each stream's sub-states should be normalized."""
    vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
    state = QuantumState(vec)
    streams = extract_thought_streams(state, partition=[0], threshold=0.01)
    for s in streams:
        assert s.state_A.is_normalized
        assert s.state_B.is_normalized
        assert s.state_A.n_qubits == 1
        assert s.state_B.n_qubits == 1


def test_partition_two_qubits():
    """Partition [0,1] on a 3-qubit state gives A of dim 4, B of dim 2."""
    vec = np.zeros(8, dtype=np.complex128)
    vec[0] = 1.0 / np.sqrt(2)
    vec[7] = 1.0 / np.sqrt(2)
    state = QuantumState(vec)
    streams = extract_thought_streams(state, partition=[0, 1], threshold=0.01)
    assert len(streams) == 2
    for s in streams:
        assert s.state_A.dim == 4
        assert s.state_B.dim == 2


def test_threshold_filters():
    """Higher threshold should filter out small streams."""
    # Normalized vector: amplitudes 0.9 and 0.1 (0.9² + 0.1² = 0.82 ≠ 1,
    # so QuantumState renormalizes; use a properly normalized vector instead)
    a = 0.9 / np.sqrt(0.82)
    b = 0.1 / np.sqrt(0.82)
    vec = np.array([a, 0, 0, b], dtype=np.complex128)
    state = QuantumState(vec)
    # With high threshold, only the dominant stream survives
    streams = extract_thought_streams(state, partition=[0], threshold=0.5)
    assert len(streams) == 1
    assert abs(streams[0].singular_value - a) < 1e-6


def test_max_streams_limit():
    vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
    state = QuantumState(vec)
    streams = extract_thought_streams(state, partition=[0], threshold=0.0, max_streams=1)
    assert len(streams) == 1


def test_thought_stream_repr():
    s = ThoughtStream(
        singular_value=0.7,
        amplitude_ratio=0.49,
        state_A=QuantumState(np.array([1, 0], dtype=np.complex128)),
        state_B=QuantumState(np.array([1, 0], dtype=np.complex128)),
    )
    r = repr(s)
    assert "ThoughtStream" in r


def test_dominant_stream():
    a = 0.9 / np.sqrt(0.82)
    b = 0.1 / np.sqrt(0.82)
    vec = np.array([a, 0, 0, b], dtype=np.complex128)
    state = QuantumState(vec)
    stream = dominant_stream(state, partition=[0], threshold=0.0)
    assert stream is not None
    assert abs(stream.singular_value - a) < 1e-6
