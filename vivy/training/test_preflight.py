"""Preflight tests — §2.8 fail-closed gates, §2.9 non-zero exit on BLOCKED."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.preflight import PreflightBlocked, require_promotion_ready, run

# Changelog: 23/09/2026 (Claude Code — P6) split the empty-gold BLOCKED case
# from the live workspace (promoted gold_train.jsonl is no longer empty).
# Changelog: 24/09/2026 (Antigravity/Claude Code — P0) empty gold and missing
# shadow receipts no longer vacuously pass (§2.8); require_promotion_ready
# enforces non-zero exit (§2.9).


class PreflightTests(unittest.TestCase):
    def test_empty_gold_dataset_blocks_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "evidence").mkdir()
            report = run(d, run_contract_tests=False)
            self.assertEqual(report["promotion"], "BLOCKED")
            self.assertEqual(report["gold_rows"], 0)
            self.assertEqual(report["shadow_actuated"], 0)
            # §2.8: empty set must NOT vacuously pass.
            self.assertEqual(report["gates"]["gold_review_provenance"], "FAIL")
            self.assertEqual(report["gates"]["gold_dataset_nonempty"], "FAIL")

    def test_current_workspace_reports_promoted_gold_without_actuation(self):
        # run_contract_tests=False avoids preflight → unittest → preflight recursion.
        report = run(".", run_contract_tests=False)
        self.assertGreater(report["gold_rows"], 0)
        self.assertEqual(report["shadow_actuated"], 0)
        self.assertEqual(report["gates"]["gold_review_provenance"], "PASS")
        self.assertEqual(report["gates"]["shadow_non_actuating"], "PASS")

    def test_gold_review_provenance_passes_on_independently_reviewed_rows(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "evidence").mkdir()
            row = {
                "label_quality": "independently_reviewed",
                "provenance": {"review_receipt_id": "human-accept-abc"},
            }
            (d / "evidence" / "gold_train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            report = run(d, run_contract_tests=False)
            self.assertEqual(report["gates"]["gold_review_provenance"], "PASS")

    def test_gold_review_provenance_fails_on_missing_review_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "evidence").mkdir()
            row = {
                "label_quality": "independently_reviewed",
                "provenance": {},
            }
            (d / "evidence" / "gold_train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            report = run(d, run_contract_tests=False)
            self.assertEqual(report["gates"]["gold_review_provenance"], "FAIL")

    def test_gold_review_provenance_fails_on_unverified_label(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "evidence").mkdir()
            row = {
                "label_quality": "unverified",
                "provenance": {"review_receipt_id": "human-accept-abc"},
            }
            (d / "evidence" / "gold_train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            report = run(d, run_contract_tests=False)
            self.assertEqual(report["gates"]["gold_review_provenance"], "FAIL")

    def test_missing_shadow_receipt_file_is_fail_not_pass(self):
        """§2.8: a missing shadow file cannot prove non-actuation."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "evidence").mkdir()
            row = {
                "label_quality": "independently_reviewed",
                "provenance": {"review_receipt_id": "human-accept-abc"},
            }
            (d / "evidence" / "gold_train.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            report = run(d, run_contract_tests=False)
            self.assertEqual(report["gates"]["shadow_receipts_present"], "FAIL")
            self.assertEqual(report["gates"]["shadow_non_actuating"], "FAIL")

    def test_require_promotion_ready_raises_when_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(PreflightBlocked):
                require_promotion_ready(d, run_contract_tests=False)


if __name__ == "__main__":
    unittest.main()
