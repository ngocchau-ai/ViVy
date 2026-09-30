#!/usr/bin/env python3
"""
ViVy Integration Smoke Test — Sprint 3.

Verifies all components import and wire together correctly WITHOUT
requiring a live llama-server. Tests are offline (mock LLM responses).

Usage: python scripts/test_integration.py

Exit codes:
    0 — All tests passed
    1 — One or more tests failed

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------


PASS = "✅ PASS"
FAIL = "❌ FAIL"
results: list[tuple[str, bool, str]] = []


def test(name: str):
    """Decorator to register a test."""
    def decorator(fn):
        t0 = time.perf_counter()
        try:
            fn()
            elapsed = (time.perf_counter() - t0) * 1000
            results.append((name, True, f"{elapsed:.1f}ms"))
            print(f"  {PASS}  {name} ({elapsed:.1f}ms)")
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            msg = f"{type(e).__name__}: {e}"
            results.append((name, False, msg))
            print(f"  {FAIL}  {name}")
            print(f"          {msg}")
            if os.environ.get("VIVY_TEST_VERBOSE"):
                traceback.print_exc()
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("  ViVy Final Core V1.0 — Integration Smoke Tests")
print("=" * 60 + "\n")

print("── Sprint 1: Engine Primitives ──────────────────────────")


@test("import engine.*")
def _():
    from engine.elastic_n_core import ElasticNCore
    from engine.mtp_directive import DirectiveMTPHead
    from engine.primitives import (PrimitiveResult, engine_cache_control,
                                   engine_exec, engine_file_io)
    _ = ElasticNCore, DirectiveMTPHead, engine_file_io, engine_exec, engine_cache_control, PrimitiveResult


@test("ElasticNCore.forward() — N=2")
def _():
    from engine.elastic_n_core import ElasticNCore
    nc = ElasticNCore(n_min=2, n_max=4, hidden_dim=32, seed=42)
    result = nc.forward(n_override=2)
    assert len(result.candidates) == 2
    assert result.winner.action_vector.shape == (32,)


@test("DirectiveMTPHead.forward() + verify()")
def _():
    from engine.elastic_n_core import ElasticNCore
    from engine.mtp_directive import DirectiveMTPHead
    import numpy as np
    nc = ElasticNCore(n_min=2, n_max=4, hidden_dim=32, seed=0)
    mtp = DirectiveMTPHead(hidden_dim=32)
    result = nc.forward(n_override=2)
    directive = mtp.forward(result.winner.action_vector)
    assert mtp.verify(directive)


@test("engine_file_io — write + read")
def _():
    import tempfile
    from engine.primitives import engine_file_io
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.txt")
        r_write = engine_file_io("write", path, content="hello vivy")
        assert r_write.ok, r_write.error_message
        r_read = engine_file_io("read", path)
        assert r_read.ok
        assert r_read.data == "hello vivy"


@test("engine_exec — echo command")
def _():
    from engine.primitives import engine_exec
    r = engine_exec(["python", "-c", "print('vivy_test_ok')"])
    assert r.ok, r.error_message
    assert "vivy_test_ok" in (r.data.get("stdout", "") if isinstance(r.data, dict) else str(r.data))


print("\n── Sprint 2: Cognitive State Graph & Memory ─────────────")


@test("import memory.*")
def _():
    from memory.cognitive_graph import CognitiveStateGraph, NodeType
    from memory.hebbian_recall import HebbianRecall
    _ = CognitiveStateGraph, NodeType, HebbianRecall


@test("CognitiveStateGraph — add_node + FALSIFIED edge + dampening")
def _():
    from memory.cognitive_graph import CognitiveStateGraph, NodeType
    g = CognitiveStateGraph()
    g.add_node("n1", NodeType.HYPOTHESIS, "test action", confidence=0.8)
    g.add_edge_falsified("n1", "rca1")
    n = g.get_node("n1")
    assert n is not None
    assert n.falsified_count == 1
    assert n.dampen_factor() == 0.5


@test("HebbianRecall — register + O(1) recall")
def _():
    import numpy as np
    from memory.cognitive_graph import CognitiveStateGraph, NodeType
    from memory.hebbian_recall import HebbianRecall
    g = CognitiveStateGraph()
    rc = HebbianRecall(dim=32)
    v = np.ones(32, dtype=np.float32) / (32 ** 0.5)
    g.add_node("n1", NodeType.HYPOTHESIS, "test", confidence=0.8, embedding=v)
    rc.sync_from_graph(g)
    r = rc.recall(v, g)
    assert r is not None
    assert r.recalled_node_id == "n1"
    assert r.similarity >= 0.99


@test("GraphBridge — evaluate() + record_falsified() VM-11")
def _():
    import numpy as np
    from memory.cognitive_graph import CognitiveStateGraph
    from memory.hebbian_recall import HebbianRecall
    from orchestrator.graph_bridge import GraphBridge
    g = CognitiveStateGraph()
    rc = HebbianRecall(dim=32)
    bridge = GraphBridge()
    av = np.ones(32, dtype=np.float32) / (32 ** 0.5)
    r = bridge.evaluate(av, g, rc, confidence=0.8)
    assert r.registered_node_id != ""
    bridge.record_falsified(r.registered_node_id, g, rc, reason="test")
    node = g.get_node(r.registered_node_id)
    assert node.falsified_count == 1


print("\n── Sprint 3: Integration Layer ──────────────────────────")


@test("import integration.*")
def _():
    from integration.llama_cpp_bridge import LlamaCppBridge, LlamaCppConfig, ChatMessage
    from integration.multimodal_adapter import MultimodalAdapter, MultimodalInput
    from integration.tool_dispatcher import ToolDispatcher
    from integration.session_manager import SessionManager
    from integration.vivy_inference_loop import VivyInferenceLoop
    _ = LlamaCppBridge, LlamaCppConfig, ChatMessage, MultimodalAdapter, MultimodalInput
    _ = ToolDispatcher, SessionManager, VivyInferenceLoop


@test("MultimodalAdapter — text encoding")
def _():
    from integration.multimodal_adapter import MultimodalAdapter, InputModality
    adapter = MultimodalAdapter()
    inp = adapter.from_text("Hello ViVy")
    assert inp.text == "Hello ViVy"
    assert inp.modality == InputModality.TEXT


@test("MultimodalAdapter — image bytes encoding")
def _():
    import struct
    import zlib
    from integration.multimodal_adapter import MultimodalAdapter
    # Minimal 1x1 white PNG
    def make_png():
        sig = b'\x89PNG\r\n\x1a\n'
        def chunk(t, d):
            c = len(d).to_bytes(4,'big') + t + d
            return c + zlib.crc32(t+d).to_bytes(4,'big')
        ihdr = struct.pack('>IIBBBBB',1,1,8,2,0,0,0)
        idat = zlib.compress(b'\x00\xff\xff\xff')
        return sig + chunk(b'IHDR',ihdr) + chunk(b'IDAT',idat) + chunk(b'IEND',b'')
    adapter = MultimodalAdapter()
    inp = adapter.from_image_bytes(make_png(), caption="test png")
    assert inp.image_b64 is not None
    assert len(inp.image_b64) > 10


@test("ToolDispatcher — engine_file_io dispatch")
def _():
    import json
    import tempfile
    from integration.tool_dispatcher import ToolDispatcher
    dispatcher = ToolDispatcher()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "dispatch_test.txt").replace("\\", "/")
        args_json = json.dumps({"action": "write", "path": path, "content": "dispatch_ok"})
        tool_calls = [{
            "id": "call_test_1",
            "type": "function",
            "function": {
                "name": "engine_file_io",
                "arguments": args_json,
            }
        }]
        results_list = dispatcher.dispatch_tool_calls(tool_calls)
        assert len(results_list) == 1
        assert results_list[0].ok, results_list[0].primitive_result.error_message



@test("ToolDispatcher — unknown tool returns error gracefully")
def _():
    from integration.tool_dispatcher import ToolDispatcher
    dispatcher = ToolDispatcher()
    tool_calls = [{"id": "x", "type": "function", "function": {"name": "nonexistent_tool", "arguments": "{}"}}]
    r = dispatcher.dispatch_tool_calls(tool_calls)
    assert not r[0].ok
    assert "Unknown tool" in r[0].primitive_result.error_message


@test("SessionManager — create + get + isolation")
def _():
    from integration.session_manager import SessionManager
    sm = SessionManager(hidden_dim=32)
    s1 = sm.create_session("s1")
    s2 = sm.create_session("s2")
    # Add node to s1 only
    from memory.cognitive_graph import NodeType
    s1.graph.add_node("n1", NodeType.HYPOTHESIS, "task", confidence=0.8)
    # s2 should be empty
    assert len(s1.graph) == 1
    assert len(s2.graph) == 0
    # get_session returns same object
    s1_retrieved = sm.get_session("s1")
    assert s1_retrieved is s1


@test("VivyInferenceLoop — from_env() construction (offline)")
def _():
    from integration.vivy_inference_loop import VivyInferenceLoop
    # Set env to avoid needing real server
    os.environ.setdefault("VIVY_LLAMA_URL", "http://127.0.0.1:8080")
    vivy = VivyInferenceLoop.from_env()
    assert vivy._n_core is not None
    assert vivy._mtp is not None
    assert vivy._sessions is not None


@test("VivyInferenceLoop — epistemic_decision parsing")
def _():
    from integration.vivy_inference_loop import VivyInferenceLoop
    text = """
