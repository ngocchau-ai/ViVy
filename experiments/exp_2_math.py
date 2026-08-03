"""Experiment 2: Mathematics — Number Theory, Sequences & Combinatorics

Test the unitary-reasoner pipeline on mathematical problems:
  - Collatz conjecture (orbit simulation)
  - Goldbach's conjecture (even numbers as sum of two primes)
  - Fibonacci sequence (closed form)
  - Catalan numbers (combinatorial interpretation)
  - Primality testing (trial division)

Expected: KnowledgeInjector matches domain patterns and injects relevant facts,
raising confidence above the 0.5 placeholder baseline.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

# ruff: noqa: E402
from llm_bridge.client import LLMClient
from orchestrator.integration import solve_problem_verbose


async def run_experiment(question: str, label: str) -> dict:
    """Run a single experiment and return structured results."""
    print(f"\n{'='*60}")
    print(f"EXPERIMENT: {label}")
    print(f"{'='*60}")
    print(f"Q: {question}\n")

    client = LLMClient()
    start = time.time()

    try:
        answer, result = await solve_problem_verbose(question, llm_client=client)
        elapsed = time.time() - start

        print(f"A: {answer}")
        print(f"\nControl signal: {result.control_signal}")
        print(f"Confidence: {result.confidence}")
        print(f"Time: {elapsed:.2f}s")

        lf = result.logic_form
        print(f"\nPropositions ({len(lf.propositions)}):")
        for p in lf.propositions:
            print(f"  • {p}")
        print(f"Relations ({len(lf.relations)}):")
        for r in lf.relations:
            print(f"  • {r}")
        print(f"Query: {lf.query}")

        return {
            "label": label,
            "question": question,
            "answer": answer,
            "control_signal": result.control_signal,
            "confidence": result.confidence,
            "elapsed": elapsed,
            "propositions": lf.propositions,
            "relations": lf.relations,
            "query": lf.query,
            "status": "ok",
        }
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERROR: {e}")
        return {
            "label": label,
            "question": question,
            "answer": str(e),
            "status": "error",
            "elapsed": elapsed,
        }


async def main():
    experiments = [
        # === NUMBER THEORY ===
        (
            "The Collatz conjecture states that for any positive integer n, "
            "repeated application of f(n) = n/2 (if even) or 3n+1 (if odd) "
            "eventually reaches 1. Explain the conjecture and its current status.",
            "Collatz Conjecture — Statement & Status",
        ),
        (
            "Goldbach's conjecture states every even integer greater than 2 "
            "can be expressed as the sum of two primes. Explain this conjecture.",
            "Goldbach's Conjecture — Statement",
        ),
        (
            "What is a prime number? How do you test if a number is prime?",
            "Primality — Definition & Test",
        ),
        (
            "Are there infinitely many twin prime pairs (p, p+2)? "
            "Explain the twin prime conjecture.",
            "Twin Prime Conjecture — Statement",
        ),
        (
            "Does an odd perfect number exist? "
            "Explain the odd perfect number problem.",
            "Odd Perfect Number — Open Problem",
        ),
        # === SEQUENCES ===
        (
            "The Fibonacci sequence starts F_0 = 0, F_1 = 1, "
            "and F_n = F_{n-1} + F_{n-2}. "
            "What is the closed-form expression for F_n?",
            "Fibonacci Sequence — Closed Form",
        ),
        (
            "Catalan numbers C_n = (1/(n+1)) * binomial(2n, n). "
            "What combinatorial structures do they count?",
            "Catalan Numbers — Combinatorial Interpretation",
        ),
        # === ALGEBRAIC STRUCTURES ===
        (
            "An elliptic curve is defined by y^2 = x^3 + ax + b. "
            "How do points on an elliptic curve form a group?",
            "Elliptic Curves — Group Law",
        ),
        (
            "What is a finite field? "
            "Explain the structure of GF(p^k).",
            "Finite Fields — Structure",
        ),
    ]

    results = []
    for question, label in experiments:
        r = await run_experiment(question, label)
        results.append(r)
        await asyncio.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    ok = [r for r in results if r["status"] == "ok"]
    err = [r for r in results if r["status"] == "error"]
    print(f"Total: {len(results)}, OK: {len(ok)}, Error: {len(err)}")
    for r in results:
        status_icon = "✅" if r["status"] == "ok" else "❌"
        conf = r.get("confidence", "N/A")
        conf_str = f"{conf:.2f}" if isinstance(conf, float) else conf
        print(f"  {status_icon} {r['label']}: {conf_str} [{r['elapsed']:.1f}s]")

    with open("experiment_results_2_math.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nResults saved to experiment_results_2_math.json")


if __name__ == "__main__":
    asyncio.run(main())