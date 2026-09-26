import tempfile
import unittest
from pathlib import Path

from training.baseline import run_baseline


class BaselineTests(unittest.TestCase):
    def test_majority_is_descriptive_and_hashes_input(self):
        text = '{"messages":[{},{},{"content":"Selected_Candidate_ID: a"}]}\n'
        text += '{"messages":[{},{},{"content":"Selected_Candidate_ID: b"}]}\n'
        text += '{"messages":[{},{},{"content":"Selected_Candidate_ID: a"}]}\n'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.jsonl"
            p.write_text(text, encoding="utf-8")
            report = run_baseline(p)
        self.assertEqual(report["rows_with_label"], 3)
        self.assertEqual(report["majority_label"], "a")
        self.assertEqual(report["majority_share"], 2 / 3)
        self.assertEqual(report["status"], "DESCRIPTIVE_ONLY_NO_INDEPENDENT_GOLD_OUTCOME")


if __name__ == "__main__":
    unittest.main()
