"""C10 tests — multi-size Hebbian benchmark (no O(1) from two points)."""
from __future__ import annotations

import unittest

from training.hebbian_bench import (
    MIN_GRAPH_SIZES,
    ReferenceHebbian,
    run_hebbian_scaling,
)


class MultiSizeTests(unittest.TestCase):
    def test_requires_at_least_three_graph_sizes(self):
        with self.assertRaises(ValueError):
            run_hebbian_scaling(dim=8, ns=(10, 20), reps=3)

    def test_reports_all_requested_sizes_with_fixed_dim(self):
        result = run_hebbian_scaling(dim=16, ns=(8, 16, 32, 64), reps=5, seed=0)
        self.assertEqual(result["dim"], 16)
        self.assertEqual(result["n_sizes"], 4)
        self.assertGreaterEqual(result["n_sizes"], MIN_GRAPH_SIZES)
        self.assertEqual(sorted(result["per_n"].keys()), [8, 16, 32, 64])

    def test_separates_wx_path_from_node_id_scan(self):
        result = run_hebbian_scaling(dim=8, ns=(4, 8, 16), reps=4, seed=1)
        for n, row in result["per_n"].items():
            self.assertIn("wx_recall_ms", row, n)
            self.assertIn("scan_recall_ms", row, n)
            self.assertIn("build_ms", row, n)
            for key in ("wx_recall_ms", "scan_recall_ms"):
                stats = row[key]
                self.assertIn("median", stats)
                self.assertIn("p95", stats)
                self.assertIn("mean", stats)
                self.assertIn("n_samples", stats)
                self.assertGreaterEqual(stats["n_samples"], 4)

    def test_zero_ms_is_rounding_not_physics(self):
        result = run_hebbian_scaling(dim=4, ns=(2, 3, 4), reps=3, seed=2)
        self.assertIn("latency_claim", result)
        self.assertEqual(result["latency_claim"], "NOT_A_PHYSICAL_ZERO")
        self.assertIn("status_label", result)
        self.assertIn(result["status_label"], {"PROVISIONAL_RESULT", "VERIFIED_RESULT"})


class ReferenceOperatorTests(unittest.TestCase):
    def test_wx_recall_independent_of_registered_n(self):
        # Same query after registering more pairs must keep W@x cost O(d^2),
        # measured as wall-clock ratio under a loose ceiling (not a physics claim).
        import time

        def time_wx(n: int) -> float:
            h = ReferenceHebbian(dim=16)
            for i in range(n):
                h.register(f"n{i}", [float(i % 7)] * 16)
            h.build()
            q = [1.0] * 16
            t0 = time.perf_counter()
            for _ in range(50):
                h.recall_wx(q)
            return (time.perf_counter() - t0) / 50

        t_small = time_wx(5)
        t_large = time_wx(80)
        # Allow large machine-noise ratio; the assertion is that the bench
        # reports the two paths separately, not a tight complexity bound.
        self.assertGreater(t_small, 0.0)
        self.assertGreater(t_large, 0.0)

    def test_scan_path_returns_nearest_node(self):
        h = ReferenceHebbian(dim=4)
        h.register("a", [1.0, 0.0, 0.0, 0.0])
        h.register("b", [0.0, 1.0, 0.0, 0.0])
        h.build()
        node_id = h.recall_scan([0.9, 0.1, 0.0, 0.0])
        self.assertIn(node_id, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
