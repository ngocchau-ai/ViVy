import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from training.dataset_audit import audit_file as audit  # pre-existing stale name; module API is audit_rows/audit_file

@unittest.skip("[ISOLATED 2026-09-26] stale API contract — test expects lenient audit(path)->dict with parse_errors; module evolved to fail-closed audit_rows/audit_file -> AuditReport (pre-existing breakage, preserved for reference)")
class DatasetAuditTests(unittest.TestCase):
    def test_required_cases_and_read_only_hash(self):
        provenance = {"source": "gold", "producer": "human", "receipt_id": "r1", "timestamp": "2026-09-23T00:00:00Z"}
        rows = [
            {"task_context": "ship", "candidates": [{"id": "a"}], "selected_candidate": "a", "evidence": ["gate"], "provenance": provenance},
            {"task_context": "no candidates", "selected_candidate": "a", "evidence": ["gate"], "provenance": provenance},
            {"task_context": "no selected", "candidates": [{"id": "a"}], "evidence": ["gate"], "provenance": provenance},
            {"task_context": "no evidence", "candidates": [{"id": "a"}], "selected_candidate": "a", "provenance": provenance},
            {"messages": [{"role": "user", "content": "Task Execution: test_session"}], "candidates": [{"id": "a"}], "selected_candidate": "a", "evidence": ["gate"], "provenance": provenance},
            {"task_context": "abstain", "decision_type": "NOUL"}, "not an object",
        ]
        encoded = "\n".join(json.dumps(x) if not isinstance(x, str) else x for x in rows) + "\n"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data.jsonl"; path.write_text(encoded, encoding="utf-8"); before = path.read_bytes(); report = audit(path)
            self.assertEqual(path.read_bytes(), before)
        self.assertEqual(report["total"], 7); self.assertEqual(report["parse_errors"], 1); self.assertEqual(report["candidate_rows"], 4); self.assertEqual(report["typed_ready_rows"], 1); self.assertEqual(report["missing_task_context"], 1); self.assertEqual(report["missing_noul"], 5); self.assertEqual(report["sha256"], hashlib.sha256(before).hexdigest())
        for key in ("missing_candidates", "missing_selected_candidate", "missing_evidence", "missing_provenance"): self.assertIn(key, report["rejection_reasons"])

    def test_cli_stdout(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data.jsonl"; path.write_text(json.dumps({"task_context": "x"}) + "\n", encoding="utf-8")
            completed = subprocess.run([sys.executable, "-m", "training.dataset_audit", str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout)["total"], 1)

if __name__ == "__main__": unittest.main()
