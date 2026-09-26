"""P5 Cartography Sparse RAM/activation benchmark (Gate 9).

Measures what this machine can actually observe:

  1. .catlas export size and import latency (CoarseKnowledgeAtlas round-trip)
  2. HebbianRecall scaling vs graph size n — W@x path (graph=None) vs the
     nearest-node scan path (with graph). Build cost is recorded separately.
  3. RAM budget ceiling math (10% buffer cap, 85% circuit breaker)
  4. Sparse activation top-k ratio (10% high-salience neurons)
  5. Cautreo in-process put/get wall-clock (observation only)

Gate 9 claims matrix — every unbenchmarkable absolute stays UNVERIFIED in the
receipt:

  - catlas_size_under_8mb   TESTED iff measured sizes are all < 8 MiB
  - catlas_load_under_2ms   TESTED iff max measured import_ms < 2.0
  - hebbian_o1_graph_size   TESTED iff no-graph recall stays flat in n
  - 100b_on_10gb            always UNVERIFIED (no 100B weights on this host)
  - zero_latency_c_abi      always UNVERIFIED (measured numbers are > 0)

Receipt label is TESTED_MECHANISM. Numbers in the receipt are observations
on this machine — they are NOT product latency/RAM claims.

Changelog:
    23/09/2026 (Claude Code — P5 Cartography RAM/activation benchmark): Initial.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from integration.cautreo_cartographer import (
    AtlasNode,
    CautreoCartographer,
    CoarseKnowledgeAtlas,
)
from memory.cognitive_graph import CognitiveStateGraph, NodeType
from memory.hebbian_recall import HebbianRecall

BENCHMARK_STATUS_LABEL = "TESTED_MECHANISM"
BENCHMARK_PROTOCOL = (
    "P5 cartography benchmark: .catlas size/load, HebbianRecall scaling vs n, "
    "RAM 10% ceiling + 85% breaker, sparse top-k ratio, Cautreo put/get "
    "wall-clock (mechanism observations, not product claims)"
)

# Claim keys emitted in every receipt. Absolute / unbenchmarkable ones are
# pinned UNVERIFIED regardless of local measurement.
CLAIM_KEYS = (
    "catlas_size_under_8mb",
    "catlas_load_under_2ms",
    "hebbian_o1_graph_size",
    "100b_on_10gb",
    "zero_latency_c_abi",
)

CATLAS_SIZE_LIMIT_BYTES = 8 * 1024 * 1024
CATLAS_LOAD_LIMIT_MS = 2.0
HEBBIAN_FLAT_RATIO = 3.0  # n_max/n_min no-graph recall_ms must stay under this


# ---------------------------------------------------------------------------
# Measurement primitives
# ---------------------------------------------------------------------------


def measure_catlas_roundtrip(atlas: CoarseKnowledgeAtlas, file_path: str | Path) -> dict[str, Any]:
    """Export atlas to .catlas then re-import. Returns size + latency observations."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    exported = atlas.export_catlas(str(path))
    export_ms = (time.perf_counter() - t0) * 1000.0

    if not exported or not path.exists():
        return {
            "path": str(path),
            "exported": False,
            "size_bytes": 0,
            "export_ms": export_ms,
            "import_ms": None,
            "n_nodes": len(atlas.nodes),
            "loaded_atlas": None,
            "ok": False,
        }

    size_bytes = path.stat().st_size
    imported = measure_catlas_import(path)
    return {
        "path": str(path),
        "exported": True,
        "size_bytes": size_bytes,
        "export_ms": export_ms,
        "import_ms": imported["import_ms"],
        "n_nodes": len(atlas.nodes),
        "loaded_atlas": imported.get("loaded_atlas"),
        "ok": imported["ok"],
    }


def measure_catlas_import(file_path: str | Path) -> dict[str, Any]:
    """Import a .catlas file. Fail-closed on missing/corrupt file."""
    path = Path(file_path)
    if not path.exists():
        return {
            "path": str(path),
            "ok": False,
            "size_bytes": 0,
            "import_ms": None,
            "n_nodes": 0,
            "loaded_atlas": None,
        }

    size_bytes = path.stat().st_size
    t0 = time.perf_counter()
    loaded = CoarseKnowledgeAtlas.import_catlas(str(path))
    import_ms = (time.perf_counter() - t0) * 1000.0

    if loaded is None:
        return {
            "path": str(path),
            "ok": False,
            "size_bytes": size_bytes,
            "import_ms": import_ms,
            "n_nodes": 0,
            "loaded_atlas": None,
        }
    return {
        "path": str(path),
        "ok": True,
        "size_bytes": size_bytes,
        "import_ms": import_ms,
        "n_nodes": len(loaded.nodes),
        "loaded_atlas": loaded,
    }


