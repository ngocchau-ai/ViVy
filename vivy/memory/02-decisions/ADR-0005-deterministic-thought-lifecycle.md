# ADR-0005: Deterministic ThoughtState Lifecycle Core

## Status

Accepted

## Context

ADR-0004 established Python 3.11+ as the foundation runtime and froze the
ThoughtState V1 JSON schema. The `hypothesis_population` module currently
contains only a package skeleton. NPS Core requires an executable,
deterministic ThoughtState lifecycle that can create, branch, merge, and prune
thoughts without model inference, random generation, or wall-clock
dependencies.

The `state_update` module is a future orchestration consumer and must not be
modified by this work. Evidence assimilation, the Thought Ecology graph,
ExperimentContract, Adaptive N, `N_v`/`N_e` accounting, and executor routing
remain deferred to later Stage 1 tasks.

## Decision

### 1. Module ownership

`hypothesis_population` owns all immutable ThoughtState value objects and the
create/branch/merge/prune lifecycle primitives. `state_update` remains a
future orchestration consumer and is not modified by TASK-002.

### 2. Value model and schema boundary

Use frozen, slotted standard-library `dataclasses` for all ThoughtState value
objects. The V1 schema boundary is a plain `dict`/`list` structure. No runtime
`jsonschema` dependency is introduced; structural validation is hand-written
against the V1 shape.

### 3. Caller-supplied identity and content

All IDs, timestamps, actors, event IDs, and complete semantic content
(including merged ThoughtState content and metrics) are caller-supplied. The
lifecycle code contains no wall clock, `random`, `uuid`, model inference, or
semantic embedding logic.

### 4. Merge semantics

Merge requires at least two distinct non-terminal source thoughts. Source IDs
are canonicalized before use. Sources are marked `merged`. A single `active`,
caller-supplied result thought is created. Merge never invents claims,
computes confidence arithmetic, or derives semantic content.

### 5. Prune semantics

Prune requires a non-empty `reason` and an explicit disposition. The only
valid dispositions are `rejected` and `dormant` because V1 has no `pruned`
status. The target thought must exist and not already be terminal.

### 6. Immutability and atomicity

Prior population snapshots, ThoughtState value objects, lineage index entries,
and audit events are deeply immutable. Every lifecycle transition returns a
new snapshot; the prior snapshot is never mutated. Failed transitions are
atomic and leave the original snapshot unchanged.

### 7. Canonical JSON serialization

Canonical JSON uses `ensure_ascii=False`, `sort_keys=True`, compact separators
`(",", ":")`, and deterministic collection handling. Repeated serialization
of identical data produces byte-identical output.

### 8. Deferred scope

TASK-002 does not complete all Stage 1 work. Evidence assimilation, the
Thought Ecology graph store, ExperimentContract, Adaptive N, `N_v`/`N_e`
accounting, and executor routing remain deferred.

### 9. Status allowed values

`status.allowed_values` is serialized exactly as required by ThoughtState V1.
Lifecycle transitions cannot introduce statuses outside the V1 enum:
`active`, `queued`, `testing`, `partially_verified`, `verified`, `rejected`,
`merged`, and `dormant`.

### 10. Baseline immutability

No architecture baseline document or schema file is changed by this task.

## Consequences

- `hypothesis_population` becomes the source of truth for ThoughtState value
  types and lifecycle operations.
- All lifecycle consumers must supply complete ThoughtState content, IDs, and
  timestamps; the core never generates them.
- Merge and prune are pure functions of caller-supplied data, enabling
  deterministic replay and audit.
- Frozen value objects prevent accidental mutation; state changes construct a
  new snapshot.
- Canonical JSON supports replay verification and stable cache keys.
- No production dependencies are added.
- Later Stage 1 work builds on this core without changing these invariants.

## Rejected alternatives

1. **Mutable ThoughtState with copy discipline:** rejected because frozen
   dataclasses make the boundary explicit and easier to reason about.
2. **Runtime jsonschema validation:** rejected to avoid a production
   dependency.
3. **Internal UUID or timestamp generation:** rejected because it introduces
   nondeterminism.
4. **Confidence arithmetic in merge:** rejected because it would invent
   semantic policy.
5. **A new `pruned` V1 status:** rejected because the frozen schema does not
   include it.
6. **Embedding-based merge similarity:** rejected because lifecycle code does
   not perform model inference.

## Compatibility and migration

- ThoughtState serialization produces plain dictionaries accepted by the
  existing V1 schema.
- `ARCHITECTURE.md` and all schema files remain unchanged.
- Existing TASK-001 tests remain green.
- The implementation stays compatible with Windows PowerShell, Linux shell,
  and UTF-8 repository content.
- Future `state_update` code imports lifecycle primitives from
  `hypothesis_population` without moving ownership.
