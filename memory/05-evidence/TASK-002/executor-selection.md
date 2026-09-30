# TASK-002 Executor Selection Evidence

## Decision

Use direct MiMo API sessions for coder, tester, and reviewer roles.

## Authorization and routing

- The user explicitly authorized the prepaid MiMo API, requested that the
  local model be unloaded, and prioritized preserving Codex capacity for
  orchestration.
- Hermes MCP was the preferred transport, but no Hermes MCP server or callable
  Hermes tool was exposed in the active runtime.
- The bounded fallback was the official MiMo chat-completions API.
- Model: `mimo-v2.5-pro`.
- Deep thinking: disabled after verifying the official parameter, so responses
  contain bounded final artifacts instead of reasoning-only output.
- API credentials were read from the environment and were never written into
  repository files or evidence.

## Local device outcome

The initial Ollama `qwen2.5-coder:7b` process saturated the device and did not
complete the bounded architecture response. Its runner was stopped and the
model was unloaded before MiMo implementation continued.

## Role isolation

- `mimo_coder`: production modules and hardening patches.
- `mimo_tester`: unit/integration tests and test-harness corrections.
- `mimo_reviewer`: read-only initial review and fresh final re-review.

The three roles use the same model family, so independence is low. Separate
sessions, adversarial prompts, schema validation, machine tests, Ruff,
compileall, performance measurement, and Codex contract checks mitigate this
limitation.

## Usage and rejected outputs

The runner captured 37 successful usage records totaling 366,971 prompt
tokens and 98,106 completion tokens (465,077 total). This includes design
iterations, intentionally rejected/truncated drafts, corrections, tests, and
two review passes. Rejected or truncated production/test drafts were not
applied.
