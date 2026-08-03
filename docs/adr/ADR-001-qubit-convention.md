# ADR-001: Qubit Convention — LSB-first

**Status:** Accepted (implemented in core)

## Context
The MPS representation and state vector need a consistent qubit ordering so that
`to_vector` and `from_vector` are inverses. The ordering affects gate application,
SVD stream extraction, and all downstream logic.

## Decision
- **Tensor 0 = qubit 0 = LSB** (least significant bit)
- `to_vector()` uses `order="F"` (Fortran-contiguous) flatten so that tensor 0
  varies fastest — making it the LSB of the resulting index
- `from_vector()` splits LSB first: the first SVD split peels off qubit 0 from
  the vector, then qubit 1, etc.
- Vector index: `index = sum(bit_q << q)` where `bit_q` is the state of qubit q

## Consequences
- `to_vector ∘ from_vector` is identity (verified by tests)
- CNOT gate matrix uses the standard convention where control=qubit 0, target=qubit 1
- Multi-qubit gate splits in `_apply_gate_simple` process qubits left-to-right (LSB first)