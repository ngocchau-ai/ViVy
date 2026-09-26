"""C10 tests — C-ABI layout/ownership/error contract (DLL load ≠ memory path correct)."""
from __future__ import annotations

import ctypes
import unittest

from training.abi_layout import (
    CT_MEMORY_CONTENT_MAX,
    CT_MEMORY_HASH_MAX,
    CT_MEMORY_ID_MAX,
    KIND_VALUES,
    STATUS_VALUES,
    check_struct_layout,
    copy_item_out,
    map_status,
    ownership_rules,
)


class ConstantTests(unittest.TestCase):
    def test_header_constants_match(self):
        self.assertEqual(CT_MEMORY_ID_MAX, 96)
        self.assertEqual(CT_MEMORY_HASH_MAX, 96)
        self.assertEqual(CT_MEMORY_CONTENT_MAX, 1024 * 1024)

    def test_enum_values_match_header(self):
        self.assertEqual(KIND_VALUES["HARD_FACT"], 0)
        self.assertEqual(KIND_VALUES["TASK"], 1)
        self.assertEqual(KIND_VALUES["CONSTRAINT"], 2)
        self.assertEqual(KIND_VALUES["SUMMARY"], 3)
        self.assertEqual(STATUS_VALUES["OK"], 0)
        self.assertEqual(STATUS_VALUES["INVALID"], -1)
        self.assertEqual(STATUS_VALUES["NOMEM"], -2)
        self.assertEqual(STATUS_VALUES["IO"], -3)
        self.assertEqual(STATUS_VALUES["CORRUPT"], -4)
        self.assertEqual(STATUS_VALUES["CONFLICT"], -5)
        self.assertEqual(STATUS_VALUES["NOT_FOUND"], -6)


class StructLayoutTests(unittest.TestCase):
    def test_struct_field_order_matches_header(self):
        report = check_struct_layout()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["put_fields"], [
            "id", "kind", "content", "content_len", "provenance",
            "created_at_ms", "expires_at_ms",
        ])
        self.assertEqual(report["item_fields"], [
            "id", "kind", "content", "content_len", "message_id", "tool_call_id",
            "source_offset", "source_length", "source_hash",
            "version", "created_at_ms", "updated_at_ms", "expires_at_ms", "deleted",
        ])
        self.assertEqual(report["provenance_fields"], [
            "message_id", "tool_call_id", "source_offset", "source_length", "source_hash",
        ])

    def test_sizeof_positive_and_nested_provenance(self):
        report = check_struct_layout()
        self.assertGreater(report["sizeof"]["CtMemoryPut"], 0)
        self.assertGreater(report["sizeof"]["CtMemoryItem"], 0)
        self.assertGreaterEqual(
            report["sizeof"]["CtMemoryPut"],
            report["sizeof"]["CtMemoryProvenance"],
        )
        # id arrays must be the header max
        self.assertEqual(report["id_array_len"], CT_MEMORY_ID_MAX)
        self.assertEqual(report["hash_array_len"], CT_MEMORY_HASH_MAX)


class OwnershipTests(unittest.TestCase):
    def test_copy_item_out_is_independent_of_borrowed_pointer(self):
        class FakeBorrowed:
            id = b"k1"
            kind = 0
            content = b"hello"
            content_len = 5
            version = 3
            created_at_ms = 1
            updated_at_ms = 2

        borrowed = FakeBorrowed()
        copied = copy_item_out(borrowed)
        borrowed.content = b"MUTATED"
        self.assertEqual(copied["content"], "hello")
        self.assertEqual(copied["version"], 3)

    def test_ownership_rules_document_borrowed_get(self):
        rules = ownership_rules()
        self.assertIn("get_returns_borrowed_must_copy", rules)
        self.assertTrue(rules["get_returns_borrowed_must_copy"])
        self.assertIn("put_ownership", rules)
        self.assertIn("close_invalidates", rules)


class ErrorPropagationTests(unittest.TestCase):
    def test_status_codes_map_to_exceptions(self):
        self.assertIsNone(map_status(0))
        self.assertEqual(map_status(-5).__class__.__name__, "MemoryConflict")
        self.assertEqual(map_status(-6).__class__.__name__, "MemoryNotFound")
        self.assertEqual(map_status(-1).__class__.__name__, "MemoryInvalid")
        self.assertEqual(map_status(-2).__class__.__name__, "MemoryError")
        self.assertEqual(map_status(-3).__class__.__name__, "MemoryIOError")
        self.assertEqual(map_status(-4).__class__.__name__, "MemoryCorrupt")

    def test_unknown_status_is_invalid(self):
        self.assertEqual(map_status(-99).__class__.__name__, "MemoryInvalid")
        self.assertEqual(map_status(7).__class__.__name__, "MemoryInvalid")


if __name__ == "__main__":
    unittest.main()
