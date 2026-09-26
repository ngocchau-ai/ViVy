# ADR-0009: Deterministic Executor Accounting (N_e) and Integrated Stage-1 Benchmark

## Status

Accepted

## Context

Stage 1 runtime prototype baseline (`ARCHITECTURE.md` Section 4 & 13.2) requires:
1. Deterministic executor accounting ($N_e$) separating hypothesis count ($N_h$), verifier demand ($N_v$), and allocated executor count ($N_e$).
2. Enforcement of the core architecture invariant $N_h \ge N_v \ge N_e$.
3. An integrated end-to-end Stage 1 benchmark testing the full pipeline from `ThoughtState` creation, `PopulationSnapshot`, `ThoughtEcology`, `VerificationPortfolio`, `ExecutorRouter`, `EvidencePacket`, `AssimilationPlan`, and atomic `StateUpdateEngine` execution.

Prior to this decision, `src/nps_core/executor_router/` contained only an empty `__init__.py`.

## Decision

### 1. Module Ownership

`src/nps_core/executor_router/` owns `ExecutorDescriptor`, `ExecutorAssignment`, `ExecutorRoutingPlan`, `ExecutorRouter`, and domain exceptions (`ExecutorRoutingError`, `ExecutorBudgetError`, `UnmatchedRequirementError`).

### 2. $N_e$ Accounting and Invariant Enforcement

`ExecutorRouter.route(portfolio, executors, n_h)` routes experiment contracts to matching executor descriptors deterministically and calculates $N_e$ as the number of unique allocated executor IDs. It strictly enforces $N_h \ge N_v \ge N_e$, raising `ExecutorBudgetError` if violated.

### 3. Integrated Stage 1 Benchmark

`tests/benchmark/test_stage1_runtime_benchmark.py` provides an end-to-end integration test demonstrating <100ms execution time per cycle and confirming Stage-1 completeness.

## Consequences

- Stage 1 — Deterministic Runtime Prototype exit criteria are fully satisfied and verified.
- Standard-library runtime dependencies only; zero network or external I/O.
