"""Matrix Product State (MPS) representation for the Unitary Reasoner.

Provides the MPS class which represents a quantum state as a tensor train
(Matrix Product State), enabling efficient simulation of moderate-size
quantum systems (n ≤ 20 qubits) with bond dimension χ in the range 50-200.

Classes
-------
MPS
    Matrix Product State with apply_gate(), canonical_form(), and norm().
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import svd


class MPS:
    """Matrix Product State representation.

    Represents an n-qubit quantum state as a chain of 3-index tensors:
        ψ_{s₁,s₂,…,sₙ} = ∑_{α₁,…,α_{n-1}} A^{[1]s₁}_{α₁}
                          A^{[2]s₂}_{α₁,α₂} … A^{[n]sₙ}_{α_{n-1}}

    where each A^{[k]} has shape (χ_{k-1}, 2, χ_k) with χ₀ = χₙ = 1.

    Parameters
    ----------
    tensors : List[NDArray[np.complex128]]
        List of n MPS tensors. Each tensor has shape
        (left_bond, physical_dim=2, right_bond).
    center : int, optional
        Orthogonality center position (-1 = right-canonical, default 0).
    canonicalize : bool, optional
        If True (default), bring to left-canonical form on init.

    Attributes
    ----------
    n_qubits : int
        Number of qubits.
    bond_dims : List[int]
        Bond dimensions [χ₀, χ₁, …, χₙ] with χ₀ = χₙ = 1.
    max_bond_dim : int
        Maximum bond dimension.
    """

    def __init__(
        self,
        tensors: list[NDArray[np.complex128]],
        center: int = 0,
        canonicalize: bool = True,
    ) -> None:
        if not tensors:
            raise ValueError("MPS must have at least one tensor")

        self._tensors = [t.astype(np.complex128, copy=True) for t in tensors]
        self._n_qubits = len(self._tensors)

        # Validate shapes
        for k, t in enumerate(self._tensors):
            if t.ndim != 3:
                raise ValueError(
                    f"Tensor {k} has {t.ndim} dimensions, expected 3"
                )
            if t.shape[1] != 2:
                raise ValueError(
                    f"Tensor {k} physical dim is {t.shape[1]}, expected 2"
                )

        # Validate bond consistency
        left = 1
        for k, t in enumerate(self._tensors):
            if t.shape[0] != left:
                raise ValueError(
                    f"Tensor {k} left bond {t.shape[0]} != expected {left}"
                )
            left = t.shape[2]
        if left != 1:
            raise ValueError(
                f"Final right bond {left} != 1"
            )

        self._center = center
        if canonicalize:
            self.canonical_form(target_center=center)
        else:
            # Not canonical — norm() must use the full contraction, not the
            # (non-orthogonal) center tensor.
            self._center = -1

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def n_qubits(self) -> int:
        """Number of qubits."""
        return self._n_qubits

    @property
    def tensors(self) -> list[NDArray[np.complex128]]:
        """List of MPS tensors (read-only copies)."""
        return [t.copy() for t in self._tensors]

    @property
    def bond_dims(self) -> list[int]:
        """Bond dimensions [χ₀, χ₁, …, χₙ] with χ₀ = χₙ = 1."""
        dims = [1]
        for t in self._tensors:
            dims.append(t.shape[2])
        return dims

    @property
    def max_bond_dim(self) -> int:
        """Maximum bond dimension across all bonds."""
        return max(self.bond_dims)

    @property
    def bond_dimension(self) -> int:
        """Alias for max_bond_dim."""
        return self.max_bond_dim

    @property
    def center(self) -> int:
        """Current orthogonality center index."""
        return self._center

    # ------------------------------------------------------------------
    # Norm
    # ------------------------------------------------------------------

    def norm(self) -> float:
        """Compute the Frobenius norm of the MPS.

        For a normalized MPS in canonical form, the norm is computed
        efficiently from the center tensor.

        Returns
        -------
        float
            The norm ‖ψ‖.
        """
        # If canonical, use the center tensor
        if 0 <= self._center < self._n_qubits:
            ct = self._tensors[self._center]
            # Reshape center tensor to matrix and compute Frobenius norm
            return float(np.linalg.norm(ct.reshape(-1)))
        # Otherwise compute full norm
        return self._full_norm()

    def _full_norm(self) -> float:
        """Compute norm by contracting all tensors (expensive for large n)."""
        # Contract all tensors: sum_{s} |ψ_s|²
        # This is the inner product ⟨ψ|ψ⟩
        left = np.ones((1, 1), dtype=np.complex128)
        for t in self._tensors:
            # Contract left with t and its conjugate
            # t shape: (χ_L, 2, χ_R)
            # We need to contract physical indices
            left = np.einsum(
                "ab,apc,bqd->pqcd",
                left, t, t.conj(),
                optimize=True,
            )
            # Trace over physical indices
            left = np.einsum("ppcd->cd", left, optimize=True)
        return float(np.sqrt(np.real(left[0, 0])))

    # ------------------------------------------------------------------
    # Canonical form
    # ------------------------------------------------------------------

    def canonical_form(self, target_center: int = 0) -> None:
        """Bring the MPS to canonical form with the orthogonality center.

        Performs left-to-right QR sweeps followed by right-to-left QR sweeps
        to bring the MPS into mixed-canonical form centered at target_center.

        Parameters
        ----------
        target_center : int
            Index of the orthogonality center (default 0).
        """
        n = self._n_qubits
        if target_center < 0 or target_center >= n:
            raise ValueError(
                f"target_center {target_center} out of range [0, {n})"
            )

        # Left-to-right sweep: left-canonicalize sites 0..target_center-1
        for k in range(0, target_center):
            t = self._tensors[k]
            χ_L, d, χ_R = t.shape
            # Reshape to (χ_L * d, χ_R)
            mat = t.reshape(χ_L * d, χ_R)
            Q, R = np.linalg.qr(mat)
            # Q: (χ_L * d, min(χ_L*d, χ_R))
            # R: (min(χ_L*d, χ_R), χ_R)
            new_χ = Q.shape[1]
            # Reshape Q back to (χ_L, d, new_χ)
            self._tensors[k] = Q.reshape(χ_L, d, new_χ)
            # Absorb R into next tensor
            if k + 1 < n:
                next_t = self._tensors[k + 1]
                # R shape: (new_χ, χ_R), next_t shape: (χ_R, d', χ_R')
                self._tensors[k + 1] = np.einsum(
                    "ab,bcd->acd", R, next_t, optimize=True
                )

        # Right-to-left sweep: right-canonicalize sites n-1..target_center+1
        for k in range(n - 1, target_center, -1):
            t = self._tensors[k]
            χ_L, d, χ_R = t.shape
            # Reshape to (χ_L, d * χ_R)
            mat = t.reshape(χ_L, d * χ_R)
            Q, R = np.linalg.qr(mat.T)  # QR on transpose
            # Q: (d*χ_R, min(d*χ_R, χ_L))
            # R: (min(d*χ_R, χ_L), χ_L)
            new_χ = Q.shape[1]
            # Reshape Q back to (new_χ, d, χ_R) — note the transpose
            self._tensors[k] = Q.T.reshape(new_χ, d, χ_R)
            # Absorb R into previous tensor
            if k - 1 >= 0:
                prev_t = self._tensors[k - 1]
                # R shape: (new_χ, χ_L), prev_t shape: (χ_LL, d', χ_L)
                self._tensors[k - 1] = np.einsum(
                    "abc,cd->abd", prev_t, R, optimize=True
                )

        self._center = target_center

    # ------------------------------------------------------------------
    # Apply gate
    # ------------------------------------------------------------------

    def apply_gate(
        self,
        gate: NDArray[np.complex128],
        qubits: Sequence[int],
        max_bond: int | None = None,
        truncation: float = 1e-10,
    ) -> None:
        """Apply a unitary gate to specified qubits (in-place).

        The gate is applied by contracting the relevant MPS tensors into a
        single tensor, applying the gate, then decomposing back via SVD with
        truncation.

        Parameters
        ----------
        gate : NDArray[np.complex128]
            Unitary gate matrix (2ᵏ × 2ᵏ).
        qubits : Sequence[int]
            Indices of the qubits the gate acts on, sorted.
        max_bond : int, optional
            Maximum bond dimension after truncation.
        truncation : float
            Singular value truncation threshold (default 1e-10).
        """
        qubits = sorted(qubits)
        if any(q < 0 or q >= self._n_qubits for q in qubits):
            raise ValueError(f"Qubits {qubits} out of range for {self._n_qubits} qubits")

        # Map qubit indices to MPS tensor indices.

        return self._apply_gate_simple(gate, qubits, max_bond, truncation)

    def _apply_gate_simple(
        self,
        gate: NDArray[np.complex128],
        qubits: Sequence[int],
        max_bond: int | None = None,
        truncation: float = 1e-10,
    ) -> None:
        """Simpler gate application using full contraction and SVD."""
        qubits = sorted(qubits)
        k = len(qubits)
        start = qubits[0]
        end = qubits[-1]

        # Canonicalize to first target qubit
        self.canonical_form(target_center=start)

        # Contract tensors start..end into one
        combined = self._tensors[start]
        for idx in range(start + 1, end + 1):
            combined = np.tensordot(combined, self._tensors[idx], axes=([2], [0]))

        # combined shape: (χ_L, 2, ..., 2, χ_R) with k physical dims
        # Permute to put all physical dims together
        # Current: [left, phys_1, phys_2, ..., phys_k, right]
        # We want: [left, phys_1..phys_k, right]
        s = combined.shape
        # left_bond = s[0], phys_dims = s[1:-1], right_bond = s[-1]
        phys_combined = combined.reshape(s[0], 1 << k, s[-1])

        # Apply gate: G @ phys_combined (contracting over physical dim)
        # G: (2^k, 2^k), phys_combined: (χ_L, 2^k, χ_R)
        # Result: (χ_L, 2^k, χ_R) where new_phys = G @ old_phys
        applied = np.tensordot(
            phys_combined, gate, axes=([1], [1])
        )  # (χ_L, χ_R, 2^k)
        applied = applied.transpose(0, 2, 1)  # (χ_L, 2^k, χ_R)

        # SVD
        mat = applied.reshape(s[0] * (1 << k), s[-1])
        U, S, Vh = svd(mat, lapack_driver="gesdd", check_finite=False)

        # Truncation
        if max_bond is not None:
            keep = min(len(S), max_bond)
        else:
            keep = int(np.sum(S > truncation * S[0]))
            keep = max(keep, 1)

        U = U[:, :keep]
        S = S[:keep]
        Vh = Vh[:keep, :]

        # Split back: U contains the physical indices for all k qubits
        # U shape: (χ_L * 2^k, keep)
        U_phys = U.reshape(s[0], 1 << k, keep)

        if k == 1:
            # Single-qubit gate
            SV = np.diag(S) @ Vh  # (keep, s[-1])
            self._tensors[start] = U_phys.reshape(s[0], 2, keep)
            if end + 1 < self._n_qubits:
                next_t = self._tensors[end + 1]
                self._tensors[end + 1] = np.tensordot(
                    SV, next_t, axes=([1], [0])
                )
            self._center = start
            return

        # Multi-qubit: sequentially split off each qubit via SVD
        current = U_phys  # (χ_L, 2^k, keep)

        for j in range(k):
            idx = start + j
            remaining = k - j - 1  # qubits still to split AFTER this one
            cur_shape = current.shape
            # Reshape to (left_bond, 2, 2^{remaining}, right_bond)
            reshaped = current.reshape(cur_shape[0], 2, 1 << remaining, cur_shape[-1])
            # Merge left_bond and first physical dim
            mat = reshaped.reshape(cur_shape[0] * 2, (1 << remaining) * cur_shape[-1])
            # SVD to split
            U2, S2, Vh2 = svd(mat, lapack_driver="gesdd", check_finite=False)

            if max_bond is not None:
                keep2 = min(len(S2), max_bond)
            else:
                keep2 = int(np.sum(S2 > truncation * S2[0]))
                keep2 = max(keep2, 1)

            U2 = U2[:, :keep2]
            S2 = S2[:keep2]
            Vh2 = Vh2[:keep2, :]

            # This qubit's tensor
            tensor_j = U2.reshape(cur_shape[0], 2, keep2)
            self._tensors[idx] = tensor_j

            # Remaining
            SV2 = np.diag(S2) @ Vh2  # (keep2, 2^{remaining} * right_bond)

            if remaining == 0:
                current = SV2  # (keep2, right_bond)
            else:
                current = SV2.reshape(keep2, 1 << remaining, cur_shape[-1])

        # current has shape (last_bond, right_bond)
        if end + 1 < self._n_qubits:
            next_t = self._tensors[end + 1]
            self._tensors[end + 1] = np.tensordot(
                current, next_t, axes=([1], [0])
            )
        else:
            self._tensors[end] = np.tensordot(
                self._tensors[end], current, axes=([2], [0])
            )

        self._center = start

    # ------------------------------------------------------------------
    # Conversion to/from full state vector
    # ------------------------------------------------------------------

    def to_vector(self) -> NDArray[np.complex128]:
        """Contract all tensors to obtain the full state vector.

        Tensor 0 corresponds to qubit 0 (LSB), so the vector index is
        ``sum(bit_q << q)``.

        Returns
        -------
        NDArray[np.complex128]
            Full state vector of length 2ⁿ.
        """
        # Contract from the last tensor backward so that tensor 0 becomes the
        # last (LSB) index in the resulting (2, 2, ..., 2) tensor.
        result = self._tensors[-1]
        for t in reversed(self._tensors[:-1]):
            result = np.tensordot(t, result, axes=([-1], [0]))
        # Result shape: (2, 2, ..., 2) with tensor 0 as the first axis.
        # Fortran-order flatten makes tensor 0 the LSB: index = sum(bit_q << q)
        return result.reshape(-1, order="F")

    @classmethod
    def from_vector(
        cls,
        vector: NDArray[np.complex128],
        bond_dim: int = 1,
        truncation: float = 1e-10,
    ) -> MPS:
        """Construct an MPS from a full state vector via sequential SVD.

        Parameters
        ----------
        vector : NDArray[np.complex128]
            State vector of length 2ⁿ.
        bond_dim : int, optional
            Maximum bond dimension (default 1 = no compression).
        truncation : float, optional
            Singular value truncation threshold.

        Returns
        -------
        MPS
            The MPS representation.
        """
        vec = np.asarray(vector, dtype=np.complex128).ravel()
        n_qubits = int(np.log2(len(vec)))
        if 1 << n_qubits != len(vec):
            raise ValueError(f"Vector length {len(vec)} is not a power of 2")

        tensors: list[NDArray[np.complex128]] = []
        # current: (2^{remaining}, right_bond); axis 0 = LSB of the remaining
        # qubits (index = q_k + 2*q_{k+1} + ...).
        current = vec.reshape(-1, 1)

        for k in range(n_qubits - 1):
            remaining = n_qubits - k
            # Split off the LSB (axis 0) via SVD.
            # C-order reshape puts axis 0 as MSB, so we transpose to make
            # axis 0 = LSB.
            A = current.reshape(-1, 2, current.shape[1]).transpose(1, 0, 2)
            mat = A.reshape(2, -1)
            U, S, Vh = svd(mat, lapack_driver="gesdd", check_finite=False)

            keep = min(len(S), bond_dim)
            keep = max(1, int(np.sum(S > truncation * S[0])))

            U = U[:, :keep]
            S = S[:keep]
            Vh = Vh[:keep, :]

            # This qubit's tensor: (left_bond=1, 2, keep)
            tensors.append(U.reshape(1, 2, keep))

            # Continue with the remaining qubits
            current = (np.diag(S) @ Vh).reshape(1 << (remaining - 1), keep)

        # Last tensor: (keep, 2, 1)
        last = current.T.reshape(current.shape[1], 2, 1)
        tensors.append(last)

        return cls(tensors, canonicalize=False)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"MPS(n_qubits={self._n_qubits}, "
            f"bond_dims={self.bond_dims}, "
            f"center={self._center})"
        )
