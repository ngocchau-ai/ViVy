"""One LLM backend definition — single source of truth for who answers.

WP-3 / O-04 · fixes F-B06, F-A09 (29/09/2026).

Before this module the same model had three separate configurations and one
silent fallback:

* ``llm_bridge.client.LLMClient`` read ``UNITARY_API_BASE`` and kept a
  **17-model cloud catalogue** (``gpt-4o``, ``claude-3-opus``, ``gemini-1.5-pro``
  …) that ``chat(fallback=True)`` walked when the primary model 404'd — filing
  another model's answer under the requested identity.  That is F-B06: silent
  model switching destroys reproducibility.
* ``integration.llama_cpp_bridge.LlamaCppConfig`` read ``VIVY_LLAMA_URL`` /
  ``VIVY_MODEL``.
* ``training.backend_registry`` read the same env vars a third time.

There is now exactly one configuration object.  A missing model raises
``ModelUnavailableError`` instead of switching; a slow model raises
``LLMTimeoutError`` instead of being filed as an inference failure.

Backend choice (ADR-007 as revised 29/09/2026, answers D-4 for now):

    one OpenAI-compatible HTTP contract at ``/v1/chat/completions``.

During development that endpoint is served by llama-server / Ollama running
``gemma4:e4b``.  After the D-4 parity measurement it becomes ``cautreo-server``.
Both speak the same contract, so switching backends does not change code — only
``VIVY_LLAMA_URL`` / ``VIVY_MODEL``, and the identity recorded on every receipt.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Errors — timeout is a distinct verdict, not a reasoning failure
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Raised when the LLM API returns an error or is unreachable."""


class ModelUnavailableError(LLMError):
    """Raised when the requested model is not available on the server.

    Never retried on another model (F-B06).  The caller decides whether to
    change ``model_id`` — the client will not do it behind their back.
    """


class LLMTimeoutError(LLMError):
    """The request exceeded ``timeout_s`` and was abandoned.

    Kept separate from ``LLMError`` on purpose (WP-3 acceptance: *"timeout báo
    riêng khỏi lỗi suy luận"*).  A slow model is not a wrong model; merging the
    two hides latency-budget problems behind reasoning errors and makes T11
    latency budgets unmeasurable.
    """


# ---------------------------------------------------------------------------
# Defaults — one backend, one set of numbers
# ---------------------------------------------------------------------------

#: OpenAI-compatible HTTP contract.  Served by llama-server / Ollama today and
#: by ``cautreo-server`` after D-4 parity; both expose ``/v1/chat/completions``.
DEFAULT_BACKEND_ID = "llama-server"
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL_ID = "gemma4-e4b"


