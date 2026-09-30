# ADR-0007: Deterministic Thought Ecology Graph Index

## Status

Accepted

## Context

ADR-0006 established evidence assimilation and atomic multi-thought state
updates within `evidence_assimilator` and `state_update`. Stage 1 can now
execute ThoughtState lifecycle transitions and apply evidence atomically, but
it cannot validate or query the population-wide dependency, contradiction,
overlap, shared-assumption, and evidence-impact ecology.

The `thought_ecology` module is currently an empty package skeleton. NPS Core
requires:

1. An immutable `ThoughtEcology` index built from an exact `PopulationSnapshot`.
2. Strict typed relation value objects for directed dependencies, undirected
   contradictions/overlaps, derived shared-assumptions, and caller-supplied
   evidence-impact placements.
3. Deterministic canonical serialization, SHA-256 snapshot digest binding,
   and exact-snapshot revalidation.
4. Stable query primitives for immediate neighbors, reverse dependents,
   transitive dependencies, topological order, and full neighborhood.
5. Graph invariant enforcement: unknown/self references fail, dependency
   cycles fail, conflicting shared-assumption ID reuse fails, ambiguous
   multi-bucket evidence fails.

The `hypothesis_population`, `evidence_assimilator`, and `state_update`
modules must remain byte-unchanged. No schema or architecture document may be
modified.

## Decision

### 1. Module ownership

`thought_ecology` owns all ecology relation value objects, the `ThoughtEcology`
index, construction from `PopulationSnapshot`, deterministic queries,
canonical serialization, SHA-256 snapshot digest binding, and exact-snapshot
revalidation. No other module constructs or mutates the ecology index.

### 2. Relation value objects

All relation types are frozen, slotted `dataclasses` defined in
`thought_ecology.relations`:

#### `DependencyEdge`

- `source_id: str` Ã¢Â€Â” the thought whose `graph.dependencies` contains `target_id`.
- `target_id: str` Ã¢Â€Â” the depended-upon thought.
- Directed: `DependencyEdge("A", "B")` means A depends on B.
- Sort key: `(source_id, target_id)`.

#### `ContradictionEdge`

- `first_id: str` Ã¢Â€Â” the lexicographically smaller thought ID.
- `second_id: str` Ã¢Â€Â” the lexicographically larger thought ID.
- Undirected canonical pair: if thought A lists B in `graph.contradictions` and
  thought B lists A, exactly one `ContradictionEdge(min(A,B), max(A,B))` exists.
  If only A lists B, the same canonical edge is created (one-sided accepted).
- Sort key: `(first_id, second_id)`.

#### `OverlapEdge`

- `first_id: str` Ã¢Â€Â” the lexicographically smaller thought ID.
- `second_id: str` Ã¢Â€Â” the lexicographically larger thought ID.
- Same canonical undirected pair semantics as `ContradictionEdge`.
- Sort key: `(first_id, second_id)`.

#### `SharedAssumptionLink`

- `assumption_id: str` Ã¢Â€Â” the shared assumption identifier.
- `first_thought_id: str` Ã¢Â€Â” the lexicographically smaller thought ID.
- `second_thought_id: str` Ã¢Â€Â” the lexicographically larger thought ID.
- Derived only when two distinct thoughts each contain an assumption with the
  same `assumption_id` **and** identical complete payload (all four fields:
  `assumption_id`, `statement`, `confidence`, `source`).
- If two distinct thoughts reuse the same `assumption_id` with different
  payloads, construction fails with `ConflictingAssumptionError`.
- Sort key: `(assumption_id, first_thought_id, second_thought_id)`.

#### `EvidencePlacement`

- `evidence_id: str` Ã¢Â€Â” the evidence identifier from `ThoughtState.evidence`.
- `thought_id: str` Ã¢Â€Â” the thought containing this evidence ID.
- `bucket: str` Ã¢Â€Â” exactly `"supporting"`, `"opposing"`, or `"unresolved"`.
- Caller-supplied classification; no inference.
- If the same `evidence_id` appears in multiple buckets of the same thought,
  construction fails with `AmbiguousEvidenceBucketError`.
- Sort key: `(evidence_id, thought_id, bucket)`.

### 3. `ThoughtEcology` fields

