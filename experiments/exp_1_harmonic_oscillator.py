"""
Experiment 1: Quantum Harmonic Oscillator
===========================================
Test the unitary-reasoner pipeline on the quantum harmonic oscillator:
  H = p²/2m + ½mω²x²

The system should:
1. Encode the Hamiltonian as a unitary evolution problem
2. Apply time evolution through the MPS core
3. Decode the energy eigenstates and time evolution
"""

import asyncio
import json
import os
import sys
import time

# Ensure project root is on the path when run as a script.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

from llm_bridge.client import LLMClient
from llm_bridge.decoder import CoreResult
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

        # Show logic form
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
        # === HARMONIC OSCILLATOR ===
        (
            "A quantum harmonic oscillator has Hamiltonian H = p²/2m + ½mω²x². "
            "What are the energy eigenvalues?",
            "Harmonic Oscillator — Energy Eigenvalues",
        ),
        (
            "For a quantum harmonic oscillator in the ground state, "
            "what is the wavefunction ψ₀(x)?",
            "Harmonic Oscillator — Ground State",
        ),
        (
            "A particle in a 1D infinite square well of width L is in the ground state. "
            "What is its energy?",
            "Particle in a Box — Ground State Energy",
        ),
        # === SPIN-1/2 SYSTEM ===
        (
            "A spin-1/2 particle is in state |+⟩. "
            "What is the probability of measuring spin up along the x-axis?",
            "Spin-1/2 — Measurement Probability",
        ),
        (
            "Apply the Pauli-X gate to state |0⟩. What is the resulting state?",
            "Spin-1/2 — Pauli-X Gate",
        ),
        # === QUANTUM TUNNELING ===
        (
            "A particle of energy E approaches a finite potential barrier of height V₀ > E. "
            "Explain quantum tunneling through this barrier.",
            "Quantum Tunneling — Barrier Penetration",
        ),
        # === BELL INEQUALITY ===
        (
            "In the CHSH game, two players share an entangled Bell pair. "
            "What is the maximum winning probability with quantum strategies?",
            "Bell Inequality — CHSH Game",
        ),
    ]

    results = []
    for question, label in experiments:
        r = await run_experiment(question, label)
        results.append(r)
        # Brief pause between experiments
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
        print(f"  {status_icon} {r['label']}: {r.get('confidence', 'N/A')} [{r['elapsed']:.1f}s]")

    # Save results
    with open("experiment_results_1_quantum.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to experiment_results_1_quantum.json")


if __name__ == "__main__":
    asyncio.run(main())