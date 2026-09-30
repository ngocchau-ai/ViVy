# TASK-001 Local Coder Evidence

## Role/Executor

- **Role:** `local_coder`
- **Runtime:** Ollama
- **Selected model:** `qwen2.5-coder:7b`
- **Model ID:** `dae161e27b0e`
- **Execution style:** isolated, contract-bounded micro-sessions

The smaller `qwen2.5:0.5b` and `qwen2.5-coder:3b` candidates were rejected
after failing bounded artifact trials. The 7B coder was selected for the
implementation.

## Assumptions

- TASK-001 requires the foundation contracts, Python package skeleton, and a
  minimal deterministic codegraph indexer.
- The indexer uses Python standard-library AST and JSON.
- Git HEAD metadata is recorded when the repository is versioned.

## Artifacts

### Production artifacts

- `pyproject.toml`
- package skeleton under `src/nps_core`
- four Draft 2020-12 JSON schemas under `schemas`
- `src/nps_core/codegraph/indexer.py`
- `scripts/refresh_codegraph.py`
- `CONTRIBUTING.md`
- `memory/02-decisions/ADR-0004-python-foundation.md`
- `schemas/README.md`
- `memory/03-codegraph/README.md`

### Test artifacts

Tests under `tests/architecture`, `tests/unit`, and `tests/integration` were
authored through the separate `local_tester` role.

## Contract Boundaries

The indexer:

- discovers Python files deterministically;
- excludes configured and generated directories;
- records module, class, function, and async-function nodes;
- records import and containment edges;
- records per-file parse errors;
- prevents output-path escape;
- writes deterministic JSON plus three reports;
- records Git HEAD metadata when the repository is versioned.

## Verification Handoff

Machine verification is recorded separately in `test-report.md`:

- pytest exit 0: 57 passed, 1 skipped;
- ruff exit 0: all checks passed.

## Limitations/Uncertainties

- Model selection was based on bounded artifact quality trials.
- The coder and tester use the same local model backbone under separate roles
  and sessions, so role independence is low.

## Recommendation

Implementation evidence is ready for handoff to the local reviewer. The local
coder does not self-approve TASK-001.
