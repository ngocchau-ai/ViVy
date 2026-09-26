"""P6 typed-decision metrics track tests (Gate 10).

Brier / ECE / permutation-KL over human-confirmed gold selection labels.
`gold_outcome` is `unknown` on every current gold row — outcome metrics must
stay UNVERIFIED and must never be invented.

Cấm: full SFT/LoRA on the 501 legacy rows. This module scores decisions; it
does not train.

Changelog:
    23/09/2026 (Claude Code — P6 typed-decision metrics): Initial.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from training.typed_decision_metrics import (
    METRICS_STATUS_LABEL,
    evaluate_gold,
    permutation_kl,
    selection_brier,
    write_receipt,
)


def _row(
    *,
    selected: str = "cand_a",
    gold_selected: str | None = "cand_a",
    gold_outcome: str = "unknown",
    confidence: float = 0.0,
    n_cands: int = 2,
    ids: list[str] | None = None,
) -> dict:
    cand_ids = ids or [f"cand_{chr(ord('a') + i)}" for i in range(n_cands)]
    return {
        "decision_type": "choice",
        "context_state": "Task Goal: fixture\nObservation Context: fixture",
        "candidates": [{"id": cid, "description": f"- [{cid}]: act"} for cid in cand_ids],
        "selected_candidate": selected,
        "confidence": confidence,
        "evidence_required": ["postcondition"],
        "provenance": {
            "source": "fixture",
            "producer": "test",
            "receipt_id": "legacy-fixture",
            "timestamp": "2026-09-23T00:00:00Z",
            "review_receipt_id": "human-accept-fixture",
        },
        "label_quality": "independently_reviewed",
        "split": "test",
        "review": {
            "gold_selected_candidate": gold_selected,
            "gold_outcome": gold_outcome,
            "reviewer": "vinguyen",
            "reviewed_at": "2026-09-23T00:00:00Z",
            "independent_receipt_id": "human-accept-fixture",
            "status": "REVIEWED",
        },
    }


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OutcomeMetricGateTests(unittest.TestCase):
    def test_unknown_outcomes_leave_brier_and_ece_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, [_row(), _row(selected="cand_b", gold_selected="cand_b")])
            rec = evaluate_gold(path)

        self.assertIsNone(rec.metrics["outcome_brier"])
        self.assertIsNone(rec.metrics["ece"])
        self.assertEqual(rec.metrics["outcome_brier_status"], "UNVERIFIED")
        self.assertEqual(rec.metrics["ece_status"], "UNVERIFIED")
        self.assertEqual(rec.metrics["n_outcome_known"], 0)
        self.assertEqual(rec.metrics["n_outcome_unknown"], 2)

    def test_known_outcomes_compute_brier_and_ece(self):
        rows = [
            _row(selected="cand_a", gold_selected="cand_a", gold_outcome="success"),
            _row(selected="cand_b", gold_selected="cand_b", gold_outcome="failure"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, rows)
            rec = evaluate_gold(path)

        self.assertIsNotNone(rec.metrics["outcome_brier"])
        self.assertIsNotNone(rec.metrics["ece"])
        self.assertEqual(rec.metrics["outcome_brier_status"], "MEASURED")
        self.assertEqual(rec.metrics["n_outcome_known"], 2)

    def test_evaluate_never_invents_gold_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            before = _write_jsonl(path, [_row(gold_outcome="unknown")])
            evaluate_gold(path)
            after = hashlib.sha256(path.read_bytes()).hexdigest()
            loaded = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(before, after)
        self.assertEqual(loaded["review"]["gold_outcome"], "unknown")


class SelectionBrierTests(unittest.TestCase):
    def test_perfect_one_hot_selection_scores_zero(self):
        dist = {"cand_a": 1.0, "cand_b": 0.0}
        self.assertAlmostEqual(selection_brier(dist, "cand_a"), 0.0)

    def test_wrong_one_hot_selection_scores_one(self):
        dist = {"cand_a": 1.0, "cand_b": 0.0}
        self.assertAlmostEqual(selection_brier(dist, "cand_b"), 1.0)

    def test_uniform_distribution_is_between(self):
        dist = {"cand_a": 0.5, "cand_b": 0.5}
        score = selection_brier(dist, "cand_a")
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)


class PermutationKlTests(unittest.TestCase):
    def test_stable_selection_has_zero_kl(self):
        kl = permutation_kl(original="cand_a", predictions=["cand_a", "cand_a", "cand_a"])
        self.assertAlmostEqual(kl, 0.0)

    def test_flipped_selection_has_positive_kl(self):
        kl = permutation_kl(original="cand_a", predictions=["cand_b", "cand_b", "cand_a"])
        self.assertGreater(kl, 0.0)

    def test_position_invariant_oracle_is_stable_under_permutation(self):
        """gold_oracle.propose is order-invariant — flip rate must be 0."""
        rows = [
            _row(
                selected="cand_save",
                gold_selected="cand_save",
                ids=["cand_save", "cand_discard"],
            )
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, rows)
            rec = evaluate_gold(path, permutation_seeds=5)

        self.assertAlmostEqual(rec.metrics["oracle_permutation_flip_rate"], 0.0)
        self.assertAlmostEqual(rec.metrics["oracle_permutation_kl"], 0.0)

    def test_position_sensitive_policy_is_unstable(self):
        rows = [
            _row(
                selected="cand_b",
                gold_selected="cand_b",
                ids=["cand_a", "cand_b", "cand_c"],
            )
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, rows)
            rec = evaluate_gold(
                path, permutation_seeds=6, policy="first_candidate"
            )

        self.assertGreater(rec.metrics["policy_permutation_flip_rate"], 0.0)


class SchemaAndProvenanceTests(unittest.TestCase):
    def test_schema_valid_rate_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, [_row(), _row(selected="cand_b", gold_selected="cand_b")])
            rec = evaluate_gold(path)

        self.assertEqual(rec.metrics["n_rows"], 2)
        self.assertEqual(rec.metrics["n_schema_valid"], 2)
        self.assertAlmostEqual(rec.metrics["schema_valid_rate"], 1.0)
        self.assertEqual(rec.metrics["n_independently_reviewed"], 2)

    def test_invalid_row_lowers_schema_rate(self):
        bad = _row()
        bad["confidence"] = 5.0  # out of range
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, [_row(), bad])
            rec = evaluate_gold(path)

        self.assertEqual(rec.metrics["n_schema_valid"], 1)
        self.assertAlmostEqual(rec.metrics["schema_valid_rate"], 0.5)


class NoTrainingGuardTests(unittest.TestCase):
    def test_sft_lora_flag_is_always_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, [_row()])
            rec = evaluate_gold(path)

        self.assertFalse(rec.metrics["sft_lora_executed"])
        self.assertEqual(rec.gate10_status, "UNVERIFIED")

    def test_module_does_not_import_training_stacks(self):
        import ast
        import inspect

        import training.typed_decision_metrics as mod

        src = inspect.getsource(mod)
        tree = ast.parse(src)
        banned = {"peft", "transformers", "trl", "torch", "SFTTrainer", "LoRa", "LoRA"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], banned)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn("SFTTrainer", node.value)
                self.assertNotIn("PRODUCTION-READY", node.value)


class ReceiptSchemaTests(unittest.TestCase):
    def test_receipt_carries_honest_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.jsonl"
            _write_jsonl(path, [_row()])
            rec = evaluate_gold(path)
            out = Path(tmp) / "receipt.json"
            write_receipt(rec, out)
            loaded = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(loaded["status_label"], METRICS_STATUS_LABEL)
        self.assertEqual(loaded["gate10_status"], "UNVERIFIED")
        self.assertIn("oracle_agreement_status", loaded["metrics"])
        self.assertEqual(
            loaded["metrics"]["oracle_agreement_status"], "DESCRIPTIVE_ONLY"
        )
        text = json.dumps(loaded)
        self.assertNotIn("PRODUCTION-READY", text)
        self.assertNotIn("RLCD complete", text)


if __name__ == "__main__":
    unittest.main()
