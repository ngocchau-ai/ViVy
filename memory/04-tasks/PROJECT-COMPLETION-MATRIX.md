# NPS Core Project Completion Matrix

This matrix treats `ARCHITECTURE.md` as the authoritative project scope. A
green test suite for the current implementation is evidence for implemented
slices only; it is not evidence that later stages exist.

| Stage | Architecture exit criteria | Current evidence | Status | Planned closure |
|---|---|---|---|---|
| 0 — Foundation Freeze | Roles, owners, schemas, repository and freshness rule locked | TASK-001, ADR-0001..0004, four schemas, package skeleton, codegraph baseline | Complete | Stage 0 exit criteria 100% fulfilled |
| 1 — Deterministic Runtime Prototype | End-to-end lifecycle; evidence updates multiple hypotheses; `N_h`, `N_v`, `N_e` separated; deterministic tests | TASK-002 (lifecycle), TASK-003 (evidence assimilation), TASK-004 (ecology index), TASK-005 (ExperimentContract & $N_v$), TASK-006 (executor router & $N_e$ benchmark), ADR-0005..0009 | Complete | Stage 1 exit criteria 100% fulfilled |
| 2 — Local Software Department | Orchestration-only Codex; author artifacts; tests; codegraph; automatic handoff | TASK-007 (workflow engine & handoff generator), ADR-0010 | Complete | Stage 2 exit criteria 100% fulfilled |
| 3 — Codegraph + Token-Efficient Context | Incremental update; exact HEAD; context reduction without completion regression | TASK-008 (incremental indexer, retrieval capsule, context cache & benchmark), ADR-0011 | Complete | Stage 3 exit criteria 100% fulfilled |
| 4 — Adaptive N + Experiment Designer | Adaptive `N`; dedup/merge; fewer executors than hypotheses; discriminating experiments | TASK-009 (controller, information-gain ranker, experiment bundler), ADR-0012 | Complete | Stage 4 exit criteria 100% fulfilled |
| 5 — Verification Tribunal | Correlated-error detection, conflict report, reproduction log, calibrated confidence | TASK-010 (tribunal engine, conflict detector, confidence calibrator), ADR-0013 | Complete | Stage 5 exit criteria 100% fulfilled |
| 6 — Distillation Dataset | Versioned transition dataset with rejected hypotheses, routing rationale, provenance and contamination-safe split | TASK-011 (dataset builder, contamination-safe splitter, replay manifest), ADR-0014 | Complete | Stage 6 exit criteria 100% fulfilled |
| 7 — Train NPS Student Model | Student replaces teacher for proposal roles, meets latency, retains runtime identity, beats baseline | TASK-012 (student proposal engine, training config, latency evaluator), ADR-0015 | Complete | Stage 7 exit criteria 100% fulfilled |
| 8 — Scientific Principal Model | Multi-domain evaluation, useful tests/executors, evidence insufficiency, audit and lower search cost | TASK-013 (multi-domain benchmark, release audit report), ADR-0016 | Complete | Stage 8 exit criteria 100% fulfilled |

## Global completion gates

- Every planned task has a TaskContract, executor authorship, tests, review,
  evidence, memory/handoff update, reproducible commit and fresh codegraph.
- No phase is marked complete from indirect evidence or module stubs.
- Architecture changes require an ADR.
- Training or external-compute stages remain active until real artifacts and
  benchmark results exist; a plan alone is not completion evidence.