`ThoughtEcology` is a frozen, slotted `dataclass` defined in
`thought_ecology.index`:

```python
@dataclass(frozen=True, slots=True)
class ThoughtEcology:
    snapshot_digest: str                          # SHA-256 hex of snapshot canonical JSON
    thought_ids: tuple[str, ...]                  # all snapshot thought IDs, lexical order
    dependencies: tuple[DependencyEdge, ...]      # sorted by (source_id, target_id)
    contradictions: tuple[ContradictionEdge, ...] # sorted by (first_id, second_id)
    overlaps: tuple[OverlapEdge, ...]             # sorted by (first_id, second_id)
    shared_assumptions: tuple[SharedAssumptionLink, ...]  # sorted by (assumption_id, first, second)
    evidence_placements: tuple[EvidencePlacement, ...]    # sorted by (evidence_id, thought_id, bucket)
```

### 4. Construction: `build(snapshot: PopulationSnapshot) -> ThoughtEcology`

`thought_ecology.index.build` is a pure function accepting a `PopulationSnapshot`
and returning a `ThoughtEcology`. Construction order:

1. Compute `snapshot_digest` as SHA-256 hex of the snapshot's canonical JSON
   (using `hashlib.sha256` over bytes produced by the canonical JSON function
   from ADR-0005/ADR-0006).
2. Extract `thought_ids` as a tuple of all `thought_id` values from the
   snapshot, sorted lexicographically.
3. Build `dependencies` by iterating every thought's `graph.dependencies`.
   For each `(thought_id, dep_id)` pair:
   - If `dep_id == thought_id`: fail with `SelfReferenceError`.
   - If `dep_id` not in `thought_ids`: fail with `UnknownThoughtError`.
   - Otherwise: create `DependencyEdge(thought_id, dep_id)`.
   - Deduplicate identical `(source_id, target_id)` pairs.
   - Detect cycles via DFS on the directed dependency graph. If any cycle
     exists (including multi-node cycles), fail with `DependencyCycleError`.
     The cycle detection uses a deterministic DFS that visits neighbors in
     lexical order.
4. Build `contradictions` by iterating every thought's `graph.contradictions`.
   For each `(thought_id, other_id)` pair:
   - If `other_id == thought_id`: fail with `SelfReferenceError`.
   - If `other_id` not in `thought_ids`: fail with `UnknownThoughtError`.
   - Otherwise: create canonical `ContradictionEdge(min(thought_id, other_id),
     max(thought_id, other_id))`.
   - Deduplicate identical canonical pairs.
5. Build `overlaps` with the same canonical undirected pair logic as
   contradictions, using `OverlapEdge`.
6. Build `shared_assumptions` by collecting all `(thought_id, assumption)`
   pairs from every thought's `assumptions` list. Group by `assumption_id`:
   - If a single `assumption_id` maps to multiple distinct payloads across
     different thoughts: fail with `ConflictingAssumptionError`.
   - If a single `assumption_id` has identical payload in two or more distinct
     thoughts: create one `SharedAssumptionLink` per unique pair of thought
     IDs (lexicographically ordered), deduplicated.
   - Assumptions within the same thought with the same `assumption_id` are
     handled per the caller's data; the ecology does not reject intra-thought
     duplicates (that is a ThoughtState-level concern).
7. Build `evidence_placements` by iterating every thought's `evidence`
   buckets (`supporting`, `opposing`, `unresolved`). For each
   `(thought_id, bucket, evidence_id)`:
   - If the same `evidence_id` appears in multiple buckets of the same
     `thought_id`: fail with `AmbiguousEvidenceBucketError`.
   - Otherwise: create `EvidencePlacement(evidence_id, thought_id, bucket)`.
   - Deduplicate identical triples.
8. Sort all relation tuples by their respective sort keys.
9. Return the frozen `ThoughtEcology`.

If any validation fails, no `ThoughtEcology` is returned; the
`PopulationSnapshot` is never mutated.

### 5. Domain errors

All domain errors are defined in `thought_ecology.errors` and inherit from
`ThoughtEcologyError(Exception)`:

- `UnknownThoughtError(thought_id: str, reference_source: str)` Ã¢Â€Â” a graph
  reference points to a thought ID not in the snapshot.
