"""
Unit tests for VivyInferenceLoop:
1. Cautreo Intuition Digest injection into messages prompt.
2. 2048-token context sliding window budgeter.
"""

from unittest.mock import MagicMock

from integration.llama_cpp_bridge import ChatMessage, LlamaCppBridge
from integration.multimodal_adapter import MultimodalInput
from integration.session_manager import SessionManager
from integration.vivy_inference_loop import VivyInferenceLoop


def test_intuition_digest_injection():
    # Mock context memory with an active digest
    mock_memory = MagicMock()
    mock_memory.get_summary.return_value = "TASK: optimize_code | INVARIANTS: 3 active | CONFIDENCE: 0.95"

    bridge = MagicMock(spec=LlamaCppBridge)
    sessions = MagicMock(spec=SessionManager)

    loop = VivyInferenceLoop(
        bridge=bridge,
        session_manager=sessions,
        context_memory=mock_memory,
        system_prompt="BASE_SYSTEM_PROMPT",
    )

    modal_input = MultimodalInput(text="Hello ViVy")
    messages = loop._build_messages(modal_input, history=None)

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert "BASE_SYSTEM_PROMPT" in messages[0].content
    assert "## VIVY INTUITION DIGEST (CAUTREO NATIVE MEMORY)" in messages[0].content
    assert "TASK: optimize_code" in messages[0].content
    assert messages[1].role == "user"
    assert "Hello ViVy" in messages[1].content


def test_context_budget_sliding_window():
    mock_memory = MagicMock()
    mock_memory.get_summary.return_value = ""

    bridge = MagicMock(spec=LlamaCppBridge)
    sessions = MagicMock(spec=SessionManager)

    loop = VivyInferenceLoop(
        bridge=bridge,
        session_manager=sessions,
        context_memory=mock_memory,
        system_prompt="BASE_SYSTEM_PROMPT",
    )

    # Simulate 8 historical turns
    history = [
        ChatMessage(role="user", content=f"User turn {i}")
        if i % 2 == 0
        else ChatMessage(role="assistant", content=f"Assistant turn {i}")
        for i in range(8)
    ]

    modal_input = MultimodalInput(text="Turn 9 prompt")
    messages = loop._build_messages(modal_input, history=history)

    # Total messages: 1 system prompt + 1 budgeter notice + 4 recent turns + 1 current user message = 7 messages
    assert messages[0].role == "system"
    assert "[Context Budgeter: 4 prior turns archived in Cautreo native RAM]" in messages[1].content

    # The 4 kept turns should be turn 4, 5, 6, 7
    kept_contents = [m.content for m in messages[2:6]]
    assert "User turn 4" in kept_contents[0]
    assert "Assistant turn 7" in kept_contents[3]
    assert messages[-1].content == "Turn 9 prompt"


def test_context_budget_char_limit():
    mock_memory = MagicMock()
    mock_memory.get_summary.return_value = ""

    bridge = MagicMock(spec=LlamaCppBridge)
    sessions = MagicMock(spec=SessionManager)

    loop = VivyInferenceLoop(
        bridge=bridge,
        session_manager=sessions,
        context_memory=mock_memory,
        system_prompt="BASE_SYSTEM_PROMPT",
    )

    # Create 4 very large turns (1500 chars each = 6000 chars, exceeds 3500 char limit)
    history = [
        ChatMessage(role="user", content="A" * 1500),
        ChatMessage(role="assistant", content="B" * 1500),
        ChatMessage(role="user", content="C" * 1500),
        ChatMessage(role="assistant", content="D" * 1000),
    ]

    modal_input = MultimodalInput(text="Prompt")
    messages = loop._build_messages(modal_input, history=history)

    # History should be reduced to satisfy the 3500 char limit
    kept_history = [m for m in messages if m.role in ("user", "assistant") and m.content != "Prompt"]
    total_chars = sum(len(m.content) for m in kept_history)
    assert total_chars <= 3500
