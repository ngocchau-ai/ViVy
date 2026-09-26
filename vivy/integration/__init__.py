"""
ViVy Integration Layer — Sprint 3 + VIVY-HOST-001 (DD-11)

Packages:
  integration/llama_cpp_bridge.py    — llama.cpp OpenAI-compat HTTP bridge
  integration/multimodal_adapter.py  — Image/audio → Gemma 4 E4B format
  integration/tool_dispatcher.py     — DirectiveExecutionTuple → engine primitive
  integration/session_manager.py     — CognitiveStateGraph per-session isolation
  integration/vivy_inference_loop.py — Main inference loop (think → act → observe)
  integration/vivy_host.py           — Cautreo C11 Runtime Bridge (DD-11)

Base model: Gemma 4 E4B (Apache 2.0, Text+Vision+Audio, MTP native)
Runtime:    llama.cpp server (OpenAI-compatible /v1/chat/completions)
Cautreo:    D:\\cautreov2\\91sCT\\build\\cautreo.exe (C11 Runtime, 191/191 tests)

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
    20/09/2026 (Antigravity IDE, Sprint VIVY-HOST-001 — DD-11): Add VivyHost bridge.
    23/09/2026 (Claude Code — P3 Interleaved in-memory tool dispatch): Export
        InterleavedDispatchLoop / InterleavedResult / InMemoryHandoff.
"""

from .in_memory_handoff import InMemoryHandoff
from .interleaved_dispatch import InterleavedDispatchLoop, InterleavedResult
from .llama_cpp_bridge import ChatMessage, LlamaCppBridge, LlamaCppConfig
from .multimodal_adapter import InputModality, MultimodalAdapter, MultimodalInput
from .session_manager import SessionManager, ViVySession
from .tool_dispatcher import DispatchResult, ToolDispatcher
from .vivy_host import (
    DREAM_TRIGGER_ERROR_RATE,
    CautreoStatus,
    DirectiveResult,
    KnowledgeEntry,
    RoomStatus,
    VivyHost,
)
from .vivy_inference_loop import InferenceMode, InferenceResult, VivyInferenceLoop

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
    # P3 interleaved in-memory dispatch
    "InterleavedDispatchLoop",
    "InterleavedResult",
    "InMemoryHandoff",
    # Session
    "SessionManager",
    "ViVySession",
    # Main loop
    "VivyInferenceLoop",
    "InferenceResult",
    "InferenceMode",
    # Cautreo Host Bridge (DD-11)
    "VivyHost",
    "RoomStatus",
    "CautreoStatus",
    "DirectiveResult",
    "KnowledgeEntry",
    "DREAM_TRIGGER_ERROR_RATE",
]
