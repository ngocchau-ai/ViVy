"""
ViVy Integration Layer — Sprint 3 (HOH-VIVY-FINAL-V1)

Packages:
  integration/llama_cpp_bridge.py    — llama.cpp OpenAI-compat HTTP bridge
  integration/multimodal_adapter.py  — Image/audio → Gemma 4 E4B format
  integration/tool_dispatcher.py     — DirectiveExecutionTuple → engine primitive
  integration/session_manager.py     — CognitiveStateGraph per-session isolation
  integration/vivy_inference_loop.py — Main inference loop (think → act → observe)

Base model: Gemma 4 E4B (Apache 2.0, Text+Vision+Audio, MTP native)
Runtime:    llama.cpp server (OpenAI-compatible /v1/chat/completions)

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from .llama_cpp_bridge import LlamaCppBridge, LlamaCppConfig, ChatMessage
from .multimodal_adapter import MultimodalAdapter, MultimodalInput, InputModality
from .tool_dispatcher import ToolDispatcher, DispatchResult
from .session_manager import SessionManager, ViVySession
from .vivy_inference_loop import VivyInferenceLoop, InferenceResult, InferenceMode

__all__ = [
    # Bridge
    "LlamaCppBridge",
    "LlamaCppConfig",
    "ChatMessage",
    # Multimodal
    "MultimodalAdapter",
    "MultimodalInput",
    "InputModality",
    # Tool Dispatcher
    "ToolDispatcher",
    "DispatchResult",
    # Session
    "SessionManager",
    "ViVySession",
    # Main loop
    "VivyInferenceLoop",
    "InferenceResult",
    "InferenceMode",
]
