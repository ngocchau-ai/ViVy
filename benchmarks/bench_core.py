"""Benchmark: bond dimension vs latency for the Unitary Reasoner core.

Measures how MPS bond dimension affects gate-application latency and memory,
plus dense-vs-MPS timing for representative reasoning circuits.

Usage
-----
    python -m benchmarks.bench_core
    python -m benchmarks.bench_core --n-qubits 12 --bonds 8 16 32 64
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np

# Ensure the project root is importable when run as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.evolution import GateSchedule, UnitaryEvolution  # noqa: E402
from core.gates import cnot, hadamard  # noqa: E402
from core.mps import MPS  # noqa: E402


def _random_state_vector(n_qubits: int, seed: int = 0) -> np.ndarray:
    """Create a random normalized state vector."""
    rng = np.random.default_rng(seed)
    vec = (rng.standard_normal(1 << n_qubits)
           + 1j * rng.standard_normal(1 << n_qubits))
    return vec / np.linalg.norm(vec)


def _random_mps(n_qubits: int, bond: int, seed: int = 0) -> MPS:
    """Create a random MPS with the given max bond dimension."""
    rng = np.random.default_rng(seed)
    tensors = []
    for k in range(n_qubits):
        left = 1 if k == 0 else bond
        right = 1 if k == n_qubits - 1 else bond
        t = (rng.standard_normal((left, 2, right))
             + 1j * rng.standard_normal((left, 2, right)))
        tensors.append(t)
    mps = MPS(tensors, canonicalize=False)
    mps.canonical_form(target_center=0)
    return mps


def _reasoning_schedule(n_qubits: int) -> GateSchedule:
    """A representative reasoning circuit: H on all, then nearest-neighbor CNOTs."""
    sched = GateSchedule(label="reasoning")
    for q in range(n_qubits):
        sched.add(hadamard(), [q])
    for q in range(n_qubits - 1):
        sched.add(cnot(), [q, q + 1])
    return sched


def time_mps_apply(n_qubits: int, bond: int, n_reps: int = 3) -> float:
    """Average latency (seconds) for one CNOT application on an MPS."""
    mps = _random_mps(n_qubits, bond)
    times = []
    for _ in range(n_reps):
        m = MPS.from_vector(mps.to_vector(), bond_dim=bond)
        start = time.perf_counter()
        m.apply_gate(cnot(), [0, 1], max_bond=bond)
        times.append(time.perf_counter() - start)
    return float(np.mean(times))


def time_dense_step(n_qubits: int, n_reps: int = 3) -> float:
    """Average latency (seconds) for one dense reasoning step."""
    evo = UnitaryEvolution(mode="dense")
    state = _random_state_vector(n_qubits)
    sched = _reasoning_schedule(n_qubits)
    times = []
    for _ in range(n_reps):
        start = time.perf_counter()
        evo.step(state, sched)
        times.append(time.perf_counter() - start)
    return float(np.mean(times))


def bench_bond_vs_latency(
    n_qubits: int,
    bonds: Sequence[int],
    n_reps: int = 3,
) -> dict[int, float]:
    """Benchmark MPS gate latency vs bond dimension.

    Parameters
    ----------
    n_qubits : int
        Number of qubits.
    bonds : Sequence[int]
        Bond dimensions to test.
    n_reps : int
        Repetitions per bond dimension.

    Returns
    -------
    Dict[int, float]
        Mapping bond_dim -> average latency (seconds).
    """
    results: dict[int, float] = {}
    for bond in bonds:
        results[bond] = time_mps_apply(n_qubits, bond, n_reps)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Unitary Reasoner core")
    parser.add_argument("--n-qubits", type=int, default=10)
    parser.add_argument("--bonds", type=int, nargs="+", default=[4, 8, 16, 32])
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()

    print("=== Unitary Reasoner core benchmark ===")
    print(f"n_qubits={args.n_qubits}, reps={args.reps}")
    print()

    # Bond dimension vs latency
    print("--- MPS gate latency vs bond dimension ---")
    print(f"{'bond':>6} {'latency (ms)':>14} {'norm':>10}")
    results = bench_bond_vs_latency(args.n_qubits, args.bonds, args.reps)
    for bond, lat in results.items():
        print(f"{bond:>6} {lat * 1e3:>14.3f}")

    # Dense comparison
    print()
    print("--- Dense state-vector comparison ---")
    dense_lat = time_dense_step(args.n_qubits, args.reps)
    print(f"dense step latency: {dense_lat * 1e3:.3f} ms "
          f"(2^{args.n_qubits} dim)")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
