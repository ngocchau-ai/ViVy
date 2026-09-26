"""Promotion tests — §2.7 fail-closed promotion + §2.11 no clobber."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.io_guard import RefuseOverwriteError
from training.promote_reviewed import promote


def _row(**review_overrides) -> dict:
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
        "provenance": {"source": "legacy", "producer": "legacy_to_typed", "receipt_id": "legacy-1-x", "timestamp": "extracted-not-observed"},
    }


class PromoteTests(unittest.TestCase):
    def test_pending_rows_are_not_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps({"review": {"status": "PENDING"}}) + "\n", encoding="utf-8")
            result = promote(source, output)
            self.assertEqual(result["input"], 1)
            self.assertEqual(result["promoted"], 0)
            self.assertEqual(result["pending"], 1)
            self.assertEqual(result["rejected"], 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "")

    def test_non_reviewed_status_is_rejected(self):
        for status in ("REJECTED", "UNKNOWN", "DRAFT", ""):
            with tempfile.TemporaryDirectory() as d:
                source, output = Path(d) / "in.jsonl", Path(d) / f"out-{status}.jsonl"
                source.write_text(json.dumps(_row(status=status)) + "\n", encoding="utf-8")
                result = promote(source, output)
                self.assertEqual(result["promoted"], 0, status)
                self.assertEqual(result["rejected_status"], 1, status)

    def test_candidate_outside_list_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps(_row(gold_selected_candidate="cand_zzz")) + "\n", encoding="utf-8")
            result = promote(source, output)
            self.assertEqual(result["rejected_candidate"], 1)
            self.assertEqual(result["promoted"], 0)

    def test_unresolvable_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps(_row(independent_receipt_id="not-a-receipt")) + "\n", encoding="utf-8")
            result = promote(source, output)
            self.assertEqual(result["rejected_receipt"], 1)

    def test_known_receipt_index_is_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps(_row(independent_receipt_id="human-accept-0123456789abcdef")) + "\n", encoding="utf-8")
            result = promote(source, output, known_receipt_ids=set())
            self.assertEqual(result["rejected_receipt"], 1)
            result2 = promote(source, Path(d) / "out2.jsonl", known_receipt_ids={"human-accept-0123456789abcdef"})
            self.assertEqual(result2["promoted"], 1)

    def test_unknown_outcome_is_selection_only_not_outcome_calibration(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps(_row(gold_outcome="unknown")) + "\n", encoding="utf-8")
            result = promote(source, output)
            self.assertEqual(result["promoted"], 1)
            self.assertEqual(result["outcome_unknown_selection_only"], 1)
            row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
            self.assertFalse(row["provenance"]["gold_outcome_known"])
            self.assertFalse(row["provenance"]["eligible_for_outcome_calibration"])

    def test_refuses_to_overwrite_source_or_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "in.jsonl"
            source.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                promote(source, source)
            out = Path(d) / "out.jsonl"
            promote(source, out)
            with self.assertRaises(RefuseOverwriteError):
                promote(source, out)


if __name__ == "__main__":
    unittest.main()
