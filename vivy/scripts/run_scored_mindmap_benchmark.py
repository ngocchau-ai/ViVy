#!/usr/bin/env python3
"""
run_scored_mindmap_benchmark.py — Gate 9 Benchmark Receipt.

Measures (does NOT claims):
  - rehydrate_active_subtask() latency (target < 5 ms)
  - ScoredMindmapDAG RAM overhead (target < 5 MB)
  - Sliding aperture token count (target < 300 tokens)

Output: vivyChatGPT/evidence/SCORED_MINDMAP_BENCHMARK_RECEIPT.json
"""

from __future__ import annotations

import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path

ws = Path(__file__).resolve().parents[1]
if str(ws) not in sys.path:
    sys.path.insert(0, str(ws))

from integration.checkpoint_manager import CheckpointManager  # noqa: E402
from integration.preflight_steering import (  # noqa: E402
    build_active_context,
    estimate_token_count,
)
from memory.cognitive_graph import ScoredMindmapDAG  # noqa: E402

RECEIPT_PATH = ws.parent / "vivyChatGPT" / "evidence" / "SCORED_MINDMAP_BENCHMARK_RECEIPT.json"
BENCH_SESSION = "benchmark-scored-mindmap"
N_ITERATIONS = 50


def _build_sample_dag() -> ScoredMindmapDAG:
    dag = ScoredMindmapDAG()
    dag.create_node("subtask-150", intent="Parse JSON with stdlib")
    dag.mark_in_progress("subtask-150")
    dag.stop_and_score(
        "subtask-150",
        score=3.0,
        rca_reason="stdlib json cannot handle NaN tokens",
        negative_constraint="Do not use stdlib json for NaN-bearing payloads",
    )
    dag.pivot_alternative(
        "subtask-150",
        "subtask-150-alt",
        "Parse JSON with orjson after NaN preprocessing",
    )
    return dag


def bench_rehydrate_latency(mgr: CheckpointManager, n: int = N_ITERATIONS) -> dict:
    latencies_ms: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        active, constraints = mgr.rehydrate_active_subtask(BENCH_SESSION)
        dt = (time.perf_counter() - t0) * 1000
        latencies_ms.append(dt)
    latencies_ms.sort()
    return {
        "unit": "ms",
        "n": n,
        "min": round(latencies_ms[0], 4),
        "median": round(latencies_ms[n // 2], 4),
        "p95": round(latencies_ms[int(n * 0.95)], 4),
        "max": round(latencies_ms[-1], 4),
        "active_task_id": active.task_id if active else None,
        "negative_constraint_count": len(constraints),
    }


def bench_ram_overhead() -> dict:
    tracemalloc.start()
    dag = _build_sample_dag()
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()
    stats = snapshot.statistics("filename")
    total_bytes = sum(s.size for s in stats)
    return {
        "unit": "bytes",
        "total": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 4),
        "node_count": len(dag.all_nodes()),
    }


def bench_aperture_tokens() -> dict:
    dag = _build_sample_dag()
    alt = dag.get_node("subtask-150-alt")
    assert alt is not None
    prompt = build_active_context(
        current_node=alt,
        parent_node=dag.get_node("subtask-150"),
        negative_constraints=dag.get_negative_constraints(),
        expected_evidence="Valid parsed dict with zero NaN leakage",
    )
    tokens = estimate_token_count(prompt)
    return {
        "unit": "tokens",
        "count": tokens,
        "ceiling": 300,
        "prompt_chars": len(prompt),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tmp_dir = ws / ".tmp" / "bench_checkpoints"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    mgr = CheckpointManager(checkpoint_dir=tmp_dir)
    dag = _build_sample_dag()
    mgr.save_scored_mindmap(BENCH_SESSION, dag)

    latency = bench_rehydrate_latency(mgr)
    ram = bench_ram_overhead()
    aperture = bench_aperture_tokens()

    receipt = {
        "receipt_type": "SCORED_MINDMAP_BENCHMARK",
        "plan_id": "PLAN-VIVY-SCORED-MINDMAP-DAG-2026-09-24",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "metrics": {
            "rehydrate_latency": latency,
            "ram_overhead": ram,
            "aperture_tokens": aperture,
        },
        "targets": {
            "rehydrate_latency_ms": 5.0,
            "ram_overhead_mb": 5.0,
            "aperture_tokens": 300,
        },
        "gate9_disclaimer": (
            "All metrics are MEASURED, not claimed. "
            "No 0%/0ms/PRODUCTION-READY assertions are made."
        ),
    }

    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Benchmark receipt written: {RECEIPT_PATH.name}")
    print(f"  rehydrate median: {latency['median']} ms  (target < 5)")
    print(f"  RAM overhead:     {ram['total_mb']} MB  (target < 5)")
    print(f"  aperture tokens:  {aperture['count']}  (target < 300)")


if __name__ == "__main__":
    main()
