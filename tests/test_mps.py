"""Tests for core.mps — MPS class."""

import numpy as np
import pytest

from core.gates import cnot, hadamard, pauli_x
from core.mps import MPS


def _bell_state_mps():
    """Create MPS for (|00⟩ + |11⟩)/√2."""
    # Tensor 0: (1, 2, 2)
    t0 = np.zeros((1, 2, 2), dtype=np.complex128)
    t0[0, 0, 0] = 1.0
    t0[0, 1, 1] = 1.0
    # Tensor 1: (2, 2, 1)
    t1 = np.zeros((2, 2, 1), dtype=np.complex128)
    t1[0, 0, 0] = 1.0 / np.sqrt(2)
    t1[1, 1, 0] = 1.0 / np.sqrt(2)
    return MPS([t0, t1], canonicalize=False)


class TestMPS:
    def test_init_basic(self):
        t0 = np.ones((1, 2, 1), dtype=np.complex128)
        mps = MPS([t0])
        assert mps.n_qubits == 1
        assert mps.bond_dims == [1, 1]

    def test_init_invalid_shape(self):
        with pytest.raises(ValueError):
            MPS([np.ones((1, 3, 1), dtype=np.complex128)])  # phys dim != 2

    def test_init_bond_mismatch(self):
        t0 = np.ones((1, 2, 3), dtype=np.complex128)
        t1 = np.ones((4, 2, 1), dtype=np.complex128)
        with pytest.raises(ValueError):
            MPS([t0, t1])

    def test_init_final_bond_not_one(self):
        t0 = np.ones((1, 2, 2), dtype=np.complex128)
        t1 = np.ones((2, 2, 2), dtype=np.complex128)
        with pytest.raises(ValueError):
            MPS([t0, t1])

    def test_properties(self):
        mps = _bell_state_mps()
        assert mps.n_qubits == 2
        assert mps.max_bond_dim == 2
        assert mps.bond_dimension == 2

    def test_norm(self):
        mps = _bell_state_mps()
        assert abs(mps.norm() - 1.0) < 1e-10

    def test_to_vector(self):
        mps = _bell_state_mps()
        vec = mps.to_vector()
        expected = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        assert np.allclose(vec, expected)

    def test_from_vector(self):
        vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        mps = MPS.from_vector(vec, bond_dim=2)
        recovered = mps.to_vector()
        assert np.allclose(recovered, vec)

    def test_from_vector_product_state(self):
        # |01⟩
        vec = np.array([0, 1, 0, 0], dtype=np.complex128)
        mps = MPS.from_vector(vec, bond_dim=1)
        assert mps.max_bond_dim == 1
        recovered = mps.to_vector()
        assert np.allclose(recovered, vec)

    def test_canonical_form(self):
        mps = _bell_state_mps()
        mps.canonical_form(target_center=0)
        assert mps.center == 0
        # Norm should still be 1
        assert abs(mps.norm() - 1.0) < 1e-10

    def test_canonical_form_center_1(self):
        mps = _bell_state_mps()
        mps.canonical_form(target_center=1)
        assert mps.center == 1
        assert abs(mps.norm() - 1.0) < 1e-10

    def test_apply_gate_single_qubit(self):
        # Start with |00⟩
        t0 = np.zeros((1, 2, 1), dtype=np.complex128)
        t0[0, 0, 0] = 1.0
        t1 = np.zeros((1, 2, 1), dtype=np.complex128)
        t1[0, 0, 0] = 1.0
        mps = MPS([t0, t1], canonicalize=False)

        # Apply X to qubit 0 → |01⟩
        mps.apply_gate(pauli_x(), [0])
        vec = mps.to_vector()
        assert np.allclose(vec, [0, 1, 0, 0])

    def test_apply_gate_hadamard(self):
        # Start with |00⟩
        t0 = np.zeros((1, 2, 1), dtype=np.complex128)
        t0[0, 0, 0] = 1.0
        t1 = np.zeros((1, 2, 1), dtype=np.complex128)
        t1[0, 0, 0] = 1.0
        mps = MPS([t0, t1], canonicalize=False)

        # Apply H to qubit 0 → (|00⟩ + |01⟩)/√2
        mps.apply_gate(hadamard(), [0])
        vec = mps.to_vector()
        expected = np.array([1, 1, 0, 0], dtype=np.complex128) / np.sqrt(2)
        assert np.allclose(vec, expected)

    def test_apply_gate_cnot(self):
        # Start with |10⟩ (qubit 0=0, qubit 1=1)
        t0 = np.zeros((1, 2, 1), dtype=np.complex128)
        t0[0, 1, 0] = 1.0
        t1 = np.zeros((1, 2, 1), dtype=np.complex128)
        t1[0, 0, 0] = 1.0
        mps = MPS([t0, t1], canonicalize=False)

        # CNOT with control=0, target=1 on |10⟩ → |11⟩
        mps.apply_gate(cnot(), [0, 1])
        vec = mps.to_vector()
        assert np.allclose(vec, [0, 0, 0, 1])

    def test_apply_gate_invalid_qubit(self):
        mps = _bell_state_mps()
        with pytest.raises(ValueError):
            mps.apply_gate(pauli_x(), [5])

    def test_repr(self):
        mps = _bell_state_mps()
        r = repr(mps)
        assert "MPS" in r
        assert "n_qubits=2" in r

    def test_roundtrip_bell_state(self):
        """MPS → vector → MPS → vector should be consistent."""
        vec = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        mps = MPS.from_vector(vec, bond_dim=2)
        vec2 = mps.to_vector()
        assert np.allclose(vec, vec2)

    def test_three_qubit_product(self):
        """|010⟩ = qubit 0=0, qubit 1=1, qubit 2=0"""
        n = 3
        tensors = []
        for k in range(n):
            t = np.zeros((1, 2, 1), dtype=np.complex128)
            # qubit 1 should be |1⟩
            if k == 1:
                t[0, 1, 0] = 1.0
            else:
                t[0, 0, 0] = 1.0
            tensors.append(t)
        mps = MPS(tensors, canonicalize=False)
        vec = mps.to_vector()
        # |010⟩ in binary with qubit 0 = LSB: bit0=0, bit1=1, bit2=0 → index 2
        expected = np.zeros(8, dtype=np.complex128)
        expected[2] = 1.0
        assert np.allclose(vec, expected)
