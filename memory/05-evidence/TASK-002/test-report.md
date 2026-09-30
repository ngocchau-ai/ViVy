# TASK-002 Test Evidence

## Role

- Executor: `mimo_tester`
- Runtime/model: direct MiMo API / `mimo-v2.5-pro`
- Independence: low model-family independence, separate role sessions

## Authored tests

- `tests/unit/test_thought_state_model.py`
- `tests/unit/test_thought_lifecycle.py`
- `tests/integration/test_thought_lifecycle_end_to_end.py`

Coverage includes ThoughtState V1/schema round trips, deep immutability,
canonical JSON, strict invalid inputs, lineage integrity, atomic
create/branch/merge/prune behavior, source-order-independent merge, audit
history, semantic RFC3339 validation, huge integer robustness, standard-library
production imports, and byte-identical replay.

## Machine validation

```powershell
.venv\Scripts\python.exe -m pytest -o addopts="" -ra
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m compileall -q src\nps_core
```

Results:

- pytest: 260 collected; 259 passed; 1 pre-existing Windows symlink skip;
  0 failed; 0 errors.
- Ruff: all checks passed.
- compileall: exit 0.
- Static production import allowlist: passed.
- 100-thought/100-event benchmark, five runs: maximum 0.007745 seconds against
  the 1-second budget.

The skip is inherited from TASK-001: Windows denied symlink creation. Ordinary
codegraph exclusion paths remain covered.
