# ADR-0013: Verification Tribunal Engine, Conflict Report, and Calibrated Confidence

## Status

Accepted

## Context

Stage 5 (`ARCHITECTURE.md` Section 8 & 13.6) requires:
1. Verification tribunal evaluation of evidence packets to generate `ReproductionLog` entries.
2. Conflict detection across evidence packets targeting identical hypotheses to produce `ConflictReport`s.
3. Bayesian calibrated confidence scoring (`ConfidenceCalibrator`).

## Decision

### 1. Module Ownership

`src/nps_core/verification_tribunal/` owns `ConflictReport`, `ConflictDetector`, `ConfidenceCalibrator`, `ReproductionLog`, `VerificationTribunal`, and domain exceptions (`TribunalError`, `TribunalConflictError`).

### 2. Conflict Detection & Evaluation

`ConflictDetector.detect_conflicts` checks for conflicting evidence results (`PASSED` vs `FAILED`) targeting the same hypothesis. `VerificationTribunal.evaluate` logs execution reproducibility metadata.

### 3. Calibrated Confidence

`ConfidenceCalibrator.calibrate` computes bounded posterior confidence scores using Bayesian update weights.

## Consequences

- Stage 5 exit criteria are 100% fulfilled.
- Standard-library runtime dependencies only; zero external network I/O.
