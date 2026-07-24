# NPS Core Project Completion Matrix

This matrix treats `ARCHITECTURE.md` as the authoritative project scope. A
green test suite for the current implementation is evidence for implemented
slices only; it is not evidence that later stages exist.

| Stage | Architecture exit criteria | Current evidence | Status | Planned closure |
|---|---|---|---|---|
| 0 — Foundation Freeze | Roles, owners, schemas, repository and freshness rule locked | TASK-001, ADR-0001..0004, four schemas, package skeleton, codegraph baseline | Complete | Maintain regression gates |
| 1 — Deterministic Runtime Prototype | End-to-end lifecycle; evidence updates multiple hypotheses; `N_h`, `N_v`, `N_e` separated; deterministic tests | TASK-002 proves lifecycle; TASK-003 proves strict evidence assimilation and atomic multi-thought updates; TASK-004 proves exact-snapshot Thought Ecology invariants and deterministic graph queries | In progress | TASK-005 experiment contracts and `N_v`; TASK-006 executor accounting and Stage-1 benchmark |
| 2 — Local Software Department | Orchestration-only Codex; author artifacts; tests; codegraph; automatic handoff | Role/prompt files and two manually orchestrated tasks exist | Incomplete | TASK-007 executable department workflow and handoff automation |
| 3 — Codegraph + Token-Efficient Context | Incremental update; exact HEAD; context reduction without completion regression | Full AST refresh and exact-HEAD metadata exist; incremental/context capsule/cache absent | Partial | TASK-008 incremental diff index, retrieval capsule, cache and benchmarks |
| 4 — Adaptive N + Experiment Designer | Adaptive `N`; dedup/merge; fewer executors than hypotheses; discriminating experiments | Only architecture/schema stubs | Incomplete | TASK-009 controller, information-gain ranker and experiment bundling |
| 5 — Verification Tribunal | Correlated-error detection, conflict report, reproduction log, calibrated confidence | Stub only | Incomplete | TASK-010 deterministic tribunal and formal/reproduction adapters |
| 6 — Distillation Dataset | Versioned transition dataset with rejected hypotheses, routing rationale, provenance and contamination-safe split | No dataset pipeline | Incomplete | TASK-011 dataset builder, validators, replay and version manifest |
| 7 — Train NPS Student Model | Student replaces teacher for proposal roles, meets latency, retains runtime identity, beats baseline | No train/evaluation artifact | Incomplete | TASK-012 training/evaluation pipeline plus an approved compute/data execution plan |
| 8 — Scientific Principal Model | Multi-domain evaluation, useful tests/executors, evidence insufficiency, audit and lower search cost | No integrated runtime benchmark | Incomplete | TASK-013 integrated runtime, multi-domain benchmark and release audit |

## Global completion gates

- Every planned task has a TaskContract, executor authorship, tests, review,
  evidence, memory/handoff update, reproducible commit and fresh codegraph.
- No phase is marked complete from indirect evidence or module stubs.
- Architecture changes require an ADR.
- Training or external-compute stages remain active until real artifacts and
  benchmark results exist; a plan alone is not completion evidence.
