"""Unitary gates for the Unitary Reasoner.

Provides standard quantum gates (Pauli X, Y, Z, Hadamard, CNOT, SWAP, Toffoli)
and logic-gate analogues (ModusPonens, ModusTollens, AndIntro, OrElim) as
2ⁿ × 2ⁿ unitary matrices using numpy (complex128).

All logic gates are implemented as 3-qubit (8×8) unitary matrices that encode
classical inference rules as reversible quantum operations.

Functions
---------
pauli_x() -> np.ndarray
pauli_y() -> np.ndarray
pauli_z() -> np.ndarray
hadamard() -> np.ndarray
cnot() -> np.ndarray
swap() -> np.ndarray
toffoli() -> np.ndarray
modus_ponens() -> np.ndarray
modus_tollens() -> np.ndarray
and_intro() -> np.ndarray
or_elim() -> np.ndarray
apply_gate_to_state(state, gate, qubits) -> np.ndarray
tensor_product_gate(gate, n_qubits, target_qubits) -> np.ndarray
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Single-qubit gates (2 × 2)
# ---------------------------------------------------------------------------


def pauli_x() -> NDArray[np.complex128]:
    r"""Pauli-X gate (quantum NOT).

    .. math::
        X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        2×2 unitary matrix.
    """
    return np.array([[0, 1], [1, 0]], dtype=np.complex128)


def pauli_y() -> NDArray[np.complex128]:
    r"""Pauli-Y gate.

    .. math::
        Y = \begin{pmatrix} 0 & -i \\ i & 0 \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        2×2 unitary matrix.
    """
    return np.array([[0, -1j], [1j, 0]], dtype=np.complex128)


def pauli_z() -> NDArray[np.complex128]:
    r"""Pauli-Z gate (phase flip).

    .. math::
        Z = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        2×2 unitary matrix.
    """
    return np.array([[1, 0], [0, -1]], dtype=np.complex128)


def hadamard() -> NDArray[np.complex128]:
    r"""Hadamard gate (superposition).

    .. math::
        H = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        2×2 unitary matrix.
    """
    return np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)


# ---------------------------------------------------------------------------
# Two-qubit gates (4 × 4)
# ---------------------------------------------------------------------------


def cnot() -> NDArray[np.complex128]:
    r"""CNOT (controlled-NOT) gate.

    Controls on qubit 0, flips qubit 1.

    .. math::
        \text{CNOT} = \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 0 & 1 \\
            0 & 0 & 1 & 0
        \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        4×4 unitary matrix.
    """
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 0],
        ],
        dtype=np.complex128,
    )


def swap() -> NDArray[np.complex128]:
    r"""SWAP gate.

    Swaps the state of two qubits.

    .. math::
        \text{SWAP} = \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 0 & 1 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 0 & 1
        \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        4×4 unitary matrix.
    """
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.complex128,
    )


# ---------------------------------------------------------------------------
# Three-qubit gates (8 × 8)
# ---------------------------------------------------------------------------


def toffoli() -> NDArray[np.complex128]:
    r"""Toffoli (CCNOT) gate.

    Controls on qubits 0 and 1, flips qubit 2.

    .. math::
        \text{CCNOT} = \begin{pmatrix}
            I_6 & 0 & 0 \\
            0 & 0 & 1 \\
            0 & 1 & 0
        \end{pmatrix}

    Returns
    -------
    NDArray[np.complex128]
        8×8 unitary matrix.
    """
    mat = np.eye(8, dtype=np.complex128)
    # Flip |110⟩ ↔ |111⟩  (indices 6 and 7)
    mat[6, 6] = 0
    mat[7, 7] = 0
    mat[6, 7] = 1
    mat[7, 6] = 1
    return mat


# ---------------------------------------------------------------------------
# Logic gates (inference rules as 8×8 unitary matrices)
#
# Each logic gate acts on 3 qubits and encodes a classical inference rule
# as a reversible unitary transformation.  The mapping is:
#
#   ModusPonens  (P, P→Q, Q)  — if P=1 and (P→Q)=1 then set Q=1
#   ModusTollens (Q, P→Q, P)  — if ¬Q=1 and (P→Q)=1 then set ¬P=1
#   AndIntro     (P, Q, P∧Q)  — if P=1 and Q=1 then set (P∧Q)=1
#   OrElim       (P∨Q, ¬P, Q) — if (P∨Q)=1 and ¬P=1 then set Q=1
#
# All four are structurally Toffoli-like: two control qubits determine
# whether the target qubit is flipped to the "conclusion" state.
# ---------------------------------------------------------------------------


def modus_ponens() -> NDArray[np.complex128]:
    r"""Modus Ponens inference gate (3-qubit unitary).

    Encoding: |P, P→Q, Q⟩
    Rule: if P=1 and (P→Q)=1 then set Q=1.
    Maps |1,1,0⟩ → |1,1,1⟩; all other basis states unchanged.

    Returns
    -------
    NDArray[np.complex128]
        8×8 unitary matrix.
    """
    return toffoli()


def modus_tollens() -> NDArray[np.complex128]:
    r"""Modus Tollens inference gate (3-qubit unitary).

    Encoding: |¬Q, P→Q, P⟩
    Rule: if ¬Q=1 and (P→Q)=1 then set ¬P=1 (flip P from 1 to 0).
    Maps |1,1,1⟩ → |1,1,0⟩; all other basis states unchanged.

    Returns
    -------
    NDArray[np.complex128]
        8×8 unitary matrix.
    """
    mat = np.eye(8, dtype=np.complex128)
    # |1,1,1⟩ (index 7) → |1,1,0⟩ (index 6)
    mat[6, 6] = 0
    mat[7, 7] = 0
    mat[6, 7] = 1
    mat[7, 6] = 1
    return mat


def and_intro() -> NDArray[np.complex128]:
    r"""And-Introduction inference gate (3-qubit unitary).

    Encoding: |P, Q, P∧Q⟩
    Rule: if P=1 and Q=1 then set (P∧Q)=1.
    Maps |1,1,0⟩ → |1,1,1⟩; all other basis states unchanged.

    Returns
    -------
    NDArray[np.complex128]
        8×8 unitary matrix.
    """
    return toffoli()


def or_elim() -> NDArray[np.complex128]:
    r"""Or-Elimination inference gate (3-qubit unitary).

    Encoding: |P∨Q, ¬P, Q⟩
    Rule: if (P∨Q)=1 and ¬P=1 then set Q=1.
    Maps |1,1,0⟩ → |1,1,1⟩; all other basis states unchanged.

    Returns
    -------
    NDArray[np.complex128]
        8×8 unitary matrix.
    """
    return toffoli()


# ---------------------------------------------------------------------------
# Gate application helpers
# ---------------------------------------------------------------------------


def tensor_product_gate(
    gate: NDArray[np.complex128],
    n_qubits: int,
    target_qubits: Sequence[int],
) -> NDArray[np.complex128]:
    """Embed a multi-qubit gate into a full n-qubit Hilbert space.

    Parameters
    ----------
    gate : NDArray[np.complex128]
        The k-qubit gate matrix (2ᵏ × 2ᵏ).
    n_qubits : int
        Total number of qubits in the system.
    target_qubits : Sequence[int]
        Indices of the qubits the gate acts on, in order.

    Returns
    -------
    NDArray[np.complex128]
        2ⁿ × 2ⁿ unitary matrix acting on the full space.

    Raises
    ------
    ValueError
        If gate dimension does not match target_qubits length, or if
        target_qubits are out of range.
    """
    k = len(target_qubits)
    expected_dim = 1 << k
    if gate.shape != (expected_dim, expected_dim):
        raise ValueError(
            f"Gate shape {gate.shape} does not match {k}-qubit gate "
            f"(expected {expected_dim}×{expected_dim})"
        )
    if any(q < 0 or q >= n_qubits for q in target_qubits):
        raise ValueError(f"target_qubits {target_qubits} out of range for {n_qubits} qubits")
    if len(set(target_qubits)) != k:
        raise ValueError(f"target_qubits {target_qubits} contain duplicates")

    if k == n_qubits:
        return gate.astype(np.complex128, copy=False)

    # Build the full operator via a qubit permutation.
    # We reorder qubits so that the target qubits come first (as the k LSBs of
    # the reordered index), apply (gate ⊗ I_idle), then permute back.
    #
    # Convention: qubit 0 is the LSB of the computational-basis index.
    idle = [q for q in range(n_qubits) if q not in target_qubits]
    new_order = list(target_qubits) + idle  # target qubits first

    full_dim = 1 << n_qubits

    # Permutation matrix P: P[x_orig, x_new] = 1, where x_new is the index
    # obtained by reordering the bits of x_orig into new_order.
    P = np.zeros((full_dim, full_dim), dtype=np.complex128)
    for x_orig in range(full_dim):
        bits = [(x_orig >> q) & 1 for q in range(n_qubits)]
        x_new = sum(bits[new_order[q]] << q for q in range(n_qubits))
        P[x_orig, x_new] = 1.0

    idle_dim = 1 << len(idle)
    # kron(I_idle, gate): identity on the MSBs (idle), gate on the LSBs (target)
    gate_full = np.kron(np.eye(idle_dim, dtype=np.complex128), gate)

    # full = P^T (gate ⊗ I_idle) P   (P is a real permutation, so P† = P^T)
    return P.T @ gate_full @ P


def apply_gate_to_state(
    state: NDArray[np.complex128],
    gate: NDArray[np.complex128],
    qubits: Sequence[int] | None = None,
) -> NDArray[np.complex128]:
    """Apply a unitary gate to a state vector.

    Parameters
    ----------
    state : NDArray[np.complex128]
        State vector of length 2ⁿ.
    gate : NDArray[np.complex128]
        Gate matrix (2ᵏ × 2ᵏ).
    qubits : Sequence[int] or None
        Qubit indices the gate acts on. If None, gate must be full-dimension.

    Returns
    -------
    NDArray[np.complex128]
        New state vector after applying the gate.
    """
    n_qubits = int(np.log2(len(state)))
    if qubits is None:
        return gate @ state
    full_gate = tensor_product_gate(gate, n_qubits, qubits)
    return full_gate @ state
