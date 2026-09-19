# TASK-004 Executor Selection Evidence

## Selection

- Requested transport: Hermes MCP using the prepaid MiMo API.
- Hermes MCP status: unavailable in the active Codex runtime.
- Selected transport: direct MiMo API through an ignored workspace-local
  orchestration runner.
- Model: `mimo-v2.5-pro`, thinking disabled.
- Local Ollama model: kept unloaded to reduce device load.

## Role isolation

Separate API sessions performed architect, coder, tester, production reviewer,
test reviewer, and remediation-review roles. Codex only created contracts,
checked artifact boundaries and invariants, applied MiMo-authored artifacts,
ran validation, synthesized evidence, and maintained project state.

## Usage

The runner captured 29 successful TASK-004 usage records:

- prompt tokens: 241,530;
- completion tokens: 77,219;
- total MiMo tokens: 318,749.

Rejected or superseded artifacts remain only in ignored `.codex-tmp` scratch
state. The API key was read from `MIMO_API_KEY` and was not persisted in the
repository.

## Independence limitation

Architect, coder, tester, and reviewer share the same MiMo model family.
Separate sessions, executable invariant tests, exact evidence, and mandatory
re-review mitigate but do not eliminate correlated model error.
