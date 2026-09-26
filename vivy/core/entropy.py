"""Entropy analysis for the Unitary Reasoner.

Provides functions for computing the Shannon entropy of a probability distribution
and detecting interference (non-classical superposition) in a quantum state.

Functions
---------
shannon_entropy(probs, base)
    Shannon entropy of a probability distribution.
interference_detection(state, partition)
    Detect quantum interference between thought streams.
von_neumann_entropy(state, partition)
    Von Neumann entropy of the reduced density matrix across a bipartition.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from .state import QuantumState


def shannon_entropy(
    probs: NDArray[np.float64],
    base: float = 2.0,
) -> float:
    r"""Compute the Shannon entropy of a probability distribution.

    .. math::
        H(p) = -\sum_i p_i \log_b p_i

    with the convention that 0·log(0) = 0.

    Parameters
    ----------
    probs : NDArray[np.float64]
        Probability distribution (does not need to be normalized, but should be
        non-negative).
    base : float
        Logarithm base (default 2 → entropy in bits).

    Returns
    -------
    float
        The Shannon entropy.

    Raises
    ------
    ValueError
        If any probability is negative.
    """
    probs = np.asarray(probs, dtype=np.float64).ravel()
    if np.any(probs < 0):
        raise ValueError("Probabilities must be non-negative")

    # Normalize if not already normalized
    total = probs.sum()
    if total <= 0:
        return 0.0
    p = probs / total

    # Compute -Σ p log_b p, treating 0·log(0)=0
    terms = np.zeros_like(p)
    nz = p > 0
    terms[nz] = p[nz] * np.log(p[nz]) / np.log(base)

    return float(-terms.sum())


def von_neumann_entropy(
    state: QuantumState,
    partition: Sequence[int],
    base: float = 2.0,
) -> float:
    r"""Compute the Von Neumann entropy of the reduced density matrix.

    Given a bipartition of the state into A (the qubits in *partition*) and
    B (the rest), the Von Neumann entropy of subsystem A is

    .. math::
        S(\rho_A) = -\sum_i \lambda_i \log_b \lambda_i

    where λᵢ are the eigenvalues of the reduced density matrix ρ_A = Tr_B |ψ⟩⟨ψ|.
    Equivalently, λᵢ = σᵢ² where σᵢ are the Schmidt coefficients.

    Parameters
    ----------
    state : QuantumState
        The quantum state.
    partition : Sequence[int]
        Qubit indices forming subsystem A.
    base : float
        Logarithm base (default 2 → bits).

    Returns
    -------
    float
        The Von Neumann entropy.
    """
    n_qubits = state.n_qubits
    partition = sorted(set(partition))
    if not partition:
        raise ValueError("Partition must contain at least one qubit")

    qubits_A = list(partition)
    qubits_B = [q for q in range(n_qubits) if q not in partition]

    # Build the reduced density matrix ρ_A
    dim_A = 1 << len(qubits_A)
    dim_B = 1 << len(qubits_B)

    rho_A = np.zeros((dim_A, dim_A), dtype=np.complex128)
    vec = state.vector

    for i in range(dim_A):
        for j in range(dim_A):
            # ρ_A[i,j] = Σ_b vec[i,b] * conj(vec[j,b])
            s = 0.0 + 0.0j
            for b in range(dim_B):
                idx_i = _compose_index(i, b, qubits_A, qubits_B, n_qubits)
                idx_j = _compose_index(j, b, qubits_A, qubits_B, n_qubits)
                s += vec[idx_i] * np.conj(vec[idx_j])
            rho_A[i, j] = s

    # Eigenvalues of ρ_A
    eigvals = np.linalg.eigvalsh(rho_A)
    eigvals = np.clip(eigvals, 0.0, None)

    # Entropy
    terms = np.zeros_like(eigvals)
    nz = eigvals > 1e-15
    terms[nz] = eigvals[nz] * np.log(eigvals[nz]) / np.log(base)
    return float(-terms.sum())


def interference_detection(
    state: QuantumState,
    partition: Sequence[int] | None = None,
    threshold: float = 1e-8,
) -> dict:
    """Detect quantum interference in a state.

    Quantum interference is the signature of superposition: the probability of a
    basis state differs from the sum of probabilities of its classical components.

    This function detects interference by comparing the Born-rule probabilities of the
    full state against the probabilities one would obtain from a "classical" mixture
    (the diagonal of the density matrix).  When the state is a product of
    single-qubit states, there is no interference; when qubits are entangled or
    in superposition, interference appears.

    Parameters
    ----------
    state : QuantumState
        The quantum state.
    partition : Sequence[int], optional
        Optional subset of qubits to analyze.  If None, all qubits.
    threshold : float
        Magnitude threshold for flagging interference.

    Returns
    -------
    dict
        A dictionary with keys:
            - ``has_interference``: bool — whether interference was detected.
            - ``interference_magnitude``: float — max deviation from classical.
            - ``max_interfering_basis``: int — basis state with max deviation.
            - ``entropy``: float — Shannon entropy of the distribution.
    """
    n_qubits = state.n_qubits
    probs = state.probs

    # Reference: a classical mixture has the same marginal single-qubit probabilities
    # but no cross-qubit correlations.  Build the "classical" reference distribution
    # as the product of single-qubit marginals.
    single_probs = np.zeros((n_qubits, 2), dtype=np.float64)
    for q in range(n_qubits):
        for i in range(state.dim):
            single_probs[q, (i >> q) & 1] += probs[i]

    classical = np.ones(state.dim, dtype=np.float64)
    for i in range(state.dim):
        for q in range(n_qubits):
            classical[i] *= single_probs[q, (i >> q) & 1]

    # Deviation between quantum and classical probabilities
    deviation = np.abs(probs - classical)
    max_dev = float(deviation.max())
    max_idx = int(deviation.argmax())

    has_interference = max_dev > threshold

    return {
        "has_interference": bool(has_interference),
        "interference_magnitude": max_dev,
        "max_interfering_basis": max_idx,
        "entropy": shannon_entropy(probs),
    }


def _compose_index(
    idx_A: int,
    idx_B: int,
    qubits_A: Sequence[int],
    qubits_B: Sequence[int],
    n_qubits: int,
) -> int:
    """Compose subsystem indices into a global basis index.

    Given an index within subsystem A and an index within subsystem B, reconstruct
    the global computational-basis index (qubit 0 = LSB).

    Parameters
    ----------
    idx_A : int
        Index within subsystem A.
    idx_B : int
        Index within subsystem B.
    qubits_A : Sequence[int]
        Qubit indices of subsystem A.
    qubits_B : Sequence[int]
        Qubit indices of subsystem B.
    n_qubits : int
        Total number of qubits.

    Returns
    -------
    int
        The global basis index.
    """
    global_idx = 0
    for j, q in enumerate(qubits_A):
        if (idx_A >> j) & 1:
            global_idx |= 1 << q
    for j, q in enumerate(qubits_B):
        if (idx_B >> j) & 1:
            global_idx |= 1 << q
    return global_idx
