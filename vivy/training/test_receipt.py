import tempfile
import unittest
from pathlib import Path

from training.receipt import build_receipt, make_receipt_id, write_receipt


class ReceiptTests(unittest.TestCase):
    def test_failed_gate_blocks_promotion(self):
        receipt = build_receipt(
            run_id="baseline-001", stage="baseline",
            metrics={"rows": 50},
            gates={"independent_gold": "FAIL", "dataset_hash": "PASS"},
            input_sha256="abc",
        )
        self.assertEqual(receipt["promotion"], "BLOCKED")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipt.json"
            write_receipt(p, receipt)
            self.assertEqual(p.read_text(encoding="utf-8").count("baseline-001"), 1)

    def test_empty_gates_do_not_promote(self):
        """§2.8: all([]) is True — empty gate maps must stay BLOCKED."""
        receipt = build_receipt(
            run_id="empty-001", stage="baseline",
            metrics={"rows": 0},
            gates={},
            input_sha256="abc",
        )
        self.assertEqual(receipt["promotion"], "BLOCKED")

    def test_write_receipt_refuses_overwrite(self):
        receipt = build_receipt(
            run_id="once-001", stage="baseline",
            metrics={"rows": 1},
            gates={"dataset_hash": "PASS"},
            input_sha256="abc",
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipt.json"
            write_receipt(p, receipt)
            from training.io_guard import RefuseOverwriteError
            with self.assertRaises(RefuseOverwriteError):
                write_receipt(p, receipt)
            write_receipt(p, receipt, allow_replace=True)

    def test_make_receipt_id_is_deterministic_and_order_insensitive(self):
        a = make_receipt_id(kind="oracle", payload={"rule_version": "v1", "label": "cand_01"})
        b = make_receipt_id(kind="oracle", payload={"label": "cand_01", "rule_version": "v1"})
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("oracle-"))
        self.assertEqual(len(a), len("oracle-") + 16)

    def test_make_receipt_id_changes_when_payload_changes(self):
        base = make_receipt_id(kind="human-accept", payload={"reviewer": "r1", "label": "cand_01"})
        changed = make_receipt_id(kind="human-accept", payload={"reviewer": "r1", "label": "cand_02"})
        other_kind = make_receipt_id(kind="oracle", payload={"reviewer": "r1", "label": "cand_01"})
        self.assertNotEqual(base, changed)
        self.assertNotEqual(base, other_kind)


if __name__ == "__main__":
    unittest.main()
