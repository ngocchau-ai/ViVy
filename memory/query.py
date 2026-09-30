"""Query utilities for the associative memory: similarity and analogy.

These helpers operate on *dense* pattern vectors (the outputs of a
:class:`~memory.associative.QuantumAssociativeMemory` or raw state vectors).
They provide:

* :func:`cosine_similarity` — a numerically stable complex inner-product overlap.
* :func:`analogical_reasoning` — map a query through a memory and return the
  top-``k`` stored patterns most similar to the retrieved result, i.e. "the
  retrieved memory most resembles these known patterns".

All arithmetic is ``numpy.complex128``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _as_vector(v: ArrayLike, name: str = "vector") -> NDArray[np.complex128]:
    """Coerce input to a 1-D complex128 vector."""
    arr = np.asarray(v, dtype=np.complex128)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a 1-D vector, got ndim={arr.ndim}")
    return arr


def cosine_similarity(a: ArrayLike, b: ArrayLike) -> float:
    """Cosine similarity between two vectors in ``[0, 1]``.

    Uses the magnitude of the normalised complex inner product:

    .. math::

        \\text{sim}(a, b) = \\frac{|\\langle a | b \\rangle|}
        {\\|a\\| \\, \\|b\\|}

    The result is clipped to ``[0, 1]``. The zero vector has similarity ``0``
    with everything.

    Parameters
    ----------
    a:
        First vector.
    b:
        Second vector (same length as ``a``).

    Returns
    -------
    float
        Cosine similarity in ``[0, 1]``.

    Raises
    ------
    ValueError
        If ``a`` and ``b`` have different lengths.
    """
    av = _as_vector(a, "a")
    bv = _as_vector(b, "b")
    if av.shape[0] != bv.shape[0]:
        raise ValueError(
            f"vectors must have equal length, got {av.shape[0]} vs {bv.shape[0]}"
        )
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    overlap = float(np.abs(np.vdot(av, bv)))
    return float(np.clip(overlap / (na * nb), 0.0, 1.0))


def analogical_reasoning(
    memory: Any,
    query: ArrayLike,
    candidates: Iterable[ArrayLike] | None = None,
    k: int = 3,
    iterations: int | None = None,
) -> list[tuple[NDArray[np.complex128], float]]:
    """Retrieve the top-``k`` patterns most analogous to ``query``.

    The query is first mapped through the memory's unitary dynamics
    (``memory.query``), yielding a retrieved pattern ``y_hat``. The stored
    ``candidates`` are then ranked by :func:`cosine_similarity` against
    ``y_hat``. If ``candidates`` is ``None``, the memory's own stored patterns
    are used (dense ``_pairs`` when available, else the query itself).

    Parameters
    ----------
    memory:
        An object exposing ``query(x, iterations=None) -> (y_hat, confidence)``
        and (optionally) ``_pairs`` / ``_W`` for candidate enumeration. A
        :class:`~memory.associative.QuantumAssociativeMemory` works directly.
    query:
        Query pattern, shape ``(dim,)``.
    candidates:
        Optional iterable of patterns to rank. Defaults to the memory's stored
        patterns.
    k:
        Number of top analogies to return (``k <= 0`` returns ``[]``).
    iterations:
        Optional retrieval-iteration override passed to ``memory.query``.

    Returns
    -------
    List[Tuple[NDArray[np.complex128], float]]
        The top-``k`` ``(pattern, similarity)`` pairs, best first.
    """
    if k <= 0:
        return []

    y_hat, _conf = memory.query(query, iterations=iterations)
    y_hat = _as_vector(y_hat, "y_hat")

    if candidates is None:
        candidates = _memory_candidates(memory)

    scored: list[tuple[NDArray[np.complex128], float]] = []
    for cand in candidates:
        cvec = _as_vector(cand, "candidate")
        if cvec.shape[0] != y_hat.shape[0]:
            continue
        sim = cosine_similarity(y_hat, cvec)
        scored.append((cvec, sim))

    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]


def _memory_candidates(memory: object) -> Iterable[ArrayLike]:
    """Best-effort enumeration of the patterns stored in ``memory``."""
    pairs = getattr(memory, "_pairs", None)
    if pairs:
        return [p for (_x, p) in pairs]
    W = getattr(memory, "_W", None)
    if W is not None and np.any(W):
        # Columns of W are the stored |y> patterns (unnormalised).
        return [W[:, j] for j in range(W.shape[1])]
    return []
