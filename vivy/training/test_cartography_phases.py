"""C12 tests — Cartography phase split, RSS vs buffer, 100B / vision guards."""
from __future__ import annotations

import unittest

from training.cartography_phases import (
    PHASES,
    check_100b_claim,
    check_vision_claim,
    measure_phases,
    sample_process_memory,
)


class PhaseSeparationTests(unittest.TestCase):
    def test_five_phases_are_distinct(self):
        self.assertEqual(
            tuple(PHASES),
            (
                "atlas_load",
                "weight_bytes_paged",
                "resident_ram",
                "forward_execution",
                "semantic_accuracy",
            ),
        )

    def test_measure_phases_reports_each_phase_separately(self):
        result = measure_phases(
            atlas_bytes=402_004,
            atlas_load_ms=30.01,
            weight_bytes_paged=1_048_576,
            resident_rss_bytes=2_500_000,
            forward_ms=12.5,
            semantic_correct=8,
            semantic_total=10,
        )
        for phase in PHASES:
            self.assertIn(phase, result["phases"], phase)
            self.assertIn("value", result["phases"][phase], phase)
            self.assertIn("unit", result["phases"][phase], phase)
        # atlas load is NOT forward execution and NOT semantic accuracy
        self.assertNotEqual(
            result["phases"]["atlas_load"]["value"],
            result["phases"]["forward_execution"]["value"],
        )
        self.assertNotEqual(
            result["phases"]["resident_ram"]["value"],
            result["phases"]["semantic_accuracy"]["value"],
        )
        self.assertEqual(result["phases"]["semantic_accuracy"]["value"], 0.8)
        self.assertEqual(result["phases"]["semantic_accuracy"]["unit"], "accuracy")

    def test_phases_refuse_collapsing_into_one_score(self):
        result = measure_phases(
            atlas_bytes=1,
            atlas_load_ms=1.0,
            weight_bytes_paged=1,
            resident_rss_bytes=1,
            forward_ms=1.0,
            semantic_correct=1,
            semantic_total=1,
        )
        self.assertNotIn("overall_score", result)
        self.assertFalse(result.get("collapsed_to_single_score", False))


class ResidentRamVsBufferTests(unittest.TestCase):
    def test_sample_reports_rss_and_faults_not_just_buffer(self):
        sample = sample_process_memory(allocated_buffer_bytes=4096)
        self.assertIn("allocated_buffer_bytes", sample)
        self.assertEqual(sample["allocated_buffer_bytes"], 4096)
        for key in (
            "rss_bytes",
            "private_working_set_bytes",
            "page_faults",
            "ram_savings_inferred_from_buffer",
        ):
            self.assertIn(key, sample)
        self.assertFalse(sample["ram_savings_inferred_from_buffer"])

    def test_ram_savings_cannot_be_claimed_from_buffer_alone(self):
        sample = sample_process_memory(allocated_buffer_bytes=999_999_999)
        self.assertFalse(sample["ram_savings_inferred_from_buffer"])
        self.assertNotIn("ram_savings_bytes", sample)


class ClaimGuardTests(unittest.TestCase):
    def test_100b_unverified_without_real_weights(self):
        verdict = check_100b_claim(
            claimed_parameter_count=100_000_000_000,
            weights_present=False,
            weights_bytes=0,
            nearest_artifact="qwen2-vl-72b.catlas",
        )
        self.assertEqual(verdict["status"], "UNVERIFIED")
        self.assertFalse(verdict["extrapolated_from_smaller_artifact"])
        self.assertIn("72b", verdict["note"].lower())

    def test_100b_not_extrapolated_from_72b_artifact(self):
        verdict = check_100b_claim(
            claimed_parameter_count=100_000_000_000,
            weights_present=False,
            weights_bytes=670_069,
            nearest_artifact="qwen2-vl-72b.catlas",
        )
        self.assertEqual(verdict["status"], "UNVERIFIED")
        self.assertFalse(verdict["extrapolated_from_smaller_artifact"])

    def test_vision_requires_real_images_and_labels(self):
        empty = check_vision_claim(images=[], reference_labels=[])
        self.assertEqual(empty["status"], "NOT_RUN")
        self.assertFalse(empty["has_real_images"])
        self.assertFalse(empty["has_reference_labels"])

        text_only = check_vision_claim(
            images=["a red circle on a white background"],
            reference_labels=["red circle"],
            source="text_description",
        )
        self.assertEqual(text_only["status"], "NOT_RUN")
        self.assertFalse(text_only["counts_as_multimodal_grounding"])

        real = check_vision_claim(
            images=[b"\x89PNG\r\n\x1a\nfakepngbytes"],
            reference_labels=["red circle"],
            source="image_bytes",
        )
        self.assertEqual(real["status"], "READY_FOR_TEST")
        self.assertTrue(real["counts_as_multimodal_grounding"])


if __name__ == "__main__":
    unittest.main()
