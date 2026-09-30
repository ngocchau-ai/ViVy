# Changelog

All notable changes to the Unitary Reasoner project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-08-03

### Added

- **Phase 0 quality gates** — ruff lint, mypy type checking, `make check` gate.
- **ADR documentation** — 7 architecture decision records under `docs/adr/`.
- **Dev environment scripts** — `setup.sh` (git-bash), `setup.ps1` (PowerShell).
- **`.gitignore`** — standard Python + IDE exclusions.
- **`Makefile`** — `check`, `lint`, `type`, `test`, `bench`, `demo` targets.
- **`[project.optional-dependencies] dev`** — ruff, mypy dev extras.

### Changed

- **`UnitaryEvolution.evolve()`** — `schedule` parameter now optional (defaults to empty schedule). Backward-compatible.
- **Orchestrator `_make_evolution()`** — now correctly instantiates the real `UnitaryEvolution` instead of falling back to stub.
- **`Stream` TypedDict constructor** — uses `**kwargs` for mypy compliance.
- **Various type annotations** — fixed 17 mypy errors across 5 modules.

### Fixed

- **`svd_streams.py`** — removed duplicate `dominant_stream` definition.
- **`filter.py`** — `evaluate()` return type now correctly cast to `list[Stream]`.
- **`conflict.py`** — `state_A` access uses direct indexing instead of `.get()`.
- **`state.py`** — `is_normalized` returns `bool` instead of `numpy.bool_`.
- **`memory/query.py`** — `analogical_reasoning` uses `Iterable` instead of `Sequence` for candidates.
- **`memory/associative.py`** — early-return guard on `self._W is None` for mypy narrowing.
- **`orchestrator/engine.py`** — removed unused `type: ignore` comments; added `assert` guards for encoder/decoder.

## [0.1.0] — 2026-08-02

### Added

- Initial scaffold: 33 modules, ~5,300 LOC.
- Core: `MPS`, `QuantumState`, `UnitaryEvolution`, SVD thought stream extraction.
- Memory: `QuantumAssociativeMemory` with Hebbian-style storage and polar-decomposition retrieval.
- Funnel: `FilterFunnel` with confidence scoring, conflict detection, control signals.
- LLM bridge: OpenAI-compatible client with `Encoder`/`Decoder`.
- Orchestrator: `Orchestrator` engine with encode → evolve → evaluate → decode pipeline.
- E2E syllogism benchmark (3/3 passed).
- 242 unit tests (all passing).
- Gemma 4EB integration via Ollama (beta 1).