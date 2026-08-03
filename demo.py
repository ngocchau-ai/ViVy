"""
Demo script for the Unitary Reasoner.

Runs the full encode → evolve → evaluate → decode pipeline on a syllogism
question and prints the natural-language answer.

Usage:
    python demo.py                      # offline, mocked LLM
    UNITARY_API_BASE=... python demo.py # live OpenAI-compatible API
"""

from __future__ import annotations

import asyncio
import os
import sys


def _load_env() -> None:
    """Load .env if present (simple KEY=VALUE parser, no external dep)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


async def main() -> None:
    _load_env()
    from llm_bridge.client import LLMClient
    from orchestrator.integration import solve_problem_verbose

    # Beta 1 default: live Ollama + Gemma 4EB (from .env). If no API base is
    # configured and Ollama is unreachable, fall back to the offline mock.
    if not os.environ.get("UNITARY_API_BASE"):
        print("[demo] No UNITARY_API_BASE set — using offline mock LLM.\n")
        from tests.test_e2e_syllogism import _SyllogismClient

        client = _SyllogismClient()  # type: ignore[assignment]
    else:
        client = LLMClient()

    question = "All A are B. All B are C. Therefore, are all A C?"

    print(f"QUESTION : {question}\n")
    answer, result = await solve_problem_verbose(question, llm_client=client)

    print("LOGIC FORM:")
    print(f"  propositions : {result.logic_form.propositions}")
    print(f"  relations    : {result.logic_form.relations}")
    print(f"  query        : {result.logic_form.query}")
    print(f"\nCONFIDENCE    : {result.confidence:.2f}")
    print(f"CONTROL SIGNAL: {result.control_signal}")
    print(f"\nANSWER        : {answer}\n")

    if isinstance(client, LLMClient):
        await client.close()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())