- `SelfReferenceError(thought_id: str, relation_type: str)` Ã¢Â€Â” a thought
  references itself.
- `DependencyCycleError(cycle: tuple[str, ...])` Ã¢Â€Â” a directed dependency cycle
  is detected. `cycle` contains the thought IDs in deterministic DFS order.
- `ConflictingAssumptionError(assumption_id: str, thoughts: tuple[str, ...])`
  Ã¢Â€Â” the same `assumption_id` has different payloads across thoughts.
- `AmbiguousEvidenceBucketError(evidence_id: str, thought_id: str,
  buckets: tuple[str, ...])` Ã¢Â€Â” the same evidence ID appears in multiple
  buckets of one thought.

All error fields are plain strings/tuples; errors are hashable and comparable.

### 6. Query API

All query methods are on `ThoughtEcology` and return frozen tuples. They never
mutate the ecology or snapshot. Failed queries (e.g., unknown thought ID)
raise `UnknownThoughtError`.

#### `dependencies_of(thought_id: str) -> tuple[DependencyEdge, ...]`
Returns all `DependencyEdge` where `source_id == thought_id`, sorted by
`target_id`.

#### `dependents_of(thought_id: str) -> tuple[DependencyEdge, ...]`
Returns all `DependencyEdge` where `target_id == thought_id`, sorted by
`source_id`. (Reverse dependents.)

#### `contradictions_of(thought_id: str) -> tuple[ContradictionEdge, ...]`
Returns all `ContradictionEdge` where `first_id == thought_id` or
`second_id == thought_id`, sorted by the other ID.

#### `overlaps_of(thought_id: str) -> tuple[OverlapEdge, ...]`
Returns all `OverlapEdge` where `first_id == thought_id` or
`second_id == thought_id`, sorted by the other ID.

#### `shared_assumptions_of(thought_id: str) -> tuple[SharedAssumptionLink, ...]`
Returns all `SharedAssumptionLink` where `first_thought_id == thought_id` or
`second_thought_id == thought_id`, sorted by `(assumption_id, other_id)`.

#### `evidence_for(thought_id: str) -> tuple[EvidencePlacement, ...]`
Returns all `EvidencePlacement` where `thought_id == thought_id`, sorted by
`(evidence_id, bucket)`.

#### `neighborhood(thought_id: str) -> tuple[str, ...]`
Returns the deduplicated union of all thought IDs connected to `thought_id`
via any relation type (dependencies, contradictions, overlaps,
shared-assumptions, evidence co-placement), sorted lexicographically.
Excludes `thought_id` itself.

#### `transitive_dependencies(thought_id: str) -> tuple[str, ...]`
Returns all thought IDs reachable from `thought_id` by following directed
dependency edges transitively (BFS, neighbors visited in lexical order),
excluding `thought_id` itself, sorted lexicographically. Acyclic by
construction (cycles are rejected at build time).

#### `topological_order() -> tuple[str, ...]`
Returns all `thought_ids` in a deterministic topological order respecting
dependency edges. Uses Kahn's algorithm with a lexical-order tie-break on
the ready set. If the graph were somehow cyclic (impossible after build
validation), raises `DependencyCycleError`.

### 7. Deterministic sort keys

Every relation tuple has a defined sort key (see Ã‚Â§2). All query results are
sorted by these keys before return. `topological_order` uses Kahn's algorithm
with lexical tie-break. `transitive_dependencies` uses BFS with lexical
neighbor ordering. All produce deterministic, replay-identical output.

### 8. Strict tuple types versus JSON-list `from_dict` boundary

#### Direct construction (strict tuples)

`ThoughtEcology` and all relation dataclasses accept only their declared
field types (str, tuple). Direct construction with wrong types raises
`TypeError` from the dataclass machinery.

#### `from_dict(data: dict) -> ThoughtEcology`

`ThoughtEcology.from_dict` accepts a plain dictionary where relation
collections are JSON-style **lists** of dictionaries (not tuples). It
converts lists to tuples and string-keyed dicts to dataclass instances.
This is the deserialization boundary. Validation is identical to `build`
except that the snapshot digest is taken from the dict (not recomputed)
and `validate_for` is used separately to confirm snapshot identity.

If the dict contains unknown keys, wrong types, or missing required keys,
`from_dict` raises `ValueError` with a stable message.

