"""C05 tests — independent baselines, Brier/ECE, ID-permutation stability."""
from __future__ import annotations

import unittest

from training.independent_baselines import (
    BASELINE_GOLD_COPY_FIXTURE,
    BASELINE_SEEDED_RANDOM,
    BASELINE_FIRST_CANDIDATE,
    BASELINE_TAXONOMY_MAJORITY,
    BASELINE_TFIDF_LOGREG,
    brier_multiclass,
    ece_binary,
    fit_tfidf_logreg,
    predict_first_candidate,
    predict_gold_copy_fixture,
    predict_seeded_random,
    predict_taxonomy_majority,
    run_independent_baselines,
    semantic_key,
    stable_under_id_permutation,
)


def _row(task_id: str, goal: str, candidates, selected: str, split: str = "train"):
    return {
        "task_id": task_id,
        "decision_type": "choice",
        "context_state": goal,
        "candidates": candidates,
        "selected_candidate": selected,
        "split": split,
        "provenance": {"group_key": f"g-{task_id}", "receipt_id": f"legacy-{task_id}-x",
                       "source_file_sha256": "a"},
    }


_CANDS = [
    {"id": "cand_save", "description": "click save button"},
    {"id": "cand_halt", "description": "halt and observe"},
]


class BaselineShapeTests(unittest.TestCase):
    def test_seeded_random_is_deterministic_for_seed(self):
        a = predict_seeded_random(_CANDS, seed=7)
        b = predict_seeded_random(_CANDS, seed=7)
        self.assertEqual(a["predicted_candidate"], b["predicted_candidate"])
        self.assertEqual(a["baseline_kind"], BASELINE_SEEDED_RANDOM)
        self.assertFalse(a["valid_as_ground_truth"])

    def test_seeded_random_changes_with_seed(self):
        picks = {predict_seeded_random(_CANDS, seed=s)["predicted_candidate"] for s in range(20)}
        self.assertGreater(len(picks), 1)

    def test_first_candidate_control(self):
        pred = predict_first_candidate(_CANDS)
        self.assertEqual(pred["predicted_candidate"], "cand_save")
        self.assertEqual(pred["baseline_kind"], BASELINE_FIRST_CANDIDATE)

    def test_gold_copy_fixture_is_labeled_fixture(self):
        pred = predict_gold_copy_fixture(_CANDS, gold_id="cand_halt")
        self.assertEqual(pred["predicted_candidate"], "cand_halt")
        self.assertEqual(pred["baseline_kind"], BASELINE_GOLD_COPY_FIXTURE)
        self.assertTrue(pred["is_fixture"])
        self.assertFalse(pred["valid_as_ground_truth"])

    def test_taxonomy_majority_needs_valid_taxonomy(self):
        rows = [
            _row("1", "click the save control", [{"id": "a", "description": "click save"}], "a"),
            _row("2", "click the save control", [{"id": "b", "description": "click save"}], "b"),
        ]
        pred = predict_taxonomy_majority(rows, candidates=[{"id": "a", "description": "click save"}])
        self.assertEqual(pred["baseline_kind"], BASELINE_TAXONOMY_MAJORITY)
        self.assertTrue(pred.get("valid_as_classifier_baseline"))
        # without a shared action taxonomy across records this must refuse
        refuse = predict_taxonomy_majority(rows, candidates=[{"id": "zz", "description": "unknown action"}])
        self.assertFalse(refuse.get("valid_as_classifier_baseline", False))
        self.assertIsNone(refuse.get("predicted_candidate"))


