"""
Weight Pager Benchmark — measures page_in latency, stream_compute throughput, RAM peak.

Gate 9: writes observations only to receipt JSON. No performance claims.

Usage:
    python scripts/run_weight_pager_benchmark.py [--model PATH] [--output PATH]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from integration.cautreo_binding import (  # noqa: E402
    CautreoWeightPager,
    is_native_pager_available,
)

DEFAULT_MODEL = "D:/models/gemma4-e4b/vivy-gemma-e4b-q4km.gguf"
DEFAULT_OUTPUT = "vivyChatGPT/evidence/WEIGHT_PAGER_BENCHMARK_RECEIPT.json"


def run_benchmark(model_path: str, output_path: str) -> dict:
    observations: dict = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_path": model_path,
        "native_pager": is_native_pager_available(),
        "observations": {},
    }

    if not is_native_pager_available():
        observations["observations"]["skip_reason"] = "cautreo_pager.dll not available"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(observations, indent=2), encoding="utf-8")
        return observations

    with CautreoWeightPager(model_path=model_path) as pager:
        observations["observations"]["total_slices"] = pager.total_slices

        names = list(pager._slices.keys())[:20]
        page_in_times = []
        for name in names:
            t0 = time.perf_counter()
            pager.page_in(name)
            dt = (time.perf_counter() - t0) * 1000
            page_in_times.append({"slice": name, "page_in_ms": round(dt, 3)})

        observations["observations"]["page_in_latency_ms"] = page_in_times

        ram_peak = pager.get_ram_usage_mb()
        observations["observations"]["ram_peak_mb"] = round(ram_peak, 2)

        # Stream compute on first slice
        if names:
            first = names[0]
            info = pager._slices[first]
            if info.n_dims >= 2 and len(info.dims) >= 2:
                cols = int(info.dims[-1])
                input_vec = [1.0] * min(cols, 64)
                t0 = time.perf_counter()
                out = pager.stream_compute(first, input_vec)
                dt = (time.perf_counter() - t0) * 1000
                observations["observations"]["stream_compute"] = {
                    "slice": first,
                    "input_len": len(input_vec),
                    "output_len": len(out),
                    "elapsed_ms": round(dt, 3),
                }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(observations, indent=2), encoding="utf-8")
    print(f"Benchmark receipt written to {output_path}")
    return observations


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not Path(args.model).is_file():
        print(f"Model not found: {args.model}")
        sys.exit(1)

    result = run_benchmark(args.model, args.output)
    print(json.dumps(result["observations"], indent=2))