#### `to_dict() -> dict`

`ThoughtEcology.to_dict` converts all tuples back to lists and all
dataclass instances to plain dictionaries. This is the serialization
boundary. The output is a plain `dict`/`list` structure suitable for
`json.dumps`.

### 9. Canonical JSON and SHA-256 snapshot digest

#### Canonical JSON

`ThoughtEcology.to_canonical_json() -> str` produces a deterministic JSON
string using the same conventions as ADR-0005/ADR-0006:
- `ensure_ascii=False`
- `sort_keys=True`
- compact separators `(",", ":")`
- `allow_nan=False`

Repeated serialization of an identical ecology produces byte-identical output.

#### SHA-256 snapshot digest

`snapshot_digest` is computed as `hashlib.sha256(snapshot_canonical_json.encode("utf-8")).hexdigest()`
where `snapshot_canonical_json` is the canonical JSON of the
`PopulationSnapshot` (produced by `PopulationSnapshot.to_canonical_json()`
or equivalent). This binds the ecology to one exact snapshot.

### 10. `validate_for(snapshot: PopulationSnapshot) -> None`

`ThoughtEcology.validate_for` accepts a `PopulationSnapshot` and:

1. Rebuilds a fresh `ThoughtEcology` from the supplied snapshot via `build`.
2. Compares the rebuilt ecology's `to_canonical_json()` with
   `self.to_canonical_json()`.
3. If they differ, raises `SnapshotMismatchError` (a `ThoughtEcologyError`
   subclass) with a stable message.
4. If they match, returns `None`.

This catches stale or structurally forged deserialized ecologies. The
supplied snapshot is never mutated.

### 11. Failure atomicity and no mutation

- `build` is a pure function. If any validation step fails, no partial
  `ThoughtEcology` is returned. The `PopulationSnapshot` is never mutated.
- All query methods are pure accessors. They never modify the ecology or
  snapshot. Failed queries raise domain errors without side effects.
- `validate_for` rebuilds from the supplied snapshot; the rebuild is
  discarded after comparison. The supplied snapshot is never mutated.
- `from_dict` constructs a new ecology from a dict; it does not modify any
  external state.

### 12. Standard-library / no-inference / no-dispatch boundary

`thought_ecology` uses only Python standard library modules (`dataclasses`,
`hashlib`, `json`, `collections`, `typing`). It performs no semantic
inference, confidence arithmetic, model dispatch, network calls, filesystem
operations, database queries, UUID generation, random number generation, or
wall-clock reads. All data is caller-supplied.

### 13. Deferred scope

The following are explicitly deferred and not implemented by TASK-004:

- ExperimentContract and Adaptive N (`experiment_designer`, `adaptive_n`).
- Verification Tribunal (`verification_tribunal`).
- Executor routing (`executor_router`).
- `N_v`/`N_e` accounting.
- Generic event-ledger unifying lifecycle and evidence provenance streams.
- Confidence arithmetic, semantic relevance inference, or evidence quality
  scoring.
- Model, network, database, or filesystem calls at runtime.
- Any modification to `hypothesis_population`, `evidence_assimilator`,
  `state_update`, schemas, or `ARCHITECTURE.md`.

### 14. Baseline immutability

No architecture baseline document or schema file is changed by this task.
`hypothesis_population`, `evidence_assimilator`, `state_update`, and all
schema files remain byte-unchanged.

## Consequences

- `thought_ecology` becomes the source of truth for population-wide graph
  relations and deterministic ecology queries.
- All ecology consumers must supply a complete `PopulationSnapshot`; the
  ecology never generates or mutates snapshot data.
- Frozen value objects prevent accidental mutation; the ecology is immutable
  after construction.
- Canonical JSON and SHA-256 digest binding enable replay verification,
  tamper detection, and stable cache keys.
- Deterministic sort keys and query algorithms ensure replay-identical output.
- Strict tuple-typed construction prevents type confusion; `from_dict`/`to_dict`
  provide the JSON serialization boundary.
- Graph invariants (no self-references, no unknown references, no cycles,
  no conflicting assumptions, no ambiguous evidence) are enforced at build
  time, failing closed.
