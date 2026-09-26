import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from training.triage_gold import triage


def _write_queue(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def _row(receipt_id: str, goal: str, candidates: list[dict], selected: str, observation: str = "Obs") -> dict:
    return {
        "decision_type": "choice",
        "context_state": f"Task Goal: {goal}\nObservation Context: {observation}",
        "candidates": candidates,
        "selected_candidate": selected,
        "confidence": 0.0,
        "evidence_required": ["- capture_id_matched: True"],
        "provenance": {
            "source": "cua_bounded_trajectory",
            "producer": "legacy_to_typed",
            "receipt_id": receipt_id,
            "timestamp": "extracted-not-observed",
        },
        "label_quality": "unverified",
        "split": "train",
        "review": {
            "gold_selected_candidate": None,
            "gold_outcome": None,
            "reviewer": None,
            "reviewed_at": None,
            "independent_receipt_id": None,
            "status": "PENDING",
        },
    }


TEMPLATE_ROWS = [
    _row(
        f"legacy-{557 + i}",
        f"Execute automated bounded workspace task #{i + 1:02d}",
        [
            {"id": f"cand_{i + 1:02d}_exec", "description": f"- [cand_{i + 1:02d}_exec]: Execute verified action step #{i + 1:02d} (action: click)"},
            {"id": f"cand_{i + 1:02d}_halt", "description": f"- [cand_{i + 1:02d}_halt]: Halt if precondition unmet (action: halt)"},
        ],
        f"cand_{i + 1:02d}_exec",
        observation=f"Workspace desktop window #{i + 1:02d} rendered with active GUI elements",
    )
    for i in range(3)
]

WEAK_ROW = _row(
    "legacy-455",
    "Handle unexpected network timeout during model weights download",
    [
        {"id": "cand_retry_backoff", "description": "- [cand_retry_backoff]: Wait 5s exponential backoff and retry request (action: retry)"},
        {"id": "cand_abort_wipe", "description": "- [cand_abort_wipe]: Wipe entire download cache (action: delete)"},
    ],
    "cand_retry_backoff",
)

STRONG_ROW = _row(
    "legacy-452",
    "Avoid unsafe dialog confirmation on unknown executable",
    [
        {"id": "cand_force", "description": "- [cand_force]: Force confirm without authorization (action: click)"},
        {"id": "cand_abstain", "description": "- [cand_abstain]: Halt and request human confirmation (action: halt)"},
    ],
    "cand_abstain",
)

AMBIGUOUS_ROW = _row(
    "legacy-999",
    "Do something with the window",
    [
        {"id": "a", "description": "- [a]: Click stuff (action: click)"},
        {"id": "b", "description": "- [b]: Click other stuff (action: click)"},
    ],
    "a",
)


class TriageClassificationTests(unittest.TestCase):
    def _triage(self, rows, **kwargs):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, rows)
            summary = triage(src, out, **kwargs)
            out_rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            return summary, out_rows

    def test_ambiguous_row_is_category_c(self):
        summary, out_rows = self._triage([AMBIGUOUS_ROW])
        self.assertEqual(summary["categories"]["C"], 1)
        self.assertEqual(out_rows[0]["category"], "C")
        self.assertIsNone(out_rows[0]["proposed_selected_candidate"])

    def test_template_tier_c_demotes_template_rows(self):
        summary, out_rows = self._triage(TEMPLATE_ROWS, template_tier="C")
        self.assertEqual(summary["categories"]["C"], 3)
        self.assertEqual(summary["categories"].get("A", 0), 0)
        for row in out_rows:
            self.assertEqual(row["category"], "C")

    def test_weak_tier_c_demotes_weak_rows(self):
        summary, out_rows = self._triage([WEAK_ROW], weak_tier="C")
        self.assertEqual(summary["categories"]["C"], 1)
        self.assertEqual(out_rows[0]["category"], "C")

    def test_default_tiers_keep_A_categories(self):
        summary, out_rows = self._triage([STRONG_ROW, WEAK_ROW] + TEMPLATE_ROWS)
        self.assertEqual(summary["categories"]["A"], 5)
        self.assertEqual(summary["tiers"]["A_strong"], 1)
        self.assertEqual(summary["tiers"]["A_weak"], 1)
        self.assertEqual(summary["tiers"]["A_template"], 3)
        self.assertEqual(summary["categories"].get("C", 0), 0)


class TriageDisagreementTests(unittest.TestCase):
    def test_disagreement_detection(self):
        # Build a row where oracle proposes cand_abstain but legacy says cand_force.
        row = _row(
            "legacy-452",
            "Avoid unsafe dialog confirmation on unknown executable",
            [
                {"id": "cand_force", "description": "- [cand_force]: Force confirm without authorization (action: click)"},
                {"id": "cand_abstain", "description": "- [cand_abstain]: Halt and request human confirmation (action: halt)"},
            ],
            "cand_force",  # legacy disagrees with oracle
        )
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, [row])
            summary = triage(src, out)
            out_rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(summary["disagreements"]), 1)
            self.assertTrue(out_rows[0]["disagrees_with_legacy"])
            self.assertEqual(out_rows[0]["proposed_selected_candidate"], "cand_abstain")

    def test_agreement_has_no_disagreement(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, [STRONG_ROW])
            summary = triage(src, out)
            self.assertEqual(len(summary["disagreements"]), 0)


class TriageIntegrityTests(unittest.TestCase):
    def test_queue_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            rows = [STRONG_ROW, WEAK_ROW] + TEMPLATE_ROWS
            _write_queue(src, rows)
            before = hashlib.sha256(src.read_bytes()).hexdigest()
            triage(src, out)
            after = hashlib.sha256(src.read_bytes()).hexdigest()
            self.assertEqual(before, after)

    def test_output_has_no_gold_fields(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, [STRONG_ROW])
            triage(src, out)
            out_rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            for row in out_rows:
                self.assertNotIn("gold_selected_candidate", row)
                self.assertNotIn("gold_outcome", row)
                self.assertNotIn("reviewer", row)
                self.assertNotIn("independent_receipt_id", row)
                self.assertNotIn("review", row)

    def test_refuse_queue_with_gold_fields(self):
        row = dict(STRONG_ROW)
        row["review"] = dict(STRONG_ROW["review"], gold_selected_candidate="cand_abstain", status="REVIEWED")
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, [row])
            with self.assertRaises(ValueError):
                triage(src, out)

    def test_proposal_receipt_id_present(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, [STRONG_ROW])
            triage(src, out)
            out_rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(out_rows[0]["proposal_receipt_id"].startswith("oracle-"))
            self.assertEqual(out_rows[0]["rule_version"], "gold_rules_v1")

    def test_agrees_with_legacy_field_present(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "queue.jsonl"
            out = Path(d) / "triage.jsonl"
            _write_queue(src, [STRONG_ROW])
            triage(src, out)
            out_rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertIn("agrees_with_legacy", out_rows[0])
            self.assertTrue(out_rows[0]["agrees_with_legacy"])
            self.assertFalse(out_rows[0]["disagrees_with_legacy"])


if __name__ == "__main__":
    unittest.main()
