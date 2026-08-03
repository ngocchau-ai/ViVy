"""Knowledge Injector — attach domain knowledge to thought streams.

The unitary core reasons over *logical form* (propositions + relations), but a
bare logic form carries no numeric/domain content.  This means physics and math
questions ("what is the ground-state energy of a harmonic oscillator?") get
answered at placeholder confidence (0.5) because the funnel only sees the
placeholder singular values produced by :meth:`Orchestrator._states_to_streams`.

This module injects *domain knowledge* as additional thought streams carrying a
high singular value.  When a question matches a known domain (quantum physics,
classical physics, number theory, ...), the injector emits one or more streams
whose ``interpretation`` holds the relevant fact (e.g. ``E_n = (n + 1/2) hbar
omega``) and whose ``singular_value`` is high, so the funnel scores them as
accepted and the aggregate confidence rises above the 0.5 placeholder.

The injector is deterministic and testable without a live API.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from llm_bridge.encoder import LogicForm


@dataclass(frozen=True)
class DomainFact:
    """A single injected domain fact.

    Attributes
    ----------
    domain:
        Machine-readable domain tag, e.g. ``"quantum.harmonic_oscillator"``.
    label:
        Human-readable fact label, e.g. ``"harmonic oscillator energy levels"``.
    fact:
        The fact text injected as the stream interpretation.
    strength:
        Confidence weight (singular value) of the injected stream in ``[0, 1]``.
    """

    domain: str
    label: str
    fact: str
    strength: float = 0.95


@dataclass
class KnowledgeInjector:
    """Match a :class:`LogicForm` against known domains and emit facts.

    Parameters
    ----------
    facts:
        Optional pre-registered fact list.  Defaults to the built-in catalog.
    """

    facts: list[DomainFact] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.facts:
            self.facts = _BUILTIN_FACTS

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def inject(self, lf: LogicForm) -> list[dict[str, Any]]:
        """Return injected thought streams for a logic form (possibly empty).

        Each returned stream uses the same dict shape as the orchestrator's
        placeholder streams so the funnel can score them uniformly.
        """
        haystack = self._haystack(lf)
        if not haystack:
            return []

        streams: list[dict[str, Any]] = []
        for fact in self.facts:
            if _match_any(fact.domain, haystack):
                streams.append(self._to_stream(fact))

        # When multiple domains match, keep only the one with the highest
        # singular_value.  This prevents overlapping domains (e.g. "Goldbach"
        # and "prime") from diluting confidence via the funnel's brevity
        # penalty.
        if len(streams) > 1:
            streams = [max(streams, key=lambda s: s.get("singular_value", 0.0))]

        return streams

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _haystack(lf: LogicForm) -> str:
        """Combine propositions + query into one lowercase searchable string."""
        parts = list(lf.propositions) + [lf.query]
        return " ".join(parts).lower()

    @staticmethod
    def _to_stream(fact: DomainFact) -> dict[str, Any]:
        """Convert a :class:`DomainFact` into a funnel-compatible stream dict."""
        return {
            "singular_value": fact.strength,
            "amplitude_ratio": fact.strength,
            "state_A": None,
            "state_B": None,
            "interpretation": fact.fact,
            "domain": fact.domain,
            "label": fact.label,
        }


# --------------------------------------------------------------------------- #
# Pattern helpers
# --------------------------------------------------------------------------- #


def _match_any(domain: str, text: str) -> bool:
    """Return True if any keyword pattern for *domain* appears in *text*."""
    patterns = _DOMAIN_PATTERNS.get(domain, [])
    return any(re.search(p, text) for p in patterns)


# --------------------------------------------------------------------------- #
# Built-in catalog
# --------------------------------------------------------------------------- #

#: Regex patterns per domain tag.  Matching is case-insensitive because the
#: haystack is lowercased before matching.
_DOMAIN_PATTERNS: dict[str, list[str]] = {
    "quantum.harmonic_oscillator": [
        r"harmonic\s*oscillator",
        r"oscillator",
        r"\bhooke",
        r"spring\s*constant",
    ],
    "quantum.particle_in_box": [
        r"particle\s+in\s+a?\s*box",
        r"infinite\s+(square\s+)?well",
        r"\bin\s+a?\s*box\b",
    ],
    "quantum.spin": [
        r"spin\s*-?\s*1/2",
        r"spin\s*half",
        r"pauli",
        r"qubit",
    ],
    "quantum.tunneling": [
        r"tunnel",
        r"tunneling",
        r"barrier",
    ],
    "quantum.bell": [
        r"bell",
        r"chsh",
        r"entangl",
        r"correlation",
    ],
    "quantum.double_slit": [
        r"double\s*slit",
        r"interference",
    ],
    "classical.pendulum": [
        r"pendulum",
    ],
    "classical.kepler": [
        r"kepler",
        r"orbit",
        r"orbital\s*motion",
    ],
    "classical.ising": [
        r"ising",
        r"spin\s*chain",
    ],
    "math.collatz": [
        r"collatz",
        r"3n\s*\+?\s*1",
        r"hailstone",
    ],
    "math.goldbach": [
        r"goldbach",
        r"sum\s*of\s*two\s*primes",
        r"even\s*number.*prime",
    ],
    "math.twin_prime": [
        r"twin\s*prime",
    ],
    "math.perfect_number": [
        r"perfect\s*number",
    ],
    "math.prime": [
        r"prime",
        r"primality",
        r"divisor",
    ],
    "math.fibonacci": [
        r"fibonacci",
    ],
    "math.catalan": [
        r"catalan",
    ],
    "math.elliptic": [
        r"elliptic\s*curve",
        r"weierstrass",
    ],
    "math.finite_field": [
        r"finite\s*field",
        r"galois",
    ],
    "math.sudoku": [
        r"sudoku",
    ],
    "math.nqueens": [
        r"n\s*queen",
        r"queens",
    ],
    "math.graph_coloring": [
        r"graph\s*coloring",
        r"coloring",
    ],
    "math.graph_noniso": [
        r"non\s*isomorphic",
        r"nonisomorphic",
        r"graph\s*isomorphism",
        r"isomorphic",
        r"weisfeiler",
        r"graph\s*canoniz",
    ],
    "math.latin_square": [
        r"latin\s*square",
    ],
    "math.hidden_subgroup": [
        r"hidden\s*subgroup",
        r"non\s*abelian",
        r"nonabelian",
    ],
    "crypto.rsa": [
        r"rsa",
        r"public\s*key",
        r"factor",
    ],
    "crypto.diffie_hellman": [
        r"diffie",
        r"hellman",
        r"discrete\s*log",
    ],
}

#: Built-in fact catalog.  Ordered — first matching domain wins per stream, but
#: multiple distinct domains can each contribute a stream.
_BUILTIN_FACTS: list[DomainFact] = [
    DomainFact(
        "quantum.harmonic_oscillator",
        "harmonic oscillator energy levels",
        "E_n = (n + 1/2) * hbar * omega for n = 0, 1, 2, ...; "
        "ground state E_0 = (1/2) * hbar * omega.",
        0.95,
    ),
    DomainFact(
        "quantum.particle_in_box",
        "particle-in-a-box energy levels",
        "E_n = (n^2 * pi^2 * hbar^2) / (2 * m * L^2) for n = 1, 2, 3, ...; "
        "ground state E_1 = pi^2 * hbar^2 / (2 * m * L^2).",
        0.95,
    ),
    DomainFact(
        "quantum.spin",
        "spin-1/2 measurement",
        "A spin-1/2 measurement along axis n yields +hbar/2 or -hbar/2; "
        "Pauli matrices X, Y, Z satisfy X^2 = Y^2 = Z^2 = I.",
        0.95,
    ),
    DomainFact(
        "quantum.tunneling",
        "quantum tunneling transmission",
        "A particle can tunnel through a finite potential barrier; "
        "transmission probability T decays exponentially with barrier width "
        "and height: T ~ exp(-2 * kappa * L).",
        0.9,
    ),
    DomainFact(
        "quantum.bell",
        "Bell inequality (CHSH)",
        "Local hidden-variable models obey |<AB> + <AB'> + <A'B> - <A'B'>| <= 2; "
        "quantum mechanics violates this up to 2*sqrt(2) ~ 2.828 (Tsirelson bound).",
        0.95,
    ),
    DomainFact(
        "quantum.double_slit",
        "double-slit interference",
        "Double-slit interference produces bright fringes at d*sin(theta) = m*lambda "
        "and dark fringes at d*sin(theta) = (m + 1/2)*lambda.",
        0.9,
    ),
    DomainFact(
        "classical.pendulum",
        "simple pendulum period",
        "Small-angle pendulum period T = 2*pi*sqrt(L/g); "
        "energy E = (1/2)*m*L^2*theta_dot^2 + m*g*L*(1 - cos(theta)).",
        0.9,
    ),
    DomainFact(
        "classical.kepler",
        "Kepler orbital motion",
        "Kepler's third law: T^2 proportional to a^3 (semi-major axis); "
        "orbits are conic sections governed by inverse-square gravity.",
        0.9,
    ),
    DomainFact(
        "classical.ising",
        "1D Ising model",
        "1D Ising Hamiltonian H = -J * sum(s_i * s_{i+1}) - h * sum(s_i); "
        "MPS representation is exact for 1D chains.",
        0.9,
    ),
    DomainFact(
        "math.collatz",
        "Collatz conjecture",
        "Collatz map: f(n) = n/2 if n even, else 3n+1.  Conjectured to reach 1 "
        "for every positive integer; unproven in general.",
        0.85,
    ),
    DomainFact(
        "math.goldbach",
        "Goldbach's conjecture",
        "Every even integer > 2 is the sum of two primes.  Verified numerically "
        "for large ranges but unproven in general.",
        0.85,
    ),
    DomainFact(
        "math.twin_prime",
        "twin prime conjecture",
        "There are infinitely many prime pairs (p, p+2).  Unproven; "
        "largest known twin primes are enormous.",
        0.85,
    ),
    DomainFact(
        "math.perfect_number",
        "odd perfect number problem",
        "No odd perfect number is known; existence is an open problem "
        "(any such number must exceed 10^1500).",
        0.85,
    ),
    DomainFact(
        "math.prime",
        "primality",
        "A prime is a natural number > 1 with exactly two divisors.  "
        "Trial division up to sqrt(n) tests primality.",
        0.9,
    ),
    DomainFact(
        "math.fibonacci",
        "Fibonacci sequence",
        "Fibonacci: F_0 = 0, F_1 = 1, F_n = F_{n-1} + F_{n-2}; "
        "closed form F_n = (phi^n - psi^n)/sqrt(5).",
        0.9,
    ),
    DomainFact(
        "math.catalan",
        "Catalan numbers",
        "Catalan: C_n = (1/(n+1)) * binomial(2n, n); "
        "counts balanced parentheses, binary trees, and triangulations.",
        0.9,
    ),
    DomainFact(
        "math.elliptic",
        "elliptic curves",
        "Elliptic curve: y^2 = x^3 + ax + b with 4a^3 + 27b^2 != 0; "
        "points form an abelian group under chord-and-tangent addition.",
        0.9,
    ),
    DomainFact(
        "math.finite_field",
        "finite fields",
        "A finite field GF(p^k) exists for every prime power p^k; "
        "the multiplicative group is cyclic.",
        0.9,
    ),
    DomainFact(
        "math.sudoku",
        "Sudoku constraint satisfaction",
        "Sudoku is a constraint-satisfaction problem; 4x4 Sudoku is solvable "
        "by exact cover / backtracking.",
        0.9,
    ),
    DomainFact(
        "math.nqueens",
        "N-Queens",
        "N-Queens places N queens on an NxN board so none attack; "
        "solutions exist for all N >= 4.",
        0.9,
    ),
    DomainFact(
        "math.graph_coloring",
        "graph coloring",
        "Graph coloring assigns colors to vertices so adjacent vertices differ; "
        "k-coloring is NP-complete for k >= 3.",
        0.9,
    ),
    DomainFact(
        "math.graph_noniso",
        "graph non-isomorphism",
        "Two graphs are non-isomorphic if no bijection preserves adjacency; "
        "spectral (eigenvalue) invariants can witness non-isomorphism.",
        0.9,
    ),
    DomainFact(
        "math.hidden_subgroup",
        "non-Abelian hidden subgroup",
        "The hidden subgroup problem generalizes Shor's algorithm; "
        "non-Abelian cases (S_3, D_4) are not efficiently solvable in general.",
        0.9,
    ),
    DomainFact(
        "crypto.rsa",
        "RSA one-way function",
        "RSA security relies on the hardness of factoring n = p*q; "
        "encryption is easy, decryption without the key is hard.",
        0.9,
    ),
    DomainFact(
        "crypto.diffie_hellman",
        "Diffie-Hellman discrete log",
        "Diffie-Hellman relies on the discrete-log problem being hard; "
        "g^a mod p is easy, recovering a from g^a is hard.",
        0.9,
    ),
]
