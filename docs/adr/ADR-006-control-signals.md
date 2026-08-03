# ADR-006: Control Signal Enum

**Status:** Accepted (implemented in funnel/_types.py)

## Context
The filter funnel evaluates thought streams and returns a control signal that
guides the orchestrator's next action. The signal set must be expressive enough
for reasoning loops but small enough to be predictable.

## Decision
Four control signals:
- `"continue"` — stream is coherent, proceed with current reasoning path
- `"measure"` — stream has low confidence; measure to collapse ambiguity
- `"backtrack"` — stream contains contradiction; backtrack to previous state
- `"delegate"` — stream needs external context; delegate to LLM

## Consequences
- FilterFunnel returns `"measure"` for low-confidence streams by default
- Orchestrator tests expect any of the 4 valid signals
- New signals can be added to `CONTROL_SIGNALS` without breaking existing code