"""C02 contract negatives — null/bool/NaN/Inf/dup/unknown/wrong-type/unicode/split."""
from __future__ import annotations

import math
import unittest

from training.decision_contract import (
    CONTRACT_VERSION,
    DecisionPrediction,
    check_authority,
    decision_input_from_record,
    validate_decision_input,
    validate_decision_label,
    validate_decision_prediction,
    verify_receipt_linkage,
)


def _input(**overrides):
    base = {
        "task_id": "task-1",
        "decision_type": "choice",
        "context_state": "Goal: save the file.",
        "candidates": [
            {"id": "cand_save", "description": "save", "action_type": "click"},
            {"id": "cand_halt", "description": "halt", "action_type": "halt"},
        ],
    }
    base.update(overrides)
    return base


class DecisionInputTests(unittest.TestCase):
    def test_valid_input(self):
        parsed = validate_decision_input(_input())
        self.assertEqual(parsed.task_id, "task-1")
        self.assertEqual(parsed.candidate_ids(), ("cand_save", "cand_halt"))
        self.assertEqual(parsed.contract_version, CONTRACT_VERSION)

    def test_rejects_null_task_id(self):
        with self.assertRaises(ValueError):
            validate_decision_input(_input(task_id=None))

    def test_rejects_bool_as_number_fields(self):
        # bool is not a valid confidence/number — enforced on prediction side
        with self.assertRaises(ValueError):
            validate_decision_prediction({"abstain": True, "confidence": True})

    def test_rejects_nan_inf_confidence(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                validate_decision_prediction({"abstain": True, "confidence": bad})

    def test_rejects_duplicate_candidate_ids(self):
        with self.assertRaises(ValueError):
            validate_decision_input(_input(candidates=[
                {"id": "a", "description": "x"},
                {"id": "a", "description": "y"},
            ]))

    def test_rejects_unknown_predicted_id(self):
        with self.assertRaises(ValueError):
            validate_decision_prediction(
                {"predicted_candidate": "ghost", "confidence": 0.5},
                allowed_ids=["cand_save", "cand_halt"],
            )

    def test_rejects_nested_wrong_types(self):
        with self.assertRaises(ValueError):
            validate_decision_input(_input(candidates=[{"id": 123, "description": "x"}]))
        with self.assertRaises(ValueError):
            validate_decision_input(_input(candidates=[{"id": "a", "description": None}]))
        with self.assertRaises(ValueError):
            validate_decision_input(_input(candidates="not-a-list"))

    def test_rejects_label_fields_on_input(self):
        for leaked in ("selected_candidate", "gold_selected_candidate", "gold_outcome",
                       "reviewer", "reward", "label_quality"):
            with self.assertRaises(ValueError):
                validate_decision_input(_input(**{leaked: "x"}))

    def test_decision_input_from_record_drops_labels(self):
        row = _input(
            selected_candidate="cand_save",
            gold_selected_candidate="cand_save",
            gold_outcome="unknown",
            review={"reviewer": "human"},
            reward=1.0,
        )
        parsed = decision_input_from_record(row)
        dumped = parsed.to_dict()
        self.assertNotIn("selected_candidate", dumped)
        self.assertNotIn("gold_outcome", dumped)
        self.assertNotIn("reward", dumped)

    def test_rejects_malformed_json_mapping(self):
        with self.assertRaises(ValueError):
            validate_decision_input("not-a-mapping")

    def test_accepts_malformed_unicode_in_context(self):
        # surrogates / odd unicode are data, not a crash
        parsed = validate_decision_input(_input(context_state="goal � ok \U0001f600"))
        self.assertIn("ok", parsed.context_state)

    def test_rejects_missing_evidence_shape_on_label(self):
        with self.assertRaises(ValueError):
            validate_decision_label({})

    def test_rejects_invalid_split_on_typed_decision(self):
        from training.typed_decision import validate_typed_decision
        record = {
            "decision_type": "choice",
            "candidates": [{"id": "a"}],
            "selected_candidate": "a",
            "confidence": 0.5,
            "evidence_required": ["x"],
            "provenance": {"source": "s", "producer": "p", "receipt_id": "r", "timestamp": "t"},
            "split": "validation",
        }
        with self.assertRaises(ValueError):
            validate_typed_decision(record)


class PredictionTests(unittest.TestCase):
    def test_abstain_and_prediction_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            validate_decision_prediction({
                "abstain": True, "predicted_candidate": "cand_save", "confidence": 0.5,
            })

    def test_probabilities_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            validate_decision_prediction(
                {"abstain": True, "confidence": 0.5,
                 "probabilities": {"a": 0.2, "b": 0.2}},
                allowed_ids=["a", "b"],
            )

    def test_score_is_not_a_probability(self):
        with self.assertRaises(ValueError):
            validate_decision_prediction({
                "abstain": True, "confidence": 0.5,
                "score": 0.5, "score_kind": "ordinal", "score_is_probability": True,
            })

    def test_score_requires_kind(self):
        with self.assertRaises(ValueError):
            validate_decision_prediction({
                "abstain": True, "confidence": 0.5, "score": 3, "score_kind": "probability",
            })
        ok = validate_decision_prediction({
            "abstain": True, "confidence": 0.5, "score": 3, "score_kind": "ordinal",
        })
        self.assertEqual(ok.score_kind, "ordinal")

    def test_noul_decision_type_is_not_halt_action(self):
        """decision_type=noul ≠ candidate action_type=halt ≠ abstain policy."""
        noul_input = validate_decision_input(_input(decision_type="noul", candidates=[
            {"id": "cand_abstain", "description": "do nothing", "action_type": "abstain"},
        ]))
        halt_input = validate_decision_input(_input(decision_type="choice", candidates=[
            {"id": "cand_halt", "description": "halt", "action_type": "halt"},
        ]))
        self.assertEqual(noul_input.decision_type, "noul")
        self.assertEqual(halt_input.decision_type, "choice")
        self.assertEqual(halt_input.candidates[0]["action_type"], "halt")
        abstain_pred = validate_decision_prediction({
            "abstain": True, "abstain_policy": "abstain_no_predictor", "confidence": 0.0,
        })
        self.assertTrue(abstain_pred.abstain)
        self.assertEqual(abstain_pred.abstain_policy, "abstain_no_predictor")


class AuthorityTests(unittest.TestCase):
    def test_authority_ignores_high_confidence_on_dangerous_action(self):
        decision_input = validate_decision_input(_input(candidates=[
            {"id": "cand_wipe", "description": "wipe disk", "action_type": "delete"},
            {"id": "cand_halt", "description": "halt", "action_type": "halt"},
        ]))
        hot = validate_decision_prediction(
            {"predicted_candidate": "cand_wipe", "confidence": 0.99, "probabilities": {"cand_wipe": 1.0, "cand_halt": 0.0}},
            allowed_ids=decision_input.candidate_ids(),
        )
        verdict = check_authority(decision_input, prediction=hot, approved_task_ids=[])
        self.assertFalse(verdict.allowed)
        self.assertTrue(verdict.requires_approval)

    def test_authority_allows_dangerous_action_only_with_task_approval(self):
        decision_input = validate_decision_input(_input(candidates=[
            {"id": "cand_wipe", "description": "wipe", "action_type": "delete"},
        ]))
        pred = validate_decision_prediction(
            {"predicted_candidate": "cand_wipe", "confidence": 0.9},
            allowed_ids=["cand_wipe"],
        )
        denied = check_authority(decision_input, prediction=pred, approved_task_ids=[])
        granted = check_authority(decision_input, prediction=pred, approved_task_ids=["task-1"])
        self.assertFalse(denied.allowed)
        self.assertTrue(granted.allowed)

    def test_preconditions_must_be_met(self):
        decision_input = validate_decision_input(_input())
        pred = validate_decision_prediction(
            {"predicted_candidate": "cand_save", "confidence": 0.5},
            allowed_ids=decision_input.candidate_ids(),
        )
        bad = check_authority(
            decision_input, prediction=pred,
            preconditions_met={"user_confirmed": False},
        )
        good = check_authority(
            decision_input, prediction=pred,
            preconditions_met={"user_confirmed": True},
        )
        self.assertFalse(bad.allowed)
        self.assertTrue(good.allowed)


class ReceiptLinkageTests(unittest.TestCase):
    def _label(self, **overrides):
        base = {
            "gold_selected_candidate": "cand_save",
            "gold_outcome": "unknown",
            "reviewer": "human",
            "reviewed_at": "2026-09-24T00:00:00Z",
            "independent_receipt_id": "human-accept-0123456789abcdef",
            "label_quality": "independently_reviewed",
        }
        base.update(overrides)
        return validate_decision_label(base)

    def test_self_declared_id_without_receipt_fails(self):
        label = self._label()
        self.assertFalse(verify_receipt_linkage(label, known_receipts={}))

    def test_receipt_must_link_task_or_hash_or_producer(self):
        label = self._label()
        empty_link = {
            "human-accept-0123456789abcdef": {"note": "trust me"},
        }
        self.assertFalse(verify_receipt_linkage(label, known_receipts=empty_link))
        linked = {
            "human-accept-0123456789abcdef": {
                "producer": "human", "task_id": "task-1", "payload_sha256": "abc",
            },
        }
        self.assertTrue(verify_receipt_linkage(label, known_receipts=linked, task_id="task-1"))

    def test_hash_mismatch_fails(self):
        label = self._label()
        receipts = {
            "human-accept-0123456789abcdef": {"payload_sha256": "aaa", "producer": "human"},
        }
        self.assertFalse(verify_receipt_linkage(
            label, known_receipts=receipts, expect_hash="bbb",
        ))

    def test_unknown_outcome_is_not_success(self):
        label = self._label(gold_outcome="unknown")
        self.assertFalse(label.outcome_known)
        known = self._label(gold_outcome="success")
        self.assertTrue(known.outcome_known)

    def test_rejects_bad_receipt_format(self):
        with self.assertRaises(ValueError):
            self._label(independent_receipt_id="trust-me-bro")


if __name__ == "__main__":
    unittest.main()
