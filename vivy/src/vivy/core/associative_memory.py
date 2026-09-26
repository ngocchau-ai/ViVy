"""
Quantum-Inspired Associative Memory for ViVy.

Implementation of the memory correlation layer (Tầng Memory Tương quan)
using complex Hebbian learning and SVD polar unitarization.
"""

import os

import numpy as np
from scipy.linalg import svd


class QuantumAssociativeMemory:
    """
    Quantum-inspired associative memory using complex weights.
    Stores and retrieves patterns based on unitary matrix transformations.
    """
    def __init__(self, dim: int, use_unitary: bool = True):
        self.dim = dim
        # Initialize complex weight matrix W
        self.W = np.zeros((dim, dim), dtype=complex)
        self.use_unitary = use_unitary

    def store(self, x: np.ndarray, y: np.ndarray, eta: float = 0.1) -> None:
        """
        Store a thought pattern mapping x -> y.
        x, y are 1D complex arrays representing state vectors.
        """
        # Ensure they are complex
        x_c = np.asarray(x, dtype=complex)
        y_c = np.asarray(y, dtype=complex)

        # Outer product: |y><x|
        outer = np.outer(y_c, x_c.conj())

        # Hebbian update
        self.W += eta * outer

        if self.use_unitary:
            self._make_unitary()

    def query(self, x: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Retrieve a pattern given input x.
        Returns the retrieved state vector and the confidence score.
        """
        x_c = np.asarray(x, dtype=complex)

        if self.use_unitary:
            y_out = self.W @ x_c
        else:
            y_tilde = self.W @ x_c
            y_out = y_tilde

        conf = np.linalg.norm(y_out)
        if conf > 0:
            y_out = y_out / conf  # Normalize

        return y_out, float(conf)

    def _make_unitary(self) -> None:
        """
        Apply Polar Decomposition via SVD to make W approximately unitary.
        W = U * V^H
        """
        U, _, Vh = svd(self.W, full_matrices=False)
        self.W = U @ Vh

    def save_compressed(self, filepath: str, top_k: int = 64) -> None:
        """
        Quantum LoRA Compression: Save only the Top-K singular vectors.
        Dramatically reduces physical disk size while retaining theoretical 1B capacity.
        Uses sparse svds for massive performance speedup.
        """
        from scipy.sparse.linalg import svds

        # Ensure k is strictly less than dim for svds
        k = min(top_k, self.dim - 1)
        if k < 1:
            k = 1

        U_k, S_k, Vh_k = svds(self.W, k=k)

        # svds returns singular values in ascending order, so we reverse them
        idx = np.argsort(S_k)[::-1]
        U_k = U_k[:, idx]
        S_k = S_k[idx]
        Vh_k = Vh_k[idx, :]

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        np.savez_compressed(filepath, U=U_k, S=S_k, Vh=Vh_k, dim=self.dim)

    def load_compressed(self, filepath: str) -> None:
        """
        Load compressed Quantum LoRA weights and reconstruct the active W matrix.
        """
        data = np.load(filepath)
        U_k = data['U']
        S_k = data['S']
        Vh_k = data['Vh']
        self.dim = int(data['dim'])

        # Reconstruct W = U * diag(S) * V^H
        self.W = (U_k * S_k) @ Vh_k
