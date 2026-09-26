"""Tests for run_reroute_live (TD-6 live auto-reroute evidence harness).

The harness itself is tested against a fake backend fn so the suite stays
green offline. The live measurement is produced by the CLI, not by these
tests — see ``VIVY_LIVE=1`` below for the opt-in integration check.

Changelog:
    25/09/2026 (Claude Code — TD-6 live evidence): Initial.
"""
from __future__ import annotations

import hashlib
import os
import unittest
from typing import Any

from training.backend_baseline import BackendError, BackendIdentity
from training.cross_model_adapter import CrossModelAdapter
from training.run_reroute_live import (
    ARM_BUILDERS,
    GAP_PRODUCT,
    Contract,
    LiveExecutor,
    all_floats,
    answer_number,
    build_receipt,
    clean_contracts,
    main,
    make_specs,
    reroute_contracts,
    run_arm,
    score_output,
)


def _greeting_fn(calls: list[str]):
    """Fake backend: records prompts, answers trivial arithmetic correctly.

    Replies show the derivation, so the scorer must take the LAST number —
    an earlier revision took the first and scored the operands instead.
    """
    answers = {"3 + 4": "3 + 4 = 7", "10 - 2": "10 - 2 = 8", "6 * 3": "6 * 3 = 18",
               "9 / 3": "9 / 3 = 3", "5 + 5": "5 + 5 = 10"}

    def fn(prompt: str, max_tokens: int) -> str:
        calls.append(prompt)
        for needle, reply in answers.items():
            if needle in prompt:
                return reply
        return "123456 * 789012 = 999999999999"

    return fn


def _route() -> Any:
    adapter = CrossModelAdapter()
    adapter.set_fallback("gemma4-e4b")
    return adapter.prepare_task("A", {"complexity": 0.5})


class TestAnswerNumber(unittest.TestCase):
    def test_plain_integer(self) -> None:
        self.assertEqual(answer_number("the answer is 42"), 42.0)

    def test_derivation_takes_the_last_number(self) -> None:
        """'6 * 3 = 18' must score 18, not the operand 6."""
        self.assertEqual(answer_number("6 * 3 = 18"), 18.0)

    def test_thousands_separators(self) -> None:
        self.assertEqual(answer_number("97,408,265,472"), float(GAP_PRODUCT))

    def test_negative_and_decimal(self) -> None:
        self.assertEqual(answer_number("delta -3.5 units"), -3.5)

    def test_no_number(self) -> None:
        self.assertIsNone(answer_number("no digits here"))

    def test_all_floats_keeps_order(self) -> None:
        self.assertEqual(all_floats("1, 2 and 3.5"), [1.0, 2.0, 3.5])


class TestScoreOutput(unittest.TestCase):
    def test_exact_match(self) -> None:
        c = Contract("x", "p", "exact", "READY")
        self.assertEqual(score_output(c, "READY"), (1.0, True))

    def test_exact_mismatch_is_not_partial(self) -> None:
        c = Contract("x", "p", "exact", "READY")
        self.assertEqual(score_output(c, "ready"), (0.0, False))

    def test_contains_is_case_insensitive(self) -> None:
        c = Contract("x", "p", "contains", "READY")
        self.assertEqual(score_output(c, "I am ready."), (1.0, True))

    def test_contains_all_is_graded(self) -> None:
        c = Contract("x", "p", "contains_all", ("alpha", "beta", "gamma"))
        score, satisfied = score_output(c, "alpha and beta only")
        self.assertAlmostEqual(score, 2 / 3, places=6)
        self.assertFalse(satisfied)

    def test_contains_all_all_matched(self) -> None:
        c = Contract("x", "p", "contains_all", ("alpha", "beta"))
        self.assertEqual(score_output(c, "alpha beta"), (1.0, True))

    def test_numeric_exact(self) -> None:
        c = Contract("x", "p", "numeric", 18.0)
        self.assertEqual(score_output(c, "18"), (1.0, True))

    def test_numeric_with_tolerance(self) -> None:
        c = Contract("x", "p", "numeric", 18.0, tolerance=0.5)
        self.assertEqual(score_output(c, "18.4"), (1.0, True))
        self.assertEqual(score_output(c, "20"), (0.0, False))

    def test_numeric_missing_value(self) -> None:
        c = Contract("x", "p", "numeric", 18.0)
        self.assertEqual(score_output(c, "the answer is unknown"), (0.0, False))

    def test_empty_text_is_zero(self) -> None:
        c = Contract("x", "p", "exact", "READY")
        self.assertEqual(score_output(c, "   "), (0.0, False))

    def test_output_is_deterministic(self) -> None:
        c = Contract("x", "p", "contains_all", ("a", "b"))
        first = score_output(c, "a only")
        second = score_output(c, "a only")
        self.assertEqual(first, second)


