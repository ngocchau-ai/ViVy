# TASK-003 Test Evidence

## Authored tests

- `tests/unit/test_evidence_packet_model.py`: 88 tests.
- `tests/unit/test_evidence_assimilation.py`: 57 tests.
- `tests/unit/test_atomic_state_update.py`: 75 tests.
- `tests/integration/test_multi_hypothesis_evidence_update.py`: 13 tests.

The 233 new tests cover strict schema-compatible packet parsing, direct versus
JSON collection typing, domain errors, impact set equality, plan normalization,
missing/terminal/prior-evidence targets, stale/deserialized revalidation,
complete replacement boundaries, exact evidence buckets, atomic failure,
caller-supplied metadata, explicit SHA-256 digests, prior/history immutability,
public APIs, standard-library imports, and byte-identical multi-target replay.

## Machine validation

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m compileall -q src tests
```

Results:

- pytest: 493 collected; 492 passed; one inherited Windows symlink skip; zero
  failures and zero errors.
- Ruff 0.15.22: all checks passed.
- compileall on `src` and `tests`: exit 0.
- Python: 3.12.13; pytest: 9.1.1.
- `git diff --name-only` for schemas, architecture, TASK-002 lifecycle
  production, and codegraph production: empty.
- Combined SHA-256 over the TASK-003 production/test file bytes:
  `800ecd572d490d7e2c07d8aec3ecb236c50d310c2b99261efe01da5da5074e25`.

The single skip is inherited from TASK-001 because Windows denies symlink
creation. Ordinary codegraph exclusion paths remain covered.
