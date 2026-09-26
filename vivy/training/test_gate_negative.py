"""GATE_NEGATIVE_TESTS — every fail-closed gate must actually block (C01 deliverable).

These are negative cases, not quality evidence. A gate that passes its happy
path but accepts a negative is a P0-class blocker (acceptance plan §6).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.io_guard import RefuseOverwriteError, open_write
from training.preflight import PreflightBlocked, require_promotion_ready, run as preflight_run
from training.promote_reviewed import promote
from training.receipt import build_receipt, gates_pass, write_receipt
from training.shadow_router import recommend, replay_copy_label


class PromotionNegatives(unittest.TestCase):
    def _row(self, **review_overrides) -> dict:
        review = {
            "status": "REVIEWED",
            "gold_selected_candidate": "cand_a",
            "gold_outcome": "unknown",
            "reviewer": "human",
            "reviewed_at": "2026-09-24T00:00:00Z",
            "independent_receipt_id": "human-accept-0123456789abcdef",
        }
        review.update(review_overrides)
        return {
            "decision_type": "choice",
            "candidates": [{"id": "cand_a"}, {"id": "cand_b"}],
            "selected_candidate": "cand_b",
            "review": review,
            "provenance": {"receipt_id": "legacy-1-x"},
        }

    def _promote_one(self, row, **kwargs):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps(row) + "\n", encoding="utf-8")
            return promote(source, output, **kwargs)

    def test_rejected_status_blocks(self):
        counts = self._promote_one(self._row(status="REJECTED"))
        self.assertEqual(counts["promoted"], 0)
        self.assertEqual(counts["rejected_status"], 1)

    def test_unknown_status_blocks(self):
        counts = self._promote_one(self._row(status="UNKNOWN"))
        self.assertEqual(counts["promoted"], 0)

    def test_fake_receipt_format_blocks(self):
        counts = self._promote_one(self._row(independent_receipt_id="trust-me-bro"))
        self.assertEqual(counts["rejected_receipt"], 1)

    def test_stale_receipt_not_in_index_blocks(self):
        counts = self._promote_one(
            self._row(independent_receipt_id="human-accept-0123456789abcdef"),
            known_receipt_ids={"human-accept-ffffffffffffffff"},
        )
        self.assertEqual(counts["rejected_receipt"], 1)

    def test_wrong_task_candidate_blocks(self):
        counts = self._promote_one(self._row(gold_selected_candidate="cand_from_other_task"))
        self.assertEqual(counts["rejected_candidate"], 1)

    def test_missing_required_field_blocks(self):
        counts = self._promote_one(self._row(reviewer=""))
        self.assertEqual(counts["rejected_missing_fields"], 1)

    def test_unknown_outcome_is_not_outcome_calibration(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps(self._row(gold_outcome="unknown")) + "\n", encoding="utf-8")
            promote(source, output)
            row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
        self.assertFalse(row["provenance"]["eligible_for_outcome_calibration"])


class ReceiptGateNegatives(unittest.TestCase):
    def test_empty_gates_do_not_promote(self):
        self.assertFalse(gates_pass({}))
        receipt = build_receipt(
            run_id="neg-1", stage="x", metrics={}, gates={}, input_sha256="a",
        )
        self.assertEqual(receipt["promotion"], "BLOCKED")

    def test_single_fail_gate_blocks(self):
        receipt = build_receipt(
            run_id="neg-2", stage="x", metrics={},
            gates={"a": "PASS", "b": "FAIL"}, input_sha256="a",
        )
        self.assertEqual(receipt["promotion"], "BLOCKED")

    def test_non_pass_value_blocks(self):
        self.assertFalse(gates_pass({"a": "PASS", "b": "SKIP"}))
        self.assertFalse(gates_pass({"a": "pass"}))  # case-sensitive


class PreflightNegatives(unittest.TestCase):
    def test_empty_gold_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "evidence").mkdir()
            report = preflight_run(d, run_contract_tests=False)
        self.assertEqual(report["promotion"], "BLOCKED")

    def test_missing_shadow_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "evidence").mkdir()
            (root / "evidence" / "gold_train.jsonl").write_text(
                json.dumps({
                    "label_quality": "independently_reviewed",
                    "provenance": {"review_receipt_id": "human-accept-abc"},
                }) + "\n",
                encoding="utf-8",
            )
            report = preflight_run(root, run_contract_tests=False)
        self.assertEqual(report["gates"]["shadow_receipts_present"], "FAIL")

    def test_actuated_shadow_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "evidence").mkdir()
            (root / "evidence" / "gold_train.jsonl").write_text(
                json.dumps({
                    "label_quality": "independently_reviewed",
                    "provenance": {"review_receipt_id": "human-accept-abc"},
                }) + "\n",
                encoding="utf-8",
            )
            (root / "evidence" / "shadow_receipts.jsonl").write_text(
                json.dumps({"actuated": True}) + "\n", encoding="utf-8",
            )
            report = preflight_run(root, run_contract_tests=False)
        self.assertEqual(report["gates"]["shadow_non_actuating"], "FAIL")

    def test_require_raises_so_trainer_stops(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(PreflightBlocked):
                require_promotion_ready(d, run_contract_tests=False)


class RouterLeakNegatives(unittest.TestCase):
    def test_label_is_not_recommended(self):
        result = recommend({
            "decision_type": "choice",
            "candidates": [{"id": "a"}],
            "selected_candidate": "a",
            "label_quality": "independently_reviewed",
        })
        self.assertIsNone(result.recommendation)

    def test_leaky_copy_is_tagged_and_not_accuracy(self):
        result = replay_copy_label({
            "decision_type": "choice",
            "candidates": [{"id": "a"}],
            "selected_candidate": "a",
            "label_quality": "independently_reviewed",
        })
        self.assertIn("LEAKY", result.policy)
        # Agreement here is tautological — never score it as accuracy (§2.3).
        self.assertTrue(result.agree)
        self.assertIn("CIRCULAR", result.note)

    def test_unverified_never_recommended(self):
        result = recommend({
            "decision_type": "choice",
            "candidates": [{"id": "a"}],
            "selected_candidate": "a",
            "label_quality": "unverified",
            "predicted_candidate": "a",
        })
        self.assertIsNone(result.recommendation)
        self.assertEqual(result.policy, "abstain_unverified")


class IoGuardNegatives(unittest.TestCase):
    def test_source_alias_cannot_be_clobbered(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text("x\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                open_write(src, protected=(src,))

    def test_existing_receipt_cannot_be_clobbered(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipt.json"
            p.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                open_write(p)


if __name__ == "__main__":
    unittest.main()
