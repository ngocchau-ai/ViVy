"""SVD-based thought stream extraction for the Unitary Reasoner.

Provides extract_thought_streams() which decomposes a bipartition of a quantum
state via SVD to identify independent "thought streams" — the quantum analogue
of disentangling independent lines of reasoning.

A thought stream represents a tensor-product component in the Schmidt
decomposition of the state across a partition (A = premises, B = conclusions).

Classes
-------
ThoughtStream
    A single Schmidt component with singular value, amplitude ratio, and
    the two sub-states.

Functions
---------
extract_thought_streams(state, partition, threshold)
    Decompose a state across a qubit partition via SVD.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import svd

from .state import QuantumState


@dataclass
class ThoughtStream:
    """A single thought stream from the SVD decomposition.

    Attributes
    ----------
    singular_value : float
        The singular value σᵢ (weight of this stream).
    amplitude_ratio : float
        σᵢ² / Σⱼ σⱼ² — the fraction of total amplitude in this stream.
    state_A : QuantumState
        The sub-state on partition A (premises).
    state_B : QuantumState
        The sub-state on partition B (conclusions).
    interpretation : str
        Human-readable description of this stream.
    """

    singular_value: float
    amplitude_ratio: float
    state_A: QuantumState
    state_B: QuantumState
    interpretation: str = ""

    def __repr__(self) -> str:
        return (
            f"ThoughtStream(σ={self.singular_value:.4f}, "
            f"ratio={self.amplitude_ratio:.4f}, "
            f"dim_A={self.state_A.dim}, dim_B={self.state_B.dim})"
        )


def extract_thought_streams(
    state: QuantumState,
    partition: Sequence[int],
    threshold: float = 0.05,
    max_streams: int | None = None,
) -> list[ThoughtStream]:
    """Extract thought streams from a quantum state via SVD on a bipartition.

    The state is partitioned into two subsystems A (the qubits listed in
    *partition*) and B (the remaining qubits).  The state vector is reshaped
    into a matrix M of shape (dim(A), dim(B)), and the SVD M = U Σ V†
    decomposes the state into a sum of product states:

        |ψ⟩ = Σᵢ σᵢ |uᵢ⟩_A ⊗ |vᵢ⟩_B

    Each term σᵢ |uᵢ⟩_A ⊗ |vᵢ⟩_B is a "thought stream".

    Parameters
    ----------
    state : QuantumState
        The quantum state to decompose.
    partition : Sequence[int]
        Qubit indices that form subsystem A (premises).  The remaining qubits
        form subsystem B (conclusions).
    threshold : float
        Minimum amplitude_ratio for a stream to be included (default 0.05).
    max_streams : int, optional
        Maximum number of streams to return.

    Returns
    -------
    List[ThoughtStream]
        List of thought streams, sorted by singular value descending.
        Only streams with amplitude_ratio >= threshold are included.
    """
    n_qubits = state.n_qubits
    partition = sorted(set(partition))

    if not partition:
        raise ValueError("Partition must contain at least one qubit")
    if any(q < 0 or q >= n_qubits for q in partition):
        raise ValueError(f"Partition {partition} out of range for {n_qubits} qubits")

    # Determine subsystem A and B qubits
    qubits_A = list(partition)
    qubits_B = [q for q in range(n_qubits) if q not in partition]

    n_A = len(qubits_A)
    n_B = len(qubits_B)

    # Build the matrix by iterating over all basis states
    # We need to map the computational basis ordering correctly.
    # The state vector is indexed as |x_{n-1} ... x_0⟩ (qubit 0 = LSB).
    # We need to reorder so that qubits in partition A come first.
    mat = _vector_to_matrix(state.vector, qubits_A, qubits_B, n_qubits)

    # SVD
    U, S, Vh = svd(mat, lapack_driver="gesdd", check_finite=False)

    # Total squared amplitude
    total_sq = float(np.sum(S ** 2))
    if total_sq < 1e-30:
        return []

    streams: list[ThoughtStream] = []
    for i in range(len(S)):
        sigma = float(S[i])
        ratio = float(S[i] ** 2 / total_sq)

        if ratio < threshold:
            continue

        # Extract sub-states
        vec_A = U[:, i].copy()
        vec_B = Vh[i, :].copy()

        state_A = QuantumState(vec_A, normalize=True)
        state_B = QuantumState(vec_B, normalize=True)

        interpretation = (
            f"Stream {i}: σ={sigma:.4f}, "
            f"A({n_A}q) ⊗ B({n_B}q), weight={ratio:.4f}"
        )

        streams.append(
            ThoughtStream(
                singular_value=sigma,
                amplitude_ratio=ratio,
                state_A=state_A,
                state_B=state_B,
                interpretation=interpretation,
            )
        )

        if max_streams is not None and len(streams) >= max_streams:
            break

    return streams


def _vector_to_matrix(
    vector: NDArray[np.complex128],
    qubits_A: list[int],
    qubits_B: list[int],
    n_qubits: int,
) -> NDArray[np.complex128]:
    """Reshape a state vector into a matrix across a bipartition.

    The rows correspond to subsystem A (qubits in *qubits_A*), columns to
    subsystem B (qubits in *qubits_B*).  The ordering follows the
    computational basis with qubit 0 as LSB.

    Parameters
    ----------
    vector : NDArray[np.complex128]
        State vector of length 2ⁿ.
    qubits_A : List[int]
        Qubit indices for subsystem A.
    qubits_B : List[int]
        Qubit indices for subsystem B.
    n_qubits : int
        Total number of qubits.

    Returns
    -------
    NDArray[np.complex128]
        Matrix of shape (2^{|A|}, 2^{|B|}).
    """
    dim_A = 1 << len(qubits_A)
    dim_B = 1 << len(qubits_B)

    # Build the matrix by iterating over all basis states
    mat = np.zeros((dim_A, dim_B), dtype=np.complex128)

    for idx in range(len(vector)):
        # Extract the A and B indices from the global index
        idx_A = 0
        for j, q in enumerate(qubits_A):
            if (idx >> q) & 1:
                idx_A |= 1 << j

        idx_B = 0
        for j, q in enumerate(qubits_B):
            if (idx >> q) & 1:
                idx_B |= 1 << j

        mat[idx_A, idx_B] = vector[idx]

    return mat


def dominant_stream(
    state: QuantumState,
    partition: Sequence[int],
    threshold: float = 0.0,
) -> ThoughtStream | None:
    """Get the single dominant thought stream (largest singular value).

    Parameters
    ----------
    state : QuantumState
        The quantum state.
    partition : Sequence[int]
        Qubit indices forming subsystem A.
    threshold : float
        Singular value weight threshold.

    Returns
    -------
    ThoughtStream or None
        The dominant stream, or None if the state is zero.
    """
    streams = extract_thought_streams(state, partition, threshold=threshold, max_streams=1)
    return streams[0] if streams else None


def schmidt_rank(
    state: QuantumState,
    partition: Sequence[int],
    threshold: float = 1e-10,
) -> int:
    """Compute the Schmidt rank across a bipartition.

    The Schmidt rank is the number of non-zero singular values in the
    Schmidt decomposition.

    Parameters
    ----------
    state : QuantumState
        The quantum state.
    partition : Sequence[int]
        Qubit indices forming subsystem A.
    threshold : float
        Singular values below this threshold are treated as zero.

    Returns
    -------
    int
        The Schmidt rank.
    """
    streams = extract_thought_streams(state, partition, threshold=threshold)
    return len(streams)