class TfidfLogregTests(unittest.TestCase):
    def test_fit_on_train_only_and_predict(self):
        train = [
            _row("1", "save the document now", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "a", "train"),
            _row("2", "save the file please", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "a", "train"),
            _row("3", "halt and wait", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "b", "train"),
            _row("4", "halt the run", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "b", "train"),
        ]
        model = fit_tfidf_logreg(train)
        self.assertEqual(model["baseline_kind"], BASELINE_TFIDF_LOGREG)
        self.assertEqual(model["fit_split"], "train")
        self.assertEqual(model["n_fit_rows"], 4)
        pred = model["predict"](_row("x", "save the document now", train[0]["candidates"], "a", "test"))
        self.assertEqual(pred["predicted_candidate"], "a")
        self.assertFalse(pred["valid_as_ground_truth"])

    def test_fit_refuses_non_train_rows(self):
        rows = [_row("1", "goal", _CANDS, "cand_save", "test")]
        with self.assertRaises(ValueError):
            fit_tfidf_logreg(rows)

    def test_id_permutation_does_not_change_semantic_choice(self):
        train = [
            _row("1", "save the document now", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "a", "train"),
            _row("2", "halt the run", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "b", "train"),
        ]
        model = fit_tfidf_logreg(train)
        original = model["predict"](_row("x", "save the document now", train[0]["candidates"], "a", "test"))
        renamed = [
            {"id": "zzz_9", "description": "click save"},
            {"id": "aaa_1", "description": "halt"},
        ]
        permuted = model["predict"](_row("x", "save the document now", renamed, "zzz_9", "test"))
        self.assertEqual(
            semantic_key(original, train[0]["candidates"]),
            semantic_key(permuted, renamed),
        )
        self.assertTrue(stable_under_id_permutation(model["predict"], _row("x", "save the document now", renamed, "zzz_9", "test"), renamed))


class MetricFormulaTests(unittest.TestCase):
    def test_brier_multiclass_public_formula(self):
        # one-hot gold on "a", perfect prediction → 0
        self.assertAlmostEqual(brier_multiclass({"a": 1.0, "b": 0.0}, "a"), 0.0)
        # uniform 2-class → (0.5^2 + 0.5^2)/2 = 0.25
        self.assertAlmostEqual(brier_multiclass({"a": 0.5, "b": 0.5}, "a"), 0.25)

    def test_ece_binary_public_formula(self):
        # one bin: conf 0.9, acc 0.5 over 2 samples → |0.5-0.9| = 0.4
        ece = ece_binary(
            confidences=[0.9, 0.9],
            correct=[True, False],
            n_bins=1,
        )
        self.assertAlmostEqual(ece, 0.4)
        # perfectly calibrated → 0
        self.assertAlmostEqual(ece_binary([0.5, 0.5], [True, False], n_bins=1), 0.0)


class ReportTests(unittest.TestCase):
    def test_run_reports_each_baseline_and_flags_fixture(self):
        rows = [
            _row(f"{i}", "save the document now" if i % 2 == 0 else "halt the run",
                 [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}],
                 "a" if i % 2 == 0 else "b", "train" if i < 6 else "test")
            for i in range(10)
        ]
        report = run_independent_baselines(rows, permutation_seeds=5)
        kinds = {b["baseline_kind"] for b in report["baselines"]}
        self.assertIn(BASELINE_SEEDED_RANDOM, kinds)
        self.assertIn(BASELINE_FIRST_CANDIDATE, kinds)
        self.assertIn(BASELINE_GOLD_COPY_FIXTURE, kinds)
        self.assertIn(BASELINE_TFIDF_LOGREG, kinds)
        gold_copy = next(b for b in report["baselines"] if b["baseline_kind"] == BASELINE_GOLD_COPY_FIXTURE)
        self.assertTrue(gold_copy["is_fixture"])
        self.assertFalse(gold_copy["valid_as_ground_truth"])
        self.assertGreaterEqual(report["permutation_seeds"], 5)
        self.assertFalse(report["predictor_reads_labels"])
        self.assertEqual(report["status_label"], "PROVISIONAL_RESULT")

    def test_predictor_never_reads_selected_candidate(self):
        rows = [
            _row("1", "save the document now", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "a", "train"),
            _row("2", "halt the run", [{"id": "a", "description": "click save"}, {"id": "b", "description": "halt"}], "b", "train"),
        ]
        model = fit_tfidf_logreg(rows)
        a = model["predict"](rows[0])
        mutated = dict(rows[0])
        mutated["selected_candidate"] = "GHOST_LABEL"
        mutated["gold_selected_candidate"] = "GHOST"
        mutated["gold_outcome"] = "success"
        mutated["reward"] = 99
        b = model["predict"](mutated)
        self.assertEqual(a["predicted_candidate"], b["predicted_candidate"])


if __name__ == "__main__":
    unittest.main()
