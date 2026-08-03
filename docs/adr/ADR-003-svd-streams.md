# ADR-003: SVD Thought Stream Extraction

**Status:** Accepted (implemented in core/svd_streams.py)

## Context
The unitary reasoner needs to extract interpretable "thought streams" from the
quantum state to guide reasoning. SVD-based decomposition of the MPS bond
structure provides a natural way to identify dominant reasoning paths.

## Decision
- `extract_thought_streams()` uses matricization (reshaping the MPS tensor at a
  partition point into a matrix) followed by SVD
- `dominant_stream` returns the top singular component with an explicit
  `threshold` parameter (default 0.0) to filter noise
- `schmidt_rank` counts singular values above threshold
- The partition is defined by a qubit index: left qubits vs right qubits

## Consequences
- Streams are ordered by singular value magnitude (dominant first)
- `threshold` lets callers tune sensitivity without changing the API
- Matricization respects the LSB convention (tensor 0 = qubit 0)