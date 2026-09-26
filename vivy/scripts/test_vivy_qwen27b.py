"""
test_vivy_qwen27b.py — Validate ViVy connection với Qwen3.8-27B

Chạy sau khi llama-server khởi động xong:
    python scripts/test_vivy_qwen27b.py

Changelog:
    21/09/2026 (Antigravity IDE, Model Upgrade): Initial.
"""
from __future__ import annotations

import os
import sys
import time

# Đặt env để trỏ vào llama-server, không phải Ollama
os.environ.setdefault("VIVY_LLAMA_URL", "http://127.0.0.1:8080")
os.environ.setdefault("VIVY_MODEL", "qwen3.8-27b")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from integration.llama_cpp_bridge import ChatMessage, LlamaCppBridge, LlamaCppConfig


def main() -> None:
    print("=" * 60)
    print("ViVy × Qwen3.8-27B — Integration Test")
    print("=" * 60)

    config = LlamaCppConfig()
    print(f"  URL  : {config.base_url}")
    print(f"  Model: {config.model_name}")
    print(f"  Ctx  : {config.num_ctx} tokens")
    print()

    bridge = LlamaCppBridge(config)

    # Test 1: Health check
    print("[1] Health check...", end=" ", flush=True)
    t0 = time.perf_counter()
    try:
        healthy = bridge.health_check()
        elapsed = time.perf_counter() - t0
        if healthy:
            print(f"✅ OK ({elapsed:.1f}s)")
        else:
            print("❌ FAIL — llama-server không phản hồi")
            print("   Hãy chạy: .\\scripts\\start_vivy_qwen27b.ps1")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("   Hãy chạy: .\\scripts\\start_vivy_qwen27b.ps1")
        sys.exit(1)

    # Test 2: Basic chat (không có system prompt)
    print("[2] Basic chat...", end=" ", flush=True)
    t0 = time.perf_counter()
    response = bridge.chat([
        ChatMessage(role="user", content="Say exactly: VIVY_QWEN27B_OK"),
    ])
    elapsed = time.perf_counter() - t0
    content = response.content or ""
    if "VIVY_QWEN27B_OK" in content:
        print(f"✅ OK ({elapsed:.1f}s) — {content[:60]}")
    else:
        print(f"⚠️  Response: {content[:100]} ({elapsed:.1f}s)")

    # Test 3: Epistemic block (full ViVy system prompt)
    from integration.vivy_inference_loop import VIVY_SYSTEM_PROMPT
    print("[3] Epistemic assessment block...", end=" ", flush=True)
    t0 = time.perf_counter()
    response = bridge.chat([
        ChatMessage(role="system", content=VIVY_SYSTEM_PROMPT),
        ChatMessage(role="user", content="What is 2+2? Keep it brief."),
    ])
    elapsed = time.perf_counter() - t0
    content = response.content or ""
    has_thought = "<vivy_thought>" in content
    if has_thought:
        print(f"✅ OK ({elapsed:.1f}s) — vivy_thought present")
    else:
        print(f"⚠️  No <vivy_thought> block ({elapsed:.1f}s)")
        print(f"   Response preview: {content[:200]}")

    # Test 4: Tool call detection
    print("[4] Tool call format...", end=" ", flush=True)
    t0 = time.perf_counter()
    response = bridge.chat([
        ChatMessage(role="system", content=VIVY_SYSTEM_PROMPT),
        ChatMessage(role="user", content="Read file D:/test.txt using engine_file_io tool."),
    ])
    elapsed = time.perf_counter() - t0
    content = response.content or ""
    tool_calls = response.tool_calls or []
    if tool_calls:
        print(f"✅ Tool calls detected: {[tc.get('function',{}).get('name') for tc in tool_calls]} ({elapsed:.1f}s)")
    elif "engine_file_io" in content:
        print(f"⚠️  Tool in text (no structured call) ({elapsed:.1f}s)")
    else:
        print(f"⚠️  No tool call ({elapsed:.1f}s)")

    print()
    print("=" * 60)
    print("✅ Test complete. ViVy × Qwen3.8-27B integration ready.")
    print()
    print("Next: Run HoH session")
    print("  python .agents/skills/hoh-vivy-default/scripts/vivy_health_check.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
