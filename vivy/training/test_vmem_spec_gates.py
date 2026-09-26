"""C13 tests — VMEM spec thresholds (verbatim + version) and VM-01…VM-11 measurement shapes."""
from __future__ import annotations

import unittest

from training.vmem_spec_gates import (
    VM_IDS,
    evaluate_spec_thresholds,
    judge_vm_measurement,
    quote_threshold,
)


class SpecThresholdTests(unittest.TestCase):
    def test_quote_threshold_requires_verbatim_and_version(self):
        ok = quote_threshold(
            vm_id="VM-01",
            spec_name="VIVY_COGNITIVE_CORE_SPEC.md",
            spec_version="2026-09-19",
            verbatim="FORAGE sensitivity ≥ 0.8 on labeled OOD",
        )
        self.assertEqual(ok["status"], "QUOTED")
        self.assertEqual(ok["spec_version"], "2026-09-19")
        self.assertIn("verbatim", ok)

        missing_version = quote_threshold(
            vm_id="VM-01",
            spec_name="x.md",
            spec_version="",
            verbatim="something",
        )
        self.assertEqual(missing_version["status"], "GAP")

        missing_text = quote_threshold(
            vm_id="VM-02",
            spec_name="x.md",
            spec_version="v1",
            verbatim="",
        )
        self.assertEqual(missing_text["status"], "GAP")

    def test_missing_threshold_is_gap_not_pass(self):
        report = evaluate_spec_thresholds(
            [
                {"vm_id": "VM-01", "spec_name": "s.md", "spec_version": "v1", "verbatim": "sens ≥ 0.8"},
                {"vm_id": "VM-02", "spec_name": "s.md", "spec_version": "v1", "verbatim": ""},
            ]
        )
        self.assertEqual(report["thresholds"]["VM-01"]["status"], "QUOTED")
        self.assertEqual(report["thresholds"]["VM-02"]["status"], "GAP")
        self.assertEqual(report["overall"], "GAP")
        self.assertNotEqual(report["overall"], "PASS")

    def test_all_vm_ids_covered(self):
        self.assertEqual(
            tuple(VM_IDS),
            tuple(f"VM-{i:02d}" for i in range(1, 12)),
        )


class VMMeasurementShapeTests(unittest.TestCase):
    def test_vm01_requires_labeled_ood_and_false_escalation(self):
        bad = judge_vm_measurement(
            "VM-01",
            {"n_forage": 10, "note": "all FORAGE decisions look right"},
        )
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertIn("false_escalation", bad["missing"])

        good = judge_vm_measurement(
            "VM-01",
            {
                "ood_labeled": True,
                "in_domain_labeled": True,
                "sensitivity": 0.9,
                "false_escalation_rate": 0.05,
                "denominator": 100,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm02_confusion_matrix_not_adapter_presence(self):
        bad = judge_vm_measurement("VM-02", {"adapter_exists": True, "accuracy": 1.0})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-02",
            {
                "confusion_matrix": {"text": {"text": 8, "image": 0}, "image": {"text": 1, "image": 7}},
                "inputs_include": ["real", "corrupt", "mixed"],
                "denominator": 16,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm03_requires_source_trace_not_call_count(self):
        bad = judge_vm_measurement("VM-03", {"n_tool_calls": 42})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-03",
            {
                "traces": [{"retrieval_id": "r1", "source": "doc#a"}],
                "source_required": True,
                "necessary_recall": 0.8,
                "denominator": 10,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm04_bytes_not_cache_entries(self):
        bad = judge_vm_measurement("VM-04", {"cache_entries": 7})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-04",
            {
                "bytes_eligible": 1000,
                "bytes_evicted": 400,
                "memory_after_eviction_bytes": 600,
                "reload_correct": True,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm05_four_part_schema_plus_provenance(self):
        bad = judge_vm_measurement("VM-05", {"lesson_text": "always do X"})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-05",
            {
                "schema": {
                    "claim": "c",
                    "evidence": "e",
                    "scope": "s",
                    "limits": "l",
                },
                "provenance": {"source": "receipt:x", "reviewer": "human"},
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm06_parse_is_not_correctness(self):
        bad = judge_vm_measurement("VM-06", {"parse_ok": True})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-06",
            {
                "parse_ok": True,
                "bounded_target": "sandbox#1",
                "evidence_criteria": ["exit_code", "stdout_hash"],
                "criteria_met": True,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm07_seeded_faults_and_blind_rca(self):
        bad = judge_vm_measurement("VM-07", {"named_the_error": "it was a timeout"})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-07",
            {
                "seeded_faults": [{"id": "f1", "root_cause": "null_ptr"}],
                "blind_diagnosis": True,
                "diagnosed_root_cause": "null_ptr",
                "fix_confirmed": True,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm08_restart_is_not_self_heal(self):
        bad = judge_vm_measurement("VM-08", {"process_restarted": True})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-08",
            {
                "sandbox_faults": 3,
                "regressions": 0,
                "rollback_ok": True,
                "success_denominator": 3,
                "successes": 3,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm09_memory_bench_is_not_ttft(self):
        bad = judge_vm_measurement("VM-09", {"memory_get_ms": 0.003, "label": "TTFT"})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-09",
            {
                "ttft_cold_ms": 120.0,
                "ttft_warm_ms": 40.0,
                "total_cold_ms": 900.0,
                "total_warm_ms": 300.0,
                "hardware": "cpu-i7",
                "n_samples": 30,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm10_paired_n_needs_quality_and_oom_fallback(self):
        bad = judge_vm_measurement("VM-10", {"n": 3, "note": "more cores = smarter"})
        self.assertEqual(bad["verdict"], "FAIL")

        good = judge_vm_measurement(
            "VM-10",
            {
                "paired": {
                    "N=1": {"quality": 0.5, "resource": 1.0},
                    "N=2": {"quality": 0.6, "resource": 1.8},
                    "N=3": {"quality": 0.62, "resource": 2.5},
                },
                "oom_events": 0,
                "fallback_taken": False,
                "denominator": 30,
            },
        )
        self.assertEqual(good["verdict"], "PASS")

    def test_vm11_simulation_is_not_production(self):
        bad = judge_vm_measurement(
            "VM-11",
            {"repeat_rate": 0.03, "status_label": "SIMULATED_PROTOCOL", "live": False},
        )
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertIn("live", " ".join(bad["missing"]).lower())

        good = judge_vm_measurement(
            "VM-11",
            {
                "repeat_rate": 0.03,
                "false_inhibition_rate": 0.01,
                "status_label": "LIVE_MODEL_OBSERVATION",
                "live": True,
                "denominator": 100,
                "ci95": [0.0, 0.08],
            },
        )
        self.assertEqual(good["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
