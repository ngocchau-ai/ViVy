"""Tests for native_parity_decision (Plan 2 A — fix-or-retire).

Changelog:
    24/09/2026 (Claude Code — Plan 2 A): Initial.
"""
from __future__ import annotations

import unittest

from training.native_parity_decision import (
    ParityDecision,
    ParityEvidence,
    decide_native_parity,
    decision_to_dict,
    l40_evidence,
)


class TestParityEvidence(unittest.TestCase):
    def test_defaults(self) -> None:
        e = ParityEvidence(check_id="c1", status="PASS")
        self.assertEqual(e.detail, "")
        self.assertEqual(e.receipt_id, "")

    def test_frozen(self) -> None:
        e = ParityEvidence(check_id="c1", status="PASS")
        with self.assertRaises(AttributeError):
            e.status = "FAIL"  # type: ignore[misc]


class TestL40Evidence(unittest.TestCase):
    def test_has_fail_checks(self) -> None:
        evid = l40_evidence()
        self.assertEqual(len(evid), 4)
        statuses = {e.check_id: e.status for e in evid}
        self.assertEqual(statuses["forward-logits-parity"], "FAIL")
        self.assertEqual(statuses["exact-prompt-parity"], "FAIL")
        self.assertEqual(statuses["tokenizer-parity"], "PASS")
        self.assertEqual(statuses["template-parity"], "PASS")


class TestDecideA_fix(unittest.TestCase):
    def test_a_fix_when_all_conditions_met(self) -> None:
        d = decide_native_parity(
            [ParityEvidence(check_id="c1", status="PASS")],
            fix_available=True,
            fix_has_regression=True,
            budget_exhausted=False,
        )
        self.assertEqual(d.decision, "A-fix")
        self.assertEqual(d.gate1_status, "native_residency_closed")
        self.assertTrue(d.native_memory_retained)
        self.assertEqual(d.label, "PROVISIONAL_RESULT")

    def test_a_fix_requires_regression(self) -> None:
        d = decide_native_parity(
            [],
            fix_available=True,
            fix_has_regression=False,
            budget_exhausted=False,
        )
        self.assertEqual(d.decision, "A-retire")
        self.assertIn("regression", d.rationale)


class TestDecideA_retire(unittest.TestCase):
    def test_retire_when_budget_exhausted(self) -> None:
        d = decide_native_parity(
            l40_evidence(),
            fix_available=False,
            fix_has_regression=False,
            budget_exhausted=True,
        )
        self.assertEqual(d.decision, "A-retire")
        self.assertEqual(d.gate1_status, "llama_server_only")
        self.assertTrue(d.native_memory_retained)

    def test_retire_when_no_fix(self) -> None:
        d = decide_native_parity([], fix_available=False, budget_exhausted=False)
        self.assertEqual(d.decision, "A-retire")

    def test_retire_when_fix_without_regression(self) -> None:
        d = decide_native_parity(
            [], fix_available=True, fix_has_regression=False, budget_exhausted=False
        )
        self.assertEqual(d.decision, "A-retire")

    def test_isolate_not_delete(self) -> None:
        d = decide_native_parity([], fix_available=False)
        self.assertIn("isolate", d.rationale.lower())
        self.assertIn("not delete", d.rationale.lower())

    def test_abi_unstable_drops_memory(self) -> None:
        d = decide_native_parity([], fix_available=False, abi_stable=False)
        self.assertFalse(d.native_memory_retained)

    def test_claim_boundary(self) -> None:
        d = decide_native_parity([], fix_available=False)
        self.assertIn("PRODUCTION-READY = NOT_CLAIMED", d.claim_boundary)
        self.assertIn("Does NOT indict llama-server", d.claim_boundary)


class TestDecisionToDict(unittest.TestCase):
    def test_serializes(self) -> None:
        d = decide_native_parity(l40_evidence(), fix_available=False)
        obj = decision_to_dict(d)
        self.assertEqual(obj["decision"], "A-retire")
        self.assertEqual(obj["gate1_status"], "llama_server_only")
        self.assertEqual(len(obj["evidence"]), 4)
        self.assertIn("PROVISIONAL_RESULT", obj["label"])
        self.assertIn("NOT_CLAIMED", obj["claim_boundary"])


class TestParityDecisionType(unittest.TestCase):
    def test_is_dataclass(self) -> None:
        self.assertTrue(hasattr(ParityDecision, "__dataclass_fields__"))


if __name__ == "__main__":
    unittest.main()