class TestContractValidation(unittest.TestCase):
    def test_unknown_check_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Contract("x", "p", "guess", "y")

    def test_numeric_requires_number(self) -> None:
        with self.assertRaises(TypeError):
            Contract("x", "p", "numeric", "eighteen")  # type: ignore[arg-type]

    def test_contains_all_requires_tuple(self) -> None:
        with self.assertRaises(TypeError):
            Contract("x", "p", "contains_all", "alpha")  # type: ignore[arg-type]

    def test_exact_requires_string(self) -> None:
        with self.assertRaises(TypeError):
            Contract("x", "p", "exact", 3.0)  # type: ignore[arg-type]

    def test_negative_tolerance_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Contract("x", "p", "numeric", 1.0, tolerance=-0.1)


class TestArmContracts(unittest.TestCase):
    def test_reroute_arm_carries_real_ground_truth(self) -> None:
        contracts = reroute_contracts()
        self.assertEqual(contracts["C"].expected, float(GAP_PRODUCT))
        self.assertEqual(contracts["C"].check, "numeric")

    def test_clean_arm_differs_only_at_c(self) -> None:
        clean, reroute = clean_contracts(), reroute_contracts()
        self.assertEqual(set(clean), set(reroute))
        self.assertNotEqual(clean["C"].expected, reroute["C"].expected)
        for nid in ("A", "B", "D", "E"):
            self.assertEqual(clean[nid].expected, reroute[nid].expected)

    def test_diamond_shape(self) -> None:
        specs = make_specs()
        self.assertEqual(len(specs), 5)
        parents = {s.node_id: s.parent for s in specs}
        self.assertEqual(parents["B"], "A")
        self.assertEqual(parents["C"], "A")
        self.assertEqual(parents["D"], "B")
        self.assertEqual(parents["E"], "C")
        self.assertIsNone(parents["A"])

    def test_plan_prior_prefers_c_over_b(self) -> None:
        specs = {s.node_id: s.score for s in make_specs()}
        self.assertGreater(specs["C"], specs["B"])
        self.assertGreater(specs["E"], specs["D"])

    def test_arm_builders_registered(self) -> None:
        self.assertEqual(set(ARM_BUILDERS), {"clean", "reroute"})


class TestLiveExecutor(unittest.TestCase):
    def test_records_every_call(self) -> None:
        prompts: list[str] = []
        executor = LiveExecutor(_greeting_fn(prompts), clean_contracts())
        text, score, ok = executor("A", _route())
        self.assertEqual(text, "3 + 4 = 7")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)
        self.assertEqual(len(executor.calls), 1)
        call = executor.calls[0]
        self.assertEqual(call["node_id"], "A")
        self.assertTrue(call["contract_satisfied"])
        self.assertEqual(call["prompt_sha256"], hashlib.sha256(
            clean_contracts()["A"].prompt.encode("utf-8")).hexdigest())
        self.assertIsInstance(call["latency_ms"], float)

    def test_derivation_scores_the_answer_not_the_operand(self) -> None:
        """Regression: '6 * 3 = 18' must score 18.0, not the operand 6."""
        executor = LiveExecutor(_greeting_fn([]), clean_contracts())
        _text, score, _ok = executor("C", _route())
        self.assertEqual(score, 1.0)
        self.assertEqual(executor.calls[0]["answer_number"], 18.0)

    def test_raw_output_is_kept_for_audit(self) -> None:
        executor = LiveExecutor(_greeting_fn([]), clean_contracts())
        executor("A", _route())
        call = executor.calls[0]
        self.assertEqual(call["output_text"], "3 + 4 = 7")
        self.assertEqual(
            call["output_sha256"],
            hashlib.sha256(b"3 + 4 = 7").hexdigest(),
        )

    def test_transport_success_with_wrong_answer(self) -> None:
        """ok stays True (call worked) while score drops — the planner then
        reroutes on the below-threshold path, not by faking a transport error."""
        executor = LiveExecutor(
            lambda prompt, max_tokens: "I am not sure", clean_contracts(),
        )
        _text, score, ok = executor("A", _route())
        self.assertTrue(ok)
        self.assertEqual(score, 0.0)
        self.assertFalse(executor.calls[0]["contract_satisfied"])
        self.assertEqual(executor.calls[0]["error"], "")

    def test_backend_error_is_not_success(self) -> None:
        def boom(prompt: str, max_tokens: int) -> str:
            raise BackendError("timeout", "gave up after 180s")

        executor = LiveExecutor(boom, clean_contracts())
        text, score, ok = executor("A", _route())
        self.assertEqual((text, score, ok), ("", 0.0, False))
        self.assertIn("timeout", executor.calls[0]["error"])

    def test_unexpected_exception_is_captured(self) -> None:
        def boom(prompt: str, max_tokens: int) -> str:
            raise OSError("socket closed")

        executor = LiveExecutor(boom, clean_contracts())
        _text, score, ok = executor("A", _route())
        self.assertFalse(ok)
        self.assertEqual(score, 0.0)
        self.assertIn("OSError", executor.calls[0]["error"])

    def test_missing_contract_fails_closed(self) -> None:
        executor = LiveExecutor(_greeting_fn([]), clean_contracts())
        text, score, ok = executor("ghost", _route())
        self.assertEqual((text, score, ok), ("", 0.0, False))
        self.assertIn("no contract", executor.calls[0]["error"])


