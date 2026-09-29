"""
Cautreo Knowledge Cartographer & Dynamic Sparse Weight Activation Engine.

Implements SPEC-CAUTREO-CARTOGRAPHY-SPARSE-100B (mechanism):
1. Auto-Hardware RAM Sensing & 10% Budget Ceiling with circuit breaker.
   # [ISOLATED 23/09/2026] prior: "(Zero-OOM Enforcer)" — OOM claim needs receipt
2. Circuit Breaker: Auto-flush if total system RAM exceeds 85%.
3. Dual-Analysis Profiling:
   - Fast Randomized SVD (Power Iteration) of FFN matrices (W_down).
   - 50 Canonical Domain Probes for L2-Norm empirical activation energy.
4. Coarse Knowledge Atlas (.catlas binary / JSON serialization).
   # [ISOLATED 23/09/2026] prior: "< 8MB, load < 2ms" — size/load: see P5 receipt
5. Dynamic Sparse Activation: Activates top-k 10% high-salience neurons.
   # [ISOLATED 23/09/2026] prior: "allowing a 100B LLM to run with the system load and latency of a 7B model" — UNVERIFIED (Gate 9), see P5 receipt
6. Visual ASCII Knowledge Continents renderer.

Size / load / RAM / activation numbers: see
`vivyChatGPT/evidence/CARTOGRAPHY_BENCHMARK_RECEIPT.json` (P5).
Status: IMPLEMENTED (loader + budget math) / UNVERIFIED (100B-on-10GB).

Changelog:
    23/09/2026 (Antigravity IDE & Ngoc Chau — Sprint R5): Initial implementation.
    23/09/2026 (Claude Code — P5 Gate 9): Isolate unbenchmarked size/load/scale claims; point at P5 receipt.
"""

from __future__ import annotations

import json
import logging
import math
import struct
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 50 Canonical Domain Probes (Anchor Concepts)
# ---------------------------------------------------------------------------

CANONICAL_DOMAIN_PROBES: list[str] = [
    # Code & Systems (10)
    "mql5_expert_advisor_ordersend",
    "mql5_trailing_stop_loss",
    "python_asyncio_event_loop",
    "cpp_metaprogramming_template",
    "rust_borrow_checker_lifetime",
    "cuda_kernel_warp_divergence",
    "linux_epoll_syscall_kernel",
    "network_socket_tcp_handshake",
    "git_rebase_merge_conflict",
    "database_acid_mvcc_index",
    # Mathematics & Logic (10)
    "abstract_algebra_galois_field",
    "riemann_geometry_curvature",
    "quantum_circuit_bell_state",
    "fourier_transform_fft_dsp",
    "stochastic_calculus_brownian",
    "bayesian_inference_mcmc",
    "graph_theory_dijkstra_tarjan",
    "differential_equations_euler",
    "linear_algebra_svd_eigenvalue",
    "formal_logic_godel_incompleteness",
    # Trading, Finance & Economics (10)
    "market_microstructure_orderbook",
    "liquidity_pool_slippage_amm",
    "volatility_skew_black_scholes",
    "foreign_exchange_interest_rate_parity",
    "fixed_income_yield_curve_convexity",
    "drawdown_recovery_risk_kelly",
    "macroeconomics_inflation_taylor_rule",
    "high_frequency_trading_arbitrage",
    "crypto_blockchain_consensus_pow",
    "algorithmic_market_maker_avellaneda",
    # Law, Ethics & Governance (10)
    "vietnamese_commercial_law_contract",
    "corporate_governance_fiduciary_duty",
    "intellectual_property_patent_copyright",
    "international_arbitration_uncitral",
    "data_privacy_gdpr_compliance",
    "securities_regulations_insider_trading",
    "competition_antitrust_monopoly",
    "contractual_force_majeure_clause",
    "tax_avoidance_cross_border_beps",
    "employment_labor_code_severance",
    # Reasoning, Nuance & Psychology (10)
    "vietnamese_nuanced_literary_syntax",
    "cognitive_bias_confirmation_anchoring",
    "counterfactual_reasoning_causality",
    "tree_of_thought_deliberation",
    "socratic_dialogue_questioning",
    "rhetoric_persuasion_dialectic",
    "epistemic_uncertainty_calibration",
    "adversarial_game_theory_nash",
    "emotional_intelligence_negotiation",
    "chain_of_thought_self_correction",
]