def measure_ram_budget(cart: CautreoCartographer | None = None) -> dict[str, Any]:
    """Record the 10% RAM ceiling + 85% circuit-breaker configuration."""
    if cart is None:
        cart = CautreoCartographer(ram_ratio=0.10, circuit_breaker_threshold=0.85)
    hw = cart.hardware_ram_bytes
    max_buf = cart.max_buffer_bytes
    return {
        "hardware_ram_bytes": hw,
        "ram_ratio": cart.ram_ratio,
        "max_buffer_bytes": max_buf,
        "budget_fraction_of_hw": (max_buf / hw) if hw else 0.0,
        "circuit_breaker_threshold": cart.circuit_breaker_threshold,
    }


def measure_sparse_activation(
    total_neurons: int = 14336, top_k_ratio: float = 0.10
) -> dict[str, Any]:
    """Record the top-k high-salience activation ratio (mechanism)."""
    top_k_count = int(total_neurons * top_k_ratio)
    return {
        "total_neurons": total_neurons,
        "top_k_ratio": top_k_ratio,
        "top_k_count": top_k_count,
        "activation_ratio": (top_k_count / total_neurons) if total_neurons else 0.0,
        "sparsity_ratio": 1.0 - ((top_k_count / total_neurons) if total_neurons else 0.0),
    }


def run_hebbian_scaling(
    dim: int = 32, ns: tuple[int, ...] = (10, 50, 100), reps: int = 20
) -> list[dict[str, Any]]:
    """Measure HebbianRecall.recall cost vs registered graph size n.

    For each n:
      - register n random key/value pairs
      - time _build_W separately (amortised batch update)
      - time `reps` recalls with graph=None  (W@x path only)
      - time `reps` recalls with a CognitiveStateGraph (adds O(n) node scan)
    """
    rng = np.random.default_rng(42)
    points: list[dict[str, Any]] = []

    for n in ns:
        mem = HebbianRecall(dim=dim)
        graph = CognitiveStateGraph()
        for i in range(n):
            key = rng.standard_normal(dim).astype(np.float32)
            val = rng.standard_normal(dim).astype(np.float32)
            node_id = f"hyp_{n}_{i}"
            mem.register(node_id, key, val)
            graph.add_node(
                node_id=node_id,
                node_type=NodeType.HYPOTHESIS,
                content=f"p5 scaling node {i}",
                embedding=key.tolist(),
            )

        t_build = time.perf_counter()
        mem._build_W()
        build_ms = (time.perf_counter() - t_build) * 1000.0

        query = rng.standard_normal(dim).astype(np.float32)

        # Warmup (excluded) so first-call overhead is not the measurement.
        mem.recall(query, graph=None)
        mem.recall(query, graph=graph)

        t0 = time.perf_counter()
        for _ in range(max(1, reps)):
            mem.recall(query, graph=None)
        recall_ms_no_graph = (time.perf_counter() - t0) * 1000.0 / max(1, reps)

        t0 = time.perf_counter()
        for _ in range(max(1, reps)):
            mem.recall(query, graph=graph)
        recall_ms_with_graph = (time.perf_counter() - t0) * 1000.0 / max(1, reps)

        points.append(
            {
                "n": n,
                "dim": dim,
                "reps": max(1, reps),
                "build_ms": build_ms,
                "recall_ms_no_graph": recall_ms_no_graph,
                "recall_ms_with_graph": recall_ms_with_graph,
            }
        )

    return points


def measure_cautreo_latency(reps: int = 50) -> dict[str, Any] | None:
    """Wall-clock put/get on CautreoContextMemory. Observation only — not a 0ms claim."""
    try:
        from integration.cautreo_binding import CautreoContextMemory, CautreoMemoryKind
    except Exception:  # noqa: BLE001
        return None

    try:
        mem = CautreoContextMemory(max_items=max(16, reps + 8))
    except Exception:  # noqa: BLE001
        return None

    try:
        content = "p5 latency probe payload"
        t0 = time.perf_counter()
        for i in range(reps):
            mem.put(f"p5_probe_{i}", CautreoMemoryKind.SUMMARY, content)
        put_ms = (time.perf_counter() - t0) * 1000.0 / max(1, reps)

        t0 = time.perf_counter()
        for i in range(reps):
            mem.get(f"p5_probe_{i}")
        get_ms = (time.perf_counter() - t0) * 1000.0 / max(1, reps)

        return {
            "reps": max(1, reps),
            "put_ms": put_ms,
            "get_ms": get_ms,
            "claimed_latency_ms": None,
        }
    except Exception:  # noqa: BLE001
        return None
    finally:
        try:
            mem.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


@dataclass
class CartographyBenchmarkReceipt:
    """Receipt for a P5 cartography RAM/activation benchmark run."""

    status_label: str
    protocol: str
    generated_at: str
    claims: dict[str, str] = field(default_factory=dict)
    catlas: list[dict[str, Any]] = field(default_factory=list)
    hebbian: dict[str, Any] = field(default_factory=dict)
    ram_budget: dict[str, Any] = field(default_factory=dict)
    sparse_activation: dict[str, Any] = field(default_factory=dict)
    cautreo: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _claim_catlas_size(members: list[dict[str, Any]]) -> str:
    sizes = [m["size_bytes"] for m in members if m.get("exported") or m.get("ok")]
    if not sizes:
        return "UNVERIFIED"
    return "TESTED" if all(s < CATLAS_SIZE_LIMIT_BYTES for s in sizes) else "UNVERIFIED"


