# ADR-0006: Evidence Assimilation and Atomic Multi-Thought State Update

## Status

Accepted

## Context

ADR-0005 established the deterministic ThoughtState lifecycle core within `hypothesis_population`, including immutable value objects, create/branch/merge/prune primitives, and canonical JSON serialization. The `state_update` module was explicitly deferred as a future orchestration consumer. Stage 1 can now execute ThoughtState lifecycle transitions but cannot parse EvidencePacket V1, attach one evidence item to several affected hypotheses, or apply those state changes atomically.

The `evidence_assimilator` and `state_update` modules are currently empty package skeletons. NPS Core requires:

1. A strict, immutable EvidencePacket V1 value model with canonical serialization that is lossless and schema-compatible.
2. A normalized, immutable AssimilationPlan that maps one evidence packet to per-hypothesis impacts.
3. An atomic state-update engine that replaces every affected ThoughtState together or none, preserves lineage, records provenance, and produces a deterministic, replayable audit record.

The EvidencePacket V1 JSON schema (`schemas/evidence_packet.schema.json`) and ThoughtState V1 JSON schema (`schemas/thought_state.schema.json`) are frozen. No schema or architecture document may be modified. The `hypothesis_population` lifecycle modules (`thought_state.py`, `lifecycle.py`) must remain byte-unchanged.

## Decision

### 1. Module ownership

`evidence_assimilator` owns strict EvidencePacket V1 value/serialization, EvidenceImpact validation, and a normalized immutable AssimilationPlan. `state_update` owns atomic replacement of all affected ThoughtStates and the deterministic EvidenceUpdateRecord. Neither module modifies `hypothesis_population`, schemas, or any TASK-002 lifecycle module.

### 2. EvidencePacket strict model

A frozen, slotted `dataclass` `EvidencePacket` is defined in `evidence_assimilator`. It parses from and serializes to a plain `dict`/`list` structure accepted by the V1 JSON schema. The model enforces stricter invariants than the base schema:

- `provenance` must be non-empty (at least one entry).
- `affected_hypotheses` must be non-empty and contain unique entries.
- `artifacts` entries must be unique.
- `provenance` entries must be unique.
- All string fields must be non-empty.
- `confidence` must be a finite number in [0, 1]; booleans are rejected.
- `reproducibility.seed` must be an integer or `None`.

The base schema remains lossless: any dictionary accepted by the V1 schema and satisfying the stricter invariants round-trips through `from_dict` â `to_dict` without data loss. No runtime `jsonschema` dependency is introduced.

### 3. EvidenceImpact and AssimilationPlan

`EvidenceImpact` is a frozen dataclass holding a single hypothesis target ID and a caller-supplied classification (`supporting`, `opposing`, or `unresolved`). The runtime performs no confidence arithmetic, relevance inference, or semantic classification.

`AssimilationPlan` is a frozen, normalized dataclass holding:

- The validated `EvidencePacket`.
- A tuple of `EvidenceImpact` entries, sorted lexicographically by target ID.
- Validation that the impact target set (as a set) exactly equals `packet.affected_hypotheses` (as a set).
- Validation that every target exists in the current snapshot and is non-terminal.
- Validation that the evidence ID is not already present in any bucket of any target thought.

### 4. Caller-supplied complete replacement ThoughtStates

The caller supplies complete replacement `ThoughtState` objects for every affected hypothesis. The runtime performs no confidence arithmetic, relevance inference, clock, UUID, or randomness. Each replacement:

- **Retains** `thought_id`, `parent_ids`, `created_at`, `interpretation`, `hypothesis`, `assumptions`, `executor_profile`, and `graph` from the prior state.
- **May change** `evidence`, `metrics`, `verification_plan`, and `status`.
- The evidence ID is added exactly once to the caller-selected `supporting`/`opposing`/`unresolved` bucket, absent from the other two buckets, with no removal of existing evidence IDs.

The runtime validates these boundary conditions; violations produce stable domain errors and leave the prior snapshot unchanged.

### 5. Atomic state update

`state_update.apply_evidence` accepts:

- The current `PopulationSnapshot`.
- A validated `AssimilationPlan`.
- A mapping from target thought ID to the caller-supplied replacement `ThoughtState`.
- Caller-supplied `record_id`, `timestamp`, and `actor`.

The function:

1. Validates that every target in the plan has a corresponding replacement.
2. Validates that no extra replacements exist beyond the plan targets.
3. Validates replacement boundary conditions (retained fields match, evidence bucket semantics correct).
4. Constructs a new `PopulationSnapshot` with all replacements applied atomically.
5. Constructs an `EvidenceUpdateRecord` (see Â§6).
6. Returns the new snapshot and the record. The prior snapshot is never mutated.

