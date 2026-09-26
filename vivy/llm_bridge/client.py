"""
LLM Client — OpenAI-compatible HTTPX async wrapper.

Provides a unified interface to 17 available models via an OpenAI-compatible
API endpoint.  Supports streaming and non-streaming chat completions, model
listing, and automatic fallback when a model is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default model catalogue  (17 models)
# ---------------------------------------------------------------------------
# These are representative model names for an OpenAI-compatible provider.
# Override via the UNITARY_MODEL_LIST env var (JSON array of strings).
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
# Exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Raised when the LLM API returns an error or is unreachable."""


class ModelUnavailableError(LLMError):
    """Raised when the requested model is not available on the server."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _load_model_list() -> list[str]:
    """Load model list from env var or fall back to DEFAULT_MODELS."""
    raw = os.environ.get("UNITARY_MODEL_LIST")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return list(DEFAULT_MODELS)


@dataclass
class LLMClient:
    """Async HTTPX client for an OpenAI-compatible chat API.

    Parameters
    ----------
    base_url:
        API root URL.  Defaults to the ``UNITARY_API_BASE`` env var or
        ``http://localhost:8000/v1``.
    api_key:
        API key.  Defaults to the ``UNITARY_API_KEY`` env var.
    default_model:
        Model name to use when none is specified.  Defaults to the
        ``UNITARY_DEFAULT_MODEL`` env var or ``"gpt-4o-mini"``.
    timeout:
        HTTP request timeout in seconds.
    models:
        Optional override of the model catalogue.  If not provided, reads
        from the ``UNITARY_MODEL_LIST`` env var (JSON) or falls back to
        ``DEFAULT_MODELS``.
    """

    base_url: str = field(
        default_factory=lambda: os.environ.get(
            "UNITARY_API_BASE", "http://localhost:8000/v1"
        )
    )
    api_key: str = field(
        default_factory=lambda: os.environ.get("UNITARY_API_KEY", "")
    )
    default_model: str = field(
        default_factory=lambda: os.environ.get(
            "UNITARY_DEFAULT_MODEL", "gpt-4o-mini"
        )
    )
    timeout: float = 60.0
    models: list[str] = field(default_factory=_load_model_list)

    def __post_init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

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
        fallback: bool = True,
    ) -> str:
        """Send a chat prompt and return the model's text response.

        Parameters
        ----------
        prompt:
            User message content.
        model:
            Model to use.  Falls back to ``self.default_model`` when
            ``None``.
        system_prompt:
            Optional system-level instruction.
        temperature:
            Sampling temperature (0 = deterministic).
        max_tokens:
            Maximum tokens in the response.
        fallback:
            If ``True``, try other models from the catalogue when the
            primary model returns a 404 / model-not-found error.
        """
        model = model or self.default_model
        messages = _build_messages(prompt, system_prompt)

        try:
            return await self._chat_once(model, messages, temperature, max_tokens)
        except ModelUnavailableError:
            if not fallback:
                raise
            return await self._chat_with_fallback(messages, temperature, max_tokens)

    async def list_models(self) -> list[str]:
        """Return the list of available model names.

        First tries the server's ``/v1/models`` endpoint; falls back to
        the local catalogue.
        """
        try:
            data = await self._get_json("models")
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            logger.warning("Could not fetch model list from server; using local catalogue")
            return list(self.models)

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
            raise LLMError(f"Request timed out after {self.timeout}s") from exc
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
        for model in self.models:
            if model == self.default_model:
                continue  # already tried
            try:
                return await self._chat_once(model, messages, temperature, max_tokens)
            except ModelUnavailableError:
                continue
        raise LLMError("All models exhausted — none available on server")

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
