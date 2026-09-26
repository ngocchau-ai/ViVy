import json
import tempfile
import unittest
from pathlib import Path

from training.gold_review_queue import create_queue


class GoldQueueTests(unittest.TestCase):
    def test_queue_is_pending_and_preserves_label(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps({"selected_candidate": "a"}) + "\n", encoding="utf-8")
            self.assertEqual(create_queue(source, output), 1)
            row = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(row["selected_candidate"], "a")
        self.assertEqual(row["review"]["status"], "PENDING")
        self.assertIsNone(row["review"]["gold_outcome"])


if __name__ == "__main__":
    unittest.main()
