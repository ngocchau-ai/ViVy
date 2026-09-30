"""Tests for core.entropy — shannon_entropy and interference_detection."""

import numpy as np
import pytest

from core.entropy import interference_detection, shannon_entropy, von_neumann_entropy
from core.state import QuantumState


class TestShannonEntropy:
    def test_certain(self):
        # H([1, 0]) = 0
        assert abs(shannon_entropy(np.array([1.0, 0.0])) - 0.0) < 1e-12

    def test_uniform_bits(self):
        # H([0.5, 0.5]) = 1 bit
        assert abs(shannon_entropy(np.array([0.5, 0.5])) - 1.0) < 1e-12

    def test_uniform_4(self):
        # H([0.25]*4) = 2 bits
        assert abs(shannon_entropy(np.ones(4) / 4) - 2.0) < 1e-12

    def test_natural_log_base(self):
        # H([0.5, 0.5]) with base e = ln 2
        assert abs(shannon_entropy(np.array([0.5, 0.5]), base=np.e) - np.log(2)) < 1e-12

    def test_unnormalized(self):
        # H([2, 2]) = H([0.5, 0.5]) = 1
        assert abs(shannon_entropy(np.array([2.0, 2.0])) - 1.0) < 1e-12

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            shannon_entropy(np.array([1.0, -0.5]))

    def test_zero_entropy_for_zero(self):
        assert shannon_entropy(np.zeros(4)) == 0.0


class TestVonNeumannEntropy:
    def test_product_state_zero(self):
        # Product state has zero entanglement entropy
        state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        s = von_neumann_entropy(state, partition=[0])
        assert abs(s) < 1e-10

    def test_bell_state_one_bit(self):
        # Bell state (|00⟩ + |11⟩)/√2 has entropy 1 bit
        vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        state = QuantumState(vec)
        s = von_neumann_entropy(state, partition=[0])
        assert abs(s - 1.0) < 1e-10


class TestInterferenceDetection:
    def test_product_state_no_interference(self):
        # |00⟩ has no interference
        state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        result = interference_detection(state)
        assert result["has_interference"] is False
        assert result["interference_magnitude"] < 1e-8

    def test_superposition_has_interference(self):
        # A non-product superposition (|00⟩ + |01⟩ + |10⟩)/√3 has
        # interference: its Born probabilities [1/3,1/3,1/3,0] differ from
        # the classical product of single-qubit marginals.
        vec = np.array([1, 1, 1, 0], dtype=np.complex128) / np.sqrt(3)
        state = QuantumState(vec)
        result = interference_detection(state)
        assert result["has_interference"] is True

    def test_product_superposition_no_interference(self):
        # A uniform superposition is a product state (H|0⟩ ⊗ H|0⟩), so the
        # Born probabilities match the classical product of marginals → no interference.
        state = QuantumState.uniform(2)
        result = interference_detection(state)
        assert result["has_interference"] is False

    def test_bell_state_has_interference(self):
        # Bell state (|00⟩ + |11⟩)/√2 has interference
        vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        state = QuantumState(vec)
        result = interference_detection(state)
        assert result["has_interference"] is True

    def test_entropy_in_result(self):
        state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        result = interference_detection(state)
        assert "entropy" in result
        assert result["entropy"] == 0.0

    def test_max_interfering_basis(self):
        state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        result = interference_detection(state)
        assert "max_interfering_basis" in result
