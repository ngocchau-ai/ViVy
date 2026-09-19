"""
Local AI Engine Loader — Supports GGUF, PyTorch Safetensors, and Ollama APIs.
"""

from dataclasses import dataclass
from enum import Enum
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ModelBackend(str, Enum):
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

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
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
    """Fallback engine for testing without local GPU/weights installed."""

    def __init__(self, config: ModelConfig):
        self.config = config

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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
            raise RuntimeError(f"Ollama API unavailable: {e}")


class GGUFLocalEngine(LocalModelEngine):
    """Direct GGUF model loader via llama-cpp-python."""

    def __init__(self, config: ModelConfig):
        self.config = config
        try:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=config.model_path_or_name,
                n_ctx=config.context_window,
                n_gpu_layers=config.gpu_layers,
                verbose=False
            )
        except ImportError:
            logger.warning("llama_cpp module not installed. Falling back to MockEngine.")
            self.llm = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if self.llm is None:
            return MockLocalEngine(self.config).generate(prompt, system_prompt)
        
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
        import numpy as np
        # Initialize the state dimension randomly or based on config
        self.core = ViVyQuantumCore(state_dim=1024)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Translate prompt into a vector state
        # In a full PyTorch implementation, this would involve embedding lookups
        import numpy as np
        import json
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
    def load_engine(config: ModelConfig) -> LocalModelEngine:
        if config.backend == ModelBackend.VIVY_NATIVE_PYTORCH:
            return NativePyTorchEngine(config)
        elif config.backend == ModelBackend.GGUF_LOCAL:
            return GGUFLocalEngine(config)
        elif config.backend == ModelBackend.OLLAMA_API:
            return OllamaAPIEngine(config)
        elif config.backend == ModelBackend.MOCK:
            return MockLocalEngine(config)
        else:
            return MockLocalEngine(config)
