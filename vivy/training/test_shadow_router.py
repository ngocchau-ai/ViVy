"""Shadow-router tests — §2.3 label leakage + §2.5 abstain semantics."""
from __future__ import annotations

import unittest

from training.shadow_router import predict_input, recommend, replay_copy_label


class ShadowRouterTests(unittest.TestCase):
    def test_unverified_label_is_abstained(self):
        result = recommend({
            "decision_type": "choice",
            "candidates": [{"id": "a"}, {"id": "b"}],
            "selected_candidate": "b",
            "confidence": 0.8,
        })
        self.assertIsNone(result.recommendation)
        self.assertIsNone(result.agree)
        self.assertFalse(result.actuated)

    def test_reviewed_label_without_predictor_does_not_copy_label(self):
        """§2.3: copying selected_candidate is label leakage — must abstain."""
        result = recommend({
            "decision_type": "choice", "candidates": [{"id": "b"}, {"id": "c"}],
            "selected_candidate": "b", "confidence": 0.8,
            "label_quality": "independently_reviewed",
        })
        self.assertIsNone(result.recommendation)
        self.assertIsNone(result.agree)
        self.assertEqual(result.policy, "abstain_no_predictor")

    def test_external_predictor_is_scored_not_label(self):
        result = recommend({
            "decision_type": "choice",
            "candidates": [{"id": "b"}, {"id": "c"}],
            "selected_candidate": "c",
            "predicted_candidate": "b",
            "confidence": 0.4,
            "label_quality": "independently_reviewed",
        })
        self.assertEqual(result.recommendation, "b")
        self.assertEqual(result.observed, "c")
        self.assertFalse(result.agree)
        self.assertEqual(result.policy, "external_predictor")

    def test_predicted_candidate_outside_set_is_rejected(self):
        result = recommend({
            "decision_type": "choice",
            "candidates": [{"id": "b"}],
            "selected_candidate": "b",
            "predicted_candidate": "zzz",
            "label_quality": "independently_reviewed",
        })
        self.assertIsNone(result.recommendation)

    def test_noul_has_no_recommendation(self):
        result = recommend({"decision_type": "noul", "selected_candidate": None, "confidence": 0.2})
        self.assertIsNone(result.recommendation)
        self.assertFalse(result.actuated)

    def test_abstain_semantics_cover_cand_abstain_refusal_reobserve(self):
        for cid, action in (
            ("cand_abstain", ""),
            ("cand_x", "refusal"),
            ("cand_y", "reobserve"),
        ):
            result = recommend({
                "decision_type": "choice",
                "candidates": [{"id": cid, "action_type": action}],
                "selected_candidate": cid,
                "label_quality": "independently_reviewed",
            })
            self.assertIsNone(result.recommendation, cid)
            self.assertEqual(result.policy, "abstain_semantics")

    def test_predict_input_strips_labels(self):
        payload = predict_input({
            "decision_type": "choice",
            "context_state": "goal",
            "candidates": [{"id": "a", "description": "click", "action_type": "click"}],
            "selected_candidate": "a",
            "gold_selected_candidate": "a",
            "gold_outcome": "success",
            "reviewer": "human",
        })
        self.assertNotIn("selected_candidate", payload)
        self.assertNotIn("gold_selected_candidate", payload)
        self.assertNotIn("gold_outcome", payload)
        self.assertNotIn("reviewer", payload)
        self.assertEqual(payload["candidates"][0]["id"], "a")

    def test_replay_copy_label_is_isolated_leaky_fixture(self):
        result = replay_copy_label({
            "decision_type": "choice",
            "candidates": [{"id": "b"}],
            "selected_candidate": "b",
            "label_quality": "independently_reviewed",
        })
        self.assertEqual(result.recommendation, "b")
        self.assertTrue(result.agree)
        self.assertIn("LEAKY", result.policy)
        self.assertIn("CIRCULAR", result.note)


if __name__ == "__main__":
    unittest.main()
