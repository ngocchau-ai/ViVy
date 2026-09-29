"""Deterministic generator for the T2 eval set (WP-7 / O-02).

120 items — 4 domains × 30 (``quantum`` · ``math`` · ``graph`` · ``compute``).
Each domain splits **8 dev / 22 held-out**.  30 items are adversarial
(underdetermined, or missing the one datum the question needs); the other 90 are
answerable.

Every answer is **computed**, never typed, so the set cannot carry a typo as a
ground truth.  The generator is seeded, so re-running it reproduces the set
byte-for-byte and the committed hashes stay valid.

D-7 (29/09/2026): held-out is written **outside** ``Vivy_final/``.  This script
refuses to materialise held-out inside the repo tree.  What the repo commits is
``heldout_manifest.json`` — ids and SHA-256 only, no prompt and no answer — so
the harness can reject a substituted file without the answer ever sitting in a
knowledge base.

Usage
-----
    # the 32 dev items, committed in the repo
    python -m benchmarks.eval_set.generate --split dev

    # the 88 held-out items, for the project owner (D-7)
    python -m benchmarks.eval_set.generate --split heldout \\
        --out D:\\91s_heldout\\vivy_T2\\heldout_set.jsonl

    # refresh the committed manifest
    python -m benchmarks.eval_set.generate --write-manifest

Changelog:
    29/09/2026 (Claude Code — WP-7/O-02): Initial.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.eval_set.schema import (  # noqa: E402
    ANSWER_LINE_INSTRUCTION,
    DOMAINS,
    INSUFFICIENT,
    EvalItem,
    manifest_for,
    sha256_item,
    write_jsonl,
)

#: Fixed seed: the set is a fixture, not a lottery.
SEED = 20260929

DEV_PER_DOMAIN = 8
HELDOUT_PER_DOMAIN = 22
ITEMS_PER_DOMAIN = DEV_PER_DOMAIN + HELDOUT_PER_DOMAIN  # 30

#: Adversarial items per domain — 8+8+7+7 = 30 across the set.
ADVERSARIAL_PER_DOMAIN = {"quantum": 8, "math": 8, "graph": 7, "compute": 7}

EVAL_SET_DIR = Path(__file__).resolve().parent
DEV_PATH = EVAL_SET_DIR / "dev_set.jsonl"
MANIFEST_PATH = EVAL_SET_DIR / "heldout_manifest.json"


# ---------------------------------------------------------------------------
# Item constructors
# ---------------------------------------------------------------------------


def _item(
    *,
    domain: str,
    prompt: str,
    expected: str,
    expected_kind: str,
    kind: str = "answerable",
    tolerate: float = 0.0,
    missing_data: bool = False,
    notes: str = "",
    tags: Sequence[str] = (),
    index: int = 0,
) -> EvalItem:
    """Build an item with a provisional id; the split is assigned later."""
    item = EvalItem(
        id=f"{domain}-x{index:03d}",
        domain=domain,
        split="dev",
        kind=kind,
        prompt=f"{prompt}\n\n{ANSWER_LINE_INSTRUCTION}",
        expected=expected,
        expected_kind=expected_kind,
        tolerate=tolerate,
        missing_data=missing_data,
        notes=notes,
        tags=tuple(tags),
    )
    item.validate()
    return item


def _adversarial(
    *,
    domain: str,
    prompt: str,
    missing_data: bool,
    notes: str,
    tags: Sequence[str] = (),
    index: int = 0,
) -> EvalItem:
    return _item(
        domain=domain,
        kind="adversarial",
        prompt=prompt,
        expected=INSUFFICIENT,
        expected_kind="insufficient",
        missing_data=missing_data,
        notes=notes,
        tags=tags,
        index=index,
    )


# ---------------------------------------------------------------------------
# math — 22 answerable + 8 adversarial
# ---------------------------------------------------------------------------


def _math_answerable(rng: random.Random, index: int) -> EvalItem:
    family = index % 11
    if family == 0:
        a, b = rng.randint(12, 99), rng.randint(12, 99)
        return _item(domain="math", index=index, tags=("arithmetic",),
                     prompt=f"What is {a} × {b}?",
                     expected=str(a * b), expected_kind="number")
    if family == 1:
        a = rng.choice([2, 3, 4, 5, 6, 7, 8, 9])
        x = rng.randint(2, 12)
        b = rng.randint(1, 30)
        c = a * x + b
        return _item(domain="math", index=index, tags=("algebra",),
                     prompt=f"Solve for x: {a}x + {b} = {c}",
                     expected=str(x), expected_kind="number")
    if family == 2:
        n = rng.randint(15, 60)
        return _item(domain="math", index=index, tags=("series",),
                     prompt=f"What is the sum of the first {n} positive integers?",
                     expected=str(n * (n + 1) // 2), expected_kind="number")
    if family == 3:
        a, b = rng.randint(1, 6), rng.randint(1, 9)
        x0 = rng.randint(2, 9)
        return _item(domain="math", index=index, tags=("calculus",),
                     prompt=(f"Let f(x) = {a}x² + {b}x. What is f'({x0})?"),
                     expected=str(2 * a * x0 + b), expected_kind="number")
    if family == 4:
        pct = rng.choice([5, 10, 12, 15, 20, 25, 30, 40, 60, 75])
        # n chosen as a multiple of 100/gcd(pct, 100) so the result is exact.
        unit = 100 // math.gcd(pct, 100)
        n = rng.randint(4, 60) * unit
        assert (pct * n) % 100 == 0
        return _item(domain="math", index=index, tags=("percent",),
                     prompt=f"What is {pct}% of {n}?",
                     expected=str(pct * n // 100), expected_kind="number")
    if family == 5:
        a = rng.randint(20, 200)
        b = rng.randint(20, 200)
        return _item(domain="math", index=index, tags=("number_theory",),
                     prompt=f"What is gcd({a}, {b})?",
                     expected=str(math.gcd(a, b)), expected_kind="number")
    if family == 6:
        # (x^2 - k^2)/(x - k) = x + k, for x != k.  Answered in the form "x + c".
        k = rng.randint(2, 12)
        return _item(domain="math", index=index, tags=("algebra", "simplify"),
                     prompt=(f"Simplify (x² − {k * k})/(x − {k}) and give the result "
                             f"in the form `x + c`."),
                     expected=f"x + {k}", expected_kind="text")
    if family == 7:
        r1, r2 = rng.randint(1, 9), rng.randint(1, 9)
        s, p = r1 + r2, r1 * r2
        roots = sorted({r1, r2})
        return _item(domain="math", index=index, tags=("algebra", "roots"),
                     prompt=f"Find the real roots of x² − {s}x + {p} = 0. "
                            f"Give them as a comma-separated list.",
                     expected="{" + ",".join(str(r) for r in roots) + "}",
                     expected_kind="set")
    if family == 8:
        n = rng.randint(20, 200)
        return _item(domain="math", index=index, tags=("arithmetic", "expression"),
                     prompt=f"What is ({n} + {n // 3}) × ({n // 2} − {n // 6})?",
                     expected=f"({n} + {n // 3}) * ({n // 2} - {n // 6})",
                     expected_kind="expression")
    if family == 9:
        w = rng.randint(2, 20)
        h = rng.randint(2, 20)
        return _item(domain="math", index=index, tags=("geometry",),
                     prompt=f"A rectangle has width {w} and height {h}. "
                            f"What is its area?",
                     expected=str(w * h), expected_kind="number")
    a, d, n = rng.randint(1, 9), rng.randint(2, 9), rng.randint(5, 20)
    return _item(domain="math", index=index, tags=("series",),
                 prompt=f"What is the sum of the first {n} terms of the arithmetic "
                        f"sequence starting at {a} with common difference {d}?",
                 expected=str(n * (2 * a + (n - 1) * d) // 2), expected_kind="number")


_MATH_ADVERSARIAL = [
    ("Solve for x.", True, "no equation given",
     ("algebra", "missing")),
    ("A continuous function f is defined on [0, 1] with f(0) = 1 and f(1) = 3. "
     "What is the exact value of ∫₀¹ f(x) dx?", False,
     "boundary values do not determine the integral", ("calculus", "underdetermined")),
    ("The quadratic x² + bx + c = 0 has two distinct real roots. "
     "What are they?", True, "b and c never given", ("algebra", "missing")),
    ("A positive integer n satisfies n > 100. What is n?", True,
     "one inequality is not a value", ("number_theory", "underdetermined")),
    ("What is the derivative of f at x = 2?", True, "f is never given",
     ("calculus", "missing")),
    ("A triangle has one side of length 5 and one angle of 40°. "
     "What is its area?", False,
     "a side and an angle do not fix the triangle", ("geometry", "underdetermined")),
    ("The sequence aₙ satisfies a₁ = 1 and aₙ₊₁ > aₙ for all n. "
     "What is a₁₀?", False, "monotone does not determine a term",
     ("series", "underdetermined")),
    ("What is the value of the sum Σ 1/k?", True, "limits never given",
     ("series", "missing")),
]


def _math_adversarial(index: int) -> EvalItem:
    prompt, missing, notes, tags = _MATH_ADVERSARIAL[index % len(_MATH_ADVERSARIAL)]
    return _adversarial(domain="math", index=index, prompt=prompt,
                        missing_data=missing, notes=notes, tags=tags)


# ---------------------------------------------------------------------------
# graph — 23 answerable + 7 adversarial
# ---------------------------------------------------------------------------


def _random_edges(rng: random.Random, n: int, m: int) -> list[tuple[int, int]]:
    possible = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(possible)
    return sorted(possible[:m])


def _components(n: int, edges: Sequence[tuple[int, int]]) -> int:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    return len({find(i) for i in range(n)})


def _graph_answerable(rng: random.Random, index: int) -> EvalItem:
    family = index % 11
    if family == 0:
        n = rng.randint(5, 12)
        return _item(domain="graph", index=index, tags=("complete",),
                     prompt=f"How many edges does the complete graph K{n} have?",
                     expected=str(n * (n - 1) // 2), expected_kind="number")
    if family == 1:
        n = rng.randint(5, 8)
        edges = _random_edges(rng, n, rng.randint(4, n + 3))
        v = rng.randrange(n)
        nbrs = sorted({b if a == v else a for a, b in edges if a == v or b == v})
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("adjacency",),
                     prompt=f"A simple undirected graph has vertex set "
                            f"{{0, …, {n - 1}}} and edge set {edge_text}. "
                            f"What are the neighbours of vertex {v}? "
                            f"Give them as a comma-separated list in braces, e.g. `{{1, 2}}`.",
                     expected="{" + ",".join(str(x) for x in nbrs) + "}",
                     expected_kind="set")
    if family == 2:
        n = rng.randint(5, 9)
        edges = _random_edges(rng, n, rng.randint(3, n + 4))
        v = rng.randrange(n)
        deg = sum(1 for a, b in edges if a == v or b == v)
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("degree",),
                     prompt=f"Graph with vertex set {{0, …, {n - 1}}} and edges "
                            f"{edge_text}. What is the degree of vertex {v}?",
                     expected=str(deg), expected_kind="number")
    if family == 3:
        n = rng.randint(6, 10)
        edges = _random_edges(rng, n, rng.randint(3, n))
        comps = _components(n, edges)
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("components",),
                     prompt=f"Graph with vertex set {{0, …, {n - 1}}} and edges "
                            f"{edge_text}. How many connected components does it have?",
                     expected=str(comps), expected_kind="number")
    if family == 4:
        n = rng.randint(3, 7)
        edges = [(i, i + 1) for i in range(n - 1)]  # path -> tree
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("tree",),
                     prompt=f"A connected graph has vertex set {{0, …, {n - 1}}} "
                            f"and edges {edge_text}. Is it a tree? Answer `yes` or `no`.",
                     expected="yes", expected_kind="text")
    if family == 5:
        n = 6
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]  # C4 + 2 isolated -> not connected
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("tree", "connected"),
                     prompt=f"A graph has vertex set {{0, …, 5}} and edges "
                            f"{edge_text}. Is it a tree? Answer `yes` or `no`.",
                     expected="no", expected_kind="text")
    if family == 6:
        n = rng.randint(4, 7)
        edges = [(i, i + 1) for i in range(n - 1)]
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        u, v = 0, n - 1
        return _item(domain="graph", index=index, tags=("path",),
                     prompt=f"Graph with vertex set {{0, …, {n - 1}}} and edges "
                            f"{edge_text} (unweighted). What is the length of the "
                            f"shortest path from {u} to {v}?",
                     expected=str(v - u), expected_kind="number")
    if family == 7:
        # C_n is bipartite iff n even
        n = rng.choice([4, 5, 6, 7, 8, 9, 10])
        edges = [(i, (i + 1) % n) for i in range(n)]
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in sorted(edges)) + "}"
        return _item(domain="graph", index=index, tags=("bipartite",),
                     prompt=f"Graph with vertex set {{0, …, {n - 1}}} and edges "
                            f"{edge_text}. Is the graph bipartite? "
                            f"Answer `yes` or `no`.",
                     expected="yes" if n % 2 == 0 else "no", expected_kind="text")
    if family == 8:
        n = rng.randint(5, 9)
        edges = _random_edges(rng, n, rng.randint(n - 1, n + 3))
        degs = {sum(1 for a, b in edges if a == v or b == v) for v in range(n)}
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("degree",),
                     prompt=f"Graph with vertex set {{0, …, {n - 1}}} and edges "
                            f"{edge_text}. What are the **distinct** vertex degrees "
                            f"present? Give them as a comma-separated list in braces.",
                     expected="{" + ",".join(str(d) for d in sorted(degs)) + "}",
                     expected_kind="set")
    if family == 9:
        n = rng.randint(4, 8)
        edges = [(i, i + 1) for i in range(n - 1)]
        edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
        return _item(domain="graph", index=index, tags=("leaves",),
                     prompt=f"A tree has vertex set {{0, …, {n - 1}}} and edges "
                            f"{edge_text}. How many leaves (degree 1) does it have?",
                     expected="2", expected_kind="number")
    n = rng.randint(5, 9)
    edges = _random_edges(rng, n, rng.randint(4, n + 4))
    m = len(edges)
    edge_text = "{" + ", ".join(f"({a}, {b})" for a, b in edges) + "}"
    return _item(domain="graph", index=index, tags=("handshaking",),
                 prompt=f"Graph with vertex set {{0, …, {n - 1}}} and edges "
                        f"{edge_text}. What is the sum of all vertex degrees?",
                 expected=str(2 * m), expected_kind="number")


_GRAPH_ADVERSARIAL = [
    ("A simple graph G has 12 vertices and every vertex has degree at least 3. "
     "What is the exact number of edges of G?", False,
     "degree bounds give a range, not a count", ("edges", "underdetermined")),
    ("A tree T has 20 vertices. How many leaves does T have?", False,
     "vertex count does not fix the leaf count", ("tree", "underdetermined")),
    ("Graph G is connected and has 7 vertices and 9 edges. "
     "How many cycles does G have?", False,
     "connected + counts do not fix the cycle count", ("cycles", "underdetermined")),
    ("A graph G has 5 vertices and 4 edges. Is G a tree? Answer `yes` or `no`.", False,
     "5v/4e can be a tree or a cycle-plus-isolated; connectivity is unknown",
     ("tree", "underdetermined")),
    ("What is the adjacency matrix of G?", True, "G is never given",
     ("adjacency", "missing")),
    ("A planar graph G has 8 vertices. How many edges does G have?", False,
     "planarity bounds the edges but does not fix them", ("planar", "underdetermined")),
    ("Vertices u and v are in the same connected component of G. "
     "What is the distance between u and v?", True, "no distances given",
     ("path", "missing")),
]


def _graph_adversarial(index: int) -> EvalItem:
    prompt, missing, notes, tags = _GRAPH_ADVERSARIAL[index % len(_GRAPH_ADVERSARIAL)]
    return _adversarial(domain="graph", index=index, prompt=prompt,
                        missing_data=missing, notes=notes, tags=tags)


# ---------------------------------------------------------------------------
# compute — 23 answerable + 7 adversarial
# ---------------------------------------------------------------------------


def _compute_answerable(rng: random.Random, index: int) -> EvalItem:
    family = index % 11
    if family == 0:
        n = rng.randint(5, 500)
        return _item(domain="compute", index=index, tags=("binary",),
                     prompt=f"What is {n} in binary (no leading zeros, no spaces)?",
                     expected=bin(n)[2:], expected_kind="text")
    if family == 1:
        a = rng.randint(2, 9)
        b = rng.randint(3, 12)
        m = rng.choice([7, 11, 13, 17, 19, 23, 29, 31])
        return _item(domain="compute", index=index, tags=("modular",),
                     prompt=f"What is {a}^{b} mod {m}?",
                     expected=str(pow(a, b, m)), expected_kind="number")
    if family == 2:
        n = rng.randint(5, 10)
        return _item(domain="compute", index=index, tags=("factorial",),
                     prompt=f"What is {n}! ?",
                     expected=str(math.factorial(n)), expected_kind="number")
    if family == 3:
        n = rng.randint(1000, 999999)
        return _item(domain="compute", index=index, tags=("digits",),
                     prompt=f"What is the sum of the decimal digits of {n}?",
                     expected=str(sum(int(d) for d in str(n))), expected_kind="number")
    if family == 4:
        n = rng.choice([100, 256, 500, 1000, 2048, 4096])
        return _item(domain="compute", index=index, tags=("search",),
                     prompt=f"In the worst case, how many comparisons does binary "
                            f"search need to decide membership in a sorted array of "
                            f"{n} elements?",
                     expected=str(math.ceil(math.log2(n + 1))), expected_kind="number")
    if family == 5:
        a = rng.randint(100, 9000)
        m = rng.choice([10, 100, 1000])
        return _item(domain="compute", index=index, tags=("modular",),
                     prompt=f"What is {a} mod {m}?",
                     expected=str(a % m), expected_kind="number")
    if family == 6:
        n = rng.randint(2, 100000)
        return _item(domain="compute", index=index, tags=("bits",),
                     prompt=f"How many bits are needed to represent {n} in binary "
                            f"(unsigned, no leading zeros)?",
                     expected=str(n.bit_length()), expected_kind="number")
    if family == 7:
        n = rng.randint(100, 100000)
        return _item(domain="compute", index=index, tags=("logarithm",),
                     prompt=f"What is ⌊log₂{n}⌋?",
                     expected=str(n.bit_length() - 1), expected_kind="number")
    if family == 8:
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        return _item(domain="compute", index=index, tags=("arithmetic", "expression"),
                     prompt=f"What is {a} × {b} + {a} − {b}?",
                     expected=f"{a} * {b} + {a} - {b}", expected_kind="expression")
    if family == 9:
        n = rng.randint(2, 30)
        # number of unordered pairs = C(n,2)
        return _item(domain="compute", index=index, tags=("combinatorics",),
                     prompt=f"How many unordered pairs can be formed from {n} "
                            f"distinct items?",
                     expected=str(n * (n - 1) // 2), expected_kind="number")
    a, m = rng.randint(3, 20), rng.choice([8, 9, 11, 13])
    return _item(domain="compute", index=index, tags=("modular", "expression"),
                 prompt=f"What is ({a}^3 + {a}^2) mod {m}?",
                 expected=f"({a}**3 + {a}**2) % {m}", expected_kind="expression")


_COMPUTE_ADVERSARIAL = [
    ("The program ran and produced output. How many milliseconds did it take?",
     True, "no timing recorded", ("latency", "missing")),
    ("A hash table has n entries and the hash function is uniform. "
     "What is the exact number of collisions?", False,
     "uniform hashing gives an expectation, not a realised count",
     ("hashing", "underdetermined")),
    ("What is the output of this program?", True, "the program is never given",
     ("code", "missing")),
    ("Sort the list L in ascending order. What is the third element of L?",
     True, "L is never given", ("sorting", "missing")),
    ("Algorithm A runs in O(n log n) on an input of size n. "
     "How many elementary steps does A take on n = 1000?", False,
     "a big-O class is not an exact step count", ("complexity", "underdetermined")),
    ("A BFS is run on a graph with 50 vertices. How many edges does it visit?",
     False, "the graph is never given", ("traversal", "missing")),
    ("The array is sorted. What is its median?", True,
     "the array contents are never given", ("statistics", "missing")),
]


def _compute_adversarial(index: int) -> EvalItem:
    prompt, missing, notes, tags = _COMPUTE_ADVERSARIAL[index % len(_COMPUTE_ADVERSARIAL)]
    return _adversarial(domain="compute", index=index, prompt=prompt,
                        missing_data=missing, notes=notes, tags=tags)


# ---------------------------------------------------------------------------
# quantum — 22 answerable + 8 adversarial
# ---------------------------------------------------------------------------


def _quantum_answerable(rng: random.Random, index: int) -> EvalItem:
    family = index % 11
    if family == 0:
        # state a|0> + b|1> normalised via a 3-4-5 style ratio
        pairs = [(3, 4), (5, 12), (8, 15), (20, 21), (7, 24), (9, 40)]
        a, b = rng.choice(pairs)
        norm = math.hypot(a, b)
        prob = (a / norm) ** 2
        return _item(domain="quantum", index=index, tags=("measurement",),
                     prompt=(f"A qubit is in the state ({a}|0⟩ + {b}|1⟩)/√({a}²+{b}²). "
                             f"What is the probability of measuring |0⟩? "
                             f"Give a decimal to at least 6 decimal places."),
                     expected=f"{prob:.12f}", expected_kind="number", tolerate=1e-6)
    if family == 1:
        return _item(domain="quantum", index=index, tags=("pauli", "eigenvalues"),
                     prompt="What are the eigenvalues of the Pauli-X matrix? "
                            "Give them as a comma-separated list in braces, e.g. `{-1, 1}`.",
                     expected="{-1,1}", expected_kind="set")
    if family == 2:
        a, b, c, d = rng.randint(-5, 5), rng.randint(-5, 5), rng.randint(-5, 5), rng.randint(-5, 5)
        return _item(domain="quantum", index=index, tags=("linear_algebra",),
                     prompt=f"What is the trace of the matrix [[{a}, {b}], [{c}, {d}]]?",
                     expected=str(a + d), expected_kind="number")
    if family == 3:
        return _item(domain="quantum", index=index, tags=("hadamard",),
                     prompt="A qubit in state |0⟩ passes through a Hadamard gate. "
                            "What is the probability of measuring |1⟩? "
                            "Give a decimal to at least 6 decimal places.",
                     expected="0.5", expected_kind="number", tolerate=1e-9)
    if family == 4:
        n = rng.randint(1, 12)
        return _item(domain="quantum", index=index, tags=("register",),
                     prompt=f"How many computational basis states does a register of "
                            f"{n} qubit(s) have?",
                     expected=str(2 ** n), expected_kind="number")
    if family == 5:
        a, b, c, d = rng.randint(-4, 4), rng.randint(-4, 4), rng.randint(-4, 4), rng.randint(-4, 4)
        det = a * d - b * c
        return _item(domain="quantum", index=index, tags=("linear_algebra",),
                     prompt=f"What is the determinant of the matrix [[{a}, {b}], [{c}, {d}]]?",
                     expected=str(det), expected_kind="number")
    if family == 6:
        # <0|Z|0> = +1
        return _item(domain="quantum", index=index, tags=("pauli", "expectation"),
                     prompt="What is the expectation value ⟨0|Z|0⟩ of the Pauli-Z "
                            "operator in the state |0⟩?",
                     expected="1", expected_kind="number")
    if family == 7:
        # X·Z = [[0, 1], [1, 0]]·[[1, 0], [0, -1]] = [[0, -1], [1, 0]]
        return _item(domain="quantum", index=index, tags=("pauli", "algebra"),
                     prompt="Compute the matrix product X·Z of the Pauli matrices "
                            "(X first, then Z). Give the result in the form "
                            "`[[a, b], [c, d]]` with integer entries.",
                     expected="[[0, -1], [1, 0]]", expected_kind="text")
    if family == 8:
        return _item(domain="quantum", index=index, tags=("gates",),
                     prompt="How many parameters does a general single-qubit "
                            "unitary have? (Ignore the global phase.)",
                     expected="3", expected_kind="number")
    if family == 9:
        return _item(domain="quantum", index=index, tags=("bell",),
                     prompt="What is the probability of measuring |00⟩ on the Bell "
                            "state (|00⟩ + |11⟩)/√2? Give a decimal to at least "
                            "6 decimal places.",
                     expected="0.5", expected_kind="number", tolerate=1e-9)
    # family 10: state discrimination
    return _item(domain="quantum", index=index, tags=("measurement",),
                 prompt="A qubit is in the state |1⟩. What is the probability of "
                        "measuring |1⟩? Give a decimal to at least 6 decimal places.",
                 expected="1.0", expected_kind="number", tolerate=1e-9)


_QUANTUM_ADVERSARIAL = [
    ("A qubit is in some pure state |ψ⟩. What is the probability of measuring |0⟩?",
     True, "the state is never given", ("measurement", "missing")),
    ("A density matrix ρ acts on a 2-dimensional Hilbert space and has Tr(ρ²) = 1. "
     "What is ρ?", False, "purity 1 says pure, not which state",
     ("density_matrix", "underdetermined")),
    ("The Hamiltonian H has ground-state energy E₀ = −1. "
     "What is the ground state of H?", False, "an eigenvalue does not fix the eigenvector",
     ("hamiltonian", "underdetermined")),
    ("A quantum circuit contains 4 CNOT gates and some single-qubit gates. "
     "What unitary does it implement?", True, "the circuit is never given",
     ("circuit", "missing")),
    ("Two qubits are entangled. What is their joint state?", True,
     "entanglement does not specify a state", ("entanglement", "missing")),
    ("A measurement in the computational basis yields outcome 0 with probability 1/2. "
     "What was the pre-measurement state?", False,
     "a measurement distribution does not fix the state", ("measurement", "underdetermined")),
    ("The channel ε maps a qubit to a qubit and is completely positive. "
     "What is ε?", False, "CP is a property, not a specification",
     ("channels", "underdetermined")),
    ("State |ψ⟩ satisfies ⟨ψ|Z|ψ⟩ = 0. What is |ψ⟩?",
     False, "one expectation value does not fix the state",
     ("expectation", "underdetermined")),
]


def _quantum_adversarial(index: int) -> EvalItem:
    prompt, missing, notes, tags = _QUANTUM_ADVERSARIAL[index % len(_QUANTUM_ADVERSARIAL)]
    return _adversarial(domain="quantum", index=index, prompt=prompt,
                        missing_data=missing, notes=notes, tags=tags)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

_DOMAIN_FNS: dict[str, tuple[Callable[[random.Random, int], EvalItem], Callable[[int], EvalItem]]] = {
    "quantum": (_quantum_answerable, _quantum_adversarial),
    "math": (_math_answerable, _math_adversarial),
    "graph": (_graph_answerable, _graph_adversarial),
    "compute": (_compute_answerable, _compute_adversarial),
}


def build_domain(domain: str, rng: random.Random) -> list[EvalItem]:
    """30 items for one domain, split 8 dev / 22 held-out, adversarial stratified."""
    answerable_fn, adversarial_fn = _DOMAIN_FNS[domain]
    n_adv = ADVERSARIAL_PER_DOMAIN[domain]
    n_ans = ITEMS_PER_DOMAIN - n_adv

    items = [answerable_fn(rng, i) for i in range(n_ans)]
    items += [adversarial_fn(i) for i in range(n_adv)]

    # Deterministic shuffle, then stratify so both splits carry adversarial items.
    order = list(range(ITEMS_PER_DOMAIN))
    rng.shuffle(order)
    adv_idx = [i for i in order if items[i].kind == "adversarial"]
    ans_idx = [i for i in order if items[i].kind == "answerable"]

    # dev gets 2 adversarial + 6 answerable when the domain has >=2 adversarial.
    dev_adv = adv_idx[:2]
    dev_ans = ans_idx[: DEV_PER_DOMAIN - 2]
    dev_set = set(dev_adv) | set(dev_ans)

    out: list[EvalItem] = []
    for position, i in enumerate(order):
        old = items[i]
        split = "dev" if i in dev_set else "heldout"
        new = EvalItem(
            id=f"{domain}-{split[:2]}-{position:03d}",
            domain=domain,
            split=split,
            kind=old.kind,
            prompt=old.prompt,
            expected=old.expected,
            expected_kind=old.expected_kind,
            tolerate=old.tolerate,
            missing_data=old.missing_data,
            notes=old.notes,
            tags=old.tags,
        )
        new.validate()
        out.append(new)

    n_dev = sum(1 for x in out if x.split == "dev")
    assert n_dev == DEV_PER_DOMAIN, f"{domain}: expected {DEV_PER_DOMAIN} dev, got {n_dev}"
    assert len(out) == ITEMS_PER_DOMAIN
    return out


def build_all(seed: int = SEED) -> list[EvalItem]:
    rng = random.Random(seed)
    items: list[EvalItem] = []
    for domain in DOMAINS:
        items.extend(build_domain(domain, rng))

    ids = [i.id for i in items]
    if len(set(ids)) != len(ids):
        raise AssertionError("duplicate eval item ids")
    for item in items:
        item.validate()

    n_adv = sum(1 for i in items if i.kind == "adversarial")
    if n_adv != sum(ADVERSARIAL_PER_DOMAIN.values()):
        raise AssertionError(f"expected 30 adversarial, got {n_adv}")
    return items


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return EVAL_SET_DIR.parents[2]


def _is_inside_repo(path: Path) -> bool:
    repo = _repo_root().resolve()
    try:
        path.resolve().relative_to(repo)
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252 and this repo path holds non-ASCII.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "heldout", "all"], default=None)
    parser.add_argument("--out", default=None, help="output .jsonl path")
    parser.add_argument("--write-manifest", action="store_true",
                        help="rewrite heldout_manifest.json in the repo")
    parser.add_argument("--write-dev", action="store_true",
                        help="rewrite dev_set.jsonl in the repo")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args(argv)

    items = build_all()

    if args.write_dev:
        dev = [i for i in items if i.split == "dev"]
        write_jsonl(str(DEV_PATH), dev)
        print(f"wrote {len(dev)} dev items -> {DEV_PATH}")

    if args.write_manifest:
        heldout = [i for i in items if i.split == "heldout"]
        payload = {
            "seed": SEED,
            "n_heldout": len(heldout),
            "domains": list(DOMAINS),
            "note": (
                "ids + sha256 only. The held-out prompts and answers are NOT in "
                "this repo (D-7, 29/09/2026). Regenerate the file with "
                "`python -m benchmarks.eval_set.generate --split heldout --out <path "
                "outside Vivy_final>` and hand that path to the harness."
            ),
            "items": manifest_for(heldout),
        }
        MANIFEST_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(heldout)} held-out hashes -> {MANIFEST_PATH}")

    if args.split:
        selected = items if args.split == "all" else [i for i in items if i.split == args.split]
        if args.out:
            out = Path(args.out).expanduser()
            if args.split in ("heldout", "all") and _is_inside_repo(out):
                print(
                    f"REFUSED: held-out must not be written inside the repo "
                    f"({out} is under {_repo_root()}). Choose a path outside "
                    f"Vivy_final/ — see benchmarks/eval_set/README.md (D-7).",
                    file=sys.stderr,
                )
                return 2
            out.parent.mkdir(parents=True, exist_ok=True)
            write_jsonl(str(out), selected)
            print(f"wrote {len(selected)} {args.split} items -> {out}")
        else:
            print(f"{len(selected)} {args.split} items (pass --out to write)")
            if args.print_summary:
                for item in selected[:5]:
                    print(f"  {item.id}  {item.kind:11s}  {item.expected_kind}")

    if args.print_summary:
        for domain in DOMAINS:
            subset = [i for i in items if i.domain == domain]
            dev = [i for i in subset if i.split == "dev"]
            heldout = [i for i in subset if i.split == "heldout"]
            adv = sum(1 for i in subset if i.kind == "adversarial")
            print(f"{domain:8s}  total={len(subset)}  dev={len(dev)}  "
                  f"heldout={len(heldout)}  adversarial={adv}")
        print(f"TOTAL     {len(items)}  adversarial="
              f"{sum(1 for i in items if i.kind == 'adversarial')}")
        print(f"dev sha256 example: {sha256_item(items[0])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
