import json
import tempfile
import unittest
from pathlib import Path

from training.legacy_to_typed import migrate


class LegacyMigrationTests(unittest.TestCase):
    def test_only_explicit_cua_rows_are_migrated_and_marked_unverified(self):
        row = {"source": "cua", "messages": [{}, {
            "content": "Goal: save\nBounded Candidate Table:\n- [save]: click save\nSelect the safest"
        }, {"content": "Selected_Candidate_ID: save\nExpected_Evidence: postcondition"}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "in.jsonl"
            p.write_text(json.dumps(row) + "\n", encoding="utf-8")
            rows = list(migrate(p))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["selected_candidate"], "save")
        self.assertEqual(rows[0]["label_quality"], "unverified")
        self.assertTrue(rows[0]["provenance"]["receipt_id"].startswith("legacy-"))


if __name__ == "__main__":
    unittest.main()
