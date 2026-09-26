import numpy as np

from vivy.core.vivy_brain import FilterFunnelSignal, ViVyQuantumCore


def test_vivy_quantum_core_initialization():
    core = ViVyQuantumCore(state_dim=256)
    assert core.state_dim == 256
    assert core.memory.dim == 256

def test_destructive_interference_detection():
    core = ViVyQuantumCore(state_dim=4)
    # Create a state vector with two high amplitude opposite phase components
    state = np.array([1.0, -1.0, 0.0, 0.0], dtype=complex)
    result = core.process_state(state)
    assert result["destructive_interference"]
    # The signal should be DELEGATE when destructive interference is found
    assert result["signal"] == FilterFunnelSignal.DELEGATE

def test_halt_on_converged_state():
    core = ViVyQuantumCore(state_dim=4)
    # Converged state (low entropy)
    state = np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)
    result = core.process_state(state)
    assert result["entropy"] < 1.0

def test_backtrack_on_high_entropy():
    core = ViVyQuantumCore(state_dim=1024)
    # Uniform state (high entropy)
    state = np.ones(1024, dtype=complex) / np.sqrt(1024)
    result = core.process_state(state)
    assert result["entropy"] > 3.0
    # The signal should be BACKTRACK due to high entropy
    assert result["signal"] == FilterFunnelSignal.BACKTRACK
