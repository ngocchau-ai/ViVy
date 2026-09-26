"""C09 tests — thinking budget A/B is server-side verified, not self-declared."""
from __future__ import annotations

import unittest

from training.thinking_budget import (
    BUDGETS,
    ThinkingBudgetHarness,
    verify_server_thinking,
)


class BudgetHarnessTests(unittest.TestCase):
    def test_known_budgets(self):
        self.assertEqual(BUDGETS, (0, 384, 1024))

    def test_requested_budget_must_be_one_of_the_ab_set(self):
        harness = ThinkingBudgetHarness()
        with self.assertRaises(ValueError):
            harness.arm(requested_budget_tokens=512)

    def test_server_echo_must_match_request(self):
        ok = verify_server_thinking(
            requested_budget_tokens=384,
            server_reported_thinking_tokens=384,
            server_reported_budget=384,
        )
        self.assertTrue(ok["verified"])
        self.assertEqual(ok["verdict"], "PASS")

        bad = verify_server_thinking(
            requested_budget_tokens=384,
            server_reported_thinking_tokens=12,
            server_reported_budget=1024,
        )
        self.assertFalse(bad["verified"])
        self.assertEqual(bad["verdict"], "FAIL")

        # budget 0 must produce 0 thinking tokens
        zero_leak = verify_server_thinking(
            requested_budget_tokens=0,
            server_reported_thinking_tokens=7,
            server_reported_budget=0,
        )
        self.assertEqual(zero_leak["verdict"], "FAIL")

    def test_missing_server_fields_is_not_run_not_pass(self):
        result = verify_server_thinking(
            requested_budget_tokens=1024,
            server_reported_thinking_tokens=None,
            server_reported_budget=None,
        )
        self.assertEqual(result["verdict"], "NOT_RUN")
        self.assertFalse(result["verified"])

    def test_harness_refuses_self_attested_result(self):
        harness = ThinkingBudgetHarness()
        harness.arm(requested_budget_tokens=0)
        record = harness.close(
            server_reported_thinking_tokens=0,
            server_reported_budget=0,
            latency_ms=12.5,
        )
        self.assertEqual(record["verdict"], "PASS")
        self.assertEqual(record["budget"], 0)
        self.assertTrue(record["server_side_verified"])
        self.assertFalse(record["self_attested"])

        unverified = harness.arm(requested_budget_tokens=1024)
        record2 = harness.close(
            server_reported_thinking_tokens=None,
            server_reported_budget=None,
            latency_ms=None,
        )
        self.assertEqual(record2["verdict"], "NOT_RUN")
        self.assertFalse(record2["server_side_verified"])
        self.assertIsNone(record2["latency_ms"])


if __name__ == "__main__":
    unittest.main()
