# ADR-005: Evolution Engine — Probe Signature

**Status:** Accepted (implemented in orchestrator/engine.py)

## Context
The orchestrator needs to create `UnitaryEvolution` instances dynamically.
The evolution engine's constructor signature varies depending on mode
("dense" vs "mps"), making it fragile to use `__mro__[1]` for discovery.

## Decision
- `_make_evolution()` uses a **probe signature** — it inspects the constructor
  via `inspect.signature` instead of `__mro__[1]`
- `UnitaryEvolution.evolve()` requires a `schedule` argument; the current stub
  logs a warning and returns the input unchanged
- Mode is selected via `mode="dense"` or `mode="mps"`

## Consequences
- `_make_evolution()` works with any future evolution subclass
- The stub in `evolve()` is a known gap to be hardened in phase 0
- `step()` works with both state vectors and MPS depending on mode