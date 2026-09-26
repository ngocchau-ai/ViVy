#!/usr/bin/env python3
"""P2 VM-11 Error-Dampening Measurement Harness tests.

Measures repeated-error-rate over 100 consecutive tasks against the
CognitiveStateGraph dampener and emits a receipt.

VM-11 (VMEM): Pass ≤10% repeat, Excellence ≤2% on 100 consecutive tasks.

Gate 9: the receipt is a SIMULATED_PROTOCOL measurement of the dampener
mechanism. It is NOT a live-model accuracy claim.

Changelog:
    23/09/2026 (Claude Code — P2 VM-11 Measurement Harness): Initial.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VM11ReceiptSchemaTests(unittest.TestCase):
    def test_receipt_has_gate9_required_fields(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=20, seed=7)
        for field in (
            "n_tasks",
            "n_repeat_errors",
            "repeat_rate",
            "pass_threshold",
            "excellence_threshold",
            "verdict",
            "seed",
            "protocol",
            "generated_at",
            "status_label",
        ):
            self.assertTrue(hasattr(receipt, field), f"missing field: {field}")

    def test_status_label_is_gate9_honest(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=20, seed=7)
        self.assertEqual(receipt.status_label, "SIMULATED_PROTOCOL")
        self.assertNotEqual(receipt.status_label, "VERIFIED_RESULT")

    def test_protocol_names_the_mechanism_not_live_model(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=20, seed=7)
        self.assertIn("CognitiveStateGraph", receipt.protocol)
        self.assertNotIn("PRODUCTION-READY", receipt.protocol)

    def test_receipt_is_json_serializable(self):
        import json

        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=10, seed=1)
        blob = json.dumps(receipt.to_dict())
        self.assertTrue(blob)


class VM11MeasurementTests(unittest.TestCase):
    def test_runs_exactly_n_tasks(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=100, seed=42)
        self.assertEqual(receipt.n_tasks, 100)
        self.assertEqual(len(receipt.trials), 100)

    def test_repeat_rate_is_fraction_in_unit_interval(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=100, seed=42)
        self.assertGreaterEqual(receipt.repeat_rate, 0.0)
        self.assertLessEqual(receipt.repeat_rate, 1.0)
        self.assertAlmostEqual(
            receipt.repeat_rate,
            receipt.n_repeat_errors / receipt.n_tasks,
            places=6,
        )

    def test_verdict_uses_vm11_thresholds(self):
        from orchestrator.vm11_harness import (
            VM11_EXCELLENCE_THRESHOLD,
            VM11_PASS_THRESHOLD,
            run_measurement,
        )

        self.assertEqual(VM11_PASS_THRESHOLD, 0.10)
        self.assertEqual(VM11_EXCELLENCE_THRESHOLD, 0.02)

        receipt = run_measurement(n_tasks=100, seed=42)
        self.assertEqual(receipt.pass_threshold, VM11_PASS_THRESHOLD)
        self.assertEqual(receipt.excellence_threshold, VM11_EXCELLENCE_THRESHOLD)
        self.assertIn(receipt.verdict, {"EXCELLENCE", "PASS", "FAIL"})
        if receipt.repeat_rate <= VM11_EXCELLENCE_THRESHOLD:
            self.assertEqual(receipt.verdict, "EXCELLENCE")
        elif receipt.repeat_rate <= VM11_PASS_THRESHOLD:
            self.assertEqual(receipt.verdict, "PASS")
        else:
            self.assertEqual(receipt.verdict, "FAIL")

    def test_same_seed_is_reproducible(self):
        from orchestrator.vm11_harness import run_measurement

        a = run_measurement(n_tasks=50, seed=99)
        b = run_measurement(n_tasks=50, seed=99)
        self.assertEqual(a.n_repeat_errors, b.n_repeat_errors)
        self.assertEqual([t.chosen for t in a.trials], [t.chosen for t in b.trials])

    def test_repeat_error_means_chose_previously_falsified_and_failed_again(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=100, seed=42)
        for trial in receipt.trials:
            if trial.repeat_error:
                self.assertTrue(trial.previously_falsified)
                self.assertTrue(trial.failed)
        counted = sum(1 for t in receipt.trials if t.repeat_error)
        self.assertEqual(counted, receipt.n_repeat_errors)


class VM11DampenerEffectTests(unittest.TestCase):
    def test_dampener_repeat_rate_below_undampened_baseline(self):
        from orchestrator.vm11_harness import run_measurement

        dampened = run_measurement(n_tasks=100, seed=42, use_dampener=True)
        baseline = run_measurement(n_tasks=100, seed=42, use_dampener=False)
        self.assertLess(
            dampened.repeat_rate,
            baseline.repeat_rate,
            "dampener should reduce repeated-error-rate vs undampened baseline",
        )

    def test_dampened_run_meets_vm11_pass_threshold(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=100, seed=42, use_dampener=True)
        self.assertLessEqual(
            receipt.repeat_rate,
            receipt.pass_threshold,
            f"VM-11 FAIL: repeat_rate={receipt.repeat_rate:.3f}",
        )

    def test_graph_state_persists_across_tasks(self):
        """Dampening must accumulate — 100 tasks share one CognitiveStateGraph."""
        from orchestrator.vm11_harness import VM11Harness

        harness = VM11Harness(seed=3, use_dampener=True)
        harness.run(n_tasks=30)
        stats = harness.graph.stats()
        self.assertGreater(stats.falsified_edge_count, 0)
        self.assertGreater(stats.dampened_node_count, 0)


class VM11BaselineLabelTests(unittest.TestCase):
    def test_baseline_receipt_still_labelled_simulated(self):
        from orchestrator.vm11_harness import run_measurement

        receipt = run_measurement(n_tasks=50, seed=1, use_dampener=False)
        self.assertEqual(receipt.status_label, "SIMULATED_PROTOCOL")
        self.assertIn("baseline", receipt.protocol.lower())


if __name__ == "__main__":
    unittest.main()
