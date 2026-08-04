"""Experiment 4: Mathematical Computation — Actual Calculation & Reasoning

Unlike exp_2 (domain recognition), this forces the model to *compute*:
  - Exact numerical results (Fibonacci, Catalan, series sum)
  - Equation solving (quadratic, derivative, integral)
  - Number theory (prime factorization, modular arithmetic, Goldbach verification)
  - Linear algebra (eigenvalues)

Each problem has a ground-truth answer.  We report both the pipeline's
confidence AND whether the model's output contains the correct result.
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from core import DomainFact, KnowledgeInjector
from llm_bridge import LLMClient
from orchestrator.integration import solve_problem_verbose

load_dotenv()


def _problem(question: str, answer: str) -> dict:
    """Build a computation problem with ground truth."""
    return {
        "question": question,
        "answer": answer,
    }


PROBLEMS = [
    _problem(
        "Compute the 50th Fibonacci number. Show your work.",
        "12586269025",
    ),
    _problem(
        "Verify Goldbach's conjecture for 100: find two primes that sum to 100.",
        "97",
    ),
    _problem(
        "Solve the quadratic equation x^2 - 5x + 6 = 0. Give both roots.",
        "3",
    ),
    _problem(
        "Compute the definite integral from 0 to 1 of x^2 dx.",
        "1/3",
    ),
    _problem(
        "Factor 84 into prime factors.",
        "2^2",
    ),
    _problem(
        "Find the eigenvalues of the 2x2 matrix [[2, 1], [1, 2]].",
        "3",
    ),
    _problem(
        "Compute the 10th Catalan number C(10).",
        "16796",
    ),
    _problem(
        "Sum the integers from 1 to 100.",
        "5050",
    ),
    _problem(
        "Compute 7^5 modulo 13.",
        "11",
    ),
    _problem(
        "Find the derivative of x^3 sin(x) evaluated at x = pi.",
        "pi^3",
    ),
]


def _normalize(text: str) -> str:
    """Collapse whitespace, lowercase, remove punctuation for matching."""
    text = re.sub(r"[^a-z0-9/^+\-*=\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _answer_in_output(answer: str, output: str) -> bool:
    """Check if the ground-truth answer appears in the model output."""
    norm_output = _normalize(output)
    norm_answer = _normalize(answer)
    # Direct substring match
    if norm_answer in norm_output:
        return True
    # Number matching: strip all spaces and compare digit sequences
    digits_answer = re.sub(r"\D", "", norm_answer)
    digits_output = re.sub(r"\D", "", norm_output)
    if digits_answer and digits_answer in digits_output:
        return True
    # Regex word-boundary match
    if re.search(rf"\b{re.escape(norm_answer)}\b", norm_output):
        return True
    return False


async def run_experiment(client: LLMClient, prob: dict, idx: int) -> dict:
    question = prob["question"]
    expected = prob["answer"]
    print(f"\n{'='*60}")
    print(f"EXPERIMENT {idx}: {question[:80]}...")
    print(f"{'='*60}")

    t0 = time.time()
    try:
        answer, result = await solve_problem_verbose(question, llm_client=client)
        elapsed = time.time() - t0

        confidence = float(result.confidence)
        control = str(result.control_signal)
        conclusion = str(answer)

        correct = _answer_in_output(expected, conclusion)

        print(f"  Confidence: {confidence:.3f}")
        print(f"  Correct: {correct} (expected '{expected}')")
        print(f"  Control: {control}")
        print(f"  Answer: {conclusion[:120]}")
        print(f"  Time: {elapsed:.1f}s")

        return {
            "experiment": idx,
            "question": question,
            "expected": expected,
            "answer": conclusion,
            "confidence": round(confidence, 4),
            "correct": correct,
            "control": control,
            "time_seconds": round(elapsed, 1),
            "status": "ok",
        }
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ERROR: {e}")
        return {
            "experiment": idx,
            "question": question,
            "expected": expected,
            "confidence": 0.0,
            "correct": False,
            "error": str(e),
            "time_seconds": round(elapsed, 1),
            "status": "error",
        }


async def main() -> None:
    injector = KnowledgeInjector()
    # Register a computation domain fact so the pipeline has something to inject
    injector.facts.append(
        DomainFact(
            "math.computation",
            "general mathematical computation",
            "Apply the appropriate mathematical operation to compute the exact result.",
            0.85,
        )
    )

    client = LLMClient()
    results = []
    total_ok = 0

    for i, prob in enumerate(PROBLEMS, 1):
        r = await run_experiment(client, prob, i)
        if r.get("correct"):
            total_ok += 1
        results.append(r)
        await asyncio.sleep(1)

    n = len(PROBLEMS)
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {n}, Correct: {total_ok}, Error: {n - total_ok}")
    for r in results:
        mark = "✅" if r.get("correct") else "❌"
        print(f"  {mark} {r['question'][:60]}: "
              f"conf={r['confidence']:.2f}, "
              f"expected='{r['expected']}'")

    out_path = Path(__file__).resolve().parent.parent / "experiment_results_4_computation.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
