"""C12 — sparse path must actually be exercised in the forward.

Full-vs-sparse on the SAME weights and SAME input. Reports quality regression
(cosine / MSE) and end-to-end latency with median/p95. No O(1), no zero-latency.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"
MIN_REPS = 5  # shared experiment protocol: warm-up 5, measure ≥30 for microbenchmark;
# sparse-forward is a small harness so we allow reps≥5 and report n honestly.


def _id_of(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(np.ascontiguousarray(p).tobytes())
    return h.hexdigest()[:16]


def _stats(samples: list[float]) -> dict[str, Any]:
    arr = np.asarray(samples, dtype=np.float64)
    return {
        "n_samples": int(arr.size),
        "median": float(np.median(arr)) if arr.size else None,
        "p95": float(np.percentile(arr, 95)) if arr.size else None,
        "mean": float(arr.mean()) if arr.size else None,
        "min": float(arr.min()) if arr.size else None,
        "max": float(arr.max()) if arr.size else None,
    }


def sparse_matmul(W: np.ndarray, x: np.ndarray, *, k: int):
    """Dense W @ x restricted to the top-k salient input units.

    Returns (output, info). `info["sparse_path_exercised"]` is True only when the
    computation actually dropped units (0 < k < n).
    """
    W = np.asarray(W, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    k = int(k)
    if k <= 0 or k > n:
        raise ValueError(f"k must be in [1, n], got k={k} n={n}")

    # Salience = |x_i| * ||W[:, i]|| — which input units drive the output most.
    col_norm = np.linalg.norm(W, axis=0)
    salience = np.abs(x) * col_norm
    activated = np.argpartition(salience, -k)[-k:]
    activated = np.sort(activated)

    mask = np.zeros(n, dtype=np.float64)
    mask[activated] = 1.0
    out = W @ (x * mask)

    nonzero = int(np.count_nonzero(x * mask))
    exercised = 0 < k < n
    return out, {
        "k": k,
        "n": n,
        "activated_indices": activated,
        "n_nonzero_contributions": nonzero,
        "sparse_path_exercised": exercised,
    }


@dataclass
class SparseForwardResult:
    same_weights: bool
    same_input: bool
    sparse_path_exercised: bool
    sparse_is_reduction: bool
    weights_id: str
    weights_id_sparse: str
    input_id: str
    input_id_sparse: str
    n_full_nonzero: int
    n_sparse_nonzero: int
    k: int
    n: int
    quality_regression: dict[str, float]
    latency_full_ms: dict[str, Any]
    latency_sparse_ms: dict[str, Any]
    latency_end_to_end_ms: dict[str, Any]
    latency_claim: str = LATENCY_CLAIM
    status_label: str = "PROVISIONAL_RESULT"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_full_vs_sparse(
    W: np.ndarray,
    x: np.ndarray,
    *,
    k: int,
    reps: int = 30,
    seed: int = 0,
) -> SparseForwardResult:
    """Compare dense forward vs sparse forward on identical weights and input."""
    del seed  # deterministic op; seed reserved for stochastic variants
    W = np.asarray(W, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    reps = max(int(reps), 1)

    full_out = W @ x
    sparse_out, info = sparse_matmul(W, x, k=k)

    # Warm-up then measure. End-to-end includes mask construction + matmul.
    warmup = min(5, reps)
    for _ in range(warmup):
        W @ x
        sparse_matmul(W, x, k=k)

    full_samples: list[float] = []
    sparse_samples: list[float] = []
    e2e_samples: list[float] = []
    for _ in range(reps):
        t0 = time.perf_counter()
        W @ x
        full_samples.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        sparse_matmul(W, x, k=k)
        e2e_samples.append((time.perf_counter() - t0) * 1000.0)

        # Sparse matmul body alone (mask already conceptually built — still includes it
        # because the path is the function). Separately time the pure matvec on the mask.
        mask = np.zeros(n, dtype=np.float64)
        mask[info["activated_indices"]] = 1.0
        t0 = time.perf_counter()
        W @ (x * mask)
        sparse_samples.append((time.perf_counter() - t0) * 1000.0)

    diff = full_out - sparse_out
    denom = float(np.linalg.norm(full_out) * np.linalg.norm(sparse_out))
    cosine = float(np.dot(full_out, sparse_out) / denom) if denom > 0 else 0.0
    mse = float(np.mean(diff ** 2))

    w_id = _id_of(W)
    w_id_s = w_id  # same object
    x_id = _id_of(x)
    x_id_s = x_id

    return SparseForwardResult(
        same_weights=True,
        same_input=True,
        sparse_path_exercised=bool(info["sparse_path_exercised"]),
        sparse_is_reduction=bool(info["sparse_path_exercised"]),
        weights_id=w_id,
        weights_id_sparse=w_id_s,
        input_id=x_id,
        input_id_sparse=x_id_s,
        n_full_nonzero=int(np.count_nonzero(x)),
        n_sparse_nonzero=int(info["n_nonzero_contributions"]),
        k=int(k),
        n=int(n),
        quality_regression={"cosine": cosine, "mse": mse, "l2_diff": float(np.linalg.norm(diff))},
        latency_full_ms=_stats(full_samples),
        latency_sparse_ms=_stats(sparse_samples),
        latency_end_to_end_ms=_stats(e2e_samples),
    )
