# TASK-005 — Deterministic Experiment Contract and Verifier Budget

## Status

Active.

## Contract

`orchestration/codex/tasks/TASK-005.yaml`

## Executor

- Direct MiMo API, model `mimo-v2.5-pro`.
- Isolated architect/coder/tester/reviewer sessions.
- Hermes MCP is unavailable in the active runtime.
- Local Ollama remains unloaded.

## Objective

Complete the Stage-1 ExperimentContract and verifier-demand accounting slice
with strict compatibility to `schemas/experiment.schema.json`, explicit
caller-supplied verification needs, deterministic `N_v`, and exact-snapshot
validation without implementing Adaptive N or executor routing.

## Completion gates

- ADR-0008 accepted.
- Production and tests authored by MiMo sessions.
- Full regression, Ruff, compileall, schema, digest, replay, and import checks
  pass.
- Fresh reviewer has no unresolved actionable finding.
- Schemas, architecture, TASK-002 through TASK-004 production remain unchanged.
- Evidence, handoff, commit, and post-commit exact-HEAD codegraph exist.
