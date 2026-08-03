"""Tests for core.state — QuantumState class."""

import numpy as np
import pytest

from core.state import QuantumState


class TestQuantumState:
    def test_init_basic(self):
        vec = np.array([1, 0], dtype=np.complex128)
        s = QuantumState(vec)
        assert s.n_qubits == 1
        assert s.dim == 2
        assert s.is_normalized

    def test_init_normalizes(self):
        vec = np.array([3, 0], dtype=np.complex128)
        s = QuantumState(vec)
        assert abs(s.norm() - 1.0) < 1e-12

    def test_init_invalid_dim(self):
        with pytest.raises(ValueError):
            QuantumState(np.array([1, 2, 3], dtype=np.complex128))

    def test_amplitudes(self):
        vec = np.array([1 + 1j, 1 - 1j], dtype=np.complex128)
        s = QuantumState(vec)
        amps = s.amplitudes
        expected = np.sqrt(2) / 2  # after normalization
        assert np.allclose(amps, [expected, expected])

    def test_phases(self):
        vec = np.array([1, 1j], dtype=np.complex128)
        s = QuantumState(vec)
        phases = s.phases
        assert np.allclose(phases, [0, np.pi / 2])

    def test_probs(self):
        vec = np.array([1, 0], dtype=np.complex128)
        s = QuantumState(vec)
        assert np.allclose(s.probs, [1, 0])

    def test_norm(self):
        vec = np.array([3, 4], dtype=np.complex128)
        s = QuantumState(vec, normalize=False)
        assert abs(s.norm() - 5.0) < 1e-12

    def test_inner_product(self):
        s1 = QuantumState(np.array([1, 0], dtype=np.complex128))
        s2 = QuantumState(np.array([0, 1], dtype=np.complex128))
        assert abs(s1.inner_product(s2)) < 1e-12
        assert abs(s1.inner_product(s1) - 1.0) < 1e-12

    def test_inner_product_dim_mismatch(self):
        s1 = QuantumState(np.array([1, 0], dtype=np.complex128))
        s2 = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        with pytest.raises(ValueError):
            s1.inner_product(s2)

    def test_fidelity(self):
        s1 = QuantumState(np.array([1, 0], dtype=np.complex128))
        s2 = QuantumState(np.array([0, 1], dtype=np.complex128))
        assert abs(s1.fidelity(s2)) < 1e-12
        assert abs(s1.fidelity(s1) - 1.0) < 1e-12

    def test_measure(self):
        vec = np.array([1, 0], dtype=np.complex128)
        s = QuantumState(vec)
        samples = s.measure(n_shots=100)
        assert np.all(samples == 0)

    def test_measure_qubit(self):
        # |01⟩ state (qubit 0 = 1, qubit 1 = 0)
        vec = np.array([0, 1, 0, 0], dtype=np.complex128)
        s = QuantumState(vec)
        outcome, collapsed = s.measure_qubit(0)
        assert outcome == 1
        assert collapsed.n_qubits == 2

    def test_measure_qubit_invalid(self):
        s = QuantumState(np.array([1, 0], dtype=np.complex128))
        with pytest.raises(ValueError):
            s.measure_qubit(5)

    def test_apply(self):
        from core.gates import hadamard, pauli_x

        s = QuantumState(np.array([1, 0], dtype=np.complex128))
        s2 = s.apply(pauli_x())
        assert np.allclose(s2.vector, [0, 1])

        # H|0⟩ = (|0⟩ + |1⟩)/√2
        s3 = s.apply(hadamard())
        expected = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
        assert np.allclose(s3.vector, expected)

    def test_copy(self):
        s1 = QuantumState(np.array([1, 0], dtype=np.complex128))
        s2 = s1.copy()
        assert s1 == s2
        assert s1.vector is not s2.vector  # different memory

    def test_repr(self):
        s = QuantumState(np.array([1, 0], dtype=np.complex128))
        r = repr(s)
        assert "QuantumState" in r
        assert "n_qubits=1" in r

    def test_eq(self):
        s1 = QuantumState(np.array([1, 0], dtype=np.complex128))
        s2 = QuantumState(np.array([1, 0], dtype=np.complex128))
        assert s1 == s2
        s3 = QuantumState(np.array([0, 1], dtype=np.complex128))
        assert s1 != s3

    def test_basis(self):
        s = QuantumState.basis(3, 5)  # |101⟩
        assert s.n_qubits == 3
        assert s.dim == 8
        assert np.allclose(s.vector[5], 1)
        assert np.allclose(s.vector.sum(), 1)

    def test_uniform(self):
        s = QuantumState.uniform(3)
        assert s.n_qubits == 3
        assert s.is_normalized
        expected = np.ones(8) / np.sqrt(8)
        assert np.allclose(s.amplitudes, expected)

    def test_from_probs(self):
        probs = np.array([0.25, 0.25, 0.25, 0.25])
        s = QuantumState.from_probs(probs)
        assert s.is_normalized
        assert np.allclose(s.probs, probs)

    def test_from_probs_invalid(self):
        with pytest.raises(ValueError):
            QuantumState.from_probs(np.array([0.5, 0.5, 0.5]))
