"""Unitary Reasoner — core quantum-inspired reasoning module.

Provides unitary gates, quantum state representation, matrix product states (MPS),
unitary evolution, SVD-based thought stream extraction, and entropy analysis
for quantum-inspired logical inference.
"""

from .entropy import interference_detection, shannon_entropy, von_neumann_entropy
from .evolution import GateSchedule, UnitaryEvolution
from .gates import (
    and_intro,
    apply_gate_to_state,
    cnot,
    hadamard,
    modus_ponens,
    modus_tollens,
    or_elim,
    pauli_x,
    pauli_y,
    pauli_z,
    swap,
    tensor_product_gate,
    toffoli,
)
from .mps import MPS
from .state import QuantumState
from .svd_streams import (
    ThoughtStream,
    dominant_stream,
    extract_thought_streams,
    schmidt_rank,
)

__all__ = [
    # gates
    "pauli_x",
    "pauli_y",
    "pauli_z",
    "hadamard",
    "cnot",
    "swap",
    "toffoli",
    "modus_ponens",
    "modus_tollens",
    "and_intro",
    "or_elim",
    "apply_gate_to_state",
    "tensor_product_gate",
    # state
    "QuantumState",
    # mps
    "MPS",
    # evolution
    "UnitaryEvolution",
    "GateSchedule",
    # svd_streams
    "extract_thought_streams",
    "ThoughtStream",
    "dominant_stream",
    "schmidt_rank",
    # entropy
    "shannon_entropy",
    "interference_detection",
    "von_neumann_entropy",
]
