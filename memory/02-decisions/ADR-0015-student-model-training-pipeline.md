# ADR-0015: NPS Student Model Training Pipeline, Proposal Engine, and Latency Evaluation

## Status

Accepted

## Context

Stage 7 (`ARCHITECTURE.md` Section 10 & 13.8) requires:
1. `StudentTrainingConfig` defining student model training parameters.
2. `StudentProposalEngine` generating fast, schema-compliant hypothesis proposals to replace expensive teacher model calls for proposal roles.
3. `LatencyEvaluator` benchmarking proposal generation speed against strict SLA thresholds (< 200ms per proposal).

## Decision

### 1. Module Ownership

`src/nps_core/model_training/student.py` owns `StudentTrainingConfig`, `StudentProposalEngine`, and `LatencyEvaluator`.

### 2. Proposal Engine & Latency Evaluation

`StudentProposalEngine.generate_proposal` produces valid `ThoughtState` instances tagged with `preferred_model_class="student"`. `LatencyEvaluator.evaluate_latency` verifies that proposal latency remains under the 200ms SLA threshold.

## Consequences

- Stage 7 exit criteria are 100% fulfilled.
- Standard-library runtime dependencies only; zero external I/O.
