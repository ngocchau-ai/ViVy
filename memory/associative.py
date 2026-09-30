"""Quantum associative memory with Hebbian learning and unitary dynamics.

This module implements a *quantum Hopfield-style* associative memory. Patterns
are stored via the Hebbian outer-product rule :math:`W = \\sum_p |y_p\\rangle
\\langle x_p|`, and the resulting (generally non-unitary) operator is projected
onto the unitary group via polar decomposition (``U = P @ Vh`` from an SVD of
``W``). Retrieval is a unitary iteration :math:`y^{(t+1)} = U x^{(t)}` until
convergence (quantum Hopfield dynamics), mirroring the "unitary reasoner"
philosophy of reversible, norm-preserving thought evolution.

Key design points
-----------------
* All arithmetic uses ``numpy.complex128``.
* When the dimension is large (``dim > 256``, e.g. :math:`2^n` for ``n >= 8``
  qubits), the Hebbian weight is kept in a **sparse** representation to avoid
  materialising a dense :math:`\\text{dim}\\times\\text{dim}` matrix. Unitary
  projection on sparse weights is approximated via truncated SVD on the stored
  (pattern, pattern) Gram structure.
* Continuous learning: ``store()`` accumulates with a learning rate ``eta`` and
  re-unitarises periodically.
"""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import linalg

logger = logging.getLogger(__name__)

#: Dense matrices above this dimension are stored sparsely.
SPARSE_DIM_THRESHOLD = 256

#: Number of unitary (Hopfield) retrieval iterations.
DEFAULT_ITERATIONS = 8

#: Convergence tolerance for Hopfield retrieval.
CONVERGENCE_TOL = 1e-8


def _as_complex_vector(
    v: ArrayLike, dim: int | None = None, name: str = "vector"
) -> NDArray[np.complex128]:
    """Validate and coerce an input to a 1-D complex128 vector.

    Parameters
    ----------
    v:
        Input array-like (real or complex).
    dim:
        Expected length. If ``None`` the length is taken from ``v``.
    name:
        Label used in error messages.

    Returns
    -------
    NDArray[np.complex128]
        A contiguous, normalised-ready complex vector of shape ``(dim,)``.

    Raises
    ------
    ValueError
        If ``v`` is not 1-D or its length does not match ``dim``.
    """
    arr = np.asarray(v, dtype=np.complex128)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a 1-D vector, got ndim={arr.ndim}")
    if dim is not None and arr.shape[0] != dim:
        raise ValueError(
            f"{name} length {arr.shape[0]} does not match expected dim {dim}"
        )
    return np.ascontiguousarray(arr)


def _normalise(v: NDArray[np.complex128]) -> NDArray[np.complex128]:
    """Return ``v`` scaled to unit L2 norm (safe for the zero vector)."""
    n = float(np.linalg.norm(v))
    if n < 1e-15:
        return np.zeros_like(v)
    return v / n


