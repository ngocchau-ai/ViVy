"""
Unit tests for ParallelContextPipeline (Simultaneous Input Decomposition & Compression).
"""

from unittest.mock import MagicMock

from integration.llama_cpp_bridge import LlamaCppBridge
from integration.multimodal_adapter import MultimodalInput
from integration.parallel_context_pipeline import (
    ParallelContextPipeline,
)
from integration.session_manager import SessionManager
from integration.vivy_inference_loop import VivyInferenceLoop


def test_short_input_passthrough():
    pipeline = ParallelContextPipeline(activation_threshold_chars=500)
    short_text = "This is a short task: optimize function foo() in file bar.py"
    res = pipeline.process(short_text)

    assert not res.is_processed
    assert res.fused_prompt == short_text
    assert res.total_segments == 1


def test_long_input_parallel_decomposition_and_compression():
    mock_memory = MagicMock()
    pipeline = ParallelContextPipeline(
        activation_threshold_chars=300,
        max_segment_chars=200,
        context_memory=mock_memory,
    )

    long_text = (
        "# SYSTEM OBJECTIVE\n"
        "Goal: Refactor entire inference loop to support 0ms memory access.\n"
        "Constraint: Never break 2048 token window.\n\n"
        "Paragraph 1: In this section, we describe the legacy architecture.\n"
        "It was flawed due to unbound context accumulation.\n\n"
        "Paragraph 2: The second problem was lack of intuition injection.\n"
        "We needed to wire Cautreo context memory directly.\n\n"
        "Paragraph 3: The third problem was ungrounded tensor benchmarks.\n"
        "Everything must be verifiable and deterministic."
    )

    res = pipeline.process(long_text, task_id="task_test_01")

    assert res.is_processed
    assert res.total_segments >= 3
    assert len(res.compressed_digest) > 0
    assert "SYSTEM OBJECTIVE" in res.compressed_digest
    assert "Refactor entire inference loop" in res.compressed_digest

    # Verify that remaining segments (S2..SK) were stored into Cautreo Memory
    assert len(res.remaining_segment_ids) == res.total_segments - 1
    assert mock_memory.store_hard_fact.call_count == len(res.remaining_segment_ids)

    # Verify fusion prompt format
    assert "[PARALLEL_INPUT_PIPELINE: LONG_INPUT_DETECTED]" in res.fused_prompt
    assert "## 1. COMPRESSED OVERVIEW" in res.fused_prompt
    assert "## 2. ACTIVE WORKING SEGMENT" in res.fused_prompt
    assert "## 3. CONTEXT CHAIN CONTINUATION INSTRUCTIONS" in res.fused_prompt


def test_vivy_inference_loop_auto_parallel_pipeline():
    mock_memory = MagicMock()
    mock_memory.get_summary.return_value = ""

    pipeline = ParallelContextPipeline(
        activation_threshold_chars=200,
        max_segment_chars=150,
        context_memory=mock_memory,
    )

    bridge = MagicMock(spec=LlamaCppBridge)
    sessions = MagicMock(spec=SessionManager)

    loop = VivyInferenceLoop(
        bridge=bridge,
        session_manager=sessions,
        context_memory=mock_memory,
        parallel_pipeline=pipeline,
    )

    long_prompt = "Goal: Large Task\n\n" + "Data block line describing the heavy task requirements.\n" * 10
    modal_input = MultimodalInput(text=long_prompt)

    messages = loop._build_messages(modal_input, history=None)
    user_msg = messages[-1]

    assert user_msg.role == "user"
    assert "[PARALLEL_INPUT_PIPELINE: LONG_INPUT_DETECTED]" in user_msg.content
    assert "COMPRESSED OVERVIEW" in user_msg.content
