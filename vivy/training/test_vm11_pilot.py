"""C11 tests — VM-11 pilot: sim vs live labels, known/novel/conflict, false inhibition."""
from __future__ import annotations

import unittest

from training.vm11_pilot import (
    LIVE_LABEL,
    SIM_LABEL,
    PilotTask,
    run_pilot,
)


class TaskMixTests(unittest.TestCase):
    def test_pilot_requires_known_novel_and_conflict(self):
        with self.assertRaises(ValueError):
            run_pilot(
                [
                    PilotTask(1, kind="known_error", action="force_confirm", fails=True),
                ],
                mode="simulated",
                seed=0,
            )

    def test_sim_and_live_labels_are_distinct(self):
        self.assertEqual(SIM_LABEL, "SIMULATED_PROTOCOL")
        self.assertEqual(LIVE_LABEL, "LIVE_MODEL_OBSERVATION")
        self.assertNotEqual(SIM_LABEL, LIVE_LABEL)


class PilotMeasurementTests(unittest.TestCase):
    def _tasks(self):
        tasks = []
        # 40 known-error (same root cause/action repeats if not dampened)
        for i in range(40):
            tasks.append(
                PilotTask(i, kind="known_error", action="force_confirm", fails=True, root_cause="poisoned_cache")
            )
        # 40 novel-error
        for i in range(40, 80):
            tasks.append(
                PilotTask(i, kind="novel_error", action=f"novel_{i}", fails=True, root_cause=f"cause_{i}")
            )
        # 20 conflicting negative constraints (condition changes → valid reattempt)
        for i in range(80, 100):
            tasks.append(
                PilotTask(
                    i,
                    kind="conflict_constraint",
                    action="force_confirm",
                    fails=True,
                    root_cause="poisoned_cache",
                    condition_changed=True,
                )
            )
        return tasks

    def test_one_hundred_task_pilot_reports_denominators(self):
        result = run_pilot(self._tasks(), mode="simulated", seed=42, use_dampener=True)
        self.assertEqual(result["n_tasks"], 100)
        self.assertEqual(result["status_label"], SIM_LABEL)
        self.assertEqual(result["repeat_errors"] + result["new_errors"] + result["valid_reattempts"] + result["recovered"],
                         result["n_failed_or_ok_accounted"])
        for key in ("repeat_rate", "false_inhibition_rate", "task_success_rate"):
            self.assertIn(key, result)
            self.assertIn(f"{key}_denominator", result)

    def test_simulated_and_live_modes_use_same_task_sequence(self):
        tasks = self._tasks()
        sim = run_pilot(tasks, mode="simulated", seed=42, use_dampener=True)
        live = run_pilot(tasks, mode="live", seed=42, use_dampener=True, live_backend="stub")
        self.assertEqual(sim["task_sequence_hash"], live["task_sequence_hash"])
        self.assertEqual(sim["status_label"], SIM_LABEL)
        self.assertEqual(live["status_label"], LIVE_LABEL)

    def test_dampener_off_baseline_uses_same_sequence(self):
        tasks = self._tasks()
        on = run_pilot(tasks, mode="simulated", seed=42, use_dampener=True)
        off = run_pilot(tasks, mode="simulated", seed=42, use_dampener=False)
        self.assertEqual(on["task_sequence_hash"], off["task_sequence_hash"])
        self.assertTrue(on["use_dampener"])
        self.assertFalse(off["use_dampener"])

    def test_live_mode_without_backend_is_not_run_not_pass(self):
        result = run_pilot(self._tasks(), mode="live", seed=0, use_dampener=True, live_backend=None)
        self.assertEqual(result["status_label"], "NOT_RUN")
        self.assertEqual(result["verdict"], "NOT_RUN")
        self.assertIsNone(result["repeat_rate"])


if __name__ == "__main__":
    unittest.main()
