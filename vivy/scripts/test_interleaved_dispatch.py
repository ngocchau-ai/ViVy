#!/usr/bin/env python3
"""P3 Interleaved in-memory tool dispatch tests.

Replaces file-JSON handoff (15–30s per the Antigravity report) with an
in-process dispatch loop: ToolDispatcher → CautreoContextMemory (C-ABI),
interleaved with the LLM loop. Tool results and the HoH handoff land in
Cautreo in-process memory first; file write is optional and secondary.

Gate 9: these tests assert in-memory dispatch, Cautreo put/get wiring, and
handoff schema only. They do NOT claim a latency number without a
reproducible benchmark receipt.

Changelog:
    23/09/2026 (Claude Code — P3 Interleaved in-memory tool dispatch): Initial.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Fake LLM bridge: returns canned tool_calls then a final answer.
# ---------------------------------------------------------------------------


class _FakeBridge:
    """Minimal chat_safe-compatible stand-in for LlamaCppBridge."""

    def __init__(self, rounds: list[dict]) -> None:
        self._rounds = list(rounds)
        self._i = 0
        self.calls: list[dict] = []

    def chat_safe(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), "kwargs": dict(kwargs)})
        if self._i >= len(self._rounds):
            return {"content": "done", "tool_calls": [], "finish_reason": "stop"}
        payload = self._rounds[self._i]
        self._i += 1
        return {
            "content": payload.get("content", ""),
            "tool_calls": payload.get("tool_calls", []),
            "finish_reason": payload.get("finish_reason", "tool_calls"),
            "prompt_tokens": 1,
            "completion_tokens": 1,
        }


def _tool_call(tool_name: str, arguments: dict, call_id: str = "call_1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": tool_name, "arguments": json.dumps(arguments)},
    }


class CautreoMemoryToolTests(unittest.TestCase):
    """ToolDispatcher gains in-process Cautreo memory tools."""

    def test_cautreo_put_is_a_known_tool(self):
        from integration.tool_dispatcher import ToolDispatcher

        d = ToolDispatcher()
        self.assertIn("cautreo_put", d._TOOL_HANDLERS)
        self.assertIn("cautreo_get", d._TOOL_HANDLERS)

    def test_cautreo_put_stores_into_context_memory(self):
        from integration.cautreo_binding import CautreoContextMemory, CautreoMemoryKind
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            d = ToolDispatcher(context_memory=mem)
            results = d.dispatch_tool_calls(
                [
                    _tool_call(
                        "cautreo_put",
                        {
                            "item_id": "fact_p3",
                            "kind": "HARD_FACT",
                            "content": "in-process tool result",
                        },
                        call_id="c1",
                    )
                ]
            )
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].ok, results[0].to_tool_response_content())
            item = mem.get("fact_p3")
            self.assertIsNotNone(item)
            self.assertEqual(item.content, "in-process tool result")
            self.assertEqual(item.kind, CautreoMemoryKind.HARD_FACT)
        finally:
            mem.close()

    def test_cautreo_get_reads_from_context_memory(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            mem.store_task("task_p3", "handoff task body")
            d = ToolDispatcher(context_memory=mem)
            results = d.dispatch_tool_calls(
                [_tool_call("cautreo_get", {"item_id": "task_p3"}, call_id="c2")]
            )
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].ok)
            data = results[0].primitive_result.data
            self.assertEqual(data["content"], "handoff task body")
        finally:
            mem.close()

    def test_cautreo_get_missing_item_fails_closed(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            d = ToolDispatcher(context_memory=mem)
            results = d.dispatch_tool_calls(
                [_tool_call("cautreo_get", {"item_id": "nope"}, call_id="c3")]
            )
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].ok)
        finally:
            mem.close()

    def test_cautreo_put_without_memory_fails_closed(self):
        from integration.tool_dispatcher import ToolDispatcher

        d = ToolDispatcher(context_memory=None)
        results = d.dispatch_tool_calls(
            [_tool_call("cautreo_put", {"item_id": "x", "kind": "TASK", "content": "y"})]
        )
        self.assertFalse(results[0].ok)


class InterleavedDispatchLoopTests(unittest.TestCase):
    """In-memory interleaved loop: chat → dispatch → chat, no file round-trip."""

    def test_loops_tool_calls_then_returns_final_content(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.interleaved_dispatch import InterleavedDispatchLoop
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            bridge = _FakeBridge(
                [
                    {
                        "content": "",
                        "tool_calls": [
                            _tool_call(
                                "cautreo_put",
                                {
                                    "item_id": "fact_loop",
                                    "kind": "HARD_FACT",
                                    "content": "looped",
                                },
                                call_id="t1",
                            )
                        ],
                        "finish_reason": "tool_calls",
                    }
                ]
            )
            loop = InterleavedDispatchLoop(
                bridge=bridge,
                dispatcher=ToolDispatcher(context_memory=mem),
                context_memory=mem,
            )
            result = loop.run(messages=[{"role": "user", "content": "store a fact"}])
            self.assertEqual(result.final_content, "done")
            self.assertEqual(result.rounds, 2)  # 1 tool round + 1 final
            self.assertEqual(len(result.dispatch_results), 1)
            self.assertTrue(result.dispatch_results[0].ok)
            self.assertIsNotNone(mem.get("fact_loop"))
        finally:
            mem.close()

    def test_tool_results_land_in_cautreo_as_task_summary(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.interleaved_dispatch import InterleavedDispatchLoop
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            bridge = _FakeBridge(
                [
                    {
                        "content": "",
                        "tool_calls": [
                            _tool_call(
                                "cautreo_put",
                                {
                                    "item_id": "fact_x",
                                    "kind": "HARD_FACT",
                                    "content": "payload",
                                },
                                call_id="t1",
                            )
                        ],
                    }
                ]
            )
            loop = InterleavedDispatchLoop(
                bridge=bridge,
                dispatcher=ToolDispatcher(context_memory=mem),
                context_memory=mem,
            )
            result = loop.run(messages=[{"role": "user", "content": "go"}])
            # Dispatch results themselves are archived in Cautreo (SUMMARY kind).
            self.assertIsNotNone(result.memory_archive_id)
            archived = mem.get(result.memory_archive_id)
            self.assertIsNotNone(archived)
            self.assertIn("cautreo_put", archived.content)
        finally:
            mem.close()

    def test_max_rounds_terminates_and_reports_limit(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.interleaved_dispatch import InterleavedDispatchLoop
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            endless = [
                {
                    "content": "",
                    "tool_calls": [
                        _tool_call(
                            "cautreo_put",
                            {"item_id": f"k{i}", "kind": "TASK", "content": "c"},
                            call_id=f"c{i}",
                        )
                    ],
                    "finish_reason": "tool_calls",
                }
                for i in range(5)
            ]
            bridge = _FakeBridge(endless)
            loop = InterleavedDispatchLoop(
                bridge=bridge,
                dispatcher=ToolDispatcher(context_memory=mem),
                context_memory=mem,
                max_rounds=3,
            )
            result = loop.run(messages=[{"role": "user", "content": "loop"}])
            self.assertEqual(result.rounds, 3)
            self.assertTrue(result.hit_round_limit)
        finally:
            mem.close()

    def test_no_tool_calls_returns_immediately(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.interleaved_dispatch import InterleavedDispatchLoop
        from integration.tool_dispatcher import ToolDispatcher

        mem = CautreoContextMemory(max_items=16)
        try:
            bridge = _FakeBridge([{"content": "plain", "tool_calls": [], "finish_reason": "stop"}])
            loop = InterleavedDispatchLoop(
                bridge=bridge,
                dispatcher=ToolDispatcher(context_memory=mem),
                context_memory=mem,
            )
            result = loop.run(messages=[{"role": "user", "content": "hi"}])
            self.assertEqual(result.final_content, "plain")
            self.assertEqual(result.rounds, 1)
            self.assertEqual(result.dispatch_results, [])
            self.assertFalse(result.hit_round_limit)
        finally:
            mem.close()


class InMemoryHandoffTests(unittest.TestCase):
    """HoH handoff lives in Cautreo first; file write is optional."""

    def test_publish_handoff_to_cautreo_memory(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.in_memory_handoff import InMemoryHandoff

        mem = CautreoContextMemory(max_items=16)
        try:
            handoff = InMemoryHandoff(context_memory=mem)
            payload = handoff.publish(
                task_id="sess_1",
                status="READY_FOR_REVIEW",
                response="directive body",
                validation={"valid": True, "violations": []},
            )
            self.assertTrue(payload["in_memory"])
            self.assertIsNotNone(payload["memory_id"])
            stored = mem.get(payload["memory_id"])
            self.assertIsNotNone(stored)
            body = json.loads(stored.content)
            self.assertEqual(body["task_id"], "sess_1")
            self.assertEqual(body["status"], "READY_FOR_REVIEW")
            self.assertEqual(body["response"], "directive body")
        finally:
            mem.close()

    def test_read_handoff_from_cautreo_memory(self):
        from integration.cautreo_binding import CautreoContextMemory
        from integration.in_memory_handoff import InMemoryHandoff

        mem = CautreoContextMemory(max_items=16)
        try:
            pub = InMemoryHandoff(context_memory=mem)
            payload = pub.publish(
                task_id="sess_2",
                status="NEEDS_REVIEW",
                response="body",
                validation={"valid": False, "violations": ["missing Expected_Evidence"]},
            )
            reader = InMemoryHandoff(context_memory=mem)
            body = reader.read(payload["memory_id"])
            self.assertIsNotNone(body)
            self.assertEqual(body["task_id"], "sess_2")
            self.assertEqual(body["status"], "NEEDS_REVIEW")
            self.assertIn("missing Expected_Evidence", body["remaining_risks"])
        finally:
            mem.close()

    def test_publish_without_memory_fails_closed(self):
        from integration.in_memory_handoff import InMemoryHandoff

        h = InMemoryHandoff(context_memory=None)
        with self.assertRaises(RuntimeError):
            h.publish(
                task_id="x",
                status="READY_FOR_REVIEW",
                response="y",
                validation={"valid": True, "violations": []},
            )

    def test_optional_file_write_is_secondary(self):
        import tempfile

        from integration.cautreo_binding import CautreoContextMemory
        from integration.in_memory_handoff import InMemoryHandoff

        mem = CautreoContextMemory(max_items=16)
        try:
            with tempfile.TemporaryDirectory() as td:
                h = InMemoryHandoff(context_memory=mem)
                payload = h.publish(
                    task_id="sess_3",
                    status="READY_FOR_REVIEW",
                    response="body",
                    validation={"valid": True, "violations": []},
                    file_path=os.path.join(td, "handoff.json"),
                )
                self.assertTrue(payload["in_memory"])
                self.assertIsNotNone(payload["memory_id"])
                self.assertTrue(os.path.exists(payload.get("file_path") or ""))
        finally:
            mem.close()


class Gate9LabelTests(unittest.TestCase):
    """P3 must not invent latency claims."""

    def test_interleaved_module_docstring_has_no_latency_claim(self):
        import ast

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "integration",
            "interleaved_dispatch.py",
        )
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        doc = ast.get_docstring(tree) or ""
        for line in doc.splitlines():
            if "[ISOLATED" in line:
                continue
            low = line.lower()
            self.assertNotIn("0ms", low)
            self.assertNotIn("0 ms", low)
            self.assertNotIn("0.00ms", low)
            self.assertNotIn("zero-latency", low)
            self.assertNotIn("15-30s", low.replace("–", "-"))
            self.assertNotIn("15–30s", low)
            self.assertNotIn("production-ready", low)


if __name__ == "__main__":
    unittest.main()