class TestRunArm(unittest.TestCase):
    def test_clean_arm_completes_without_reroute(self) -> None:
        block = run_arm("clean", _greeting_fn([]), model_alias="gemma4-e4b")
        self.assertTrue(block["completed"])
        self.assertEqual(block["reroute_count"], 0)
        self.assertEqual(block["path"], ["A", "C", "E"])
        self.assertEqual(block["preferred_path"], ["A", "C", "E"])
        self.assertFalse(block["reroute_observed"])
        self.assertEqual(block["node_call_count"], 3)

    def test_reroute_arm_reroutes_on_capability_gap(self) -> None:
        """Node C answers the 6x6 product wrong -> planner re-plans to A->B->D."""
        block = run_arm("reroute", _greeting_fn([]), model_alias="gemma4-e4b")
        self.assertTrue(block["reroute_observed"])
        self.assertEqual(block["reroute_count"], 1)
        self.assertEqual(block["reroutes"][0]["node_id"], "C")
        self.assertEqual(block["reroutes"][0]["new_path"], ["A", "B", "D"])
        self.assertEqual(block["path"], ["A", "B", "D"])
        self.assertTrue(block["completed"])

        # C was attempted once and never retried; A ran once across both paths.
        node_ids = [c["node_id"] for c in block["node_calls"]]
        self.assertEqual(node_ids.count("C"), 1)
        self.assertEqual(node_ids.count("A"), 1)
        self.assertIn("B", node_ids)
        self.assertIn("D", node_ids)

    def test_reroute_reason_cites_score_not_transport(self) -> None:
        block = run_arm("reroute", _greeting_fn([]), model_alias="gemma4-e4b")
        reason = block["reroutes"][0]["reason"]
        self.assertIn("below threshold", reason)
        self.assertNotIn("executor reported failure", reason)

    def test_preferred_path_is_plan_time_not_post_mutation(self) -> None:
        """run() overwrites node scores; the snapshot must still show A->C->E."""
        block = run_arm("reroute", _greeting_fn([]), model_alias="gemma4-e4b")
        self.assertEqual(block["preferred_path"], ["A", "C", "E"])
        self.assertEqual(block["path"], ["A", "B", "D"])

    def test_answer_rule_is_disclosed(self) -> None:
        block = run_arm("reroute", _greeting_fn([]), model_alias="gemma4-e4b")
        self.assertIn("LAST number", block["answer_rule"])

    def test_all_nodes_executed_are_contract_bound(self) -> None:
        block = run_arm("reroute", _greeting_fn([]), model_alias="gemma4-e4b")
        for call in block["node_calls"]:
            self.assertTrue(call["prompt_sha256"])
            self.assertIsNotNone(call["expected"])
            self.assertIsNotNone(call["latency_ms"])

    def test_unknown_arm_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_arm("ghost", _greeting_fn([]), model_alias="gemma4-e4b")