If any validation fails, the prior snapshot is returned byte-identical and no record is produced.

### 6. EvidenceUpdateRecord

`EvidenceUpdateRecord` is a frozen, immutable dataclass representing a separate provenance stream entry. It is **not** appended to `PopulationSnapshot.history` (which remains reserved for lifecycle `TransitionEvent` entries per ADR-0005). The record is a standalone artifact until a future generic event-ledger ADR unifies provenance streams.

The record contains:

- `record_id`: caller-supplied string.
- `timestamp`: caller-supplied RFC3339/ISO-8601 timezone-aware string.
- `actor`: caller-supplied non-empty string.
- `evidence_id`: the packet's evidence ID.
- `content_hash`: the packet's `content_hash` field.
- `sorted_target_ids`: lexicographically sorted tuple of affected thought IDs.
- `prior_state_digest`: SHA-256 hex digest of the prior snapshot's canonical JSON.
- `result_state_digest`: SHA-256 hex digest of the result snapshot's canonical JSON.

Serialization produces a plain dictionary. Canonical JSON uses the same conventions as ADR-0005 (`ensure_ascii=False`, `sort_keys=True`, compact separators, `allow_nan=False`).

### 7. Canonical serialization and determinism

All new value objects serialize to plain `dict`/`list` structures. Canonical JSON uses `ensure_ascii=False`, `sort_keys=True`, compact separators `(",", ":")`, and `allow_nan=False`. Repeated serialization of identical data produces byte-identical output. SHA-256 digests are computed over canonical JSON bytes using `hashlib` from the standard library.

### 8. Validation order

The complete update batch is validated before a new `PopulationSnapshot` is constructed:

1. EvidencePacket strict validation.
2. AssimilationPlan construction (impact set equality, target existence, non-terminal check, evidence ID absence).
3. Replacement ThoughtState boundary validation (retained fields, evidence bucket semantics).
4. Only then: snapshot construction and record production.

Invalid provenance, target, replacement, or impact leaves the prior snapshot byte-identical.

### 9. No modification to schemas or TASK-002 lifecycle modules

`ARCHITECTURE.md`, all schema files, `thought_state.py`, `lifecycle.py`, and all other `hypothesis_population` modules remain byte-unchanged. The new modules import `ThoughtState`, `PopulationSnapshot`, and related types from `hypothesis_population` but do not modify them.

### 10. Deferred scope

TASK-003 does not complete all Stage 1 work. The following remain deferred:

- Thought Ecology graph store (`thought_ecology`).
- ExperimentContract and Adaptive N (`experiment_designer`, `adaptive_n`).
- Verification Tribunal (`verification_tribunal`).
- Executor routing (`executor_router`).
- `N_v`/`N_e` accounting.
- Generic event-ledger unifying lifecycle and evidence provenance streams.
- Confidence arithmetic, semantic relevance inference, or evidence quality scoring.
- Model, network, database, or filesystem calls at runtime.

### 11. Status allowed values

Replacement ThoughtStates must use status values from the V1 enum. The runtime does not introduce new statuses. Transitions triggered by evidence assimilation are caller-directed; the runtime only validates that the replacement status is a valid V1 state.

### 12. Baseline immutability

No architecture baseline document or schema file is changed by this task.

## Consequences

- `evidence_assimilator` becomes the source of truth for EvidencePacket value types, impact classification, and assimilation plan construction.
- `state_update` becomes the source of truth for atomic multi-thought replacement and provenance record production.
- All evidence assimilation consumers must supply complete EvidencePacket data, impact classifications, replacement ThoughtStates, and identity/timestamp; the core never generates them.
- Frozen value objects prevent accidental mutation; state changes construct a new snapshot.
- Canonical JSON supports replay verification and stable cache keys.
- The EvidenceUpdateRecord provenance stream is separate from lifecycle history, enabling future unification without breaking existing consumers.
- No production dependencies are added beyond the Python standard library.
- Later Stage 1 work builds on these modules without changing these invariants.
- SHA-256 state digests enable tamper-evident audit trails.

## Rejected alternatives

1. **Appending EvidenceUpdateRecord to PopulationSnapshot.history:** rejected because `history` is reserved for lifecycle `TransitionEvent` entries per ADR-0005. Mixing provenance streams would complicate future event-ledger unification and break the existing history contract.

2. **Runtime confidence arithmetic or relevance inference:** rejected because it would invent semantic policy. The caller is the sole authority on impact classification and replacement ThoughtState content.

