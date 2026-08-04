"""Experiment 3: Graph Theory — Non-Isomorphism & Symmetry Detection

Test the unitary-reasoner pipeline on structural graph problems:
  - Graph isomorphism / non-isomorphism detection
  - Symmetry detection in boolean formulas
  - Constraint satisfaction (graph coloring)

Expected: KnowledgeInjector matches graph-theory domain patterns and injects
relevant facts, raising confidence above the 0.5 placeholder baseline.
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
        # === GRAPH ISOMORPHISM ===
        (
            "Two graphs G1 and G2 are isomorphic if there exists a bijection "
            "between their vertex sets that preserves adjacency. "
            "Explain the graph isomorphism problem and its complexity.",
            "Graph Isomorphism — Problem Definition",
        ),
        (
            "The Weisfeiler-Lehman algorithm computes a canonical labeling "
            "of graph vertices. How does it detect non-isomorphic graphs?",
            "Weisfeiler-Lehman — Graph Canonization",
        ),
        (
            "A complete graph K3 (triangle) and a cycle C3 (3-cycle) "
            "are isomorphic. Explain why.",
            "Graph Isomorphism — K3 vs C3",
        ),
        (
            "A complete graph K3 and a path graph P3 (3 vertices) "
            "are NOT isomorphic. Explain why.",
            "Graph Non-Isomorphism — K3 vs P3",
        ),
        # === SYMMETRY DETECTION ===
        (
            "The boolean formula (x AND y) OR (NOT x AND NOT y) "
            "is symmetric under swapping x and y. Explain this symmetry.",
            "Boolean Symmetry — XOR-like Formula",
        ),
        (
            "The boolean formula (x AND y) OR (x AND z) "
            "is NOT symmetric under swapping y and z. Explain why.",
            "Boolean Asymmetry — Non-Symmetric Formula",
        ),
        # === CONSTRAINT SATISFACTION ===
        (
            "The graph coloring problem asks whether vertices of a graph "
            "can be colored with k colors such that adjacent vertices "
            "have different colors. Explain this problem.",
            "Graph Coloring — Problem Definition",
        ),
        (
            "A complete graph K4 requires 4 colors for proper coloring. "
            "Explain why K4 is not 3-colorable.",
            "Graph Coloring — K4 Chromatic Number",
        ),
        # === LATIN SQUARES ===
        (
            "A Latin square of order n is an n×n array filled with n symbols, "
            "each appearing exactly once in each row and column. "
            "Explain the connection between Latin squares and group theory.",
            "Latin Squares — Group Theory Connection",
        ),
        # === SUDOKU ===
        (
            "Sudoku is a constraint satisfaction problem. "
            "A 4×4 Sudoku puzzle uses numbers 1-4 in a 4×4 grid "
            "with 2×2 blocks. Explain the constraints.",
            "Sudoku 4×4 — Constraint Satisfaction",
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

    with open("experiment_results_3_graph.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nResults saved to experiment_results_3_graph.json")


if __name__ == "__main__":
    asyncio.run(main())
