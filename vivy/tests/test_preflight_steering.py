"""
Unit tests for Preflight Steering Engine — ViVy V6 & Cautreo Native Architecture.

Verifies:
1. PreflightPacket formatting of Negative Constraints (VM-11), Directive, and Anchors.
2. Extraction of falsified nodes from CognitiveStateGraph.
3. Pre-Actuation Memory Steering injection into VivyInferenceLoop system messages.
4. Invariant: Falsified failure is converted into a hard negative constraint.
"""

from unittest.mock import MagicMock

from engine.mtp_directive import DirectiveExecutionTuple
from integration.preflight_steering import PreflightPacket, PreflightSteering
from integration.session_manager import SessionManager
from integration.vivy_inference_loop import VivyInferenceLoop
from memory.cognitive_graph import CognitiveStateGraph, EdgeType, NodeType


def test_preflight_packet_formatting():
    packet = PreflightPacket(
        negative_constraints=["Do not use OrderSend without slippage check", "Avoid recursion in indicator"],
        directive_summary="Action Directive: `DELEGATE` | Confidence: 0.95",
        intuition_anchors=["MT5 Bridge connection verified on port 8080"],
        recommended_slot="code_py_specialist",
    )
    injection = packet.to_system_injection()
    assert "PRE-FLIGHT HARD NEGATIVE CONSTRAINTS (VM-11 DAMPENER ACTIVE)" in injection
    assert "[FORBIDDEN / DO NOT REPEAT]: Do not use OrderSend without slippage check" in injection
    assert "[FORBIDDEN / DO NOT REPEAT]: Avoid recursion in indicator" in injection
    assert "N-CORE MTP DIRECTIVE PRE-GUIDANCE" in injection
    assert "CAUTREO NATIVE INTUITION ANCHORS" in injection


def test_extract_negative_constraints_from_graph():
    graph = CognitiveStateGraph(max_nodes=100)

    # Add a normal hypothesis
    graph.add_node("node_0", NodeType.HYPOTHESIS, "Write standard MT5 script")

    # Add another node and falsify it
    bad_node = graph.add_node(
        "node_1",
        NodeType.HYPOTHESIS,
        "Use hardcoded magic number 123456",
        metadata={"falsified_reason": "Order rejected: magic number conflict with master EA"},
    )
    graph.add_edge(bad_node.node_id, "evidence_fail", EdgeType.FALSIFIED)

    constraints = PreflightSteering.extract_negative_constraints(graph)
    assert len(constraints) == 1
    assert "Order rejected: magic number conflict with master EA" in constraints[0]


def test_compile_packet_slot_detection():
    graph = CognitiveStateGraph(max_nodes=100)
    directive = DirectiveExecutionTuple(
        target_id="PRETRAINED_SPECIALIST",
        opcode="EXECUTE_CODE",
        payload_hash="dummy_hash",
        signature="dummy_sig",
        payload_json={"task": "mt5"},
        confidence=0.88,
        core_index=0,
        generation_ms=1.5,
    )

    packet = PreflightSteering.compile_packet(
        task_text="Please write a python script to test MT5 connector",
        graph=graph,
        directive=directive,
    )
    assert packet.recommended_slot == "code_py_specialist"
    assert packet.directive_summary is not None
    assert "Target Component: `PRETRAINED_SPECIALIST`" in packet.directive_summary
    assert "Opcode: `EXECUTE_CODE`" in packet.directive_summary


def test_vivy_inference_loop_injects_preflight_steering():
    # Setup mock bridge
    mock_bridge = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "<vivy_thought>\nEpistemic_Decision: EXECUTE_DIRECTLY\nExpected_Evidence: None\n</vivy_thought>\nDone"
    mock_response.has_tool_calls = False
    mock_response.finish_reason = "stop"
    mock_response.prompt_tokens = 50
    mock_response.completion_tokens = 20
    mock_bridge.chat_safe.return_value = mock_response

    session_mgr = SessionManager()
    session = session_mgr.get_or_create("test_session")

    # Seed a falsified node into session's graph
    bad_node = session.graph.add_node(
        "bad_node_mem",
        NodeType.HYPOTHESIS,
        "Invalid memory access attempt",
        metadata={"falsified_reason": "Memory access out of bounds at offset 0x400"},
    )
    session.graph.add_edge(bad_node.node_id, "bounds_check_fail", EdgeType.FALSIFIED)

    loop = VivyInferenceLoop(
        bridge=mock_bridge,
        session_manager=session_mgr,
        system_prompt="Base system prompt.",
    )

    loop.infer("Write a fast MT5 connector script", session_id="test_session")

    # Verify that bridge.chat_safe was called with messages containing the preflight injection
    called_messages = mock_bridge.chat_safe.call_args[0][0]
    system_msg = called_messages[0]
    assert system_msg.role == "system"
    assert "PRE-FLIGHT HARD NEGATIVE CONSTRAINTS (VM-11 DAMPENER ACTIVE)" in system_msg.content
    assert "Memory access out of bounds at offset 0x400" in system_msg.content
    assert "N-CORE MTP DIRECTIVE PRE-GUIDANCE" in system_msg.content

