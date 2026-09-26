# ADR-007: LLM Backend — OpenAI-Compatible, Env-Config

**Status:** Accepted (implemented in llm_bridge/client.py)

## Context
The LLM bridge must talk to multiple backends (cloud APIs, local Ollama, local
llama-server) without code changes. The interface must be switchable at runtime.

## Decision
- Use the **OpenAI-compatible HTTP API** (`/v1/chat/completions`) as the
  universal contract
- Configuration via environment variables:
  - `UNITARY_API_BASE` — base URL (e.g. `http://localhost:11434/v1`)
  - `UNITARY_API_KEY` — bearer token (empty for local)
  - `UNITARY_DEFAULT_MODEL` — model name
  - `UNITARY_MODEL_LIST` — JSON array of available models
- **Beta 1 default:** Ollama at `http://localhost:11434/v1`, model `gemma4:e4b`
- `.env` is loaded by `demo.py` (simple KEY=VALUE parser, no external dep)

## Consequences
- Switching backends = changing env vars, no code edits
- Local models (Ollama, llama-server) work with empty API key
- The client auto-discovers models via `/v1/models` when `MODEL_LIST` is unset