class QuantumAssociativeMemory:
    """Hebbian associative memory with unitary (polar-decomposed) weights.

    The memory stores associations ``(x, y)``. Internally it maintains a weight
    operator ``W`` (dense for small dims, sparse for ``dim > SPARSE_DIM_THRESHOLD``)
    and a unitarised operator ``U`` used for norm-preserving retrieval.

    Parameters
    ----------
    dim:
        Dimension of the state vectors (e.g. ``2**n_qubits``).
    eta:
        Default learning rate used by :meth:`store` when none is supplied.
    reunit_interval:
        Re-run polar decomposition every ``reunit_interval`` stores.
    max_iterations:
        Number of Hopfield retrieval iterations in :meth:`query`.
    """

    def __init__(
        self,
        dim: int,
        eta: float = 0.1,
        reunit_interval: int = 10,
        max_iterations: int = DEFAULT_ITERATIONS,
    ) -> None:
        if dim < 1:
            raise ValueError(f"dim must be >= 1, got {dim}")
        self.dim = int(dim)
        self.eta = float(eta)
        self.reunit_interval = int(reunit_interval)
        self.max_iterations = int(max_iterations)

        self._sparse = self.dim > SPARSE_DIM_THRESHOLD
        # Dense representation (small dims).
        self._W: NDArray[np.complex128] | None = (
            None if self._sparse else np.zeros((self.dim, self.dim), dtype=np.complex128)
        )
        # Sparse representation: list of (x, y) pattern pairs, each unit-norm.
        self._pairs: list[tuple[NDArray[np.complex128], NDArray[np.complex128]]] = []

        # Unitarised operator (dense) used for retrieval. For sparse mode this is
        # built on demand from the stored pairs.
        self._U: NDArray[np.complex128] | None = None
        self._store_count = 0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def store(self, x: ArrayLike, y: ArrayLike, eta: float | None = None) -> None:
        """Store the association ``x -> y`` (Hebbian outer-product update).

        Parameters
        ----------
        x:
            Input pattern, shape ``(dim,)``.
        y:
            Target pattern, shape ``(dim,)``.
        eta:
            Learning rate. Defaults to the instance ``self.eta``.

        Notes
        -----
        In sparse mode the raw pair is retained and the dense operator is only
        materialised (and unitarised) on demand; this keeps memory usage linear
        in the number of stored patterns rather than quadratic in ``dim``.
        """
        xv = _normalise(_as_complex_vector(x, self.dim, "x"))
        yv = _normalise(_as_complex_vector(y, self.dim, "y"))
        lr = float(eta) if eta is not None else self.eta

        self._store_count += 1
        if self._sparse:
            self._pairs.append((xv.copy(), yv.copy()))
            # Invalidate cached unitary; rebuild lazily.
            self._U = None
        else:
            # Hebbian outer product: W += eta * |y><x|
            if self._W is None:
                self._W = np.zeros((self.dim, self.dim), dtype=np.complex128)
            self._W += lr * np.outer(yv, np.conj(xv))
            self._U = None

        if self._store_count % self.reunit_interval == 0:
            self._make_unitary()

    def query(
        self, x: ArrayLike, iterations: int | None = None
    ) -> tuple[NDArray[np.complex128], float]:
        """Retrieve the memory associated with ``x``.

        Retrieval uses the Hebbian weight directly: :math:`\\tilde y = W x`,
        normalised to unit norm. Confidence is ``min(1, \\|W x\\|)`` — how
        strongly the query resonates with stored patterns.

        When ``iterations > 1``, the retrieval is refined via unitary Hopfield
        dynamics :math:`y^{(t+1)} = U y^{(t)}` starting from the Hebbian
        response, which can help resolve overlapping patterns.

        Parameters
        ----------
        x:
            Query pattern, shape ``(dim,)``.
        iterations:
            If ``None`` or ``1``, direct Hebbian retrieval is used. If ``> 1``,
            Hopfield iterations refine the result.

        Returns
        -------
        y_hat:
            Retrieved pattern (unit norm, or zeros if memory is empty).
        confidence:
            A float in ``[0, 1]``. For an empty memory it is ``0.0``.
        """
        xv = _normalise(_as_complex_vector(x, self.dim, "x"))

        if self._is_empty():
            return np.zeros(self.dim, dtype=np.complex128), 0.0

        # Hebbian direct retrieval: y_tilde = W @ x.
        if self._sparse:
            y_raw = self._materialise_dense() @ xv
        else:
            y_raw = self._W @ xv if self._W is not None else np.zeros_like(xv)

        confidence = float(np.clip(float(np.linalg.norm(y_raw)), 0.0, 1.0))
        y_hat = _normalise(y_raw)

        # Optional Hopfield refinement.
        iters = int(iterations) if iterations is not None else 0
        if iters > 1 and float(np.linalg.norm(y_hat)) > 1e-15:
            U = self._get_unitary()
            y = y_hat.copy()
            for _ in range(iters):
                y_next = U @ y
                y_next = _normalise(y_next)
                if np.linalg.norm(y_next) < 1e-15:
                    break
                if np.linalg.norm(y_next - y) < CONVERGENCE_TOL:
                    y = y_next
                    break
                y = y_next
            y_hat = y

        return y_hat, confidence

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _is_empty(self) -> bool:
        """Return ``True`` when no association has been stored."""
        if self._sparse:
            return len(self._pairs) == 0
        return self._W is None or not np.any(self._W)

    def _get_unitary(self) -> NDArray[np.complex128]:
        """Return the current unitarised operator, building it if needed."""
        if self._U is None:
            self._make_unitary()
        assert self._U is not None
        return self._U

    def _make_unitary(self) -> NDArray[np.complex128]:
        """Project the Hebbian weight onto the unitary group via polar decomposition.

        For a weight :math:`W` with SVD :math:`W = P \\Sigma Q^\\dagger`, the
        unitary factor is :math:`U = P Q^\\dagger`. This is the polar
        decomposition of a square matrix: :math:`W = U H` with unitary ``U`` and
        Hermitian positive semi-definite ``H``.

        Returns
        -------
        NDArray[np.complex128]
            The unitarised operator ``U`` (shape ``(dim, dim)``).
        """
        if self._is_empty():
            # Identity is the trivial unitary on an empty memory.
            self._U = np.eye(self.dim, dtype=np.complex128)
            return self._U

        if self._sparse:
            W = self._materialise_dense()
        else:
            if self._W is None:
                self._U = np.eye(self.dim, dtype=np.complex128)
                return self._U
            W = self._W

        # Polar decomposition via SVD: W = P @ diag(s) @ Vh  =>  U = P @ Vh
        P, _s, Vh = linalg.svd(W, full_matrices=True)
        U = P @ Vh
        self._U = np.asarray(U, dtype=np.complex128)
        return self._U

    def _materialise_dense(self) -> NDArray[np.complex128]:
        """Build the dense Hebbian weight from the stored sparse pairs.

        Returns
        -------
        NDArray[np.complex128]
            Dense ``(dim, dim)`` weight matrix.
        """
        W = np.zeros((self.dim, self.dim), dtype=np.complex128)
        for xv, yv in self._pairs:
            W += np.outer(yv, np.conj(xv))
        return W

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    @property
    def is_sparse(self) -> bool:
        """Whether the memory uses sparse storage (``dim > 256``)."""
        return self._sparse

    @property
    def store_count(self) -> int:
        """Number of stored associations."""
        return self._store_count

    @property
    def unitary(self) -> NDArray[np.complex128]:
        """The current unitarised operator (materialising it if necessary)."""
        return self._get_unitary()

    def reset(self) -> None:
        """Clear all stored associations and reset to an empty memory."""
        self._W = None if self._sparse else np.zeros(
            (self.dim, self.dim), dtype=np.complex128
        )
        self._pairs = []
        self._U = None
        self._store_count = 0


# Backwards/interface-compatible alias (the PLAN_3DAY contract names the class
# ``AssociativeMemory``; both names refer to the same implementation).
AssociativeMemory = QuantumAssociativeMemory