- No production dependencies are added beyond the Python standard library.
- Later Stage 1 work (Adaptive N, ExperimentContract, tribunal) can consume
  `ThoughtEcology` without modifying these invariants.

## Rejected alternatives

1. **Mutable ecology with incremental updates:** rejected because frozen
   dataclasses make the ecology boundary explicit and prevent partial
   updates from violating invariants. Rebuild from snapshot is cheap for
   Stage 1 population sizes.

2. **Shared-assumption links from `assumption_id` alone (ignoring payload):**
   rejected because two thoughts could reuse an ID with different meanings.
   Requiring payload equality ensures semantic identity.

3. **Allowing conflicting assumption ID reuse with a warning:** rejected
   because it would silently produce incorrect shared-assumption links.
   Fail-closed is required.

4. **Allowing same evidence ID in multiple buckets with a warning:** rejected
   because it would produce ambiguous evidence placements. Fail-closed is
   required.

5. **Mutable query results (lists instead of tuples):** rejected because
   callers could mutate returned data, violating immutability invariants.

6. **Internal UUID, timestamp, or random generation:** rejected because it
   introduces nondeterminism, violating the replay-identical contract.

7. **Runtime jsonschema validation:** rejected to avoid a production
   dependency, consistent with ADR-0004, ADR-0005, and ADR-0006.

8. **Embedding-based similarity for contradiction/overlap inference:** rejected
   because the ecology does not perform model inference. Relations are
   caller-supplied via `ThoughtState.graph`.

9. **Storing the full snapshot inside the ecology:** rejected because it would
   duplicate data. The SHA-256 digest binds the ecology to the snapshot
   without storing it.

10. **Allowing dependency cycles with a warning:** rejected because cycles
    would make topological order and transitive dependencies undefined.
    Fail-closed is required.

## Compatibility and migration

- `ThoughtEcology` serialization produces plain dictionaries/lists suitable
  for `json.dumps` and accepted by any JSON consumer.
- `ARCHITECTURE.md` and all schema files remain unchanged.
- Existing TASK-001, TASK-002, and TASK-003 tests remain green.
- The implementation stays compatible with Windows PowerShell, Linux shell,
  and UTF-8 repository content.
- `thought_ecology` imports `PopulationSnapshot` and `ThoughtState` from
  `hypothesis_population` but does not modify them.
- Future work (Adaptive N, ExperimentContract, tribunal) can consume
  `ThoughtEcology` without modifying these modules.

## Security

- Unknown/self graph references fail with stable domain errors (fail-closed).
- Dependency cycles fail deterministically (fail-closed).
- Conflicting shared-assumption ID reuse fails (fail-closed).
- Ambiguous multi-bucket evidence fails (fail-closed).
- Deserialized ecology cannot bypass exact-snapshot validation; `validate_for`
  rebuilds from the supplied snapshot and compares canonical JSON.
- Invalid ecology construction leaves the `PopulationSnapshot`
  byte-identical.
- No network, filesystem, database, UUID, random, or clock calls are made
  at runtime.

## Validation

### Acceptance criteria

1. Public ecology types and domain errors import from
   `nps_core.thought_ecology`.
2. The index contains every snapshot thought exactly once in lexical order.
3. `ThoughtState.graph.dependencies` creates directed `DependencyEdge`
   entries; `contradictions` and `overlaps` create canonical undirected
   `ContradictionEdge`/`OverlapEdge` pairs.
4. Reciprocal symmetric declarations collapse to one edge; one-sided
   declarations are accepted and normalized.
5. Unknown or self graph references fail with stable domain errors
   (`UnknownThoughtError`, `SelfReferenceError`).
6. Dependency cycles, including multi-node cycles, fail deterministically
   (`DependencyCycleError`).
7. Shared-assumption links are derived only from equal `assumption_id` and
   equal complete assumption payload; conflicting reuse of an ID fails
   (`ConflictingAssumptionError`).
8. Evidence-impact links preserve caller-supplied thought ID and bucket
   classification without inference.
9. The same evidence ID in multiple buckets of one thought is rejected as
   ambiguous (`AmbiguousEvidenceBucketError`).
10. `dependencies_of`, `dependents_of`, `contradictions_of`, `overlaps_of`,
    `shared_assumptions_of`, `evidence_for`, `neighborhood`,
    `transitive_dependencies`, and `topological_order` are deterministic.
