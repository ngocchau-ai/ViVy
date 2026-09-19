"""
Self-Training Script for ViVy Native Core.

This script simulates a training loop for the ViVy Quantum Core, 
where the model learns from simulated experiences or historic market states.
Successful thought patterns are distilled and stored into the Quantum Associative Memory.
"""

import numpy as np
import os
import sys
import logging

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from vivy.core.vivy_brain import ViVyQuantumCore, FilterFunnelSignal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train_vivy_core(epochs: int = 100, state_dim: int = 1024):
    """
    Simulates the self-training loop for ViVy.
    """
    logger.info(f"Initializing ViVy Native Core (dim={state_dim}) for self-training...")
    core = ViVyQuantumCore(state_dim=state_dim, memory_use_unitary=True)
    
    successful_patterns = 0
    
    for epoch in range(1, epochs + 1):
        # 1. Simulate an incoming market state (embedded into complex space)
        # We inject structured patterns (e.g., clear trends) to allow the funnel to converge
        if epoch % 5 == 0:
            # Create a highly deterministic "uptrend" or "downtrend" pattern with near-zero entropy
            simulated_state = np.zeros(state_dim, dtype=complex)
            active_idx = np.random.choice(state_dim, size=1, replace=False) # 1 dominant feature
            simulated_state[active_idx] = 1.0 + 0j
        else:
            # Pure random noise (high entropy)
            simulated_state = np.random.randn(state_dim) + 1j * np.random.randn(state_dim)
            
        # Normalize state
        norm = np.linalg.norm(simulated_state)
        if norm > 0:
            simulated_state = simulated_state / norm
            
        # 2. Process through the 4-Level Self-Verification Filter Funnel
        result = core.process_state(simulated_state)
        
        # 3. Assess the outcome and reinforce memory
        # If the funnel decides to HALT (Converged state, strong conclusion), 
        # it is considered a successful pattern to remember.
        if result["signal"] == FilterFunnelSignal.HALT:
            successful_patterns += 1
            # Simulated outcome vector representing a clear decision (e.g., BUY/SELL action embedding)
            target_outcome = np.zeros(state_dim, dtype=complex)
            target_outcome[np.random.randint(0, state_dim)] = 1.0 + 0j
            core.memory.store(simulated_state, target_outcome, eta=0.1)
            
        if epoch % 10 == 0 or result["signal"] == FilterFunnelSignal.HALT:
            logger.info(f"Epoch {epoch}/{epochs} | Entropy: {result['entropy']:.2f} | "
                        f"Signal: {result['signal']} | Stored Patterns: {successful_patterns}")
            
    # Save the learned memory weights
    weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../modelfiles/vivy_core_memory.npy'))
    os.makedirs(os.path.dirname(weights_path), exist_ok=True)
    np.save(weights_path, core.memory.W)
    logger.info(f"Self-training complete. Memory weights saved to {weights_path}.")

if __name__ == "__main__":
    train_vivy_core(epochs=50, state_dim=1024)