@dataclass(frozen=True)
class LLMBackend:
    """The single LLM configuration: URL, model-id, timeout, num_ctx.

    Every component that talks to a model — ``llm_bridge.client.LLMClient``,
    ``integration.llama_cpp_bridge.LlamaCppBridge``, the orchestrator, the
    benchmark harness — builds from this object, so a receipt can always say
    which backend and which model actually answered.
    """

    backend_id: str = DEFAULT_BACKEND_ID
    base_url: str = DEFAULT_BASE_URL
    model_id: str = DEFAULT_MODEL_ID
    timeout_s: float = 180.0
    num_ctx: int = 32768
    api_key: str = ""
    temperature: float = 0.15
    top_p: float = 0.9
    max_tokens: int = 2048

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> LLMBackend:
        """Build from environment variables, falling back to the defaults.

        ======================  =========================  ==================
        Variable                Meaning                    Default
        ======================  =========================  ==================
        ``VIVY_BACKEND_ID``     backend label for receipts ``llama-server``
        ``VIVY_LLAMA_URL``      server root (no ``/v1``)   ``127.0.0.1:8080``
        ``VIVY_MODEL``          model-id served            ``gemma4-e4b``
        ``VIVY_LLM_TIMEOUT_S``  request timeout, seconds   ``180``
        ``VIVY_LLM_NUM_CTX``    context window             ``32768``
        ``VIVY_API_KEY``        bearer token (local: empty) empty
        ======================  =========================  ==================

        The ``VIVY_LLAMA_URL`` / ``VIVY_MODEL`` names are kept from
        ``LlamaCppConfig`` so existing launchers keep working — this module
        unifies the *values*, it does not rename the knobs.
        """
        return cls(
            backend_id=os.environ.get("VIVY_BACKEND_ID", DEFAULT_BACKEND_ID),
            base_url=os.environ.get("VIVY_LLAMA_URL", DEFAULT_BASE_URL).rstrip("/"),
            model_id=os.environ.get("VIVY_MODEL", DEFAULT_MODEL_ID),
            timeout_s=float(os.environ.get("VIVY_LLM_TIMEOUT_S", "180")),
            num_ctx=int(os.environ.get("VIVY_LLM_NUM_CTX", "32768")),
            api_key=os.environ.get("VIVY_API_KEY", ""),
            temperature=float(os.environ.get("VIVY_LLM_TEMPERATURE", "0.15")),
            top_p=float(os.environ.get("VIVY_LLM_TOP_P", "0.9")),
            max_tokens=int(os.environ.get("VIVY_LLM_MAX_TOKENS", "2048")),
        )

    # ------------------------------------------------------------------
    # Derived views
    # ------------------------------------------------------------------

    @property
    def openai_base_url(self) -> str:
        """API root as ``httpx`` clients expect it (with the ``/v1`` suffix)."""
        return f"{self.base_url.rstrip('/')}/v1"

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/v1/chat/completions"

    def with_model(self, model_id: str) -> LLMBackend:
        """Same backend, different model — explicit, never a silent switch."""
        return LLMBackend(
            backend_id=self.backend_id,
            base_url=self.base_url,
            model_id=model_id,
            timeout_s=self.timeout_s,
            num_ctx=self.num_ctx,
            api_key=self.api_key,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
        )

    # ------------------------------------------------------------------
    # Receipts
    # ------------------------------------------------------------------

    def config_hash(self) -> str:
        """Stable hash of the decoding/template config.

        Mirrors ``training.backend_registry.config_hash`` so a receipt from the
        product path and one from the training path name the same settings.
        """
        payload = {
            "backend_id": self.backend_id,
            "base_url": self.base_url,
            "model_id": self.model_id,
            "timeout_s": self.timeout_s,
            "num_ctx": self.num_ctx,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def identity(self) -> dict[str, Any]:
        """What actually serves a request — required on every receipt.

        Shape matches ``training.backend_baseline.BackendIdentity.to_dict()`` so
        the two paths can be diffed directly.
        """
        return {
            "backend_id": self.backend_id,
            "model_alias": self.model_id,
            "model_hash": "",  # filled by a live probe when /v1/models is reachable
            "config_hash": self.config_hash(),
            "base_url": self.base_url,
            "extra": {
                "num_ctx": self.num_ctx,
                "timeout_s": self.timeout_s,
                "contract": "openai-compatible:/v1/chat/completions",
            },
        }

    def describe(self) -> str:
        return (
            f"{self.backend_id} model={self.model_id} "
            f"url={self.base_url} timeout={self.timeout_s}s num_ctx={self.num_ctx}"
        )


def identity_from_env() -> dict[str, Any]:
    """Convenience: the receipt shard for the configured backend."""
    return LLMBackend.from_env().identity()


def decode_backend_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise a stored identity dict without inventing missing fields."""
    out: dict[str, Any] = {
        "backend_id": str(payload.get("backend_id", "")),
        "model_alias": str(payload.get("model_alias", "")),
        "model_hash": str(payload.get("model_hash", "")),
        "config_hash": str(payload.get("config_hash", "")),
        "base_url": str(payload.get("base_url", "")),
    }
    extra = payload.get("extra")
    out["extra"] = dict(extra) if isinstance(extra, Mapping) else {}
    return out


__all__ = [
    "DEFAULT_BACKEND_ID",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL_ID",
    "LLMBackend",
    "LLMError",
    "LLMTimeoutError",
    "ModelUnavailableError",
    "decode_backend_identity",
    "identity_from_env",
]
