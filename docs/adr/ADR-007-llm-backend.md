# ADR-007: LLM Backend — one OpenAI-compatible contract, one configuration

**Status:** Accepted · **revised 29/09/2026** (Claude Code, WP-3 / O-04)
**Supersedes:** the multi-model fallback decision below (kept as `[ISOLATED]`)
**Related:** `vivy/llm_bridge/backend.py`, `vivy/llm_bridge/client.py`,
`vivy/integration/llama_cpp_bridge.py`, `docs/public/quickstart.md`,
`docs/public/architecture.md`, `training/backend_registry.py`

---

## Context

The LLM bridge must talk to a model server without code changes when the server
changes. Three findings forced this revision:

* **F-A09** — the same model was configured in three places with three env-var
  sets (`UNITARY_*` in `llm_bridge/client.py`, `VIVY_LLAMA_URL`/`VIVY_MODEL` in
  `integration/llama_cpp_bridge.py`, and again inside
  `training/backend_registry.py`). A receipt could not name one source of truth.
* **F-B06** — `LLMClient.chat(fallback=True)` silently walked a **17-model cloud
  catalogue** on a 404 and returned whichever model answered, filing that answer
  under the originally requested identity. That destroys reproducibility.
  `training/backend_registry.py:8` had already marked it `[ISOLATED]` for C01.
* **D-4 (open)** — the docs contradicted themselves: `docs/public/*` sold an
  Ollama install flow (`ollama pull`, port `11434`) while
  `docs/ARCHITECTURE_FINAL.md:28` declared independence from Ollama via the
  Cautreo C-ABI. A reader could not tell which path is real.

## Decision

1. **One backend contract:** the OpenAI-compatible HTTP API
   `/v1/chat/completions`. It is the only interface the runtime speaks.
2. **One configuration object:** `llm_bridge.backend.LLMBackend` —
   `base_url`, `model_id`, `timeout_s`, `num_ctx`, plus decoding knobs.
   `LlamaCppConfig`, `LLMClient` and the benchmark harness all build from it.
   Env knobs: `VIVY_LLAMA_URL`, `VIVY_MODEL`, `VIVY_LLM_TIMEOUT_S`,
   `VIVY_LLM_NUM_CTX`, `VIVY_BACKEND_ID`, `VIVY_API_KEY`. The older `UNITARY_*`
   names are `[ISOLATED]`.
3. **One active backend during development:** llama-server / Ollama serving
   **`gemma4:e4b`** at `http://127.0.0.1:8080`. This is what the code defaults to
   and what the launchers start.
4. **After the D-4 parity measurement**, the same contract is served by
   `cautreo-server.exe` (already an OpenAI-compatible binary on port 8080).
   Switching is a config change, not a code change. Until parity is measured,
   **Ollama/llama-server is the reference** and Cautreo-native remains
   `role="isolated-unverified"` in `training/backend_registry.py`.
5. **No silent model fallback.** A missing model raises
   `ModelUnavailableError`. Changing models is explicit
   (`LLMBackend.with_model(...)`).
6. **Timeout is its own verdict.** `LLMTimeoutError` is raised separately from
   inference failures so latency budgets (T11) stay measurable. A slow model is
   not a wrong model.
7. **Every receipt carries identity.** `ChatResponse.backend_id` / `model_id`
   and `LLMBackend.identity()` name what actually answered. Shape matches
   `training.backend_baseline.BackendIdentity` so product and training receipts
   diff cleanly.

## Consequences

* Switching servers = changing `VIVY_LLAMA_URL` / `VIVY_MODEL`, no code edits —
  unchanged from the original decision.
* Local models work with an empty `VIVY_API_KEY`.
* A run is reproducible: same input + same `config_hash` ⇒ same backend. The
  17-model cloud catalogue can no longer answer a request.
* Latency problems surface as `LLMTimeoutError` / `delegate_kind="timeout"`
  instead of hiding inside a generic error.
* `docs/public/quickstart.md` and `docs/public/architecture.md` now describe the
  same path as this ADR and as `ARCHITECTURE_FINAL.md`.

## Open question (D-4)

Whether Cautreo-native reaches semantic parity with the reference backend is
**not decided here**. It is measured, not assumed. When the parity receipt
exists, a follow-up ADR records the switch; until then the reference stays
Ollama/llama-server.

---

## `[ISOLATED 29/09/2026]` — original decision (kept for the record)

> **Status (was):** Accepted (implemented in llm_bridge/client.py)
>
> ## Context
> The LLM bridge must talk to multiple backends (cloud APIs, local Ollama, local
> llama-server) without code changes. The interface must be switchable at runtime.
>
> ## Decision
> - Use the **OpenAI-compatible HTTP API** (`/v1/chat/completions`) as the
>   universal contract
> - Configuration via environment variables:
>   - `UNITARY_API_BASE` — base URL (e.g. `http://localhost:11434/v1`)
>   - `UNITARY_API_KEY` — bearer token (empty for local)
>   - `UNITARY_DEFAULT_MODEL` — model name
>   - `UNITARY_MODEL_LIST` — JSON array of available models
> - **Beta 1 default:** Ollama at `http://localhost:11434/v1`, model `gemma4:e4b`
> - `.env` is loaded by `demo.py` (simple KEY=VALUE parser, no external dep)
>
> ## Consequences
> - Switching backends = changing env vars, no code edits
> - Local models (Ollama, llama-server) work with empty API key
> - The client auto-discovers models via `/v1/models` when `MODEL_LIST` is unset

### Why the above is isolated, point by point

| Original claim | Status | Why |
|:--|:--|:--|
| "multiple backends (cloud APIs …)" | `[REPLACED]` | The product has one local backend. Cloud APIs were never wired to a product path. |
| `UNITARY_API_BASE` / `UNITARY_API_KEY` / `UNITARY_DEFAULT_MODEL` | `[ISOLATED]` | Second source of truth (F-A09). Now `VIVY_*` via `LLMBackend`. |
| `UNITARY_MODEL_LIST` (JSON array) | `[ISOLATED]` | Fed the silent fallback (F-B06). |
| "Beta 1 default: Ollama at `localhost:11434`" | `[CORRECTED]` | Code and launchers use `127.0.0.1:8080`. `11434` is Ollama's native port; the runtime talks to the OpenAI-compatible surface on `8080`. |
| "auto-discovers models via `/v1/models`" | `[NARROWED]` | `/v1/models` is still read for *listing*. It is never used to substitute a model. |
| "`.env` is loaded by `demo.py`" | `[ISOLATED]` | Not a product path. `.env` must never be committed. |
