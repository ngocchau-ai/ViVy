"""Tests for check_known_limits — KNOWN_LIMITATIONS consistency (D4)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from training.check_known_limits import check_known_limits, parse_limitations


class ParseLimitationsTests(unittest.TestCase):
    def test_parse_table_rows(self):
        text = """
## §2 Register

| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-01 | **NOT_RUN** | llama-server down. Receipt `evidence/receipt-001.json` = INFRA_INCOMPLETE. | C01 live |
| L-02 | **GAP** | no threshold table exists. | VM-x PASS |
"""
        entries = parse_limitations(text)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["id"], "L-01")
        self.assertEqual(entries[0]["label"], "NOT_RUN")
        self.assertIn("evidence/receipt-001.json", entries[0]["receipt_refs"])
        self.assertEqual(entries[1]["id"], "L-02")

    def test_parse_no_receipt_refs(self):
        text = """
| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-30 | **INCONCLUSIVE** | gold_outcome is unknown on all rows. | action-success |
"""
        entries = parse_limitations(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["receipt_refs"], [])


class CheckKnownLimitsTests(unittest.TestCase):
    def test_all_receipts_exist_passes(self):
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            limits = dp / "KNOWN_LIMITATIONS.md"
            receipts = dp / "evidence"
            receipts.mkdir()
            # Create the referenced receipt
            (receipts / "receipt-001.json").write_text("{}", encoding="utf-8")
            limits.write_text(
                "| L-01 | NOT_RUN | Receipt `evidence/receipt-001.json` down. | C01 |\n",
                encoding="utf-8",
            )
            result = check_known_limits(limits, receipts)
            self.assertEqual(result["status"], "PASS")

    def test_missing_receipt_fails(self):
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            limits = dp / "KNOWN_LIMITATIONS.md"
            receipts = dp / "evidence"
            receipts.mkdir()
            # receipt-001.json NOT created
            limits.write_text(
                "| L-01 | NOT_RUN | Receipt `evidence/receipt-001.json` down. | C01 |\n",
                encoding="utf-8",
            )
            result = check_known_limits(limits, receipts)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("receipt-001" in p for p in result["problems"]))

    def test_missing_limits_file_errors(self):
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            result = check_known_limits(dp / "nope.md", dp)
            self.assertEqual(result["status"], "ERROR")

    def test_missing_receipts_dir_errors(self):
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            limits = dp / "l.md"
            limits.write_text("x", encoding="utf-8")
            result = check_known_limits(limits, dp / "nope")
            self.assertEqual(result["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
