"""C08 tests — token ledger requires a real tokenizer; no silent approximation."""
from __future__ import annotations

import unittest

from training.token_ledger import (
    ApproximateTokenizer,
    TokenLedger,
    TokenizerRequired,
    byte_tokenizer,
)


class RealTokenizerTests(unittest.TestCase):
    def test_refuses_without_tokenizer(self):
        with self.assertRaises(TokenizerRequired):
            TokenLedger(tokenizer=None)

    def test_approximate_tokenizer_is_labeled(self):
        tok = ApproximateTokenizer()
        self.assertTrue(tok.is_approximate)
        self.assertEqual(tok.kind, "approximate_whitespace")
        with self.assertRaises(TokenizerRequired):
            TokenLedger(tokenizer=tok, require_real_tokenizer=True)

    def test_byte_tokenizer_is_exact_for_bytes(self):
        self.assertFalse(byte_tokenizer.is_approximate)
        self.assertEqual(byte_tokenizer.kind, "byte_exact")
        self.assertEqual(byte_tokenizer.count("abc"), 3)
        self.assertEqual(byte_tokenizer.count("héllo"), len("héllo".encode("utf-8")))


class LedgerTests(unittest.TestCase):
    def test_ledger_records_before_after_and_delta(self):
        ledger = TokenLedger(tokenizer=byte_tokenizer)
        ledger.record("context_before", "abcdefghij")   # 10
        ledger.record("context_after", "abcde")          # 5
        summary = ledger.summary()
        self.assertEqual(summary["counts"]["context_before"], 10)
        self.assertEqual(summary["counts"]["context_after"], 5)
        self.assertEqual(summary["delta_before_to_after"], -5)
        self.assertEqual(summary["tokenizer_kind"], "byte_exact")
        self.assertFalse(summary["is_approximate"])
        self.assertEqual(summary["status_label"], "VERIFIED_COUNTS")

    def test_approximate_counts_are_not_verified(self):
        ledger = TokenLedger(tokenizer=ApproximateTokenizer(), require_real_tokenizer=False)
        ledger.record("x", "one two three")
        summary = ledger.summary()
        self.assertTrue(summary["is_approximate"])
        self.assertEqual(summary["status_label"], "APPROXIMATE_NOT_VERIFIED")

    def test_reduction_percent_is_reported_not_invented(self):
        ledger = TokenLedger(tokenizer=byte_tokenizer)
        ledger.record("context_before", "x" * 100)
        ledger.record("context_after", "x" * 40)
        self.assertAlmostEqual(ledger.summary()["reduction_percent"], 60.0)


if __name__ == "__main__":
    unittest.main()
