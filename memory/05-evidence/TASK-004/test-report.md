# TASK-004 Test Evidence

## Authored tests

- `tests/unit/test_thought_ecology.py`: 77 tests.
- `tests/integration/test_thought_ecology_population.py`: 24 tests.

The 101 new tests cover relation validation, strict direct tuple versus JSON
list construction, unknown/self/duplicate/cycle failures, reciprocal
undirected collapse, shared-assumption conflicts and pair generation, evidence
ambiguity and placement, every public query family, deterministic
target-before-source topology, canonical serialization, exact SHA-256 snapshot
binding, structural forgery rejection, replay identity, snapshot/history
immutability, and a static production-import allowlist.

## Machine validation

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m compileall -q src tests
```

Results:

- pytest: 594 collected; 593 passed; one inherited Windows symlink skip; zero
  failures and zero errors.
- Ruff 0.15.22: all checks passed.
- compileall on `src` and `tests`: exit 0.
- Python: 3.12.13; pytest: 9.1.1.
- Protected-scope `git diff --name-only` for schemas, architecture, lifecycle,
  TASK-003 production, and codegraph production: empty.
- Combined SHA-256 over the TASK-004 production/test file bytes:
  `efb08e3f2136d94cb3cd0024c6e2b35b5948c03aee9e43746fa2b92692205cd7`.

The single skip is inherited from TASK-001 because Windows denies symlink
creation. Ordinary codegraph exclusion paths remain covered.
