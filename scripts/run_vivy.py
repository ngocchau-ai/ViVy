#!/usr/bin/env python3
"""
ViVy Inference Runner — Sprint 3.

One-command launch for ViVy Final Core V1.0.

Usage:
    python scripts/run_vivy.py --mode chat
    python scripts/run_vivy.py --mode agentic
    python scripts/run_vivy.py --mode batch --input "Explain ElasticNCore"

Requires:
    - llama-server running on port 8080 (or VIVY_LLAMA_URL env var)
    - Gemma 4 E4B Q4_K_M loaded

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integration.llama_cpp_bridge import LlamaCppBridge, LlamaCppConfig
from integration.vivy_inference_loop import InferenceMode, VivyInferenceLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vivy.runner")


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------


BANNER = r"""
 ╔═══════════════════════════════════════════════════════════╗
 ║          ViVy Final Core V1.0 — Omni-Epistemic AI         ║
 ║  ElasticNCore · CognitiveStateGraph · HebbianRecall O(1)  ║
 ║  Base model: Gemma 4 E4B (Text + Vision + Audio)          ║
 ╚═══════════════════════════════════════════════════════════╝
"""


# ---------------------------------------------------------------------------
# Mode runners
# ---------------------------------------------------------------------------


def run_chat(vivy: VivyInferenceLoop) -> None:
    """Interactive CHAT mode — single-turn, no tool calling."""
    print(BANNER)
    print("Mode: CHAT | Ctrl+C or 'exit' to quit\n")

    session_id = "chat_default"
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[ViVy] Goodbye.")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("[ViVy] Goodbye.")
            break
        if not user_input:
            continue

        result = vivy.infer(user_input, session_id=session_id, mode=InferenceMode.CHAT)

        if result.ok:
            print(f"\nViVy: {result.response_text}")
            print(
                f"  [{result.epistemic_decision} | {result.llm_tokens_used} tokens | "
                f"{result.total_elapsed_ms:.0f}ms | graph nodes: {vivy._sessions.get_session(session_id).graph.__len__() if vivy._sessions.get_session(session_id) else '?'}]\n"
            )
        else:
            print(f"\n[ERROR] {result.error}\n")


def run_agentic(vivy: VivyInferenceLoop) -> None:
    """Interactive AGENTIC mode — multi-turn with tool calling."""
    print(BANNER)
    print("Mode: AGENTIC | Tool calling enabled | Ctrl+C or 'exit' to quit\n")

    session_id = "agentic_default"
    while True:
        try:
            user_input = input("Task: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[ViVy] Goodbye.")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("[ViVy] Goodbye.")
            break
        if not user_input:
            continue

        result = vivy.infer(user_input, session_id=session_id, mode=InferenceMode.AGENTIC)

        if result.ok:
            print(f"\nViVy: {result.response_text}")

            if result.tool_dispatch_results:
                print(f"\n  Tools used ({result.rounds} rounds):")
                for dr in result.tool_dispatch_results:
                    status = "✓" if dr.ok else "✗"
                    print(f"    {status} {dr.tool_name} ({dr.elapsed_ms:.0f}ms)")

            print(
                f"  [{result.epistemic_decision} | {result.llm_tokens_used} tokens | "
                f"{result.total_elapsed_ms:.0f}ms]\n"
            )
        else:
            print(f"\n[ERROR] {result.error}\n")


def run_batch(vivy: VivyInferenceLoop, input_text: str) -> None:
    """Single batch inference — non-interactive."""
    print(BANNER)
    print(f"Mode: BATCH\nInput: {input_text}\n")

    result = vivy.infer(input_text, session_id="batch", mode=InferenceMode.BATCH)

    if result.ok:
        print(f"Response:\n{result.response_text}")
        print(f"\nStats: {result.epistemic_decision} | {result.llm_tokens_used} tokens | {result.total_elapsed_ms:.0f}ms")
    else:
        print(f"ERROR: {result.error}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ViVy Final Core V1.0 — Inference Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--mode", choices=["chat", "agentic", "batch"], default="agentic")
    parser.add_argument("--input", type=str, help="Input text for batch mode")
    parser.add_argument("--server", type=str, help="llama-server URL (overrides VIVY_LLAMA_URL)")
    parser.add_argument("--model", type=str, help="Model name (overrides VIVY_MODEL)")
    args = parser.parse_args()

    # Override env vars from CLI args
    if args.server:
        os.environ["VIVY_LLAMA_URL"] = args.server
    else:
        os.environ.setdefault("VIVY_LLAMA_URL", "http://127.0.0.1:11434")
    if args.model:
        os.environ["VIVY_MODEL"] = args.model
    else:
        os.environ.setdefault("VIVY_MODEL", "vivy-final:v1")

    # Build ViVy
    bridge = LlamaCppBridge()

    # Health check
    if not bridge.health():
        print(f"[ERROR] Cannot connect to Ollama at {bridge.config.base_url}")
        print("  Make sure Ollama is running:")
        print("    ollama serve")
        print("  And that vivy-final:v1 is built:")
        print("    ollama create vivy-final:v1 -f Modelfile.vivy")
        sys.exit(1)

    print(f"[OK] Connected to Ollama at {bridge.config.base_url}")
    models = bridge.list_models()
    if models:
        print(f"[OK] Available models: {', '.join(models[:5])}")

    vivy = VivyInferenceLoop.from_env()
    # Replace bridge with health-checked one
    vivy._bridge = bridge

    # Run selected mode
    if args.mode == "chat":
        run_chat(vivy)
    elif args.mode == "agentic":
        run_agentic(vivy)
    elif args.mode == "batch":
        if not args.input:
            print("[ERROR] --input required for batch mode")
            sys.exit(1)
        run_batch(vivy, args.input)


if __name__ == "__main__":
    main()
