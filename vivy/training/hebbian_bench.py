"""C10 — multi-size Hebbian recall benchmark (W@x vs node-ID scan).

Acceptance-plan C10.3: benchmark nhiều kích thước graph, không suy O(1) từ
hai điểm. Tách W@x và node-ID scan; report fixed dimensions.

Operator is W = Y @ pinv(X) (Moore–Penrose), matching
`Vivy final/core/memory/hebbian_recall.py`. This bench measures that operator
at many n and reports a wall-clock distribution per path — it does not claim
a complexity class from the numbers.

Changelog:
    2026-09-24 (Claude Code — P5 C10): Initial.
"""
from __future__ import annotations

import time
from typing import Iterable, Sequence

import numpy as np

MIN_GRAPH_SIZES = 3
DEFAULT_STATUS_LABEL = "PROVISIONAL_RESULT"
LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"


class ReferenceHebbian:
    """W = Y @ pinv(X) reference operator used for multi-size measurement."""

    def __init__(self, dim: int) -> None:
        if dim < 1:
            raise ValueError("dim must be ≥ 1")
        self.dim = dim
        self._kv: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._W: np.ndarray | None = None
        self._dirty = True

    def register(self, node_id: str, key: Sequence[float], value: Sequence[float] | None = None) -> None:
        x = np.asarray(key, dtype=np.float32).ravel()
        if x.shape[0] != self.dim:
            raise ValueError(f"key dim {x.shape[0]} != {self.dim}")
        y = np.asarray(value if value is not None else key, dtype=np.float32).ravel()
        if y.shape[0] != self.dim:
            raise ValueError(f"value dim {y.shape[0]} != {self.dim}")
        self._kv[node_id] = (x, y)
        self._dirty = True

    def build(self) -> float:
        t0 = time.perf_counter()
        items = list(self._kv.values())
        if not items:
            self._W = np.zeros((self.dim, self.dim), dtype=np.float32)
        else:
            X = np.stack([kv[0] for kv in items], axis=1)
            Y = np.stack([kv[1] for kv in items], axis=1)
            self._W = (Y @ np.linalg.pinv(X)).astype(np.float32)
        self._dirty = False
        return (time.perf_counter() - t0) * 1000.0

    def recall_wx(self, query: Sequence[float]) -> np.ndarray:
        if self._W is None or self._dirty:
            self.build()
        x = np.asarray(query, dtype=np.float32).ravel()
        norm = np.linalg.norm(x)
        if norm > 1e-8:
            x = x / norm
        assert self._W is not None
        return self._W @ x

    def recall_scan(self, query: Sequence[float]) -> str | None:
        y = self.recall_wx(query)
        y_norm = np.linalg.norm(y)
        y = y / y_norm if y_norm > 1e-8 else y
        best_id = None
        best_sim = -1.0
        for node_id, (_x, val) in self._kv.items():
            v_norm = np.linalg.norm(val)
            v = val / v_norm if v_norm > 1e-8 else val
            sim = float(np.dot(y, v))
            if sim > best_sim:
                best_sim = sim
                best_id = node_id
        return best_id


def _stats(samples: Iterable[float]) -> dict[str, float | int]:
    xs = list(samples)
    if not xs:
        return {"median": 0.0, "p95": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0, "n_samples": 0}
    arr = np.asarray(xs, dtype=np.float64)
    return {
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "mean": float(arr.mean()),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "n_samples": int(arr.size),
    }


def run_hebbian_scaling(
    *,
    dim: int,
    ns: Sequence[int],
    reps: int = 10,
    seed: int = 0,
) -> dict:
    """Measure W@x and node-ID scan at many graph sizes with a fixed dim.

    Refuses fewer than MIN_GRAPH_SIZES distinct n — two points cannot support
    an O(1) vs O(n) separation.
    """
    ns = list(ns)
    if len(ns) < MIN_GRAPH_SIZES:
        raise ValueError(
            f"need ≥{MIN_GRAPH_SIZES} graph sizes to separate W@x from scan; got {ns}"
        )
    if reps < 1:
        raise ValueError("reps must be ≥ 1")

    rng = np.random.default_rng(seed)
    per_n: dict[int, dict] = {}

    for n in ns:
        h = ReferenceHebbian(dim=dim)
        keys = rng.normal(size=(n, dim)).astype(np.float32)
        for i in range(n):
            h.register(f"node-{i}", keys[i])
        build_ms = h.build()

        q = rng.normal(size=dim).astype(np.float32)
        wx_samples: list[float] = []
        scan_samples: list[float] = []
        for _ in range(reps):
            t0 = time.perf_counter()
            h.recall_wx(q)
            wx_samples.append((time.perf_counter() - t0) * 1000.0)
            t1 = time.perf_counter()
            h.recall_scan(q)
            scan_samples.append((time.perf_counter() - t1) * 1000.0)

        per_n[int(n)] = {
            "n": int(n),
            "build_ms": build_ms,
            "wx_recall_ms": _stats(wx_samples),
            "scan_recall_ms": _stats(scan_samples),
        }

    return {
        "dim": dim,
        "reps": reps,
        "seed": seed,
        "n_sizes": len(ns),
        "per_n": per_n,
        "status_label": DEFAULT_STATUS_LABEL,
        "latency_claim": LATENCY_CLAIM,
        "note": (
            "wall-clock observations at fixed dim; W@x and node-ID scan are "
            "separate paths; 0ms would be rounding, not a physical zero"
        ),
    }
