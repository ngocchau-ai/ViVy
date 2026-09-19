# Contributing to NPS Core TASK-001

## Python 3.11+ and src-layout setup using `uv sync --extra dev`

Ensure you have Python 3.11 or later installed. Set up the project layout with:

```sh
uv sync --extra dev
```

## Run tests with `uv run pytest`; run lint with `uv run ruff check .`

To run tests and linting, use:

```sh
uv run pytest
uv run ruff check .
```

## Codex is orchestration-only; production patches require a local author

All production changes must be made locally by an author.

## Every patch needs TaskContract, tests or exemption, local review and evidence

Each patch must include a TaskContract, tests, or an exemption. Local review and evidence are required before merging.

## Architecture changes require an ADR

Any architecture changes must be documented in an Architecture Decision Record (ADR).

## Before task closure run `uv run python scripts/refresh_codegraph.py` and verify `codegraph_commit == repository HEAD`

Before closing a task, refresh the code graph and ensure it matches the repository head.
