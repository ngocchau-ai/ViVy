# ADR-004: Associative Memory Dimension

**Status:** Accepted (implemented in memory/associative.py)

## Context
The associative memory stores and retrieves reasoning patterns. It must handle both
small (few qubits) and large (many features) cases without unbounded memory growth.

## Decision
- `AssociativeMemory` requires an explicit `dim` parameter (e.g. `dim=8` for
  the orchestrator default)
- Dense storage when `dim <= 256`; sparse storage above that threshold
- Supports Hebbian-style association and quantum Hopfield retrieval
- `QuantumAssociativeMemory` extends with quantum-state-based retrieval

## Consequences
- Callers must pass `dim` explicitly — no hidden magic default
- The orchestrator uses `dim=8` for its working state
- Sparse mode bounds memory for high-dimensional feature spaces