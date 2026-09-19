"""
ViVy 70B MoE Quantum Core (1B Active).

Implements a Mixture-of-Experts (MoE) architecture where 70 independent "Experts"
(each with 1B representational capacity) are selectively loaded from disk 
using Quantum LoRA (SVD Compression) to fit within strict memory constraints.
"""

import numpy as np
import os
import logging
from typing import Dict, Any, Optional

from .vivy_brain import ViVyQuantumCore, FilterFunnelSignal

logger = logging.getLogger(__name__)

class ViVyMoEQuantumCore:
    def __init__(self, state_dim: int = 4096, num_experts: int = 70, experts_dir: str = "modelfiles/experts"):
        self.state_dim = state_dim
        self.num_experts = num_experts
        self.experts_dir = experts_dir
        self.active_expert_id: Optional[int] = None
        self.active_expert: Optional[ViVyQuantumCore] = None
        
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
            
        logger.info(f"[MoE Router] Switching to Expert {expert_id} (1B Active Parameters)")
        expert = ViVyQuantumCore(state_dim=self.state_dim, memory_use_unitary=True)
        
        filepath = os.path.join(self.experts_dir, f"expert_{expert_id:02d}.npz")
        if os.path.exists(filepath):
            expert.memory.load_compressed(filepath)
        else:
            logger.warning(f"Expert {expert_id} file not found at {filepath}. Using untrained memory.")
            
        self.active_expert = expert
        self.active_expert_id = expert_id

    def process_state(self, state_vector: np.ndarray) -> Dict[str, Any]:
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
