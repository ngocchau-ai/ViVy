"""Tests for llm_bridge.backend.LLMBackend — one configuration, one identity.

WP-3 / O-04 (F-A09, F-B06).  Before this module the same model was configured
in three places (``LLMClient`` + ``LlamaCppConfig`` + ``training.backend_registry``)
and answered through a silent 17-model fallback.
"""

from __future__ import annotations

import pytest

from llm_bridge.backend import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ID,
    LLMBackend,
    LLMError,
    LLMTimeoutError,
    ModelUnavailableError,
    decode_backend_identity,
    identity_from_env,
)


def test_defaults_are_one_real_local_backend() -> None:
    b = LLMBackend()
    assert b.base_url == DEFAULT_BASE_URL
    assert b.model_id == DEFAULT_MODEL_ID
    assert b.backend_id == "llama-server"
    assert b.timeout_s > 0 and b.num_ctx > 0


def test_from_env_reads_the_documented_knobs(monkeypatch) -> None:
    monkeypatch.setenv("VIVY_LLAMA_URL", "http://10.0.0.5:9999/")
    monkeypatch.setenv("VIVY_MODEL", "gemma4-e4b-instruct")
    monkeypatch.setenv("VIVY_LLM_TIMEOUT_S", "12.5")
    monkeypatch.setenv("VIVY_LLM_NUM_CTX", "8192")
    monkeypatch.setenv("VIVY_BACKEND_ID", "cautreo-server")
    monkeypatch.setenv("VIVY_API_KEY", "secret")

    b = LLMBackend.from_env()
    assert b.base_url == "http://10.0.0.5:9999", "trailing slash must not leak into URLs"
    assert b.model_id == "gemma4-e4b-instruct"
    assert b.timeout_s == 12.5
    assert b.num_ctx == 8192
    assert b.backend_id == "cautreo-server"
    assert b.api_key == "secret"


def test_urls_are_derived_not_duplicated() -> None:
    b = LLMBackend(base_url="http://127.0.0.1:8080")
    assert b.openai_base_url == "http://127.0.0.1:8080/v1"
    assert b.chat_completions_url == "http://127.0.0.1:8080/v1/chat/completions"


def test_with_model_is_explicit_and_never_silent() -> None:
    a = LLMBackend(model_id="gemma4-e4b")
    c = a.with_model("qwen2-vl-72b")
    assert a.model_id == "gemma4-e4b", "the original must not mutate"
    assert c.model_id == "qwen2-vl-72b"
    assert c.base_url == a.base_url and c.timeout_s == a.timeout_s


def test_config_hash_is_stable_and_sensitive() -> None:
    a = LLMBackend()
    assert a.config_hash() == LLMBackend().config_hash(), "same config → same hash"
    assert a.config_hash() != a.with_model("other").config_hash()
    assert a.config_hash() != LLMBackend(temperature=0.9).config_hash()
    assert len(a.config_hash()) == 64


def test_identity_matches_the_training_receipt_shape() -> None:
    """Same keys as ``training.backend_baseline.BackendIdentity.to_dict()``."""
    ident = LLMBackend().identity()
    assert set(ident) == {
        "backend_id", "model_alias", "model_hash", "config_hash", "base_url", "extra",
    }
    assert ident["backend_id"] == "llama-server"
    assert ident["model_alias"] == DEFAULT_MODEL_ID
    assert ident["model_hash"] == "", "unknown until a live probe fills it"
    assert ident["config_hash"]
    assert ident["extra"]["contract"] == "openai-compatible:/v1/chat/completions"


def test_identity_from_env_and_decode_roundtrip() -> None:
    ident = identity_from_env()
    decoded = decode_backend_identity(ident)
    assert decoded == ident

    sparse = decode_backend_identity({"backend_id": "x"})
    assert sparse["model_alias"] == ""
    assert sparse["extra"] == {}, "never invent fields that were not recorded"


def test_error_hierarchy_separates_timeout_from_unavailability() -> None:
    """WP-3 acceptance: "timeout báo riêng khỏi lỗi suy luận"."""
    assert issubclass(LLMTimeoutError, LLMError)
    assert issubclass(ModelUnavailableError, LLMError)
    assert not issubclass(LLMTimeoutError, ModelUnavailableError)
    assert not issubclass(ModelUnavailableError, LLMTimeoutError)

    with pytest.raises(LLMTimeoutError):
        raise LLMTimeoutError("slow")
