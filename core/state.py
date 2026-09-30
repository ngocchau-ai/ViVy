"""Quantum state representation for the Unitary Reasoner.

Provides the QuantumState class which wraps a complex state vector in
Hilbert space and exposes amplitudes, phases, and probabilities.

Classes
-------
QuantumState
    Complex state vector with properties for amplitudes, phases, and
    probability distribution over computational basis states.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class QuantumState:
    """A quantum state vector in 2ⁿ-dimensional Hilbert space.

    Parameters
    ----------
    amplitudes : NDArray[np.complex128]
        Complex state vector of length 2ⁿ.
    normalize : bool, optional
        If True (default), automatically normalize the vector on construction.

    Attributes
    ----------
    vector : NDArray[np.complex128]
        The raw state vector.
    n_qubits : int
        Number of qubits.
    dim : int
        Hilbert space dimension (2ⁿ).
    """

    def __init__(
        self,
        amplitudes: NDArray[np.complex128],
        normalize: bool = True,
    ) -> None:
        self._vector = np.asarray(amplitudes, dtype=np.complex128).ravel()
        dim = self._vector.shape[0]
        # Validate dimension is a power of 2
        if dim & (dim - 1) != 0 or dim == 0:
            raise ValueError(
                f"State vector length {dim} is not a power of 2"
            )
        self._n_qubits = int(np.log2(dim))

        if normalize:
            nrm = np.linalg.norm(self._vector)
            if nrm > 0:
                self._vector = self._vector / nrm

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def vector(self) -> NDArray[np.complex128]:
        """The raw state vector (read-only copy)."""
        return self._vector.copy()

    @property
    def n_qubits(self) -> int:
        """Number of qubits in this state."""
        return self._n_qubits

    @property
    def dim(self) -> int:
        """Hilbert space dimension (2ⁿ)."""
        return 1 << self._n_qubits

    @property
    def amplitudes(self) -> NDArray[np.float64]:
        """Magnitude (absolute value) of each amplitude."""
        return np.abs(self._vector)

    @property
    def phases(self) -> NDArray[np.float64]:
        """Complex phase (angle in radians) of each amplitude."""
        return np.angle(self._vector)

    @property
    def probs(self) -> NDArray[np.float64]:
        """Probability distribution over computational basis states.

        Returns an array of length 2ⁿ where probs[i] = |⟨i|ψ⟩|².
        """
        return self.amplitudes ** 2

    @property
    def is_normalized(self) -> bool:
        """Whether the state vector is normalized (within numerical tolerance)."""
        return bool(abs(np.linalg.norm(self._vector) - 1.0) < 1e-12)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def norm(self) -> float:
        """Compute the L2 norm of the state vector.

        Returns
        -------
        float
            The Euclidean norm ‖ψ‖.
        """
        return float(np.linalg.norm(self._vector))

    def inner_product(self, other: QuantumState) -> complex:
        """Compute the inner product ⟨ψ|φ⟩.

        Parameters
        ----------
        other : QuantumState
            The other state vector.

        Returns
        -------
        complex
            The inner product ⟨self|other⟩ = ∑ᵢ self_i̅ · other_i.
        """
        if self.dim != other.dim:
            raise ValueError(
                f"Dimension mismatch: {self.dim} vs {other.dim}"
            )
        return complex(np.vdot(self._vector, other._vector))

    def fidelity(self, other: QuantumState) -> float:
        """Compute the fidelity |⟨ψ|φ⟩|² between two states.

        Parameters
        ----------
        other : QuantumState
            The other state.

        Returns
        -------
        float
            Fidelity = |⟨self|other⟩|².
        """
        ip = self.inner_product(other)
        return float(abs(ip) ** 2)

    def measure(self, n_shots: int = 1) -> NDArray[np.int64]:
        """Sample computational basis states according to the Born rule.

        Parameters
        ----------
        n_shots : int
            Number of measurement samples (default 1).

        Returns
        -------
        NDArray[np.int64]
            Array of shape (n_shots,) containing sampled basis-state indices.
        """
        return np.random.choice(self.dim, size=n_shots, p=self.probs)

    def measure_qubit(self, qubit: int) -> tuple[int, QuantumState]:
        """Measure a single qubit and collapse the state.

        Parameters
        ----------
        qubit : int
            Index of the qubit to measure.

        Returns
        -------
        Tuple[int, QuantumState]
            (outcome, collapsed_state) where outcome is 0 or 1.
        """
        if qubit < 0 or qubit >= self._n_qubits:
            raise ValueError(f"Qubit {qubit} out of range [0, {self._n_qubits})")

        # Compute probability of measuring |1⟩ on this qubit
        prob1 = 0.0
        for i in range(self.dim):
            if (i >> qubit) & 1:
                prob1 += self.probs[i]

        outcome = 1 if np.random.random() < prob1 else 0

        # Collapse: keep only components matching outcome, then renormalize
        new_vec = np.zeros_like(self._vector)
        for i in range(self.dim):
            if ((i >> qubit) & 1) == outcome:
                new_vec[i] = self._vector[i]

        nrm = np.linalg.norm(new_vec)
        if nrm > 0:
            new_vec /= nrm

        return outcome, QuantumState(new_vec, normalize=False)

    def apply(self, gate: NDArray[np.complex128]) -> QuantumState:
        """Apply a unitary gate (full-dimension) to this state.

        Parameters
        ----------
        gate : NDArray[np.complex128]
            2ⁿ × 2ⁿ unitary matrix.

        Returns
        -------
        QuantumState
            New state after applying the gate.
        """
        return QuantumState(gate @ self._vector, normalize=False)

    def copy(self) -> QuantumState:
        """Return a deep copy of this state."""
        return QuantumState(self._vector.copy(), normalize=False)

    def __repr__(self) -> str:
        return (
            f"QuantumState(n_qubits={self._n_qubits}, "
            f"dim={self.dim}, norm={self.norm():.6f})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, QuantumState):
            return NotImplemented
        return np.allclose(self._vector, other._vector)

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def basis(cls, n_qubits: int, basis_index: int = 0) -> QuantumState:
        """Create a computational basis state |i⟩.

        Parameters
        ----------
        n_qubits : int
            Number of qubits.
        basis_index : int
            Index of the basis state (default 0 = |0...0⟩).

        Returns
        -------
        QuantumState
            The basis state |basis_index⟩.
        """
        dim = 1 << n_qubits
        vec = np.zeros(dim, dtype=np.complex128)
        vec[basis_index] = 1.0
        return cls(vec, normalize=False)

    @classmethod
    def uniform(cls, n_qubits: int) -> QuantumState:
        """Create a uniform superposition over all basis states.

        Parameters
        ----------
        n_qubits : int
            Number of qubits.

        Returns
        -------
        QuantumState
            (1/√2ⁿ) ∑ₓ |x⟩.
        """
        dim = 1 << n_qubits
        vec = np.ones(dim, dtype=np.complex128) / np.sqrt(dim)
        return cls(vec, normalize=False)

    @classmethod
    def from_probs(cls, probs: NDArray[np.float64]) -> QuantumState:
        """Create a state with given probabilities and zero phases.

        Parameters
        ----------
        probs : NDArray[np.float64]
            Probability distribution (must sum to 1).

        Returns
        -------
        QuantumState
            State with amplitudes = √(probs).
        """
        probs = np.asarray(probs, dtype=np.float64).ravel()
        if abs(probs.sum() - 1.0) > 1e-10:
            raise ValueError(f"Probabilities sum to {probs.sum():.6f}, expected 1")
        vec = np.sqrt(probs).astype(np.complex128)
        return cls(vec, normalize=False)
