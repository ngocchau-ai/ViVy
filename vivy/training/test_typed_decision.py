import unittest

from training.typed_decision import validate_typed_decision


class TypedDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = {
            "decision_type": "choice",
            "candidates": [{"id": "execute"}, {"id": "noul"}],
            "selected_candidate": "execute",
            "confidence": 0.9,
            "evidence_required": ["postcondition"],
            "provenance": {
                "source": "gold",
                "producer": "human",
                "receipt_id": "receipt-1",
                "timestamp": "2026-09-23T00:00:00Z",
            },
            "split": "train",
        }

    def test_valid_choice(self) -> None:
        decision = validate_typed_decision(self.record)
        self.assertEqual(decision.selected_candidate, "execute")
        self.assertEqual(decision.confidence, 0.9)

    def test_valid_score(self) -> None:
        record = {**self.record, "decision_type": "score", "score": 0.7}
        self.assertEqual(validate_typed_decision(record).score, 0.7)

    def test_valid_noul(self) -> None:
        record = {
            **self.record,
            "decision_type": "noul",
            "selected_candidate": None,
        }
        decision = validate_typed_decision(record)
        self.assertIsNone(decision.selected_candidate)

    def test_rejects_invalid_decision_type(self) -> None:
        with self.assertRaises(ValueError):
            validate_typed_decision({**self.record, "decision_type": "freeform"})

    def test_rejects_unknown_selected_candidate(self) -> None:
        with self.assertRaises(ValueError):
            validate_typed_decision({**self.record, "selected_candidate": "missing"})

    def test_rejects_out_of_range_confidence(self) -> None:
        with self.assertRaises(ValueError):
            validate_typed_decision({**self.record, "confidence": 1.01})

    def test_rejects_missing_provenance_and_bad_split(self) -> None:
        with self.assertRaises(ValueError):
            validate_typed_decision({**self.record, "provenance": {}})
        with self.assertRaises(ValueError):
            validate_typed_decision({**self.record, "split": "validation"})

    def test_rejects_duplicate_candidates(self) -> None:
        record = {**self.record, "candidates": [{"id": "execute"}, {"id": "execute"}]}
        with self.assertRaises(ValueError):
            validate_typed_decision(record)


if __name__ == "__main__":
    unittest.main()
