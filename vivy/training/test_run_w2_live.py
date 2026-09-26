"""Tests for run_w2_live — W2 orchestrator (D6)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.run_w2_live import (
    is_terminal_honest,
    make_check_result,
    run_w2,
    write_aggregate_receipt,
)


class TerminalHonestTests(unittest.TestCase):
    def test_pass_is_honest(self):
        r = make_check_result("C01", "PASS", accuracy=0.8, denominator=5)
        self.assertTrue(is_terminal_honest(r))

    def test_not_run_with_honesty_rule_is_honest(self):
        r = make_check_result(
            "C01", "NOT_RUN",
            accuracy=None,
            reason="INFRA_INCOMPLETE",
            infra_absent=True,
            limitations_updated=True,
        )
        self.assertTrue(is_terminal_honest(r))

    def test_not_run_without_infra_absent_is_dishonest(self):
        r = make_check_result(
            "C01", "NOT_RUN",
            accuracy=None,
            reason="INFRA_INCOMPLETE",
            infra_absent=False,
            limitations_updated=True,
        )
        self.assertFalse(is_terminal_honest(r))

    def test_not_run_without_reason_is_dishonest(self):
        r = make_check_result(
            "C01", "NOT_RUN",
            accuracy=None,
            reason="LAZY",
            infra_absent=True,
            limitations_updated=True,
        )
        self.assertFalse(is_terminal_honest(r))

    def test_not_run_without_limitations_update_is_dishonest(self):
        r = make_check_result(
            "C01", "NOT_RUN",
            accuracy=None,
            reason="INFRA_INCOMPLETE",
            infra_absent=True,
            limitations_updated=False,
        )
        self.assertFalse(is_terminal_honest(r))

    def test_fail_is_not_honest(self):
        r = make_check_result("C01", "FAIL", accuracy=0.0, denominator=5)
        self.assertFalse(is_terminal_honest(r))


class RunW2Tests(unittest.TestCase):
    def test_all_pass_exits_0(self):
        checks = [lambda: make_check_result("C01", "PASS", accuracy=1.0, denominator=5) for _ in range(6)]
        report = run_w2(checks)
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["aggregate_status"], "TERMINAL_HONEST")

    def test_all_honest_not_run_exits_0(self):
        def honest_not_run(cid):
            return lambda: make_check_result(
                cid, "NOT_RUN", accuracy=None,
                reason="INFRA_INCOMPLETE", infra_absent=True, limitations_updated=True,
            )
        checks = [honest_not_run(f"C{i}") for i in range(6)]
        report = run_w2(checks)
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["aggregate_status"], "TERMINAL_HONEST")

    def test_any_fail_exits_1(self):
        checks = [
            lambda: make_check_result("C01", "PASS", accuracy=1.0, denominator=5),
            lambda: make_check_result("C09", "FAIL", accuracy=0.0, denominator=5),
            lambda: make_check_result("C10", "PASS", accuracy=1.0, denominator=5),
            lambda: make_check_result("C11", "PASS", accuracy=1.0, denominator=5),
            lambda: make_check_result("C12", "PASS", accuracy=1.0, denominator=5),
            lambda: make_check_result("C01b", "PASS", accuracy=1.0, denominator=5),
        ]
        report = run_w2(checks)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["aggregate_status"], "FAIL")
        self.assertEqual(report["fail_count"], 1)

    def test_all_infra_absent_exits_3(self):
        def raw_not_run(cid):
            return lambda: make_check_result(
                cid, "NOT_RUN", accuracy=None,
                reason="INFRA_INCOMPLETE", infra_absent=True, limitations_updated=False,
            )
        checks = [raw_not_run(f"C{i}") for i in range(6)]
        report = run_w2(checks)
        self.assertEqual(report["exit_code"], 3)

    def test_dishonest_not_run_exits_1(self):
        checks = [
            lambda: make_check_result(
                "C01", "NOT_RUN", accuracy=None,
                reason="LAZY", infra_absent=False, limitations_updated=False,
            )
            for _ in range(6)
        ]
        report = run_w2(checks)
        self.assertEqual(report["exit_code"], 1)


class WriteAggregateReceiptTests(unittest.TestCase):
    def test_write_aggregate_receipt(self):
        checks = [lambda: make_check_result("C01", "PASS", accuracy=1.0, denominator=5)]
        report = run_w2(checks)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "w2_aggregate.json"
            write_aggregate_receipt(report, p)
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["aggregate_status"], "TERMINAL_HONEST")
            self.assertEqual(data["check_count"], 1)


if __name__ == "__main__":
    unittest.main()
