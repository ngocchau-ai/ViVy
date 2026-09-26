"""Small read-only audit tests.

Change log: Codex, 2026-09-23 — cover typed readiness, legacy rejection and
malformed JSON using temporary files only.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.audit_dataset import audit_jsonl, main


class AuditDatasetTests(unittest.TestCase):
    def _write(self, lines: list[str]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_typed_ready_legacy_rejected_and_parse_error(self) -> None:
        typed = {
            "task_context": "validate a safe change",
            "decision_type": "choice",
            "candidates": [{"id": "execute"}, {"id": "noul"}],
            "selected_candidate": "execute",
            "confidence": 0.8,
            "evidence_required": ["postcondition"],
            "provenance": {
                "source": "gold",
                "producer": "human",
                "receipt_id": "r-1",
                "timestamp": "2026-09-23T00:00:00Z",
            },
            "split": "dev",
        }
        legacy = {"messages": [{"role": "user", "content": "Task Execution: old"}], "source": "legacy"}
        path = self._write([json.dumps(typed), json.dumps(legacy), "{broken"])

        report = audit_jsonl(path)

        self.assertEqual(report["total"], 3)
        self.assertEqual(report["ready_count"], 1)
        self.assertEqual(report["rejected_count"], 2)
        self.assertEqual(report["parse_errors"], 1)
        self.assertEqual(report["missing_candidates"], 1)
        self.assertEqual(report["missing_noul"], 1)
        self.assertEqual(report["missing_task_context"], 1)
        self.assertEqual(report["untyped"], 1)
        self.assertEqual(report["source_counts"], {"gold": 1, "legacy": 1})

    def test_report_path_and_input_unchanged(self) -> None:
        path = self._write([json.dumps({"source": "legacy"})])
        before = path.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            self.assertEqual(main([str(path), "--report", str(output)]), 0)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["total"], 1)


if __name__ == "__main__":
    unittest.main()
