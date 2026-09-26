"""Bounded local runtime benchmark; writes only redacted optimization telemetry."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integration.activity_log import ActivityLog

CASES = (
    ("known_answer", "What is 2+2? Answer with one digit."),
    ("directive_schema", "Return <vivy_thought> Confidence: HIGH; Epistemic_Decision: EXECUTE_DIRECTLY; Expected_Evidence: response contains PASS </vivy_thought> and then PASS."),
    ("unknown_signal", "Explain the obscure entity Zorvax-91 and state what evidence would verify it."),
)


def run(endpoint: str, model: str, max_tokens: int, log: ActivityLog) -> dict:
    results = []
    for name, prompt in CASES:
        started = time.perf_counter()
        payload = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0, "max_tokens": max_tokens, "stream": False}).encode()
        try:
            req = urllib.request.Request(endpoint + "/v1/chat/completions", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read())
            choice = data["choices"][0]
            content = choice["message"].get("content", "")
            usage = data.get("usage", {})
            row = {"case": name, "status": "PASS", "finish_reason": choice.get("finish_reason"),
                   "elapsed_s": round(time.perf_counter() - started, 3),
                   "prompt_tokens": usage.get("prompt_tokens", 0),
                   "completion_tokens": usage.get("completion_tokens", 0),
                   "output_hash": hashlib.sha256(content.encode()).hexdigest(),
                   "has_epistemic_block": "<vivy_thought>" in content,
                   "has_expected_evidence": "Expected_Evidence" in content}
        except Exception as exc:
            row = {"case": name, "status": "ERROR", "elapsed_s": round(time.perf_counter() - started, 3),
                   "error_type": type(exc).__name__}
        log.record("benchmark_case", session_id="activity-benchmark", **row)
        results.append(row)
    return {"run_id": uuid.uuid4().hex, "model": model, "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="gemma4-e4b")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--log", default=".vivy_activity.jsonl")
    args = parser.parse_args()
    print(json.dumps(run(args.endpoint, args.model, args.max_tokens, ActivityLog(args.log)), ensure_ascii=False, indent=2))