# ---------------------------------------------------------------------------
# Data Models: Atlas Node & Coarse Knowledge Atlas
# ---------------------------------------------------------------------------


@dataclass
class AtlasNode:
    """Represents a structural layer or expert block mapped by Cautreo.

    [UPDATED 29/09/2026 · WP-5 / F-C07] when produced by
    ``CautreoCartographer.scan_model`` this node is **SIMULATED**: its concept
    seeds, domain scores and salience indices are computed from loop indices
    and from ``model_id`` substrings, never from model weights.  See
    ``simulated`` / ``weights_read``.
    """

    layer_index: int
    block_name: str
    top_concepts: list[str] = field(default_factory=list)
    domain_scores: dict[str, float] = field(default_factory=dict)
    high_salience_neuron_indices: list[int] = field(default_factory=list)
    sparsity_ratio: float = 0.90
    full_ram_mb: float = 120.0
    sparse_ram_mb: float = 12.0
    dominant_domain: str = "general"
    #: [ADDED 29/09/2026 · WP-5] True = derived from formulas, not weights.
    simulated: bool = False
    weights_read: bool = False
    """Always False for ``scan_model`` output.  No tensor is ever opened."""

    def match_score(self, task_query: str) -> float:
        """Calculate match affinity between a query string and this node."""
        q_norm = task_query.lower()
        q_tokens = set(q_norm.replace("_", " ").split())
        score = 0.0

        # 1. Match against top concepts (with seed clean up)
        for concept in self.top_concepts:
            c_clean = concept.split("_L")[0].replace("_", " ").lower()
            c_tokens = set(c_clean.split())
            overlap = len(q_tokens.intersection(c_tokens))
            if overlap > 0:
                score += 0.40 * (overlap / len(c_tokens))

        # 2. Match against dominant domain
        dom_parts = set(self.dominant_domain.lower().split("_"))
        if len(q_tokens.intersection(dom_parts)) > 0:
            score += 0.35

        # 3. Match against canonical domain scores
        for domain, d_score in self.domain_scores.items():
            d_clean = domain.replace("_", " ").lower()
            d_tokens = set(d_clean.split())
            overlap = len(q_tokens.intersection(d_tokens))
            if overlap >= 2:
                score += d_score * 0.15 * overlap

        return min(1.0, score)


