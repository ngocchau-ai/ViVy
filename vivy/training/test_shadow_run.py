import json
import tempfile
import unittest
from pathlib import Path

from training.shadow_run import run


class ShadowRunTests(unittest.TestCase):
    def test_emits_non_actuating_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d) / "in.jsonl", Path(d) / "out.jsonl"
            source.write_text(json.dumps({
                "selected_candidate": "a", "confidence": 0.5,
                "decision_type": "choice", "candidates": [{"id": "a"}],
                "label_quality": "unverified",
            }) + "\n", encoding="utf-8")
            self.assertEqual(run(source, output), 1)
            receipt = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "SHADOW_ONLY")
        self.assertFalse(receipt["actuated"])
        self.assertEqual(receipt["label_quality"], "unverified")


if __name__ == "__main__":
    unittest.main()
