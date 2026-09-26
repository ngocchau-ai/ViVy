"""Summarize ViVy JSONL activity for local optimization decisions."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def analyze(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    responses = [r for r in rows if r.get("event") in {"model_response", "benchmark_case"}
                 and r.get("status") in {"OBSERVED", "PASS"}]
    return {
        "records": len(rows),
        "sessions": len({r.get("session_id") for r in rows if r.get("session_id")}),
        "events": dict(Counter(r.get("event", "unknown") for r in rows)),
        "statuses": dict(Counter(r.get("status", "unknown") for r in rows)),
        "responses": len(responses),
        "avg_latency_s": round(sum(r.get("elapsed_s", 0) for r in responses) / len(responses), 3) if responses else 0,
        "avg_prompt_tokens": round(sum(r.get("prompt_tokens", 0) for r in responses) / len(responses), 1) if responses else 0,
        "avg_completion_tokens": round(sum(r.get("completion_tokens", 0) for r in responses) / len(responses), 1) if responses else 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=".vivy_activity.jsonl")
    args = parser.parse_args()
    print(json.dumps(analyze(Path(args.path)), ensure_ascii=False, indent=2))