def _claim_catlas_load(members: list[dict[str, Any]]) -> str:
    loads = [m["import_ms"] for m in members if m.get("import_ms") is not None]
    if not loads:
        return "UNVERIFIED"
    return "TESTED" if max(loads) < CATLAS_LOAD_LIMIT_MS else "UNVERIFIED"


def _claim_hebbian(points: list[dict[str, Any]]) -> tuple[str, float | None]:
    if len(points) < 2:
        return "UNVERIFIED", None
    ordered = sorted(points, key=lambda p: p["n"])
    t_lo = ordered[0]["recall_ms_no_graph"]
    t_hi = ordered[-1]["recall_ms_no_graph"]
    if t_lo <= 0.0:
        return "UNVERIFIED", None
    ratio = t_hi / t_lo
    status = "TESTED" if ratio < HEBBIAN_FLAT_RATIO else "UNVERIFIED"
    return status, ratio


def run_benchmark(
    *,
    atlas_paths: list[str | Path] | None = None,
    hebbian_ns: tuple[int, ...] = (10, 50, 100),
    hebbian_dim: int = 32,
    hebbian_reps: int = 20,
    include_cautreo: bool = True,
    include_synthetic_atlas: bool = True,
    synthetic_layers: int = 8,
) -> CartographyBenchmarkReceipt:
    """Run the P5 measurements and build the receipt."""
    catlas_members: list[dict[str, Any]] = []

    if include_synthetic_atlas:
        atlas = CoarseKnowledgeAtlas(model_id="p5-synthetic", total_layers=synthetic_layers)
        for i in range(synthetic_layers):
            atlas.nodes[i] = AtlasNode(
                layer_index=i,
                block_name=f"p5-synthetic.blk.{i}",
                top_concepts=[f"concept_{i}"],
                domain_scores={"logic_math": 0.5},
                high_salience_neuron_indices=list(range(16)),
            )
        # Measure in a temp-adjacent location the caller can clean up; receipt
        # records size/latency only — the file itself is disposable.
        tmp_path = Path(".tmp") / "p5_synthetic.catlas"
        m = measure_catlas_roundtrip(atlas, tmp_path)
        m.pop("loaded_atlas", None)  # not JSON-serialisable
        catlas_members.append(m)

    for raw in atlas_paths or []:
        m = measure_catlas_import(raw)
        m.pop("loaded_atlas", None)
        catlas_members.append(m)

    points = run_hebbian_scaling(dim=hebbian_dim, ns=hebbian_ns, reps=hebbian_reps)
    hebbian_status, ratio = _claim_hebbian(points)

    cart = CautreoCartographer(ram_ratio=0.10, circuit_breaker_threshold=0.85)
    ram_budget = measure_ram_budget(cart)
    sparse = measure_sparse_activation(total_neurons=14336, top_k_ratio=0.10)
    cautreo = measure_cautreo_latency() if include_cautreo else None

    claims = {
        "catlas_size_under_8mb": _claim_catlas_size(catlas_members),
        "catlas_load_under_2ms": _claim_catlas_load(catlas_members),
        "hebbian_o1_graph_size": hebbian_status,
        # Cannot verify without 100B weights on this host.
        "100b_on_10gb": "UNVERIFIED",
        # Measured numbers are observations, never a zero-latency product claim.
        "zero_latency_c_abi": "UNVERIFIED",
    }

    return CartographyBenchmarkReceipt(
        status_label=BENCHMARK_STATUS_LABEL,
        protocol=BENCHMARK_PROTOCOL,
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        claims=claims,
        catlas=catlas_members,
        hebbian={
            "points": points,
            "hebbian_scaling_ratio": ratio,
            "flat_ratio_threshold": HEBBIAN_FLAT_RATIO,
            "dim": hebbian_dim,
        },
        ram_budget=ram_budget,
        sparse_activation=sparse,
        cautreo=cautreo,
    )


def write_receipt(receipt: CartographyBenchmarkReceipt, path: str | Path) -> str:
    """Write receipt JSON to path. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return str(path)


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="P5 Cartography RAM/activation benchmark (Gate 9)"
    )
    parser.add_argument("--output", default="", help="Write receipt JSON to this path")
    parser.add_argument(
        "--atlas",
        action="append",
        default=[],
        help="Existing .catlas path to measure (repeatable)",
    )
    parser.add_argument("--skip-synthetic-atlas", action="store_true")
    parser.add_argument("--skip-cautreo", action="store_true")
    args = parser.parse_args()

    receipt = run_benchmark(
        atlas_paths=args.atlas,
        include_cautreo=not args.skip_cautreo,
        include_synthetic_atlas=not args.skip_synthetic_atlas,
    )
    print(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
    print(f"\nstatus_label={receipt.status_label}")
    for key, val in receipt.claims.items():
        print(f"  {key}: {val}")
    if args.output:
        write_receipt(receipt, args.output)
        print(f"receipt → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
