# TASK-001 Test Evidence

## Role/Executor

- **Role**: Local Tester
- **Model**: qwen2.5-coder:7b
- **ID**: dae161e27b0e
- **Runtime**: Ollama
- **Independence**: Low (same model with separate role/session)

## Assumptions

- The environment is set up correctly for running the tests.
- All dependencies are installed in the virtual environment.
- The test suite and codebase are accessible.

## Commands

```powershell
.venv\Scripts\pytest.exe -q
.venv\Scripts\ruff.exe check . --exclude .codex-tmp
```

## Results

1. **pytest**
   - Exit Code: 0
   - Result: 57 passed, 1 skipped.
   - The skip is due to Windows denying symlink creation.
2. **ruff**
   - Exit Code: 0
   - Result: All checks passed.

## Acceptance Coverage

- **Architecture**: 14/14
- **CLI Integration**: 1/1 (uses a temporary Git repository, commits its
  fixture, runs the real refresh wrapper, reports FRESH, and verifies
  `repository_head == codegraph_commit == temporary HEAD`)
- **Codegraph Build**: 6/6
- **Codegraph Errors/Exclusions**: 3/3
- **Codegraph Writes/Reports**: 2/2
- **EvidencePacket**: 6/6
- **Experiment**: 6/6
- **Schema Meta**: 8/8
- **TaskContract**: 6/6
- **ThoughtState**: 6/6

## Limitations

- The symlink-directory test is skipped on Windows because the operating
  system denied symlink creation after the test caught
  `OSError`/`NotImplementedError`.
- Path exclusion logic is covered for all configured ordinary directories.

## Uncertainties

- No uncertainties identified based on the provided results.

## Recommendation

Ready for local reviewer; TASK-001 is not yet complete.
