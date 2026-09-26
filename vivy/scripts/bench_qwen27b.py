"""
bench_qwen27b.py — Evaluation script: Qwen3.8-27B vs Gemma4 E4B

[ISOLATED 26/09/2026] GIỮ LÀM TÀI LIỆU SO SÁNH / THAM KHẢO.
Script này giả định `qwen3.8-27b` còn sống — thực tế gguf đã `ISOLATED_ARCHIVED`
21/09/2026 (giải phóng NVMe cho Qwen2-VL-72B) và bị gỡ tham chiếu sống 26/09/2026.
Giữ nguyên để đối chiếu cách đo 3 benchmark + ngưỡng ra quyết định PASS/FAIL
(>= 2 tok/s, epistemic block OK, tool call OK). Không dùng làm đích nạp model.
Nguồn sự thật về trọng số: `models/model_manifest.json` (`full_path`, `status`).

Chạy 3 benchmark tasks, đo speed và quality, ra quyết định.

Usage:
    python scripts/bench_qwen27b.py

Verdict:
    PASS  (>= 2 tok/s, epistemic block OK, tool call OK) → continue Qwen27B
    FAIL  (< 1 tok/s hoặc quality issues)               → switch Gemma4 E4B

Changelog:
    21/09/2026 (Antigravity IDE): Initial — 1h evaluation framework.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

os.environ.setdefault("VIVY_LLAMA_URL", "http://127.0.0.1:8080")
os.environ.setdefault("VIVY_MODEL", "qwen3.8-27b")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

VIVY_URL = os.environ["VIVY_LLAMA_URL"]
MODEL = os.environ["VIVY_MODEL"]

TIMEOUT = 180  # 3 min per test

def chat(messages: list[dict], max_tokens: int = 100) -> tuple[str, float, float]:
    """Returns (content, elapsed_s, tok_per_s)."""
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.15,
    }).encode()
    t0 = time.perf_counter()
    req = urllib.request.Request(
        f"{VIVY_URL}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read())
    elapsed = time.perf_counter() - t0
    content = data["choices"][0]["message"]["content"] or ""
    usage = data.get("usage", {})
    gen_tokens = usage.get("completion_tokens", max(1, len(content.split())))
    tps = gen_tokens / elapsed
    return content, elapsed, tps


def run_eval() -> None:
    print("=" * 60)
    print(f"BENCHMARK: {MODEL} @ {VIVY_URL}")
    print(f"Deadline: {TIMEOUT}s per test | Target: >= 2 tok/s")
    print("=" * 60)

    results = []

    # --- Test 1: Raw speed (minimal prompt) ---
    print("\n[T1] Raw speed — 20 tokens output...")
    try:
        content, elapsed, tps = chat(
            [{"role": "user", "content": "Count from 1 to 20, one number per line."}],
            max_tokens=60,
        )
        ok = tps >= 2.0
        status = "✅ PASS" if ok else "⚠️  SLOW"
        print(f"  {status} — {tps:.2f} tok/s ({elapsed:.1f}s)")
        print(f"  Preview: {content[:80].strip()!r}")
        results.append(("speed", tps, ok))
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("speed", 0, False))

    # --- Test 2: Epistemic block ---
    from integration.vivy_inference_loop import VIVY_SYSTEM_PROMPT
    print("\n[T2] Epistemic block — <vivy_thought> present?...")
    try:
        content, elapsed, tps = chat([
            {"role": "system", "content": VIVY_SYSTEM_PROMPT},
            {"role": "user", "content": "What is 2+2?"},
        ], max_tokens=150)
        has_block = "<vivy_thought>" in content
        ok = has_block and tps >= 1.0
        status = "✅ PASS" if ok else ("⚠️  NO_BLOCK" if not has_block else "⚠️  SLOW")
        print(f"  {status} — {tps:.2f} tok/s ({elapsed:.1f}s)")
        print(f"  vivy_thought: {'PRESENT' if has_block else 'MISSING'}")
        results.append(("epistemic", tps, ok))
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("epistemic", 0, False))

    # --- Test 3: Tool call format ---
    print("\n[T3] Tool call detection...")
    try:
        content, elapsed, tps = chat([
            {"role": "system", "content": VIVY_SYSTEM_PROMPT},
            {"role": "user", "content": "Read the file D:/test.txt using engine_file_io."},
        ], max_tokens=200)
        has_tool = "engine_file_io" in content or "tool_call" in content.lower()
        ok = has_tool and tps >= 1.0
        status = "✅ PASS" if ok else ("⚠️  NO_TOOL" if not has_tool else "⚠️  SLOW")
        print(f"  {status} — {tps:.2f} tok/s ({elapsed:.1f}s)")
        print(f"  Tool mention: {'YES' if has_tool else 'NO'}")
        results.append(("tool_call", tps, ok))
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("tool_call", 0, False))

    # --- Verdict ---
    print("\n" + "=" * 60)
    passes = sum(1 for _, _, ok in results if ok)
    avg_tps = sum(tps for _, tps, _ in results if tps > 0) / max(1, len(results))

    print(f"RESULTS: {passes}/3 tests passed | Avg speed: {avg_tps:.2f} tok/s")
    print()

    if passes >= 2 and avg_tps >= 1.5:
        print("✅ VERDICT: PASS — Qwen3.8-27B đủ dùng cho HoH async tasks")
        print("   → Tiếp tục Phase 2 HoH session")
        verdict = "PASS"
    elif avg_tps >= 1.0:
        print("⚠️  VERDICT: MARGINAL — Dùng được nhưng chậm")
        print("   → Có thể tiếp tục nếu chấp nhận 60-120s/response")
        verdict = "MARGINAL"
    else:
        print("❌ VERDICT: FAIL — Quá chậm, switch về Gemma4 E4B")
        print("   Fallback: D:\\models\\gemma4-e4b\\vivy-gemma-e4b-q4km.gguf")
        print("   Chạy: .\\scripts\\start_vivy_gemma4.ps1")
        verdict = "FAIL"

    print("=" * 60)

    # Save result
    result_path = __import__("pathlib").Path(__file__).parent.parent / ".vivy_bench_result.json"
    result_path.write_text(json.dumps({
        "model": MODEL, "verdict": verdict,
        "avg_tps": round(avg_tps, 2), "passes": passes,
        "tests": [{"name": n, "tps": round(t, 2), "ok": o} for n, t, o in results],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2), encoding="utf-8")
    print(f"\nResult saved: {result_path}")


if __name__ == "__main__":
    run_eval()