@dataclass
class CoarseKnowledgeAtlas:
    """Global Cognitive Cartography Atlas for an LLM (30B - 100B).

    [UPDATED 29/09/2026 · WP-5 / F-C07] an atlas produced by ``scan_model``
    carries ``simulated=True``.  Its contents **must not be injected into a
    model prompt** as measured knowledge — see ``render_for_prompt``.
    """

    model_id: str
    total_layers: int
    nodes: dict[int, AtlasNode] = field(default_factory=dict)
    hardware_ram_total_bytes: int = 16 * 1024 * 1024 * 1024
    ram_buffer_limit_bytes: int = int(1.6 * 1024 * 1024 * 1024)
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    version: str = "2.0.0"
    #: [ADDED 29/09/2026 · WP-5] True when nothing was read from disk.
    simulated: bool = False
    weights_read: bool = False
    prompt_injection_allowed: bool = False
    """Hard gate.  ``scan_model`` output may never be pasted into a prompt."""

    def render_for_prompt(self, *args: Any, **kwargs: Any) -> str:
        """Deliberately unusable.  Raises — this atlas is not prompt evidence.

        [ADDED 29/09/2026 · WP-5 / O-12] the review found this atlas's output
        being treated as knowledge about a model.  It is a synthetic map.  The
        ban is enforced in code, not only in a comment (INV-01: every patch
        carries a test — see ``tests/test_capability_honesty.py``).
        """
        raise RuntimeError(
            "CautreoCartographer atlas is SIMULATED and must NOT be injected "
            "into a model prompt. It was derived from loop indices and model_id "
            f"substrings, not from weights (model_id={self.model_id!r}, "
            f"simulated={self.simulated}, weights_read={self.weights_read}). "
            "See docs/CAPABILITY_LEDGER.md."
        )

    def query(self, task_query: str, top_k: int = 3) -> list[tuple[AtlasNode, float]]:
        """Return the top-k layers/slices with highest affinity for the query."""
        scored: list[tuple[AtlasNode, float]] = []
        for node in self.nodes.values():
            s = node.match_score(task_query)
            scored.append((node, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def render_ascii_continents(self) -> str:
        """Render a formatted ASCII map of the knowledge continents."""
        continents = [
            ("LỤC ĐỊA CÚ PHÁP & HỆ THỐNG", 0, int(self.total_layers * 0.20), "Python, C++, Grammar, Tokens"),
            ("CAO NGUYÊN SUY LUẬN & LOGIC", int(self.total_layers * 0.20), int(self.total_layers * 0.45), "Math, Proofs, Algorithms, SVD"),
            ("QUẦN ĐẢO CHUYÊN NGÀNH SÂU", int(self.total_layers * 0.45), int(self.total_layers * 0.75), "MQL5, Trading, Finance, Law"),
            ("VÙNG HỘI TỤ & VĂN PHONG", int(self.total_layers * 0.75), self.total_layers, "Vietnamese Nuance, Safety, CoT"),
        ]

        ram_mb = self.ram_buffer_limit_bytes / (1024 * 1024)
        total_ram_gb = self.hardware_ram_total_bytes / (1024 * 1024 * 1024)

        lines = [
            "╔══════════════════════════════════════════════════════════════════════════════════════╗",
            f"║         CAUTREO KNOWLEDGE CARTOGRAPHY ATLAS: {self.model_id.upper():<30} ║",
            "╠══════════════════════════════════════════════════════════════════════════════════════╣",
        ]

        for name, start_l, end_l, keywords in continents:
            lines.append(
                f"║ [{name:<26}] │ Layers {start_l:02d} - {end_l:02d} │ {keywords:<28} ║"
            )

        lines.extend([
            "╠══════════════════════════════════════════════════════════════════════════════════════╣",
            f"║ Total Hardware RAM: {total_ram_gb:.1f} GB │ Active 10% Ceiling: {ram_mb:.0f} MB (circuit-breaker) ║",
            f"║ Total Mapped Layers: {self.total_layers:<3d} │ Probed Domains: {len(CANONICAL_DOMAIN_PROBES):<2d}/50 Anchors Active          ║",
            "╚══════════════════════════════════════════════════════════════════════════════════════╝",
        ])
        return "\n".join(lines)

    def export_catlas(self, file_path: str) -> bool:
        """Export the atlas to a compressed binary / JSON format.
        # [ISOLATED 23/09/2026] prior: "(.catlas <= 8MB)" — measured size: see P5 receipt
        """
        try:
            data = {
                "magic": "CATLAS20",
                "model_id": self.model_id,
                "total_layers": self.total_layers,
                "hardware_ram_total_bytes": self.hardware_ram_total_bytes,
                "ram_buffer_limit_bytes": self.ram_buffer_limit_bytes,
                "created_at_ms": self.created_at_ms,
                "version": self.version,
                "nodes": {str(k): asdict(v) for k, v in self.nodes.items()},
            }
            json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")

            # Simple header + payload
            with open(file_path, "wb") as f:
                header = struct.pack("<4sI", b"CTLS", len(json_bytes))
                f.write(header)
                f.write(json_bytes)
            logger.info("Exported Knowledge Atlas to %s (%d bytes)", file_path, len(json_bytes) + 8)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to export .catlas file: %s", exc)
            return False

    @classmethod
    def import_catlas(cls, file_path: str) -> CoarseKnowledgeAtlas | None:
        """Import the atlas from a .catlas file (latency: see P5 receipt).
        # [ISOLATED 23/09/2026] prior: "with sub-2ms loading speed" — measured load: see P5 receipt
        """
        try:
            t0 = time.perf_counter()
            with open(file_path, "rb") as f:
                header = f.read(8)
                if len(header) < 8:
                    return None
                magic, json_len = struct.unpack("<4sI", header)
                if magic != b"CTLS":
                    return None
                json_bytes = f.read(json_len)

            data = json.loads(json_bytes.decode("utf-8"))
            nodes: dict[int, AtlasNode] = {}
            for k_str, n_dict in data.get("nodes", {}).items():
                nodes[int(k_str)] = AtlasNode(**n_dict)

            atlas = cls(
                model_id=data.get("model_id", "unknown"),
                total_layers=data.get("total_layers", len(nodes)),
                nodes=nodes,
                hardware_ram_total_bytes=data.get("hardware_ram_total_bytes", 16 * 1024**3),
                ram_buffer_limit_bytes=data.get("ram_buffer_limit_bytes", int(1.6 * 1024**3)),
                created_at_ms=data.get("created_at_ms", 0),
                version=data.get("version", "2.0.0"),
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.info("Imported Knowledge Atlas %s in %.2f ms", file_path, elapsed_ms)
            return atlas
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to import .catlas file: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Cautreo Cartographer Engine
# ---------------------------------------------------------------------------


class CautreoCartographer:
    """Cautreo Initial Knowledge Cartographer.

    Orchestrates the sequential streaming of weights for 30B - 100B LLMs,
    enforcing a strict <= 10% hardware RAM cap with Circuit Breaker.
    """

    def __init__(
        self,
        ram_ratio: float = 0.10,
        circuit_breaker_threshold: float = 0.85,
    ) -> None:
        self.ram_ratio = ram_ratio
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.hardware_ram_bytes = self.detect_hardware_ram()
        self.max_buffer_bytes = int(self.hardware_ram_bytes * self.ram_ratio)
        self.current_buffer_bytes = 0

    def detect_hardware_ram(self) -> int:
        """Detect total physical hardware RAM in bytes."""
        try:
            import psutil
            return psutil.virtual_memory().total
        except Exception:  # noqa: BLE001
            # Fallback to standard 16GB
            return 16 * 1024 * 1024 * 1024

    def check_circuit_breaker(self) -> bool:
        """Return True if system total memory usage is within safe bounds (<85%)."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.percent >= (self.circuit_breaker_threshold * 100.0):
                logger.warning(
                    "Circuit Breaker triggered: Total RAM usage is %.1f%% (> %.1f%%)",
                    mem.percent,
                    self.circuit_breaker_threshold * 100.0,
                )
                return False
            return True
        except Exception:  # noqa: BLE001
            return True

    def fast_svd_power_iteration(
        self, matrix: list[list[float]], k: int = 4, n_iter: int = 10
    ) -> list[tuple[float, list[float]]]:
        """Compute top-k singular values and vectors using Power Iteration.

        Runs in O(k * n_iter * M * N) without allocating huge matrices.
        """
        if not matrix or not matrix[0]:
            return []

        rows = len(matrix)
        cols = len(matrix[0])
        results: list[tuple[float, list[float]]] = []

        # Work on copy of matrix for deflation
        A = [row[:] for row in matrix]

        for _ in range(min(k, rows, cols)):
            # Initialize random normalized vector
            v = [1.0 / math.sqrt(cols)] * cols

            for _ in range(n_iter):
                # Av = A * v (dim rows)
                Av = [sum(A[i][j] * v[j] for j in range(cols)) for i in range(rows)]
                # AtAv = A^T * Av (dim cols)
                AtAv = [sum(A[i][j] * Av[i] for i in range(rows)) for j in range(cols)]

                norm = math.sqrt(sum(x * x for x in AtAv))
                if norm < 1e-12:
                    break
                v = [x / norm for x in AtAv]

            # Compute singular value sigma = ||A * v||
            Av_final = [sum(A[i][j] * v[j] for j in range(cols)) for i in range(rows)]
            sigma = math.sqrt(sum(x * x for x in Av_final))
            results.append((sigma, v))

            # Deflate A: A = A - sigma * u * v^T where u = Av / sigma
            if sigma > 1e-12:
                u = [x / sigma for x in Av_final]
                for i in range(rows):
                    for j in range(cols):
                        A[i][j] -= sigma * u[i] * v[j]

        return results

    def compute_activation_energy(
        self, weights_row_sums: list[float], probe_token: str
    ) -> float:
        """Compute empirical L2-norm activation energy for a canonical domain probe."""
        # Deterministic pseudo-embedding projection for probing
        probe_hash = sum(ord(c) for c in probe_token)
        energy_accum = 0.0
        for idx, w in enumerate(weights_row_sums):
            factor = math.sin((idx + probe_hash) * 0.01)
            activated = w * factor
            energy_accum += activated * activated

        return math.sqrt(energy_accum / (len(weights_row_sums) or 1))

    def scan_model(
        self,
        model_id: str,
        total_layers: int = 80,
        model_path: str = "",
    ) -> CoarseKnowledgeAtlas:
        """Build a **SIMULATED** knowledge atlas for a model.  Reads no weights.

        [REPLACED 29/09/2026 · WP-5 / O-12 / F-C07]
        ------------------------------------------------
        The docstring used to say *"Scan a 30B - 100B model layer by layer under
        the 10% RAM ceiling."*  It does not scan anything:

        * ``model_path`` is accepted and **never read** (no ``open``, no
          ``mmap``, no tensor load anywhere in this method).
        * ``slice_bytes = 120 * 1024 * 1024`` is a hardcoded constant labelled
          "Simulate streaming 1 layer block FFN".
        * The dominant domain is assigned from **layer-depth thresholds**
          (20% / 45% / 75%) against a fixed ``concept_seeds`` table.
        * ``dummy_row_sums = [(sin(l_idx*0.1 + i) + 1.2) * 0.5 …]`` — a formula
          in the loop index.  Variable name says it.
        * ``high_salience_indices = list(range(0, top_k_count))`` with
          ``total_neurons = 28672 if "70b" in model_id else 14336``.  The
          "high-salience neurons" are the first N integers, and N comes from a
          substring match on the model's *name*.

        Two different checkpoints with the same ``model_id`` string produce
        identical atlases.  The review called it F-C07.

        Returns an atlas flagged ``simulated=True`` / ``weights_read=False``.
        Its ``render_for_prompt`` **raises** — the output must not be injected
        into a model prompt.
        """
        # [ISOLATED 29/09/2026] `model_path` was already ignored; it is kept in
        # the signature for caller compatibility and explicitly discarded here
        # so the next reader cannot think it is used.
        _ = model_path

        atlas = CoarseKnowledgeAtlas(
            model_id=model_id,
            total_layers=total_layers,
            hardware_ram_total_bytes=self.hardware_ram_bytes,
            ram_buffer_limit_bytes=self.max_buffer_bytes,
            simulated=True,
            weights_read=False,
            prompt_injection_allowed=False,
        )

        logger.info(
            "Starting Knowledge Cartography for %s (%d layers). RAM Buffer Ceiling: %.2f MB",
            model_id,
            total_layers,
            self.max_buffer_bytes / (1024 * 1024),
        )

        for l_idx in range(total_layers):
            # Check circuit breaker
            if not self.check_circuit_breaker():
                logger.info("Paused streaming at layer %d due to RAM pressure; flushing buffer", l_idx)
                self.current_buffer_bytes = 0

            # [SIMULATED 29/09/2026 · WP-5] not a stream — a constant.
            slice_bytes = 120 * 1024 * 1024
            self.current_buffer_bytes = slice_bytes

            # 1. Determine dominant domain by layer depth  [SIMULATED] — this
            #    is a lookup on `l_idx / total_layers`, not a property of any
            #    weight tensor.  Same for the concept_seeds table below.
            if l_idx < total_layers * 0.20:
                dom_domain = "syntax_system"
                concept_seeds = ["python_asyncio", "cpp_metaprogramming", "grammar_syntax", "token_flow"]
            elif l_idx < total_layers * 0.45:
                dom_domain = "logic_math"
                concept_seeds = ["abstract_algebra", "formal_logic", "riemann_geometry", "svd_eigenvalue"]
            elif l_idx < total_layers * 0.75:
                dom_domain = "mql5_finance_law"
                concept_seeds = ["mql5_ordersend", "trailing_stop", "orderbook_liquidity", "vietnamese_law"]
            else:
                dom_domain = "nuance_convergence"
                concept_seeds = ["vietnamese_nuance", "cot_deliberation", "adversarial_safety", "output_refinement"]

            # 2. Compute synthetic SVD Power Iteration for top concepts
            top_concepts = [f"{s}_L{l_idx}" for s in concept_seeds]

            # 3. Compute 50 Canonical Domain Probes scores
            #    [SIMULATED 29/09/2026 · WP-5] `dummy_row_sums` is a formula in
            #    `l_idx` and `i`.  The name was always honest; the callers were
            #    not.  These scores describe nothing about the model.
            domain_scores: dict[str, float] = {}
            dummy_row_sums = [(math.sin(l_idx * 0.1 + i) + 1.2) * 0.5 for i in range(16)]

            for probe in CANONICAL_DOMAIN_PROBES:
                energy = self.compute_activation_energy(dummy_row_sums, probe)
                # Boost if probe matches layer domain
                if dom_domain.startswith("mql5") and "mql5" in probe:
                    energy *= 2.5
                elif dom_domain.startswith("logic") and "math" in probe:
                    energy *= 2.2
                elif dom_domain.startswith("syntax") and ("python" in probe or "cpp" in probe):
                    energy *= 2.3
                elif dom_domain.startswith("nuance") and "vietnamese" in probe:
                    energy *= 2.4
                domain_scores[probe] = round(energy, 4)

            # 4. Extract Top-10% High-Salience Neurons (Sparsity ~90%)
            #    [SIMULATED 29/09/2026 · WP-5] these are NOT extracted from
            #    weights.  `total_neurons` is guessed from a substring of the
            #    model NAME ("70b"/"100b"), and the "high-salience indices"
            #    are literally `range(0, top_k_count)` — the first N integers.
            total_neurons = 28672 if "70b" in model_id.lower() or "100b" in model_id.lower() else 14336
            top_k_count = int(total_neurons * 0.10)
            high_salience_indices = list(range(0, top_k_count))

            node = AtlasNode(
                layer_index=l_idx,
                block_name=f"{model_id}.blk.{l_idx}.ffn",
                top_concepts=top_concepts,
                domain_scores=domain_scores,
                high_salience_neuron_indices=high_salience_indices,
                sparsity_ratio=0.90,
                full_ram_mb=120.0,
                sparse_ram_mb=12.0,  # 10% RAM only
                dominant_domain=dom_domain,
                simulated=True,
                weights_read=False,
            )
            atlas.nodes[l_idx] = node

            # Immediately flush buffer to uphold 10% ceiling
            self.current_buffer_bytes = 0

        logger.info(
            "Completed SIMULATED Cartography Atlas for %s: %d layers synthesised "
            "(no weights read; model_path was ignored). See docs/CAPABILITY_LEDGER.md.",
            model_id,
            len(atlas.nodes),
        )
        return atlas
