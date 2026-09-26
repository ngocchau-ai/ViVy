#!/usr/bin/env python3
"""P5 Cartography Sparse RAM/activation benchmark tests.

Gate 9: no `0ms`, `O(1)`, `<2ms`, `<=8MB`, or `100B-on-10GB` claim is accepted
without a reproducible benchmark or receipt. These tests drive the P5 harness
and assert the unbenchmarkable claims stay `UNVERIFIED` in the receipt.

Measured numbers land in `CARTOGRAPHY_BENCHMARK_RECEIPT.json` — they are
observations on this machine, not absolute product claims.

Changelog:
    23/09/2026 (Claude Code — P5 Cartography RAM/activation benchmark): Initial.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _tiny_hebbian(ns=(10, 40), dim=16, reps=5):
    from orchestrator.cartography_benchmark import run_hebbian_scaling

    return run_hebbian_scaling(dim=dim, ns=ns, reps=reps)


class CatlasMeasurementTests(unittest.TestCase):
    def test_export_import_roundtrip_records_size_and_latency(self):
        from integration.cautreo_cartographer import AtlasNode, CoarseKnowledgeAtlas
        from orchestrator.cartography_benchmark import measure_catlas_roundtrip

        atlas = CoarseKnowledgeAtlas(model_id="p5-fixture", total_layers=4)
        for i in range(4):
            atlas.nodes[i] = AtlasNode(
                layer_index=i,
                block_name=f"p5-fixture.blk.{i}",
                top_concepts=[f"concept_{i}"],
                domain_scores={"logic_math": 0.5},
                high_salience_neuron_indices=list(range(10)),
            )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p5-fixture.catlas"
            m = measure_catlas_roundtrip(atlas, path)

        self.assertTrue(m["exported"])
        self.assertGreater(m["size_bytes"], 0)
        self.assertIsNotNone(m["export_ms"])
        self.assertIsNotNone(m["import_ms"])
        self.assertEqual(m["n_nodes"], 4)
        self.assertIsNotNone(m["loaded_atlas"])

    def test_missing_atlas_file_is_fail_closed(self):
        from orchestrator.cartography_benchmark import measure_catlas_import

        m = measure_catlas_import("Z:\\does\\not\\exist.catlas")
        self.assertFalse(m["ok"])
        self.assertIsNone(m["import_ms"])
        self.assertEqual(m["size_bytes"], 0)

    def test_receipt_marks_size_claim_from_measurement(self):
        from orchestrator.cartography_benchmark import run_benchmark

        rec = run_benchmark(
            atlas_paths=[],
            hebbian_ns=(5, 15),
            hebbian_dim=8,
            hebbian_reps=3,
            include_cautreo=False,
            include_synthetic_atlas=True,
        )
        claims = rec.claims
        self.assertIn("catlas_size_under_8mb", claims)
        self.assertIn(claims["catlas_size_under_8mb"], {"TESTED", "UNVERIFIED"})
        self.assertIn("catlas_load_under_2ms", claims)
        self.assertIn(claims["catlas_load_under_2ms"], {"TESTED", "UNVERIFIED"})


class HebbianScalingTests(unittest.TestCase):
    def test_scaling_points_recorded_for_each_n(self):
        points = _tiny_hebbian()
        ns = sorted(p["n"] for p in points)
        self.assertEqual(ns, [10, 40])
        for p in points:
            self.assertGreaterEqual(p["recall_ms_no_graph"], 0.0)
            self.assertGreaterEqual(p["recall_ms_with_graph"], 0.0)

    def test_o1_graph_size_claim_is_tested_or_unverified_not_absolute(self):
        from orchestrator.cartography_benchmark import run_benchmark

        rec = run_benchmark(
            atlas_paths=[],
            hebbian_ns=(8, 24),
            hebbian_dim=8,
            hebbian_reps=3,
            include_cautreo=False,
            include_synthetic_atlas=False,
        )
        status = rec.claims["hebbian_o1_graph_size"]
        self.assertIn(status, {"TESTED", "UNVERIFIED"})
        # Never an absolute O(1) product claim without pointing at the receipt.
        self.assertNotEqual(status, "PRODUCTION-READY")
        self.assertIn("hebbian_scaling_ratio", rec.hebbian)

    def test_build_w_cost_is_recorded_separately_from_recall(self):
        points = _tiny_hebbian(ns=(12,), dim=8, reps=2)
        self.assertIn("build_ms", points[0])
        self.assertGreaterEqual(points[0]["build_ms"], 0.0)


class RamAndSparsityTests(unittest.TestCase):
    def test_ram_budget_is_ten_percent_ceiling(self):
        from integration.cautreo_cartographer import CautreoCartographer
        from orchestrator.cartography_benchmark import measure_ram_budget

        cart = CautreoCartographer(ram_ratio=0.10, circuit_breaker_threshold=0.85)
        budget = measure_ram_budget(cart)
        self.assertAlmostEqual(budget["ram_ratio"], 0.10, places=6)
        self.assertEqual(budget["max_buffer_bytes"], int(budget["hardware_ram_bytes"] * 0.10))
        self.assertAlmostEqual(budget["circuit_breaker_threshold"], 0.85, places=6)
        self.assertIn("budget_fraction_of_hw", budget)

    def test_sparse_activation_top_k_is_ten_percent(self):
        from orchestrator.cartography_benchmark import measure_sparse_activation

        sparse = measure_sparse_activation(total_neurons=14336, top_k_ratio=0.10)
        self.assertEqual(sparse["total_neurons"], 14336)
        self.assertEqual(sparse["top_k_count"], 1433)  # int(14336 * 0.10)
        self.assertAlmostEqual(sparse["activation_ratio"], 0.10, places=4)
        self.assertAlmostEqual(sparse["sparsity_ratio"], 0.90, places=4)


class UnverifiableClaimTests(unittest.TestCase):
    def test_100b_on_10gb_stays_unverified(self):
        from orchestrator.cartography_benchmark import run_benchmark

        rec = run_benchmark(
            atlas_paths=[],
            hebbian_ns=(5, 10),
            hebbian_dim=8,
            hebbian_reps=2,
            include_cautreo=False,
            include_synthetic_atlas=False,
        )
        self.assertEqual(rec.claims["100b_on_10gb"], "UNVERIFIED")

    def test_zero_latency_claim_stays_unverified_even_when_measured(self):
        from orchestrator.cartography_benchmark import run_benchmark

        rec = run_benchmark(
            atlas_paths=[],
            hebbian_ns=(5, 10),
            hebbian_dim=8,
            hebbian_reps=2,
            include_cautreo=True,
            include_synthetic_atlas=False,
        )
        self.assertEqual(rec.claims["zero_latency_c_abi"], "UNVERIFIED")
        if rec.cautreo is not None:
            self.assertIn("put_ms", rec.cautreo)
            self.assertIn("get_ms", rec.cautreo)
            # Measured numbers are observations — never asserted as 0.
            self.assertGreaterEqual(rec.cautreo["put_ms"], 0.0)
            self.assertNotEqual(rec.cautreo.get("claimed_latency_ms"), 0)


class ReceiptSchemaTests(unittest.TestCase):
    def test_receipt_serializes_and_carries_gate9_label(self):
        from orchestrator.cartography_benchmark import (
            BENCHMARK_STATUS_LABEL,
            run_benchmark,
            write_receipt,
        )

        rec = run_benchmark(
            atlas_paths=[],
            hebbian_ns=(5, 10),
            hebbian_dim=8,
            hebbian_reps=2,
            include_cautreo=False,
            include_synthetic_atlas=True,
        )
        self.assertEqual(rec.status_label, BENCHMARK_STATUS_LABEL)
        self.assertIn("benchmark", rec.protocol.lower())
        payload = rec.to_dict()
        text = json.dumps(payload)
        self.assertIn("claims", payload)
        self.assertIn("status_label", payload)
        self.assertNotIn("PRODUCTION-READY", text)
        self.assertNotIn("0.00ms", text)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "receipt.json"
            write_receipt(rec, out)
            loaded = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(loaded["status_label"], BENCHMARK_STATUS_LABEL)

    def test_receipt_never_emits_absolute_zero_or_o1_product_claim(self):
        from orchestrator.cartography_benchmark import run_benchmark

        rec = run_benchmark(
            atlas_paths=[],
            hebbian_ns=(5, 10),
            hebbian_dim=8,
            hebbian_reps=2,
            include_cautreo=False,
            include_synthetic_atlas=True,
        )
        text = json.dumps(rec.to_dict())
        for banned in ("0ms", "0.00ms", "zero-latency", "PRODUCTION-READY", "100B-on-10GB"):
            self.assertNotIn(banned, text)


class Gate9RelabelTests(unittest.TestCase):
    """Live docstrings must not carry unbenchmarked absolute claims.

    Prior claim text stays in source as `[ISOLATED …]` on the same line
    (project rule: isolate, never delete) and is exempt from this scan.
    """

    FORBIDDEN = (
        r"O\(1\)",
        r"[Zz]ero-[Ll]atency",
        r"0\.00ms",
        r"0ms\s*latency",
        r"sub-2ms",
        r"load\s*<\s*2ms",
        r"<\s*8MB",
        r"<=\s*8MB",
        r"100B\s+LLM\s+to\s+run\s+with\s+the\s+system\s+load",
        r"Zero-OOM",
        r"PRODUCTION-READY",
    )

    def _assert_docstring_clean(self, module) -> None:
        import re

        doc = module.__doc__ or ""
        live_lines = [ln for ln in doc.splitlines() if "[ISOLATED" not in ln.upper()]
        live = "\n".join(live_lines)
        for pattern in self.FORBIDDEN:
            match = re.search(pattern, live)
            if match is not None:
                self.fail(
                    f"Gate 9 violation in {module.__name__} docstring: {match.group(0)}"
                )

    def test_cartographer_docstring_has_no_unbenchmarked_claim(self):
        import integration.cautreo_cartographer as mod

        self._assert_docstring_clean(mod)

    def test_hebbian_recall_docstring_has_no_unbenchmarked_o1_claim(self):
        import memory.hebbian_recall as mod

        self._assert_docstring_clean(mod)

    def test_cautreo_binding_docstring_has_no_zero_latency_claim(self):
        import integration.cautreo_binding as mod

        self._assert_docstring_clean(mod)

    def test_hebbian_class_docstring_has_no_unbenchmarked_o1_claim(self):
        import re

        from memory.hebbian_recall import HebbianRecall

        doc = HebbianRecall.__doc__ or ""
        live_lines = [ln for ln in doc.splitlines() if "[ISOLATED" not in ln.upper()]
        live = "\n".join(live_lines)
        match = re.search(r"O\(1\)", live)
        if match is not None:
            self.fail(f"Gate 9 violation in HebbianRecall docstring: {match.group(0)}")

    def test_cautreo_context_memory_class_docstring_has_no_zero_latency(self):
        import re

        from integration.cautreo_binding import CautreoContextMemory

        doc = CautreoContextMemory.__doc__ or ""
        live_lines = [ln for ln in doc.splitlines() if "[ISOLATED" not in ln.upper()]
        live = "\n".join(live_lines)
        match = re.search(r"[Zz]ero-[Ll]atency", live)
        if match is not None:
            self.fail(
                f"Gate 9 violation in CautreoContextMemory docstring: {match.group(0)}"
            )

    def test_all_docstrings_in_touched_modules_are_clean(self):
        """AST scan: every string constant (incl. method docstrings) in P5 modules."""
        import ast
        import inspect
        import re

        import integration.cautreo_binding as binding
        import integration.cautreo_cartographer as cartographer
        import memory.hebbian_recall as hebbian

        for mod in (cartographer, hebbian, binding):
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    live_lines = [
                        ln
                        for ln in node.value.splitlines()
                        if "[ISOLATED" not in ln.upper()
                    ]
                    live = "\n".join(live_lines)
                    for pattern in self.FORBIDDEN:
                        match = re.search(pattern, live)
                        if match is not None:
                            self.fail(
                                f"Gate 9 violation in {mod.__name__} string: "
                                f"{match.group(0)}"
                            )


if __name__ == "__main__":
    unittest.main()
