"""
ViVy MoE Quantum Core — N experts over a unitary associative memory.

[REPLACED 29/09/2026 · WP-5 / O-12 / F-F07] — real scale, not a marketing name
=============================================================================

WHAT THE NAME USED TO CLAIM
    The module was titled **"ViVy 70B MoE Quantum Core (1B Active)"** and its
    docstring said there are *"70 independent Experts (each with 1B
    representational capacity)"*, routed to "fit within strict memory
    constraints".  The router log printed
    ``"[MoE Router] Switching to Expert N (1B Active Parameters)"``.

    There is no 70B model here and no 1B active parameter.  Nothing in this
    module loads a transformer.  Each "expert" is a
    ``ViVyQuantumCore`` holding one unitary associative-memory matrix.

WHAT IS ACTUALLY HERE (measured from the code)
    * ``state_dim = 4096``
    * An expert's compressed unitary memory is ``U`` of shape ``4096 x 64``
      complex128 → **524,288 complex parameters per expert** (≈ 4.2 MB
      uncompressed as complex128).
    * ``num_experts = 70`` is a **routing table size**, not 70 large models.
    * Top-1 routing by cosine similarity against ``num_experts`` random
      centroids (seed 42).  The centroids are untrained.

    The review called the 70B/1B naming F-F07.  See
    ``docs/CAPABILITY_LEDGER.md`` for the receipt status of any performance
    number attached to this module.

Naming note (29/09/2026): the class name ``ViVyMoEQuantumCore`` is kept —
renaming would break importers (hard rule #3).  Only the *claims* changed.
"""

# [ISOLATED 29/09/2026 · WP-5 / F-F07] — preserved verbatim.  Must not return
# to the live docstring above:
#
#     ViVy 70B MoE Quantum Core (1B Active).
#
#     Implements a Mixture-of-Experts (MoE) architecture where 70 independent "Experts"
#     (each with 1B representational capacity) are selectively loaded from disk
#     using Quantum LoRA (SVD Compression) to fit within strict memory constraints.
#
# ...and the router log line that repeated it at runtime:
#     logger.info(f"[MoE Router] Switching to Expert {expert_id} (1B Active Parameters)")

import logging
import os
from typing import Any

import numpy as np

from .vivy_brain import FilterFunnelSignal, ViVyQuantumCore

logger = logging.getLogger(__name__)

#: [ADDED 29/09/2026 · WP-5] Real per-expert parameter count, measured from the
#: compressed unitary ``U`` of shape ``state_dim x top_k`` complex128.
#: 4096 * 64 = 262,144 complex = 524,288 real scalars.  NOT "1B active".
EXPERT_TOP_K = 64
EXPERT_COMPLEX_PARAMS = 4096 * EXPERT_TOP_K  # 524_288 complex parameters


class ViVyMoEQuantumCore:
    """MoE router over N small unitary-memory experts.  Not a 70B model."""

    def __init__(self, state_dim: int = 4096, num_experts: int = 70, experts_dir: str = "modelfiles/experts"):
        self.state_dim = state_dim
        self.num_experts = num_experts
        self.experts_dir = experts_dir
        self.active_expert_id: int | None = None
        self.active_expert: ViVyQuantumCore | None = None

        # Initialize Router centroids (random for now, could be trained)
        # Using a deterministic seed so router is consistent across runs
        np.random.seed(42)
        self.router_centroids = np.random.randn(num_experts, state_dim)
        # Normalize centroids
        norms = np.linalg.norm(self.router_centroids, axis=1, keepdims=True)
        self.router_centroids /= norms
        np.random.seed(None) # Reset seed

    def _route(self, state_vector: np.ndarray) -> int:
        """
        Determine which expert should handle this state (Top-1 Routing).
        Uses cosine similarity.
        """
        # Ensure state is real for routing (or use magnitude)
        real_state = np.abs(state_vector)
        norm = np.linalg.norm(real_state)
        if norm > 0:
            real_state = real_state / norm

        similarities = self.router_centroids @ real_state
        best_expert = int(np.argmax(similarities)) + 1 # 1-indexed
        return best_expert

    def _load_expert(self, expert_id: int) -> None:
        """
        Lazy-loads an expert into memory.
        """
        if self.active_expert_id == expert_id and self.active_expert is not None:
            return

        # [REPLACED 29/09/2026 · WP-5] was: "(1B Active Parameters)"
        logger.info(
            f"[MoE Router] Switching to Expert {expert_id} "
            f"({EXPERT_COMPLEX_PARAMS} complex params, U {self.state_dim}x{EXPERT_TOP_K})"
        )
        expert = ViVyQuantumCore(state_dim=self.state_dim, memory_use_unitary=True)

        filepath = os.path.join(self.experts_dir, f"expert_{expert_id:02d}.npz")
        if os.path.exists(filepath):
            expert.memory.load_compressed(filepath)
        else:
            logger.warning(f"Expert {expert_id} file not found at {filepath}. Using untrained memory.")

        self.active_expert = expert
        self.active_expert_id = expert_id

    def process_state(self, state_vector: np.ndarray) -> dict[str, Any]:
        """
        Routes the state to the best expert and processes it.
        """
        expert_id = self._route(state_vector)
        self._load_expert(expert_id)

        # The active expert now processes the state
        return self.active_expert.process_state(state_vector)

    def train_expert(self, expert_id: int, epochs: int = 50, top_k_compression: int = 64) -> None:
        """
        Trains a specific expert in isolation and saves it to disk via Quantum LoRA.
        """
        logger.info(f"--- Training MoE Expert {expert_id}/{self.num_experts} ---")
        # Optimization: Disabled mid-training unitarization. The SVD compression at the end will handle it.
        expert = ViVyQuantumCore(state_dim=self.state_dim, memory_use_unitary=False)

        successful_patterns = 0
        for epoch in range(1, epochs + 1):
            if epoch % 5 == 0:
                # Highly deterministic target pattern for this expert
                simulated_state = np.zeros(self.state_dim, dtype=complex)
                active_idx = np.random.choice(self.state_dim, size=1, replace=False)
                simulated_state[active_idx] = 1.0 + 0j
            else:
                simulated_state = np.random.randn(self.state_dim) + 1j * np.random.randn(self.state_dim)

            norm = np.linalg.norm(simulated_state)
            if norm > 0:
                simulated_state = simulated_state / norm

            result = expert.process_state(simulated_state)

            if result["signal"] == FilterFunnelSignal.HALT:
                successful_patterns += 1
                target_outcome = np.zeros(self.state_dim, dtype=complex)
                target_outcome[np.random.randint(0, self.state_dim)] = 1.0 + 0j
                expert.memory.store(simulated_state, target_outcome, eta=0.1)

            if epoch % 10 == 0 or result["signal"] == FilterFunnelSignal.HALT:
                logger.info(f"Expert {expert_id} | Epoch {epoch}/{epochs} | Entropy: {result['entropy']:.2f} | Stored: {successful_patterns}")

        # Save compressed (Quantum LoRA)
        filepath = os.path.join(self.experts_dir, f"expert_{expert_id:02d}.npz")
        expert.memory.save_compressed(filepath, top_k=top_k_compression)
        logger.info(f"Expert {expert_id} saved to {filepath} (Compressed Top-{top_k_compression})")
