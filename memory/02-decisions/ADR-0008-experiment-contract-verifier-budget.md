# ADR-0008: Deterministic Experiment Contract and Verifier Budget Accounting

## Status

Accepted

## Context

ADR-0005, ADR-0006, and ADR-0007 established immutable hypothesis lifecycle, atomic evidence state updates, and population-wide thought ecology graph indexing.

Stage 1 requires a schema-compatible `ExperimentContract` runtime and `VerificationPortfolio` model to account for verifier demand ($N_v$) independently from hypothesis count ($N_h$) and executor allocation ($N_e$), as specified in `ARCHITECTURE.md` Section 4 and Section 13.2.

Prior to this decision, `src/nps_core/experiment_designer/` was an unpopulated package skeleton. NPS Core requires:

1. A frozen, schema-compatible `ExperimentContract` matching `schemas/experiment.schema.json`.
2. A frozen `VerificationNeed` value object capturing caller-supplied uncertainty requirements.
3. A frozen `VerificationPortfolio` value object binding verification needs, experiment contracts, and exact `PopulationSnapshot` digest.
4. Explicit accounting of verifier demand ($N_v = \text{len}(verification\_needs)$) satisfying $N_h \ge N_v \ge N_e$.
5. Strict validation against exact `PopulationSnapshot` (rejecting unknown hypothesis references, stale digests, $N_v > N_h$ budget violations, uncovered needs, and unlinked contracts).
6. Deterministic JSON canonical serialization and SHA-256 digest calculation.

## Decision

### 1. Module ownership

`src/nps_core/experiment_designer/` owns `ExperimentContract`, `VerificationNeed`, `VerificationPortfolio`, domain validation errors, canonical serialization, and exact-snapshot validation.

### 2. Schema compliance

`ExperimentContract` matches `schemas/experiment.schema.json` without modifying the schema file. Top-level dict serialization uses `{"experiment": { ... }}`. Numeric fields enforce strict type checks (rejecting `bool`, `NaN`, `Infinity`, and out-of-range values).

### 3. $N_v$ Verifier budget accounting

$N_v$ is calculated deterministically as the number of caller-supplied `VerificationNeed` items in the portfolio. Portfolio validation enforces $N_h \ge N_v$ against the supplied `PopulationSnapshot`.

### 4. Portfolio validation

`VerificationPortfolio.validate_for(snapshot)` verifies:
- `snapshot_digest` matches SHA-256 digest of `snapshot.to_canonical_json()`.
- Every target hypothesis in verification needs exists in `snapshot.thought_ids`.
- Every tested hypothesis in experiment contracts exists in `snapshot.thought_ids`.
- $N_v \le N_h$.
- Every verification need is covered by at least one experiment contract.
- Every experiment contract covers at least one verification need.

## Consequences

- Stage 1 experiment contract and verifier-demand accounting slice is complete and fully tested.
- `schemas/experiment.schema.json` remains byte-unchanged.
- Standard-library runtime dependencies only; no network, filesystem, or database I/O.
