# Python 3.11 Foundation Runtime

## Status: Accepted

## Context: Foundation Freeze must select a prototype language; architecture already proposes pyproject/src layout; deterministic AST tooling and JSON schema work fit the standard library ecosystem.

## Decision: Python 3.11+ for the deterministic prototype and codegraph tool; src layout; zero production dependencies in Task 001; pytest/jsonschema/ruff are development-only.

## Consequences: typed standard-library code, JSON schemas remain language-neutral, future runtime-language change needs a new ADR, local coding boundary is unchanged.