3. **Partial ThoughtState updates (patch semantics):** rejected because it would require the runtime to understand which fields to merge, introducing implicit policy. Complete replacement is explicit and auditable.

4. **Internal UUID, timestamp, or random generation:** rejected because it introduces nondeterminism, violating the replay-identical contract.

5. **Runtime jsonschema validation:** rejected to avoid a production dependency. Structural validation is hand-written against the V1 shape, consistent with ADR-0004 and ADR-0005.

6. **Single-target evidence assimilation:** rejected because the primary use case is one evidence packet affecting multiple hypotheses atomically. Single-target is a degenerate case of the multi-target design.

7. **Mutable AssimilationPlan with incremental target addition:** rejected because frozen dataclasses make the plan boundary explicit and prevent partial plans from being applied.

8. **Evidence removal or replacement in buckets:** rejected because evidence provenance must be append-only. Removing evidence would destroy audit history.

9. **Automatic terminal-state detection and skip:** rejected because the caller must explicitly handle terminal targets. Silent skipping would hide data integrity issues.

10. **Embedding-based impact classification:** rejected because the runtime does not perform model inference.

## Compatibility and migration

- EvidencePacket serialization produces plain dictionaries accepted by the existing V1 JSON schema.
- ThoughtState serialization remains unchanged; replacement states produce dictionaries accepted by the V1 schema.
- `ARCHITECTURE.md` and all schema files remain unchanged.
- Existing TASK-001 and TASK-002 tests remain green.
- The implementation stays compatible with Windows PowerShell, Linux shell, and UTF-8 repository content.
- `state_update` imports lifecycle primitives from `hypothesis_population` without moving ownership.
- Future work (event-ledger, confidence engines) can consume EvidenceUpdateRecord and AssimilationPlan without modifying these modules.

## Security

- Deserialization cannot import or instantiate arbitrary classes; all parsing uses explicit type construction.
- The complete update batch is validated before a new snapshot exists.
- Invalid provenance, target, replacement, or impact leaves the prior snapshot byte-identical.
- SHA-256 state digests provide tamper-evident audit trails.
- No network, filesystem, or database calls are made at runtime.

## Validation

### Acceptance criteria

1. Public evidence and update types import from `nps_core.evidence_assimilator` and `nps_core.state_update`.
2. EvidencePacket parses and serializes losslessly to a dictionary accepted by EvidencePacket V1.
3. Malformed keys/types, bool-as-number, non-finite/out-of-range confidence, invalid reproducibility seed, and empty required strings fail with stable domain errors.
4. Runtime enforces non-empty provenance, at least one unique affected hypothesis, and unique artifact/provenance entries even where the base schema is less strict.
5. Impact classification is exactly `supporting`, `opposing`, or `unresolved` and is caller-supplied per hypothesis.
6. The impact target set exactly matches `EvidencePacket.affected_hypotheses` after deterministic set comparison.
7. Every target exists and is non-terminal; replacements retain `thought_id`, `parent_ids`, and `created_at`.
8. Replacement preserves `interpretation`, `hypothesis`, `assumptions`, `executor_profile`, and `graph`; it may change `evidence`, `metrics`, `verification_plan`, and `status`.
9. The evidence ID is added exactly once to the selected bucket, is absent from the other buckets, and no prior evidence is removed.
10. Confidence or status changes are accepted only from the complete caller-supplied replacement; runtime performs no arithmetic or inference.
11. All replacements are applied atomically to one new `PopulationSnapshot` and the prior snapshot/history remain byte-identical.
12. A deterministic record contains caller-supplied `record_id`/`timestamp`/`actor`, sorted affected IDs, packet `content_hash`, and SHA-256 prior/result state digests.
13. Repeated input and replay produce byte-identical packet, record, and snapshot canonical JSON.
14. Production runtime uses only Python standard library and performs no executor dispatch.
15. All TASK-001 and TASK-002 tests remain green.

### Required tests

- EvidencePacket strict validation, V1 schema compatibility, and lossless/canonical round trips.
- Provenance, affected-hypothesis, and impact validation.
- Atomic multi-target success and representative failure immutability.
- Replacement boundary and exact evidence-bucket semantics.
- Unknown, duplicate, terminal, missing, and extra target rejection.
- Replay-identical multi-hypothesis integration test.
- Static standard-library import audit, full regression, and Ruff.

### Regression checks

- Schemas, architecture, and TASK-002 implementation remain byte-unchanged.
- No scratch/cache artifact is staged.
- Codegraph metadata matches exact final Git HEAD.
