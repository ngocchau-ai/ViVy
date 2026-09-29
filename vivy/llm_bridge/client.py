"""
LLM Client — OpenAI-compatible HTTPX async wrapper.

Provides a unified interface to a single configured backend via an
OpenAI-compatible API endpoint.  Configuration lives in
``llm_bridge.backend.LLMBackend`` — one URL, one model-id, one timeout.

[REPLACED 29/09/2026 · WP-3 / O-04] this module used to advertise *"17 available
models"* and silently walk that catalogue when the primary model 404'd
(``fallback=True``).  That filed another model's answer under the requested
identity (F-B06 — mất tái lập) and is now unreachable: a missing model raises
``ModelUnavailableError``.  The old catalogue is kept below as ``[ISOLATED]``
evidence, not as a live path.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from llm_bridge.backend import (
    LLMBackend,
    LLMError,
    LLMTimeoutError,
    ModelUnavailableError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default model catalogue  (17 models)
# ---------------------------------------------------------------------------
# [ISOLATED 29/09/2026 · WP-3 / O-04 / F-B06]
# These were representative model names for a cloud OpenAI-compatible provider
# and were used as a SILENT FALLBACK when the requested model 404'd.  Switching
# models behind the caller's back destroys reproducibility, so the catalogue is
# no longer consulted by any live path.  Kept only as the receipt of what used
# to happen.  Override via the UNITARY_MODEL_LIST env var (JSON array of strings)
# is likewise [ISOLATED] — it no longer feeds a fallback.
DEFAULT_MODELS: list[str] = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
    "claude-3.5-sonnet",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "llama-3.1-405b",
    "llama-3.1-70b",
    "llama-3.1-8b",
    "mixtral-8x22b",
    "deepseek-v3",
]

# ---------------------------------------------------------------------------
# Exceptions — re-exported from llm_bridge.backend (single hierarchy)
# ---------------------------------------------------------------------------
# LLMError / ModelUnavailableError / LLMTimeoutError are defined next to
# LLMBackend so there is one error family for one backend.  The names stay
# importable from here for existing callers (tests, experiments, engine).

__all__ = [
    "DEFAULT_MODELS",
    "LLMBackend",
    "LLMClient",
    "LLMError",
    "LLMTimeoutError",
    "ModelUnavailableError",
]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _load_model_list() -> list[str]:
    """[ISOLATED 29/09/2026] load the old cloud catalogue from env.

    Kept so ``LLMClient.models`` still describes what ``DEFAULT_MODELS`` held.
    No live path consults it for a chat fallback any more (F-B06).
    """
    raw = os.environ.get("UNITARY_MODEL_LIST")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return list(DEFAULT_MODELS)


def _default_backend() -> LLMBackend:
    return LLMBackend.from_env()


@dataclass
class LLMClient:
    """Async HTTPX client for an OpenAI-compatible chat API.

    Backed by a single ``LLMBackend`` (WP-3): one URL, one model-id, one
    timeout.  There is no model fallback — see the module docstring.

    Parameters
    ----------
    base_url:
        API root URL including the ``/v1`` suffix.  Defaults to the configured
        ``LLMBackend.openai_base_url`` (``VIVY_LLAMA_URL``).
    api_key:
        API key.  Defaults to ``VIVY_API_KEY`` (empty for a local server).
    default_model:
        Model name to use when none is specified.  Defaults to the configured
        ``LLMBackend.model_id`` (``VIVY_MODEL``).
    timeout:
        HTTP request timeout in seconds.  Defaults to ``VIVY_LLM_TIMEOUT_S``.
    backend:
        Optional explicit ``LLMBackend``.  When given it supplies the defaults
        above and is recorded on every call via :meth:`identity`.
    models:
        [ISOLATED 29/09/2026] the old 17-model cloud catalogue.  Retained for
        reference only; it is never used as a chat fallback.
    """

    base_url: str = ""
    api_key: str = field(default="")
    default_model: str = ""
    timeout: float = 0.0
    backend: LLMBackend = field(default_factory=_default_backend)
    models: list[str] = field(default_factory=_load_model_list)

    def __post_init__(self) -> None:
        backend = self.backend
        if not self.base_url:
            self.base_url = backend.openai_base_url
        if not self.default_model:
            self.default_model = backend.model_id
        if not self.timeout:
            self.timeout = backend.timeout_s
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Identity — every call can say who answered (C01 §2.1)
    # ------------------------------------------------------------------

    def identity(self, model: str | None = None) -> dict[str, Any]:
        """Receipt shard for the model that would serve the next call."""
        if model is None or model == self.backend.model_id:
            return self.backend.identity()
        return self.backend.with_model(model).identity()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        fallback: bool = False,
    ) -> str:
        """Send a chat prompt and return the model's text response.

        Parameters
        ----------
        prompt:
            User message content.
        model:
            Model to use.  Falls back to ``self.default_model`` when
            ``None``.  A model that is *unavailable* raises — it is never
            silently swapped for another one (F-B06).
        system_prompt:
            Optional system-level instruction.
        temperature:
            Sampling temperature (0 = deterministic).
        max_tokens:
            Maximum tokens in the response.
        fallback:
            [REPLACED 29/09/2026 · WP-3] **ignored.**  It used to walk the
            17-model cloud catalogue on a 404.  Passing ``True`` logs a
            deprecation warning and still does not switch models, so callers
            keep their signature while the hazard stays closed.
        """
        if fallback:
            logger.warning(
                "LLMClient.chat(fallback=True) is [ISOLATED 29/09/2026]: model "
                "fallback was removed (F-B06).  Raising ModelUnavailableError "
                "instead of switching models."
            )
        model = model or self.default_model
        messages = _build_messages(prompt, system_prompt)
        return await self._chat_once(model, messages, temperature, max_tokens)

    async def list_models(self) -> list[str]:
        """Return the list of available model names.

        First tries the server's ``/v1/models`` endpoint.  When the server is
        unreachable it reports the one configured model rather than the old
        17-entry cloud catalogue — claiming cloud models are present on a local
        server is a false statement (WP-3).
        """
        try:
            data = await self._get_json("models")
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            logger.warning(
                "Could not fetch model list from server; reporting the configured model only"
            )
            return [self.default_model]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _chat_once(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = await client.post(
                "chat/completions",
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            # WP-3 acceptance: "timeout báo riêng khỏi lỗi suy luận".
            raise LLMTimeoutError(
                f"Request timed out after {self.timeout}s "
                f"(model={model}, url={self.base_url})"
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMError(
                f"Cannot connect to {self.base_url} — is the server running?"
            ) from exc

        if resp.status_code == 404:
            raise ModelUnavailableError(
                f"Model '{model}' not found on server"
            )
        if resp.status_code != 200:
            detail = resp.text[:500]
            raise LLMError(
                f"API returned HTTP {resp.status_code}: {detail}"
            )

        body = resp.json()
        choices = body.get("choices", [])
        if not choices:
            raise LLMError("API response has no choices")
        return choices[0]["message"]["content"].strip()

    async def _chat_with_fallback(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """[ISOLATED 29/09/2026 · WP-3 / O-04 / F-B06]

        This used to walk the 17-model cloud catalogue and return whichever
        model answered first, filing that answer under the originally requested
        identity.  Silent model switching destroys reproducibility, so the walk
        is closed.  The method remains so the old behaviour is still readable
        and so any caller that reaches it fails loudly rather than quietly
        returning someone else's answer.
        """
        raise LLMError(
            "ISOLATED 29/09/2026 (F-B06): LLMClient model fallback was removed. "
            "The requested model was unavailable; no other model was tried. "
            "Change VIVY_MODEL / LLMBackend.model_id explicitly if that is intended."
        )

    async def _get_json(self, path: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(path, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTPX client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> LLMClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _build_messages(
    prompt: str, system_prompt: str | None
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages
