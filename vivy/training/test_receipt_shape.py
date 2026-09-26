"""Tests for receipt.py validate_live_shape (D5)."""
from __future__ import annotations

import unittest

from training.receipt import LiveShapeError, validate_live_shape


class LiveShapeValidationTests(unittest.TestCase):
    def test_complete_payload_passes(self):
        payload = {
            "live": True,
            "model": "gemma4-e4b",
            "model_hash": "abc123",
            "config_hash": "def456",
            "denominator": 50,
        }
        validate_live_shape(payload)  # should not raise

    def test_missing_fields_raise(self):
        payload = {"live": True, "model": "x"}
        with self.assertRaises(LiveShapeError) as ctx:
            validate_live_shape(payload)
        msg = str(ctx.exception)
        self.assertIn("model_hash", msg)
        self.assertIn("config_hash", msg)
        self.assertIn("denominator", msg)

    def test_all_missing_raise(self):
        with self.assertRaises(LiveShapeError):
            validate_live_shape({})

    def test_single_missing_field_raise(self):
        payload = {
            "live": True,
            "model": "x",
            "model_hash": "h",
            "config_hash": "c",
        }
        with self.assertRaises(LiveShapeError) as ctx:
            validate_live_shape(payload)
        self.assertIn("denominator", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
