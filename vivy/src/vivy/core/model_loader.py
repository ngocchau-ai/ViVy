"""
Local AI Engine Loader — Supports GGUF, PyTorch Safetensors, and Ollama APIs.
"""

import json
import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fail-loud errors and the mock-engine gate
# [REPLACED 29/09/2026] this module used to fall back to MockLocalEngine whenever
# llama_cpp was missing and whenever the backend name was unknown (F-A07 / G-02).
# A trade cycle must never silently run on a fake engine that hardcodes BUY GOLD.
# ---------------------------------------------------------------------------

MOCK_OPT_IN_ENV = "VIVY_ALLOW_MOCK_ENGINE"


class EngineUnavailableError(RuntimeError):
    """A real local engine could not be constructed (missing dep, bad weights)."""


class UnsupportedBackendError(ValueError):
    """``config.backend`` is not a known, constructible backend."""


def mock_engine_allowed(allow_mock: bool | None = None) -> bool:
    """Return True when MockLocalEngine may be constructed.

    ``allow_mock=True`` opts in explicitly (tests).  ``False`` refuses.
    ``None`` (default) falls back to the ``VIVY_ALLOW_MOCK_ENGINE`` env opt-in.
    """
    if allow_mock is not None:
        return bool(allow_mock)
    return os.environ.get(MOCK_OPT_IN_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _require_mock_allowed(context: str, allow_mock: bool | None = None) -> None:
    if not mock_engine_allowed(allow_mock):
        raise EngineUnavailableError(
            f"MockLocalEngine is banned outside explicit opt-in ({context}). "
            f"Pass allow_mock=True in tests, or set {MOCK_OPT_IN_ENV}=1 for a "
            "deliberate non-production run. Production must use a real engine."
        )


class ModelBackend(StrEnum):
    VIVY_NATIVE_PYTORCH = "vivy_native_pytorch"  # The new core reasoning engine
    GGUF_LOCAL = "gguf_local"                    # Legacy/fallback
    OLLAMA_API = "ollama_api"                    # Legacy/fallback
    MOCK = "mock"


@dataclass
class ModelConfig:
    backend: ModelBackend
    model_path_or_name: str
    temperature: float = 0.2
    max_tokens: int = 2048
    context_window: int = 8192
    gpu_layers: int = 0


class LocalModelEngine:
    """Base interface for ViVy Local AI Engine."""

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        raw_output = self.generate(prompt, system_prompt=system_prompt)
        try:
            # Clean markdown code block formatting if present
            cleaned = raw_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"Failed to parse JSON response directly: {e}. Raw: {raw_output}")
            return {"thought": raw_output, "action": "HOLD", "raw_output": raw_output}


class MockLocalEngine(LocalModelEngine):
    """[TEST DOUBLE] canned-response engine — banned in production.

    Retained because tests need a deterministic engine.  It always answers
    ``BUY GOLD`` with a fabricated confidence, so it must never reach a live
    trade cycle.  Construction is gated by :func:`mock_engine_allowed`.
    """

    def __init__(self, config: ModelConfig):
        self.config = config

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        # Generate valid ViVy response JSON for testing
        response = {
            "thought": f"ViVy Local Brain analyzed prompt: {prompt[:80]}...",
            "action": "BUY",
            "symbol": "GOLD",
            "volume": 0.1,
            "stop_loss": 2350.0,
            "take_profit": 2390.0,
            "confidence": 0.92
        }
        return json.dumps(response)


class OllamaAPIEngine(LocalModelEngine):
    """Client for local Ollama HTTP API."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            import urllib.request
            req_data = {
                "model": self.config.model_path_or_name,
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_ctx": self.config.context_window,
                }
            }
            req = urllib.request.Request(
                f"{self.api_url}/api/generate",
                data=json.dumps(req_data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("response", "")
        except Exception as e:
            logger.error(f"Ollama API request failed: {e}")
            raise RuntimeError(f"Ollama API unavailable: {e}") from e


class GGUFLocalEngine(LocalModelEngine):
    """Direct GGUF model loader via llama-cpp-python.

    [REPLACED 29/09/2026] a missing ``llama_cpp`` used to set ``self.llm = None``
    and ``generate`` silently answered via ``MockLocalEngine``.  Both paths now
    raise :class:`EngineUnavailableError`.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise EngineUnavailableError(
                "llama_cpp is not installed; GGUFLocalEngine cannot run. "
                "Install llama-cpp-python, or select a different backend."
            ) from exc
        try:
            self.llm = Llama(
                model_path=config.model_path_or_name,
                n_ctx=config.context_window,
                n_gpu_layers=config.gpu_layers,
                verbose=False
            )
        except Exception as exc:
            raise EngineUnavailableError(
                f"failed to load GGUF model {config.model_path_or_name!r}: {exc}"
            ) from exc

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:" if system_prompt else prompt
        output = self.llm(
            full_prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        return output["choices"][0]["text"]


class NativePyTorchEngine(LocalModelEngine):
    """Native ViVy Core Reasoning Engine using NumPy/PyTorch backend."""

    def __init__(self, config: ModelConfig):
        self.config = config
        # We lazy load vivy_brain to avoid circular imports or heavy torch loading

        from .vivy_brain import ViVyQuantumCore
        # Initialize the state dimension randomly or based on config
        self.core = ViVyQuantumCore(state_dim=1024)

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        # Translate prompt into a vector state
        # In a full PyTorch implementation, this would involve embedding lookups
        import json

        import numpy as np
        dummy_state = np.random.randn(1024) + 1j * np.random.randn(1024)

        # Run through the filter funnel
        result = self.core.process_state(dummy_state)

        response = {
            "thought": f"ViVy Native Core analyzed state: Entropy={result['entropy']:.2f}, Streams={result['streams_count']}",
            "action": result["signal"],
            "raw_output": result
        }
        return json.dumps(response)


class LocalModelLoader:
    """Factory loader for ViVy Local AI Engine."""

    @staticmethod
    def load_engine(config: ModelConfig, *, allow_mock: bool | None = None) -> LocalModelEngine:
        """Build the engine named by ``config.backend``.

        [REPLACED 29/09/2026] the old body returned ``MockLocalEngine`` for every
        unknown backend.  Unknown backends now raise, and MOCK requires an
        explicit opt-in (``allow_mock=True`` or ``VIVY_ALLOW_MOCK_ENGINE=1``).
        """
        if config.backend == ModelBackend.VIVY_NATIVE_PYTORCH:
            return NativePyTorchEngine(config)
        if config.backend == ModelBackend.GGUF_LOCAL:
            return GGUFLocalEngine(config)
        if config.backend == ModelBackend.OLLAMA_API:
            return OllamaAPIEngine(config)
        if config.backend == ModelBackend.MOCK:
            _require_mock_allowed("ModelBackend.MOCK", allow_mock)
            return MockLocalEngine(config)
        raise UnsupportedBackendError(
            f"unknown model backend {config.backend!r}; expected one of "
            f"{', '.join(b.value for b in ModelBackend)}"
        )
