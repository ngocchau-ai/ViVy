"""C12 tests — sparse path actually used in forward (full-vs-sparse, same weights/input)."""
from __future__ import annotations

import unittest

import numpy as np

from training.sparse_forward import (
    SparseForwardResult,
    run_full_vs_sparse,
    sparse_matmul,
)


class SparsePathUsageTests(unittest.TestCase):
    def test_sparse_matmul_reports_activated_count(self):
        rng = np.random.default_rng(0)
        W = rng.normal(size=(8, 8))
        x = rng.normal(size=8)
        out, info = sparse_matmul(W, x, k=3)
        self.assertEqual(out.shape, (8,))
        self.assertEqual(info["k"], 3)
        self.assertEqual(info["activated_indices"].shape, (3,))
        self.assertTrue(info["sparse_path_exercised"])
        self.assertEqual(info["n_nonzero_contributions"], 3)

    def test_full_vs_sparse_uses_same_weights_and_input(self):
        rng = np.random.default_rng(1)
        W = rng.normal(size=(16, 16))
        x = rng.normal(size=16)
        result = run_full_vs_sparse(W, x, k=4, reps=5, seed=0)
        self.assertIsInstance(result, SparseForwardResult)
        self.assertTrue(result.same_weights)
        self.assertTrue(result.same_input)
        self.assertTrue(result.sparse_path_exercised)
        self.assertEqual(result.weights_id, result.weights_id_sparse)
        self.assertEqual(result.input_id, result.input_id_sparse)
        # full output uses all 16 dims; sparse uses exactly k
        self.assertEqual(result.n_full_nonzero, 16)
        self.assertEqual(result.n_sparse_nonzero, 4)

    def test_quality_regression_and_end_to_end_latency_are_reported(self):
        rng = np.random.default_rng(2)
        W = rng.normal(size=(32, 32))
        x = rng.normal(size=32)
        result = run_full_vs_sparse(W, x, k=8, reps=10, seed=0)
        self.assertIn("quality_regression", result.as_dict())
        self.assertGreaterEqual(result.quality_regression["cosine"], -1.0)
        self.assertLessEqual(result.quality_regression["cosine"], 1.0)
        self.assertIn("mse", result.quality_regression)
        self.assertIsNotNone(result.latency_full_ms["median"])
        self.assertIsNotNone(result.latency_sparse_ms["median"])
        self.assertIsNotNone(result.latency_end_to_end_ms["median"])
        self.assertEqual(result.latency_full_ms["n_samples"], 10)
        self.assertEqual(result.latency_claim, "NOT_A_PHYSICAL_ZERO")

    def test_sparse_not_exercised_when_k_covers_all(self):
        rng = np.random.default_rng(3)
        W = rng.normal(size=(4, 4))
        x = rng.normal(size=4)
        result = run_full_vs_sparse(W, x, k=4, reps=3, seed=0)
        # k == n means every unit is on — not a sparse reduction
        self.assertFalse(result.sparse_is_reduction)

    def test_no_latency_zero_or_o1_claim(self):
        rng = np.random.default_rng(4)
        W = rng.normal(size=(8, 8))
        x = rng.normal(size=8)
        result = run_full_vs_sparse(W, x, k=2, reps=3, seed=0)
        self.assertEqual(result.latency_claim, "NOT_A_PHYSICAL_ZERO")
        self.assertNotIn("o1_claim", result.as_dict())


if __name__ == "__main__":
    unittest.main()
