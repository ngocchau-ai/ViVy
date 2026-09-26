"""Tests for sandbox_capture — P3 safe-subset predicate + sandbox isolation (D2)."""
from __future__ import annotations

import sys
import unittest

from training.sandbox_capture import (
    capture_row,
    capture_sandboxed,
    is_safe_subset,
    is_safe_subset_text,
)


class SafeSubsetTests(unittest.TestCase):
    def test_safe_row_passes(self):
        row = {"action": "read_file", "evidence": "parse JSON output", "intent": "summarize"}
        self.assertTrue(is_safe_subset(row))

    def test_destructive_action_refused(self):
        row = {"action": "delete_cache", "evidence": "cleanup old data"}
        self.assertFalse(is_safe_subset(row))

    def test_destructive_evidence_refused(self):
        row = {"action": "read_file", "evidence": "wipe all logs"}
        self.assertFalse(is_safe_subset(row))

    def test_case_insensitive(self):
        row = {"action": "RM -RF", "evidence": "DROP TABLE users"}
        self.assertFalse(is_safe_subset(row))

    def test_text_variant(self):
        self.assertTrue(is_safe_subset_text("just a normal sentence"))
        self.assertFalse(is_safe_subset_text("please shutdown the server"))

    def test_empty_row_is_safe(self):
        self.assertTrue(is_safe_subset({}))


class SandboxCaptureTests(unittest.TestCase):
    def test_successful_command_returns_observed(self):
        result = capture_sandboxed(
            [sys.executable, "-c", "print('ok')"],
            row_id="test-1",
        )
        self.assertEqual(result["status"], "OBSERVED")
        self.assertTrue(result["sandbox"])
        self.assertEqual(result["side_effect_repeats"], 0)
        self.assertEqual(result["kind"], "observed_outcome")

    def test_failed_command_returns_sandbox_crash(self):
        result = capture_sandboxed(
            [sys.executable, "-c", "import sys; sys.exit(1)"],
            row_id="test-2",
        )
        self.assertEqual(result["status"], "SANDBOX_CRASH")

    def test_timeout_returns_sandbox_crash(self):
        result = capture_sandboxed(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            row_id="test-3",
            timeout_s=0.5,
        )
        self.assertEqual(result["status"], "SANDBOX_CRASH")
        self.assertIn("timeout", result.get("reason", ""))

    def test_destructive_row_refused(self):
        row = {"action": "kill_process", "evidence": "force stop"}
        result = capture_row(row, row_id="test-4", command=[sys.executable, "-c", "print(1)"])
        self.assertEqual(result["status"], "REFUSED_DESTRUCTIVE")

    def test_no_command_returns_not_run(self):
        row = {"action": "read_file", "evidence": "parse"}
        result = capture_row(row, row_id="test-5")
        self.assertEqual(result["status"], "NOT_RUN")

    def test_safe_row_with_command_observes(self):
        row = {"action": "read_file", "evidence": "parse"}
        result = capture_row(row, row_id="test-6", command=[sys.executable, "-c", "print('hi')"])
        self.assertEqual(result["status"], "OBSERVED")


if __name__ == "__main__":
    unittest.main()
