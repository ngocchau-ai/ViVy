# TASK-001 Executor Selection Evidence

## Decision

Escalate the local coding profile to `qwen2.5-coder:7b`.

## Provenance

- Runtime: Ollama on localhost.
- Initial installed model: `qwen2.5:0.5b`, model ID `a8b0c5157701`.
- First escalation: `qwen2.5-coder:3b`, model ID `f72c60cabf62`.
- Selected implementation profile: `qwen2.5-coder:7b`, 7.6B parameters,
  32,768-token context, Q4_K_M quantization, after installation and metadata
  verification.

## Rejected attempts

### qwen2.5:0.5b

1. Multi-file unified-diff request returned two placeholder files, one outside
   the requested path set, and omitted all required artifacts.
2. Focused `pyproject.toml` requests produced invalid TOML, mixed Poetry and
   setuptools, and repeated invalid tables after explicit revision feedback.

No production output from these attempts was applied.

### qwen2.5-coder:3b

1. Initial `pyproject.toml` mixed Poetry and setuptools and violated PEP 621.
2. The revision produced a correct semantic JSON configuration. The model then
   serialized the optional-dependencies table incorrectly; after a focused
   correction, the accepted sections were mechanically combined into
   `pyproject.toml`.
3. Two package-skeleton attempts produced invalid Python, paths outside the
   requested set, duplicate keys and placeholder implementation.

Only the reviewed `pyproject.toml` configuration was applied. No skeleton file
from the rejected attempts was applied.

## Independence limitation

Coder, tester and reviewer roles will share the selected local backbone.
Separate sessions and executable tests mitigate role leakage, but the evidence
must not be treated as fully independent under INV-08.
