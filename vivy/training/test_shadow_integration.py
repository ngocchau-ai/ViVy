"""C07 tests — shadow integration is default-off and never calls a tool."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.shadow_integration import (
    ShadowIntegration,
    ShadowIntegrationBlocked,
    run_shadow_integration,
)


class DefaultOffTests(unittest.TestCase):
    def test_default_is_off(self):
        si = ShadowIntegration()
        self.assertFalse(si.enabled)
        self.assertFalse(si.tool_calls_allowed)

    def test_run_without_enable_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text(json.dumps({
                "decision_type": "choice",
                "context_state": "goal",
                "candidates": [{"id": "a", "description": "save"}],
            }) + "\n", encoding="utf-8")
            out = Path(d) / "out.jsonl"
            with self.assertRaises(ShadowIntegrationBlocked):
                run_shadow_integration(src, out)
            self.assertFalse(out.exists())


class NoToolCallTests(unittest.TestCase):
    def test_tool_call_attempt_is_blocked_and_counted(self):
        si = ShadowIntegration(enabled=True)
        with self.assertRaises(ShadowIntegrationBlocked):
            si.call_tool("click", {"x": 1})
        self.assertEqual(si.tool_calls_attempted, 1)
        self.assertEqual(si.tool_calls_executed, 0)

    def test_actuation_attempt_is_blocked(self):
        si = ShadowIntegration(enabled=True)
        with self.assertRaises(ShadowIntegrationBlocked):
            si.actuate("EXECUTE_DIRECTLY")
        self.assertEqual(si.actuations_executed, 0)

    def test_receipt_carries_no_tool_call_proof(self):
        si = ShadowIntegration(enabled=True)
        receipt = si.receipt_for({
            "decision_type": "choice",
            "context_state": "goal",
            "candidates": [{"id": "a", "description": "save"}],
            "selected_candidate": "a",
            "label_quality": "independently_reviewed",
        })
        self.assertEqual(receipt["tool_calls_executed"], 0)
        self.assertEqual(receipt["actuations_executed"], 0)
        self.assertTrue(receipt["no_tool_call_proof"])
        self.assertFalse(receipt["actuated"])
        self.assertEqual(receipt["status"], "SHADOW_ONLY")
        self.assertTrue(receipt["default_off_boundary"])

    def test_run_emits_instrumented_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text(json.dumps({
                "decision_type": "choice",
                "context_state": "goal",
                "candidates": [{"id": "a", "description": "save"}, {"id": "halt", "description": "halt"}],
                "selected_candidate": "a",
                "label_quality": "unverified",
            }) + "\n", encoding="utf-8")
            out = Path(d) / "out.jsonl"
            n = run_shadow_integration(src, out, enable_shadow=True)
            self.assertEqual(n, 1)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(receipt["no_tool_call_proof"])
            self.assertEqual(receipt["tool_calls_executed"], 0)
            self.assertFalse(receipt["actuated"])


if __name__ == "__main__":
    unittest.main()