11. A frozen ecology serializes losslessly to strict plain dictionaries
    (`to_dict`) and canonical JSON (`to_canonical_json`).
12. Direct tuple-typed construction is strict; `from_dict` requires JSON
    lists.
13. Ecology stores SHA-256 of the exact snapshot canonical JSON and
    `validate_for` rebuilds/compares the exact supplied snapshot.
14. A stale or structurally forged deserialized ecology fails exact-snapshot
    validation (`SnapshotMismatchError`).
15. Construction, failed queries, and validation never mutate the
    `PopulationSnapshot` or history.
16. Repeated build/replay produces byte-identical ecology canonical JSON.
17. Production runtime uses only Python standard library and performs no
    executor dispatch.
18. All TASK-001 through TASK-003 tests remain green.

### Required tests

- Strict relation/index direct and dict/JSON validation.
- Unknown, self, duplicate normalization, and dependency-cycle cases.
- Shared assumption and evidence impact derivation/conflict cases.
- All deterministic query forms and exact-snapshot validation.
- Replay-identical multi-thought integration test.
- Static standard-library import audit, full regression, Ruff, and compileall.

### Regression checks

- Schemas, architecture, TASK-002 and TASK-003 production remain
  byte-unchanged.
- No scratch/cache artifact is staged.
- Codegraph metadata matches exact final Git HEAD.
## Implementation clarifications

This section supersedes any conflicting earlier wording in ADR-0007.

### 1. Validation and error types

- Dataclasses do not enforce annotations at runtime. All direct/dict/JSON
  validation is performed explicitly in `__post_init__` (for direct
  construction) and in `from_dict`/`from_canonical_json` (for deserialization).
- Introduce a stable domain error:
  - `EcologyValidationError(ThoughtEcologyError, ValueError)` for malformed
    direct/dict/JSON values, including:
    - tuple strictness (exact element types and ordering),
    - exact keys (no missing/extra keys),
    - ID and pattern constraints,
    - digest format constraints,
    - relation element types and canonical endpoints,
    - duplicate detection within collections,
    - collection consistency (e.g., relations referencing only known thought IDs).
- Add `SnapshotMismatchError(ThoughtEcologyError)` to the domain error list.
  It carries deterministic metadata: `expected_digest` and `actual_digest`.
- All domain errors expose deterministic metadata suitable for logging and
  testing. Do not assume ordinary `Exception` instances are value-comparable
  or hashable.

### 2. Relation serialization

- Every relation type defines strict exact-key `from_dict` and `to_dict`
  methods. These methods enforce exact keys and element types.
- Only `ThoughtEcology` owns canonical JSON methods (`to_canonical_json`,
  `from_canonical_json`, and canonical serialization helpers). No alternate
  JSON method names are required. Relation types do not expose JSON methods
  directly.

### 3. Direct construction vs. derivation proof

- `ThoughtEcology.__post_init__` validates structural invariants and
  normalizes deterministic tuple ordering (e.g., lexicographic ordering of
  relations by canonical endpoints). It cannot prove snapshot-derived truth.
- `ThoughtEcology.from_dict` performs strict structural validation, but it
  does not validate "identical to build". Only `validate_for` can prove exact
  derivation: it rebuilds the ecology, checks expected/actual snapshot digests
  for error metadata, and compares the full canonical ecology JSON. Digest
  equality alone is not the proof.

### 4. Topological orientation

- Because source depends on target, every target must appear before its
  dependent source in topological order.
- Kahn indegree/readiness operates on dependency prerequisites with a
  lexical tie-break on canonical thought IDs when multiple nodes are ready.

### 5. Neighborhood evidence co-placement

- Neighborhood evidence co-placement links thoughts sharing the same
  `evidence_id`, regardless of their caller-supplied buckets.
- Evidence IDs are never treated as thought IDs.

### 6. Empty snapshots are valid

- Empty snapshots are valid: empty tuples, SHA-256 digest of the canonical
  empty representation, and empty topological order.
- All queries still reject unknown IDs.

### 7. `build` and `validate_for` snapshot typing

- `build` and `validate_for` require exact `PopulationSnapshot` instances.
  Wrong types raise `EcologyValidationError`.
