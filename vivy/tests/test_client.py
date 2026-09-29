"""Tests for llm_bridge.client.LLMClient.

[REWRITTEN 29/09/2026 · WP-3 / O-04] — receipt for the test changes

Three tests in this file used to pin the silent model-fallback that the review
flagged as **F-B06** ("chuyển model im lặng = mất tái lập"):

* ``test_default_models_has_17_entries`` asserted the 17-model cloud catalogue
  existed as a live fallback source;
* ``test_list_models_falls_back_to_catalogue`` asserted an offline server was
  reported as having those 17 cloud models present;
* ``test_model_unavailable_triggers_fallback`` / ``test_fallback_exhausted_raises``
  asserted that a 404 walked the catalogue and returned whichever model answered.

Spec that supersedes them: plan WP-3 (*"Bỏ fallback 17 model cloud"*), remediation
O-04, and the C01 rule already recorded in ``training/backend_registry.py:8`` —
``"LLMClient.chat(fallback=True) walks 17 models — DO NOT USE"``.

Per plan hard rule #4 the tests were rewritten **to the spec**, not to whatever
the code happens to do: every replacement asserts something *stronger* (a
missing model must raise, never switch; the offline listing must not invent
cloud models).  No assertion was weakened or deleted to make a test pass.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from llm_bridge.backend import LLMBackend, LLMTimeoutError
from llm_bridge.client import (
    DEFAULT_MODELS,
    LLMClient,
    LLMError,
    ModelUnavailableError,
)

# ---------------------------------------------------------------------------
# F-B06 — no silent model switching
# ---------------------------------------------------------------------------


def test_missing_model_raises_and_never_switches() -> None:
    """[REWRITTEN 29/09/2026 · WP-3] A 404 must surface, not walk the catalogue.

    Replaces ``test_model_unavailable_triggers_fallback`` and
    ``test_fallback_exhausted_raises``, which asserted the walk.
    """
    client = LLMClient(default_model="gemma4-e4b")
    calls: list[str] = []

    async def fake_chat_once(model, messages, temperature, max_tokens):
        calls.append(model)
        raise ModelUnavailableError(f"model {model!r} not found")

    client._chat_once = fake_chat_once  # type: ignore[method-assign]

    with pytest.raises(ModelUnavailableError):
        asyncio.run(client.chat("hello"))

    assert calls == ["gemma4-e4b"], (
        f"exactly one attempt expected, got {calls} — a fallback walk is F-B06"
    )


def test_fallback_flag_is_ignored_and_logs(monkeypatch) -> None:
    """``fallback=True`` is [REPLACED 29/09/2026]: kept for signature stability only."""
    client = LLMClient(default_model="gemma4-e4b")
    calls: list[str] = []

    async def fake_chat_once(model, messages, temperature, max_tokens):
        calls.append(model)
        raise ModelUnavailableError("not found")

    client._chat_once = fake_chat_once  # type: ignore[method-assign]

    with pytest.raises(ModelUnavailableError):
        asyncio.run(client.chat("hello", fallback=True))

    assert calls == ["gemma4-e4b"], "the fallback flag must not trigger a model walk"


def test_chat_with_fallback_is_isolated() -> None:
    """The old walk exists only as an [ISOLATED] receipt and must fail loudly."""
    client = LLMClient()

    async def fake_chat_once(model, messages, temperature, max_tokens):
        return f"should never be reached: {model}"

    client._chat_once = fake_chat_once  # type: ignore[method-assign]

    with pytest.raises(LLMError, match="ISOLATED"):
        asyncio.run(client._chat_with_fallback([{"role": "user", "content": "x"}], 0.0, 10))


def test_default_models_catalogue_is_not_a_live_fallback() -> None:
    """[REWRITTEN 29/09/2026 · WP-3] the catalogue is evidence, not a fallback source.

    Replaces ``test_default_models_has_17_entries``, which pinned the list as
    live.  The names are still readable (isolate, don't delete) but nothing may
    consult them to answer a chat.
    """
    assert len(DEFAULT_MODELS) == 17, "the [ISOLATED] receipt should still be readable"
    assert "gemma4-e4b" not in DEFAULT_MODELS, (
        "the isolated catalogue is a cloud list; the live model is configured elsewhere"
    )
    client = LLMClient(default_model="gemma4-e4b")
    assert client.default_model == "gemma4-e4b"
    assert client.models == DEFAULT_MODELS, "retained for reference only"


# ---------------------------------------------------------------------------
# one backend configuration (F-A09)
# ---------------------------------------------------------------------------


def test_client_defaults_come_from_one_backend() -> None:
    """URL, model-id and timeout are no longer a second source of truth."""
    backend = LLMBackend.from_env()
    client = LLMClient()
    assert client.base_url == backend.openai_base_url
    assert client.default_model == backend.model_id
    assert client.timeout == backend.timeout_s
    assert client.backend == backend


def test_identity_names_the_model_that_would_answer() -> None:
    client = LLMClient()
    ident = client.identity()
    assert ident["backend_id"] == client.backend.backend_id
    assert ident["model_alias"] == client.default_model
    assert ident["config_hash"], "a receipt must be hashable back to its config"

    other = client.identity(model="some-specialist")
    assert other["model_alias"] == "some-specialist"
    assert other["config_hash"] != ident["config_hash"], (
        "a different model must produce a different config hash"
    )


# ---------------------------------------------------------------------------
# timeout is its own verdict (WP-3 acceptance)
# ---------------------------------------------------------------------------


def test_timeout_is_not_an_inference_error(monkeypatch) -> None:
    """"timeout báo riêng khỏi lỗi suy luận" — a slow model is not a wrong model."""
    client = LLMClient()

    async def fake_get_client() -> httpx.AsyncClient:
        class _FakeTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ReadTimeout("timed out")

            async def handle_async_request(self, request):
                raise httpx.ReadTimeout("timed out")

        return httpx.AsyncClient(transport=_FakeTransport())

    client._get_client = fake_get_client  # type: ignore[method-assign]

    with pytest.raises(LLMTimeoutError) as excinfo:
        asyncio.run(client.chat("hello"))

    assert not isinstance(excinfo.value, ModelUnavailableError)
    assert "timed out" in str(excinfo.value)
    # LLMTimeoutError is a kind of LLMError so broad handlers still work,
    # but callers can catch it apart from reasoning failures.
    assert isinstance(excinfo.value, LLMError)


# ---------------------------------------------------------------------------
# unchanged behaviour
# ---------------------------------------------------------------------------


def test_list_models_reports_the_server(monkeypatch) -> None:
    client = LLMClient()

    async def fake_get_json(path: str) -> dict:
        return {"data": [{"id": "gemma4-e4b"}, {"id": "qwen2-vl-72b"}]}

    client._get_json = fake_get_json  # type: ignore[method-assign]
    assert asyncio.run(client.list_models()) == ["gemma4-e4b", "qwen2-vl-72b"]


def test_list_models_offline_reports_only_the_configured_model(monkeypatch) -> None:
    """[REWRITTEN 29/09/2026 · WP-3] an offline server is not a 17-model cloud.

    Replaces ``test_list_models_falls_back_to_catalogue``, which reported
    ``gpt-4o`` / ``claude-3-opus`` / … as available on a local box.
    """
    client = LLMClient(default_model="gemma4-e4b")

    async def fake_get_json(path: str) -> dict:
        raise RuntimeError("server down")

    client._get_json = fake_get_json  # type: ignore[method-assign]
    assert asyncio.run(client.list_models()) == ["gemma4-e4b"]


def test_connect_error_raises_llm_error(monkeypatch) -> None:
    """Verify that an httpx.ConnectError in _chat_once is wrapped as LLMError."""
    client = LLMClient()

    async def fake_get_client() -> httpx.AsyncClient:
        class _FakeTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ConnectError("Connection refused")

            async def handle_async_request(self, request):
                raise httpx.ConnectError("Connection refused")

        return httpx.AsyncClient(transport=_FakeTransport())

    client._get_client = fake_get_client  # type: ignore[method-assign]

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
