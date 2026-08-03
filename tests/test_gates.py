"""Tests for core.gates — unitary and logic gates."""

import numpy as np
import pytest

from core.gates import (
    and_intro,
    apply_gate_to_state,
    cnot,
    hadamard,
    modus_ponens,
    modus_tollens,
    or_elim,
    pauli_x,
    pauli_y,
    pauli_z,
    swap,
    tensor_product_gate,
    toffoli,
)


def assert_unitary(mat: np.ndarray) -> None:
    """Assert that a matrix is unitary."""
    n = mat.shape[0]
    assert mat.shape == (n, n)
    assert np.allclose(mat @ mat.conj().T, np.eye(n), atol=1e-12)


# ---------------------------------------------------------------------------
# Single-qubit gates
# ---------------------------------------------------------------------------


def test_pauli_x():
    X = pauli_x()
    assert_unitary(X)
    # X|0⟩ = |1⟩
    assert np.allclose(X @ np.array([1, 0]), [0, 1])
    assert np.allclose(X @ np.array([0, 1]), [1, 0])


def test_pauli_y():
    Y = pauli_y()
    assert_unitary(Y)
    assert np.allclose(Y @ np.array([1, 0]), [0, 1j])
    assert np.allclose(Y @ np.array([0, 1]), [-1j, 0])


def test_pauli_z():
    Z = pauli_z()
    assert_unitary(Z)
    assert np.allclose(Z @ np.array([1, 0]), [1, 0])
    assert np.allclose(Z @ np.array([0, 1]), [0, -1])


def test_hadamard():
    H = hadamard()
    assert_unitary(H)
    h0 = H @ np.array([1, 0])
    assert np.allclose(h0, [1 / np.sqrt(2), 1 / np.sqrt(2)])
    # H² = I
    assert np.allclose(H @ H, np.eye(2))


# ---------------------------------------------------------------------------
# Two-qubit gates
# ---------------------------------------------------------------------------


def test_cnot():
    CNOT = cnot()
    assert_unitary(CNOT)
    # CNOT|00⟩ = |00⟩, CNOT|01⟩ = |01⟩, CNOT|10⟩ = |11⟩, CNOT|11⟩ = |10⟩
    assert np.allclose(CNOT @ np.eye(4), np.eye(4)[:, [0, 1, 3, 2]])


def test_swap():
    SWAP = swap()
    assert_unitary(SWAP)
    # SWAP|01⟩ = |10⟩
    assert np.allclose(SWAP @ np.eye(4), np.eye(4)[:, [0, 2, 1, 3]])
    # SWAP² = I
    assert np.allclose(SWAP @ SWAP, np.eye(4))


# ---------------------------------------------------------------------------
# Three-qubit gates
# ---------------------------------------------------------------------------


def test_toffoli():
    T = toffoli()
    assert_unitary(T)
    # Toffoli|110⟩ = |111⟩, Toffoli|111⟩ = |110⟩
    assert np.allclose(T @ np.eye(8), np.eye(8)[:, [0, 1, 2, 3, 4, 5, 7, 6]])


def test_modus_ponens():
    MP = modus_ponens()
    assert_unitary(MP)
    # P=1, (P→Q)=1, Q=0 → Q becomes 1: |1,1,0⟩ → |1,1,1⟩
    # index of |1,1,0⟩ = 0b110 = 6, |1,1,1⟩ = 7
    assert np.allclose(MP @ np.eye(8), np.eye(8)[:, [0, 1, 2, 3, 4, 5, 7, 6]])


def test_modus_tollens():
    MT = modus_tollens()
    assert_unitary(MT)
    # ¬Q=1, (P→Q)=1 → ¬P=1: |1,1,0⟩ → |1,1,1⟩
    assert np.allclose(MT @ np.eye(8), np.eye(8)[:, [0, 1, 2, 3, 4, 5, 7, 6]])


def test_and_intro():
    AI = and_intro()
    assert_unitary(AI)
    # P=1, Q=1 → P∧Q=1: |1,1,0⟩ → |1,1,1⟩
    assert np.allclose(AI @ np.eye(8), np.eye(8)[:, [0, 1, 2, 3, 4, 5, 7, 6]])


def test_or_elim():
    OE = or_elim()
    assert_unitary(OE)
    assert_unitary(OE)


# ---------------------------------------------------------------------------
# Gate application helpers
# ---------------------------------------------------------------------------


def test_tensor_product_gate_single():
    # Embed Hadamard on qubit 0 of a 2-qubit system
    H = hadamard()
    full = tensor_product_gate(H, 2, [0])
    assert full.shape == (4, 4)
    assert_unitary(full)
    # H ⊗ I
    expected = np.kron(np.eye(2), H)
    assert np.allclose(full, expected)


def test_tensor_product_gate_second_qubit():
    # Embed Hadamard on qubit 1 of a 2-qubit system → I ⊗ H
    H = hadamard()
    full = tensor_product_gate(H, 2, [1])
    expected = np.kron(H, np.eye(2))
    assert np.allclose(full, expected)


def test_tensor_product_gate_cnot():
    # CNOT on qubits [0,1] of 2-qubit system is just CNOT
    full = tensor_product_gate(cnot(), 2, [0, 1])
    assert np.allclose(full, cnot())


def test_tensor_product_gate_invalid():
    with pytest.raises(ValueError):
        tensor_product_gate(hadamard(), 2, [0, 1])  # wrong size
    with pytest.raises(ValueError):
        tensor_product_gate(hadamard(), 2, [5])  # out of range
    with pytest.raises(ValueError):
        tensor_product_gate(cnot(), 3, [0, 0])  # duplicate


def test_apply_gate_to_state():
    # Apply X to qubit 0 of |00⟩ → |01⟩ (index 1)
    state = np.array([1, 0, 0, 0], dtype=np.complex128)
    result = apply_gate_to_state(state, pauli_x(), [0])
    assert np.allclose(result, [0, 1, 0, 0])

    # Apply X to qubit 1 of |00⟩ → |10⟩ (index 2)
    result = apply_gate_to_state(state, pauli_x(), [1])
    assert np.allclose(result, [0, 0, 1, 0])

    # Apply CNOT to |10⟩ → |11⟩
    state10 = np.array([0, 0, 1, 0], dtype=np.complex128)
    result = apply_gate_to_state(state10, cnot(), [0, 1])
    assert np.allclose(result, [0, 0, 0, 1])


def test_apply_gate_full_dim():
    state = np.array([1, 0, 0, 0], dtype=np.complex128)
    result = apply_gate_to_state(state, cnot(), None)
    assert np.allclose(result, [1, 0, 0, 0])
