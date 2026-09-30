# TASK-003 Executor Selection Evidence

## Decision

Use direct MiMo API sessions for architect, coder, tester, and reviewer roles.

## Authorization and routing

- The user explicitly authorized the prepaid MiMo API, requested reduced local
  device load, and prioritized preserving Codex capacity for orchestration.
- Hermes MCP was preferred but no Hermes server or callable tool was exposed.
- The bounded fallback was the MiMo chat-completions API.
- Model: `mimo-v2.5-pro`; thinking disabled.
- Credentials were read from the environment and were never written to the
  repository or evidence.
- The local Ollama model remained unloaded.

## Role isolation

- `mimo_architect`: ADR-0006 and public contract.
- `mimo_coder`: production value objects, plan validation, state engine, and
  tuple-strict hardening.
- `mimo_tester`: four independent unit/integration test artifacts and repairs.
- `mimo_reviewer`: read-only production review, scoped test reviews, and fresh
  remediation verification.

Model-family independence is low. Separate API sessions, adversarial tests,
schema validation, executable replay, exact digest checks, full regression,
and fresh review mitigate this limitation.

## Usage

The runner captured 21 successful TASK-003 usage records totaling 180,676
prompt tokens and 39,712 completion tokens (220,388 total). Truncated,
fabricated-context, or otherwise invalid drafts were rejected and not applied.
