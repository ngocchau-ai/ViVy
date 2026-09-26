"""Tests for cautreo_91sh_tool (Unified 91sH Tool Workflow for ViVy).

Changelog:
    25/09/2026 (Antigravity IDE & ViVy Final — HoH 91sh Onboarding): Initial.
"""
from __future__ import annotations

import unittest

from training.cautreo_91sh_tool import Cautreo91shTool


class TestCautreo91shTool(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = Cautreo91shTool(dry_run=True)

    def test_tool_spec_shape(self) -> None:
        spec = Cautreo91shTool.tool_spec()
        self.assertEqual(spec["name"], "cautreo_91sh_workflow")
        self.assertIn("parameters", spec)
        self.assertIn("action", spec["parameters"]["properties"])
        self.assertIn("action", spec["parameters"]["required"])

    def test_dispatch_compile_problem(self) -> None:
        args = {
            "action": "compile_problem",
            "goal": "Refactor 91sh into a unified Cautreo tool workflow",
        }
        res = self.tool.dispatch(args)
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "compile_problem")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("problem_graph", res["evidence"])
        self.assertTrue(res["receipt_sha256"])

    def test_dispatch_run_workflow(self) -> None:
        args = {
            "action": "run_workflow",
            "goal": "Sequential review of 91sh branches and state labeling",
            "strategy": "MULTI_AGENT_VERIFIED",
        }
        res = self.tool.dispatch(args)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(len(res["steps"]), 3)
        self.assertEqual(res["steps"][0]["action"], "problem-compiler")
        self.assertEqual(res["steps"][1]["action"], "thought-state-engine")
        self.assertEqual(res["steps"][2]["action"], "verification-engine")
        self.assertTrue(res["evidence"]["contract_verified"])
        self.assertTrue(res["receipt_sha256"])

    def test_dispatch_run_workflow_missing_goal(self) -> None:
        args = {"action": "run_workflow"}
        res = self.tool.dispatch(args)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Missing required parameter", res["error_message"])

    def test_dispatch_query_status(self) -> None:
        args = {"action": "status"}
        res = self.tool.dispatch(args)
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "status")
        self.assertIn("providers", res["evidence"])
        self.assertIn("codex", res["evidence"]["providers"])

    def test_dispatch_audit(self) -> None:
        args = {
            "action": "audit",
            "context": {"target_path": "projects/91sh"},
        }
        res = self.tool.dispatch(args)
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "audit")
        self.assertEqual(res["evidence"]["verdict"], "PASS")

    def test_dispatch_unknown_action(self) -> None:
        args = {"action": "nonexistent_action"}
        res = self.tool.dispatch(args)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Unknown 91sh action", res["error_message"])


if __name__ == "__main__":
    unittest.main()
