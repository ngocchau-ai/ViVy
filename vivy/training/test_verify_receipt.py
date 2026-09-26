"""Tests for verify_receipt — SHA256 chain integrity (D3)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.verify_receipt import (
    GENESIS,
    compute_self_sha256,
    seal_receipt,
    verify_chain,
    verify_receipt,
    verify_receipts_dir,
)


class VerifyReceiptTests(unittest.TestCase):
    def test_seal_and_verify_single_receipt(self):
        receipt = {"run_id": "r1", "stage": "test", "data": "hello"}
        sealed = seal_receipt(receipt, prev_sha256=GENESIS)
        self.assertIn("self_sha256", sealed)
        self.assertIn("prev_receipt_sha256", sealed)
        self.assertEqual(sealed["prev_receipt_sha256"], GENESIS)
        problems = verify_receipt(sealed)
        self.assertEqual(problems, [])

    def test_tampered_receipt_fails(self):
        receipt = {"run_id": "r1", "stage": "test", "data": "hello"}
        sealed = seal_receipt(receipt, prev_sha256=GENESIS)
        sealed["data"] = "tampered"
        problems = verify_receipt(sealed)
        self.assertTrue(any("mismatch" in p for p in problems))

    def test_chain_intact(self):
        r1 = seal_receipt({"run_id": "r1", "data": "a"}, prev_sha256=GENESIS)
        r2 = seal_receipt({"run_id": "r2", "data": "b"}, prev_sha256=r1["self_sha256"])
        r3 = seal_receipt({"run_id": "r3", "data": "c"}, prev_sha256=r2["self_sha256"])
        problems = verify_chain([r1, r2, r3])
        self.assertEqual(problems, [])

    def test_chain_break_detected(self):
        r1 = seal_receipt({"run_id": "r1", "data": "a"}, prev_sha256=GENESIS)
        r2 = seal_receipt({"run_id": "r2", "data": "b"}, prev_sha256=r1["self_sha256"])
        r3 = seal_receipt({"run_id": "r3", "data": "c"}, prev_sha256=GENESIS)  # wrong prev
        problems = verify_chain([r1, r2, r3])
        self.assertTrue(any("chain break" in p for p in problems))

    def test_empty_chain_fails(self):
        problems = verify_chain([])
        self.assertTrue(any("empty" in p for p in problems))

    def test_first_receipt_must_be_genesis(self):
        r1 = seal_receipt({"run_id": "r1", "data": "a"}, prev_sha256="NOT_GENESIS")
        problems = verify_chain([r1])
        self.assertTrue(any("GENESIS" in p for p in problems))

    def test_verify_receipts_dir(self):
        r1 = seal_receipt({"run_id": "r1", "data": "a"}, prev_sha256=GENESIS)
        r2 = seal_receipt({"run_id": "r2", "data": "b"}, prev_sha256=r1["self_sha256"])
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            (dp / "a_r1.json").write_text(json.dumps(r1), encoding="utf-8")
            (dp / "b_r2.json").write_text(json.dumps(r2), encoding="utf-8")
            result = verify_receipts_dir(dp)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["receipt_count"], 2)

    def test_verify_receipts_dir_detects_tamper(self):
        r1 = seal_receipt({"run_id": "r1", "data": "a"}, prev_sha256=GENESIS)
        r2 = seal_receipt({"run_id": "r2", "data": "b"}, prev_sha256=r1["self_sha256"])
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            (dp / "a_r1.json").write_text(json.dumps(r1), encoding="utf-8")
            # Tamper with r2
            r2_bad = dict(r2, data="tampered")
            (dp / "b_r2.json").write_text(json.dumps(r2_bad), encoding="utf-8")
            result = verify_receipts_dir(dp)
            self.assertEqual(result["status"], "FAIL")

    def test_compute_self_sha256_ignores_self_field(self):
        receipt = {"run_id": "r1", "data": "a"}
        h1 = compute_self_sha256(receipt)
        receipt_with_self = {**receipt, "self_sha256": "whatever"}
        h2 = compute_self_sha256(receipt_with_self)
        self.assertEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