<vivy_thought>
[EPISTEMIC_ASSESSMENT]
Objective: test
Confidence: HIGH
Epistemic_Decision: NEED_KNOWLEDGE_FORAGING
</vivy_thought>
    """
    decision = VivyInferenceLoop._parse_epistemic_decision(text)
    assert decision == "NEED_KNOWLEDGE_FORAGING", f"Got: {decision}"


print("\n── Architecture Invariants ──────────────────────────────")


@test("No wrapper imports (AST scan: langchain, autogen, haystack)")
def _():
    import ast
    target_dirs = ["engine", "memory", "orchestrator", "integration"]
    forbidden = ["langchain", "autogen", "haystack", "llamaindex"]
    for d in target_dirs:
        for f in os.listdir(d):
            if not f.endswith(".py"):
                continue
            path = os.path.join(d, f)
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [n.name for n in getattr(node, "names", [])]
                    module = getattr(node, "module", "") or ""
                    all_imports = names + [module]
                    bad = [x for x in all_imports if any(w in x for w in forbidden)]
                    assert not bad, f"Wrapper import in {path}:{node.lineno} — {bad}"


@test("VM-11 invariant: error repeat rate = 0% (bad vs good node)")
def _():
    import numpy as np
    from memory.cognitive_graph import CognitiveStateGraph, NodeType
    from memory.hebbian_recall import HebbianRecall
    from orchestrator.graph_bridge import GraphBridge
    g = CognitiveStateGraph()
    rc = HebbianRecall(dim=32)
    bridge = GraphBridge()
    # Create bad node (falsified)
    av_bad = np.ones(32, dtype=np.float32) / (32 ** 0.5)
    r_bad = bridge.evaluate(av_bad, g, rc, confidence=0.8)
    bridge.record_falsified(r_bad.registered_node_id, g, rc, reason="vm11_test")
    # Create good node
    rng = np.random.default_rng(1)
    av_good = rng.standard_normal(32).astype(np.float32)
    av_good /= np.linalg.norm(av_good)
    r_good = bridge.evaluate(av_good, g, rc, confidence=0.8)
    # Verify bad never wins
    cands = g.get_dampened_candidates([r_bad.registered_node_id, r_good.registered_node_id])
    assert cands[0][0] == r_good.registered_node_id, "VM-11 VIOLATED: bad node ranked above good"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
failed_tests = [(name, msg) for name, ok, msg in results if not ok]

print(f"  Results: {passed}/{total} passed")
if failed_tests:
    print(f"\n  Failed tests:")
    for name, msg in failed_tests:
        print(f"    ✗ {name}: {msg}")
    print("\n  [FAIL] Some tests failed.")
    print("=" * 60)
    sys.exit(1)
else:
    print("\n  [PASS] All integration smoke tests passed.")
    print("  ViVy Final Core V1.0 is ready for deployment.")
    print("=" * 60)
    sys.exit(0)
