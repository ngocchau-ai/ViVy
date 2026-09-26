"""Tests for learned_router (Plan 2 C — Brier / ECE / permutation control).

Changelog:
    24/09/2026 (Claude Code — Plan 2 C): Initial.
"""
from __future__ import annotations

import unittest

from training.learned_router import (
    MIN_ROWS_FOR_PROMOTION,
    LogisticRouter,
    baseline_brier,
    brier_score,
    build_training_set,
    check_promotion,
    evaluate_router,
    expected_calibration_error,
    extract_candidate_features,
    permutation_control,
    train_router,
)


class TestBrierScore(unittest.TestCase):
    def test_perfect(self) -> None:
        self.assertAlmostEqual(brier_score([1.0, 0.0], [1, 0]), 0.0)

    def test_uniform_prior_balanced(self) -> None:
        # All 0.5 on balanced labels → Brier = 0.25
        self.assertAlmostEqual(brier_score([0.5, 0.5], [0, 1]), 0.25)

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            brier_score([], [])

    def test_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            brier_score([0.5], [0, 1])


class TestECE(unittest.TestCase):
    def test_perfectly_calibrated(self) -> None:
        preds = [0.0, 0.0, 1.0, 1.0]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(expected_calibration_error(preds, labels), 0.0, places=2)

    def test_miscalibrated(self) -> None:
        preds = [0.9, 0.9, 0.9, 0.9]
        labels = [0, 0, 0, 0]
        self.assertGreater(expected_calibration_error(preds, labels), 0.5)

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            expected_calibration_error([], [])


class TestBaselineBrier(unittest.TestCase):
    def test_balanced(self) -> None:
        self.assertAlmostEqual(baseline_brier([0, 1]), 0.25)

    def test_all_ones(self) -> None:
        self.assertAlmostEqual(baseline_brier([1, 1, 1]), 0.0)


class TestPermutationControl(unittest.TestCase):
    def test_good_model_has_high_p(self) -> None:
        """A real model → permuted Brier ≥ real Brier → p > 0.05."""
        preds = [0.9, 0.9, 0.1, 0.1, 0.8, 0.8, 0.2, 0.2] * 5  # 40 samples
        labels = [1, 1, 0, 0, 1, 1, 0, 0] * 5
        p = permutation_control(preds, labels, n_permutations=100)
        self.assertGreater(p, 0.05)

    def test_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            permutation_control([0.5], [0, 1])


class TestEvaluateRouter(unittest.TestCase):
    def test_returns_all_metrics(self) -> None:
        preds = [0.8, 0.7, 0.2, 0.3]
        labels = [1, 1, 0, 0]
        m = evaluate_router(preds, labels, n_permutations=50)
        self.assertIn("brier_score", m)
        self.assertIn("ece", m)
        self.assertIn("baseline_brier", m)
        self.assertIn("permutation_p_value", m)
        self.assertEqual(m["n_rows"], 4)


class TestCheckPromotion(unittest.TestCase):
    def _good_metrics(self, n: int = 40) -> dict:
        return {
            "brier_score": 0.10,
            "baseline_brier": 0.25,
            "ece": 0.05,
            "permutation_p_value": 0.30,
            "n_rows": n,
        }

    def test_pass_all(self) -> None:
        ok, reason = check_promotion(self._good_metrics())
        self.assertTrue(ok)
        self.assertIn("PROVISIONAL_RESULT", reason)

    def test_fail_n_below_30(self) -> None:
        ok, reason = check_promotion(self._good_metrics(n=25))
        self.assertFalse(ok)
        self.assertIn("N=25", reason)

    def test_fail_brier_not_below_baseline(self) -> None:
        m = self._good_metrics()
        m["brier_score"] = 0.30
        ok, reason = check_promotion(m)
        self.assertFalse(ok)
        self.assertIn("Brier", reason)

    def test_fail_ece_too_high(self) -> None:
        m = self._good_metrics()
        m["ece"] = 0.15
        ok, reason = check_promotion(m)
        self.assertFalse(ok)
        self.assertIn("ECE", reason)

    def test_fail_permutation_leakage(self) -> None:
        m = self._good_metrics()
        m["permutation_p_value"] = 0.01
        ok, reason = check_promotion(m)
        self.assertFalse(ok)
        self.assertIn("leakage", reason)

    def test_min_rows_constant(self) -> None:
        self.assertEqual(MIN_ROWS_FOR_PROMOTION, 30)


class TestLogisticRouter(unittest.TestCase):
    def test_train_and_predict(self) -> None:
        features = [[1.0, 0.0], [0.0, 1.0]] * 20
        labels = [1, 0] * 20
        r = train_router(features, labels, lr=0.5, epochs=100)
        probs = r.predict_proba([[1.0, 0.0], [0.0, 1.0]])
        self.assertGreater(probs[0], probs[1])

    def test_untrained_raises(self) -> None:
        r = LogisticRouter(2)
        with self.assertRaises(RuntimeError):
            r.predict_proba([[0.5, 0.5]])

    def test_empty_features_raises(self) -> None:
        with self.assertRaises(ValueError):
            train_router([], [])

    def test_label_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            LogisticRouter(2).train([[0.1, 0.2]], [0, 1])


class TestFeatureExtraction(unittest.TestCase):
    def test_destructive_flagged(self) -> None:
        f = extract_candidate_features({"action_type": "delete", "description": "delete cache"})
        self.assertEqual(f[1], 1.0)

    def test_abstain_flagged(self) -> None:
        f = extract_candidate_features({"action_type": "abstain", "description": "no action"})
        self.assertEqual(f[2], 1.0)

    def test_empty_candidate(self) -> None:
        f = extract_candidate_features({})
        self.assertEqual(f[0], 0.0)
        self.assertEqual(f[4], 0.0)


class TestBuildTrainingSet(unittest.TestCase):
    def test_basic(self) -> None:
        records = [
            {
                "candidates": [
                    {"id": "a", "action_type": "abstain", "description": "hold"},
                    {"id": "b", "action_type": "delete", "description": "remove"},
                ],
                "selected_candidate": "a",
            }
        ]
        feats, labels = build_training_set(records)
        self.assertEqual(len(feats), 2)
        self.assertEqual(labels, [1, 0])

    def test_empty(self) -> None:
        feats, labels = build_training_set([])
        self.assertEqual(feats, [])
        self.assertEqual(labels, [])


if __name__ == "__main__":
    unittest.main()
