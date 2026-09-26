"""C13 tests — soak ≥100 tasks, timeout/restart/concurrency, no infinite loops, no lost receipts."""
from __future__ import annotations

import unittest

from training.vmem_soak import (
    MIN_SOAK_TASKS,
    run_soak,
    verify_receipts_intact,
)


class SoakScaleTests(unittest.TestCase):
    def test_min_soak_is_one_hundred(self):
        self.assertEqual(MIN_SOAK_TASKS, 100)

    def test_soak_refuses_fewer_than_min_tasks(self):
        with self.assertRaises(ValueError):
            run_soak([{"task_id": i} for i in range(10)], fault_plan=[])


class SoakBehaviorTests(unittest.TestCase):
    def _tasks(self, n=100):
        return [{"task_id": i, "prompt": f"task-{i}"} for i in range(n)]

    def test_hundred_task_soak_reports_denominators(self):
        result = run_soak(self._tasks(), fault_plan=[])
        self.assertEqual(result["n_tasks"], 100)
        self.assertEqual(result["status_label"], "PROVISIONAL_RESULT")
        for key in (
            "completed",
            "timed_out",
            "restarted",
            "concurrent_ok",
            "infinite_loops_detected",
            "receipts_written",
            "receipts_lost",
            "side_effect_repeats",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["completed"] + result["timed_out"], result["n_tasks"])
        self.assertEqual(result["receipts_lost"], 0)
        self.assertEqual(result["infinite_loops_detected"], 0)

    def test_timeout_fault_is_bounded_not_infinite(self):
        result = run_soak(self._tasks(100), fault_plan=[{"kind": "timeout", "at_task": 7}])
        self.assertEqual(result["timed_out"], 1)
        self.assertEqual(result["infinite_loops_detected"], 0)
        self.assertEqual(result["max_steps_per_task"], 1)  # single bounded attempt after timeout

    def test_restart_fault_recovers_without_repeating_side_effects(self):
        result = run_soak(
            self._tasks(100),
            fault_plan=[{"kind": "restart", "at_task": 3}],
        )
        self.assertEqual(result["restarted"], 1)
        self.assertEqual(result["side_effect_repeats"], 0)

    def test_unavailable_backend_falls_back_with_log(self):
        result = run_soak(
            self._tasks(100),
            fault_plan=[{"kind": "unavailable", "at_task": 5}],
        )
        self.assertEqual(result["fallback_taken"], 1)
        self.assertGreaterEqual(len(result["fallback_log"]), 1)
        self.assertEqual(result["receipts_lost"], 0)

    def test_concurrent_tasks_keep_receipts(self):
        result = run_soak(self._tasks(100), fault_plan=[], concurrency=4)
        self.assertTrue(result["concurrent_ok"])
        self.assertEqual(result["receipts_written"], 100)
        self.assertEqual(result["receipts_lost"], 0)

    def test_verify_receipts_intact_detects_loss(self):
        result = run_soak(self._tasks(100), fault_plan=[])
        check = verify_receipts_intact(result["receipts"])
        self.assertTrue(check["ok"])
        self.assertEqual(check["expected"], 100)
        self.assertEqual(check["found"], 100)

        broken = dict(result)
        broken["receipts"] = result["receipts"][:-1]
        check2 = verify_receipts_intact(broken["receipts"], expected=100)
        self.assertFalse(check2["ok"])
        self.assertEqual(check2["missing"], 1)


if __name__ == "__main__":
    unittest.main()
