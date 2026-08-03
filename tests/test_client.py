"""Tests for llm_bridge.client.LLMClient."""

from __future__ import annotations

import pytest

from llm_bridge.client import (
    DEFAULT_MODELS,
    LLMClient,
    LLMError,
    ModelUnavailableError,
)


def test_default_models_has_17_entries() -> None:
    assert len(DEFAULT_MODELS) == 17


def test_list_models_falls_back_to_catalogue(monkeypatch) -> None:
    client = LLMClient()

    async def fake_get_json(path: str) -> dict:
        raise RuntimeError("server down")

    monkeypatch.setattr(client, "_get_json", fake_get_json)
    # run directly via asyncio
    import asyncio

    result = asyncio.run(client.list_models())
    assert result == DEFAULT_MODELS


def test_model_unavailable_triggers_fallback(monkeypatch) -> None:
    """When the primary model 404s, fallback tries the next model."""
    client = LLMClient(default_model="gpt-4o")
    calls: list[str] = []

    async def fake_chat_once(model, messages, temperature, max_tokens):
        calls.append(model)
        if model == "gpt-4o":
            raise ModelUnavailableError("not found")
        return f"response from {model}"

    monkeypatch.setattr(client, "_chat_once", fake_chat_once)
    import asyncio

    result = asyncio.run(client.chat("hello"))
    assert calls[0] == "gpt-4o"
    assert calls[1] == "gpt-4o-mini"  # first fallback in catalogue
    assert result == "response from gpt-4o-mini"


def test_fallback_exhausted_raises(monkeypatch) -> None:
    client = LLMClient(default_model="gpt-4o")

    async def fake_chat_once(model, messages, temperature, max_tokens):
        raise ModelUnavailableError("not found")

    monkeypatch.setattr(client, "_chat_once", fake_chat_once)
    import asyncio

    with pytest.raises(LLMError):
        asyncio.run(client.chat("hello"))


def test_connect_error_raises_llm_error(monkeypatch) -> None:
    """Verify that an httpx.ConnectError in _chat_once is wrapped as LLMError."""
    import httpx

    client = LLMClient()

    # Mock _get_client to return a client whose post raises ConnectError.
    async def fake_get_client() -> httpx.AsyncClient:
        class _FakeTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ConnectError("Connection refused")

            async def handle_async_request(self, request):
                raise httpx.ConnectError("Connection refused")

        return httpx.AsyncClient(transport=_FakeTransport())

    monkeypatch.setattr(client, "_get_client", fake_get_client)
    import asyncio

    with pytest.raises(LLMError, match="Cannot connect"):
        asyncio.run(client.chat("hello"))


def test_build_messages() -> None:
    from llm_bridge.client import _build_messages

    with_sys = _build_messages("hi", "be helpful")
    assert with_sys == [
        {"role": "system", "content": "be helpful"},
        {"role": "user", "content": "hi"},
    ]
    without_sys = _build_messages("hi", None)
    assert without_sys == [{"role": "user", "content": "hi"}]