class TestBuildReceipt(unittest.TestCase):
    @staticmethod
    def _health() -> dict[str, Any]:
        return {"backend_id": "llama-server", "reachable": True,
                "base_url": "http://127.0.0.1:8080", "models": ["gguf"]}

    @staticmethod
    def _backend() -> BackendIdentity:
        return BackendIdentity(
            backend_id="llama-server", model_alias="gemma4-e4b",
            config_hash="abc", base_url="http://127.0.0.1:8080",
        )

    def _both_arms(self) -> list[dict[str, Any]]:
        return [
            run_arm("clean", _greeting_fn([]), model_alias="gemma4-e4b"),
            run_arm("reroute", _greeting_fn([]), model_alias="gemma4-e4b"),
        ]

    def test_happy_path_promotes(self) -> None:
        receipt = build_receipt(
            self._both_arms(), run_id="t1",
            health=self._health(), backend=self._backend(),
        )
        self.assertEqual(receipt["promotion"], "PROMOTED")
        self.assertTrue(all(v == "PASS" for v in receipt["gates"].values()))
        self.assertEqual(receipt["receipt_type"], "SCORED_MINDMAP_REROUTE_LIVE")

    def test_unreachable_backend_blocks(self) -> None:
        health = self._health() | {"reachable": False}
        receipt = build_receipt(
            self._both_arms(), run_id="t1",
            health=health, backend=self._backend(),
        )
        self.assertEqual(receipt["gates"]["backend_reachable"], "FAIL")
        self.assertEqual(receipt["promotion"], "BLOCKED")

    def test_missing_reroute_blocks(self) -> None:
        """A treatment arm that never rerouted must not be filed as evidence."""
        clean = run_arm("clean", _greeting_fn([]), model_alias="gemma4-e4b")
        clean["arm"] = "reroute"  # pretend the treatment produced no reroute
        clean["reroute_observed"] = False
        clean["reroutes"] = []
        clean["reroute_count"] = 0
        receipt = build_receipt(
            [clean], run_id="t1", health=self._health(), backend=self._backend(),
        )
        self.assertEqual(
            receipt["gates"]["reroute_observed_under_live_inference"], "FAIL",
        )
        self.assertEqual(receipt["promotion"], "BLOCKED")

    def test_no_calls_blocks(self) -> None:
        receipt = build_receipt(
            [], run_id="t1", health=self._health(), backend=self._backend(),
        )
        self.assertEqual(receipt["gates"]["every_node_call_is_live"], "FAIL")
        self.assertEqual(receipt["promotion"], "BLOCKED")

    def test_ground_truth_is_disclosed(self) -> None:
        receipt = build_receipt(
            self._both_arms(), run_id="t1",
            health=self._health(), backend=self._backend(),
        )
        treatment = next(a for a in receipt["arms"] if a["arm"] == "reroute")
        self.assertEqual(treatment["contracts"]["C"]["expected"], float(GAP_PRODUCT))
        self.assertEqual(
            receipt["gates"]["contract_ground_truth_disclosed"], "PASS",
        )

    def test_measurements_carry_latency(self) -> None:
        receipt = build_receipt(
            self._both_arms(), run_id="t1",
            health=self._health(), backend=self._backend(),
        )
        latency = receipt["measurements"]["latency_ms"]
        self.assertGreater(latency["n"], 0)
        self.assertIn("median", latency)
        self.assertIn("p95", latency)

    def test_gate9_disclaimer_present(self) -> None:
        receipt = build_receipt(
            self._both_arms(), run_id="t1",
            health=self._health(), backend=self._backend(),
        )
        self.assertIn("MEASURED", receipt["gate9_disclaimer"])
        self.assertIn("scope_limit", receipt)


class TestCli(unittest.TestCase):
    def test_unknown_arm_is_usage_error(self) -> None:
        self.assertEqual(
            main(["--run-id", "x", "--output", "unused.json", "--arms", "ghost"]),
            4,
        )


@unittest.skipUnless(
    os.environ.get("VIVY_LIVE") == "1",
    "set VIVY_LIVE=1 to run the live integration check against :8080",
)
class TestLiveIntegration(unittest.TestCase):
    """Opt-in: runs the real harness against the live backend."""

    def test_live_run_produces_evidence(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = f"{td}/live.json"
            code = main([
                "--run-id", "live-it", "--output", out, "--allow-replace",
            ])
        self.assertIn(code, (0, 2))


if __name__ == "__main__":
    unittest.main()
