"""C06 tests — training smoke is gated, tiny, and never claims RLCD for SFTTrainer-only."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.smoke_train import (
    CLAIM_CEILING,
    NOT_RLCD,
    SmokeTrainBlocked,
    run_smoke,
)


def _gold_rows(n: int = 8) -> str:
    lines = []
    for i in range(n):
        lines.append(json.dumps({
            "task_id": f"task-{i}",
            "decision_type": "choice",
            "context_state": f"Goal {i}",
            "candidates": [{"id": "a", "description": "save"}, {"id": "b", "description": "halt"}],
            "selected_candidate": "a" if i % 2 == 0 else "b",
            "split": "train",
            "label_quality": "independently_reviewed",
            "gold_outcome": "unknown",
            "provenance": {
                "group_key": f"g{i}", "receipt_id": f"legacy-{i}-abc",
                "review_receipt_id": f"human-accept-{i:016x}",
                "source_file_sha256": "a",
            },
        }))
    return "\n".join(lines) + "\n"


class SmokeGateTests(unittest.TestCase):
    def test_refuses_legacy_501_dataset(self):
        with tempfile.TemporaryDirectory() as d:
            legacy = Path(d) / "vivy_train_dataset.jsonl"
            legacy.write_text(_gold_rows(4), encoding="utf-8")
            gold = Path(d) / "gold_train.jsonl"
            gold.write_text(_gold_rows(4), encoding="utf-8")
            with self.assertRaises(SmokeTrainBlocked):
                run_smoke(legacy, steps=1)

    def test_requires_preflight_ready(self):
        with tempfile.TemporaryDirectory() as d:
            # empty gold + missing shadow ⇒ preflight BLOCKED
            gold = Path(d) / "gold_train.jsonl"
            gold.write_text(_gold_rows(4), encoding="utf-8")
            result = run_smoke(gold, steps=1, root=d, require_preflight=True)
            self.assertFalse(result["preflight_ok"])
            self.assertEqual(result["n_steps"], 0)
            self.assertTrue(result["blocked"])

    def test_smoke_is_tiny_and_labels_itself(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "evidence").mkdir()
            (root / "evidence" / "gold_train.jsonl").write_text(_gold_rows(8), encoding="utf-8")
            (root / "evidence" / "shadow_receipts.jsonl").write_text("{}\n", encoding="utf-8")
            gold = root / "evidence" / "gold_train.jsonl"
            result = run_smoke(gold, steps=2, root=root, require_preflight=True)
            self.assertTrue(result["preflight_ok"])
            self.assertLessEqual(result["n_steps"], 8)
            self.assertEqual(result["claim_ceiling"], CLAIM_CEILING)
            self.assertEqual(result["rlcd_claim"], NOT_RLCD)
            self.assertIn("smoke", result["label"].lower())
            self.assertFalse(result.get("is_full_sft", False))

    def test_escalating_steps_still_capped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "evidence").mkdir()
            (root / "evidence" / "gold_train.jsonl").write_text(_gold_rows(8), encoding="utf-8")
            (root / "evidence" / "shadow_receipts.jsonl").write_text("{}\n", encoding="utf-8")
            gold = root / "evidence" / "gold_train.jsonl"
            result = run_smoke(gold, steps=10_000, root=root, require_preflight=True)
            self.assertLessEqual(result["n_steps"], 8)
            self.assertTrue(result["capped"])


class ClaimLabelTests(unittest.TestCase):
    def test_sfttrainer_only_is_not_rlcd(self):
        self.assertEqual(NOT_RLCD, "NOT_RLCD_SFTTRAINER_ONLY")

    def test_claim_ceiling_is_provisional(self):
        self.assertEqual(CLAIM_CEILING, "PROVISIONAL_RESULT")


if __name__ == "__main__":
    unittest.main()
