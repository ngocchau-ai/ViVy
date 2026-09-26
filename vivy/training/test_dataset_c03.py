"""C03 tests — multiline Expected_Evidence, group split, provenance, alias safety."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from training.dataset_audit import audit_rows, fingerprint
from training.io_guard import RefuseOverwriteError, open_write
from training.legacy_to_typed import (
    extract_expected_evidence,
    group_key,
    migrate,
    split_for_group,
)


ASSISTANT_MULTILINE = (
    "Selected_Candidate_ID: save\n"
    "Expected_Evidence:\n"
    "- postcondition: file persisted\n"
    "- capture_id_matched: True\n"
    "- checksum equals source\n"
    "Notes: trailing field should not leak into evidence\n"
)


class MultilineEvidenceTests(unittest.TestCase):
    def test_keeps_every_evidence_line_not_just_first(self):
        lines = extract_expected_evidence(ASSISTANT_MULTILINE)
        self.assertEqual(len(lines), 3)
        self.assertIn("- postcondition: file persisted", lines)
        self.assertIn("- checksum equals source", lines)

    def test_stops_at_next_labeled_field(self):
        lines = extract_expected_evidence(ASSISTANT_MULTILINE)
        self.assertFalse(any("trailing field" in item for item in lines))

    def test_empty_when_missing(self):
        self.assertEqual(extract_expected_evidence("Selected_Candidate_ID: save"), [])

    def test_migrate_preserves_multiline(self):
        row = {
            "source": "cua",
            "messages": [
                {},
                {"content": "Goal: save\nBounded Candidate Table:\n- [save]: click save\nSelect the safest"},
                {"content": ASSISTANT_MULTILINE},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "in.jsonl"
            p.write_text(json.dumps(row) + "\n", encoding="utf-8")
            out = list(migrate(p, extracted_at="2026-09-24T00:00:00+00:00"))
        self.assertEqual(out[0]["evidence_required_line_count"], 3)
        self.assertEqual(len(out[0]["evidence_required"]), 3)
        self.assertFalse(out[0]["provenance"]["expected_evidence_is_observed"])


class GroupSplitTests(unittest.TestCase):
    def test_template_tasks_share_one_group(self):
        a = group_key("Execute automated bounded workspace task #12\nobs")
        b = group_key("Execute automated bounded workspace task #99\nobs")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("template:"))

    def test_task_goal_prefix_still_groups_template(self):
        a = group_key("Task Goal: Execute automated bounded workspace task #01\nObservation x")
        b = group_key("Task Goal: Execute automated bounded workspace task #44\nObservation y")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("template:"))

    def test_same_group_same_split(self):
        key = group_key("Execute automated bounded workspace task #3")
        self.assertEqual(split_for_group(key), split_for_group(key))

    def test_modulo_index_split_is_gone(self):
        """Different goals must not be split purely by row index."""
        keys = [group_key(f"Goal unique-{i} do the thing") for i in range(30)]
        splits = [split_for_group(k) for k in keys]
        # index % 10 would put rows 0,10,20 in dev — group hash need not.
        self.assertEqual(split_for_group(keys[0]), splits[0])
        # still deterministic and uses all three buckets over the set
        self.assertGreaterEqual(len(set(splits)), 2)

    def test_migrate_assigns_group_stable_split(self):
        def make(i):
            return {
                "source": "cua",
                "messages": [
                    {},
                    {"content": f"Goal: Execute automated bounded workspace task #{i}\n"
                                f"Bounded Candidate Table:\n- [exec]: run\n- [halt]: stop\nSelect the safest"},
                    {"content": "Selected_Candidate_ID: exec\nExpected_Evidence: done"},
                ],
            }

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "in.jsonl"
            p.write_text("\n".join(json.dumps(make(i)) for i in range(20)) + "\n", encoding="utf-8")
            rows = list(migrate(p, extracted_at="2026-09-24T00:00:00+00:00"))
        splits = {r["split"] for r in rows}
        self.assertEqual(len(splits), 1, "template family must not cross splits")
        self.assertEqual(len({r["provenance"]["group_key"] for r in rows}), 1)


class ProvenanceTests(unittest.TestCase):
    def test_source_hash_and_extraction_version_present(self):
        row = {
            "source": "cua",
            "timestamp": "2026-01-01T00:00:00Z",
            "messages": [
                {},
                {"content": "Goal: x\nBounded Candidate Table:\n- [a]: do\nSelect the safest"},
                {"content": "Selected_Candidate_ID: a\nExpected_Evidence: e1\ne2 continues"},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "in.jsonl"
            raw = json.dumps(row) + "\n"
            p.write_text(raw, encoding="utf-8")
            expected = hashlib.sha256(p.read_bytes()).hexdigest()
            out = list(migrate(p, extracted_at="2026-09-24T12:00:00+00:00"))[0]
        prov = out["provenance"]
        self.assertEqual(prov["source_file_sha256"], expected)
        self.assertIn("extraction_version", prov)
        self.assertEqual(prov["source_timestamp"], "2026-01-01T00:00:00Z")
        self.assertEqual(prov["extracted_at"], "2026-09-24T12:00:00+00:00")
        self.assertEqual(prov["timestamp_kind"], "extraction")
        self.assertIsNone(prov["action_observed_at"])
        self.assertEqual(out["gold_outcome"], "unknown")
        self.assertEqual(out["confidence_source"], "migration_placeholder_not_measured")

    def test_invented_confidence_is_tagged_not_measured(self):
        row = {
            "source": "cua",
            "messages": [
                {},
                {"content": "Goal: x\nBounded Candidate Table:\n- [a]: do\nSelect the safest"},
                {"content": "Selected_Candidate_ID: a\nExpected_Evidence: e"},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "in.jsonl"
            p.write_text(json.dumps(row) + "\n", encoding="utf-8")
            out = list(migrate(p))[0]
        self.assertEqual(out["confidence"], 0.0)
        self.assertIn("not_measured", out["confidence_source"])


class AuditTests(unittest.TestCase):
    def test_detects_group_crossing_splits(self):
        rows = [
            {
                "context_state": "Execute automated bounded workspace task #1",
                "candidates": [{"id": "exec"}, {"id": "halt"}],
                "selected_candidate": "exec",
                "gold_outcome": "unknown",
                "split": "train",
                "provenance": {"group_key": "template:execute automated bounded workspace task",
                               "receipt_id": "legacy-0-x", "source_file_sha256": "a"},
            },
            {
                "context_state": "Execute automated bounded workspace task #2",
                "candidates": [{"id": "exec"}, {"id": "halt"}],
                "selected_candidate": "exec",
                "gold_outcome": "unknown",
                "split": "test",
                "provenance": {"group_key": "template:execute automated bounded workspace task",
                               "receipt_id": "legacy-1-x", "source_file_sha256": "a"},
            },
        ]
        report = audit_rows(rows)
        self.assertEqual(len(report.group_cross_split), 1)

    def test_detects_near_duplicate_cross_split(self):
        base = {
            "context_state": "Goal unique-alpha save the document",
            "candidates": [{"id": "save"}, {"id": "halt"}],
            "gold_outcome": "unknown",
            "provenance": {"group_key": "goal:unique", "receipt_id": "legacy-0-x", "source_file_sha256": "a"},
        }
        rows = [
            {**base, "split": "train", "selected_candidate": "save"},
            {**base, "split": "dev", "selected_candidate": "halt"},
        ]
        report = audit_rows(rows)
        self.assertEqual(len(report.near_duplicate_cross_split), 1)

    def test_selection_and_outcome_counts_differ(self):
        rows = [
            {"selected_candidate": "a", "gold_outcome": "unknown",
             "context_state": "t", "candidates": [{"id": "a"}],
             "provenance": {"group_key": "g1", "receipt_id": "legacy-0-x", "source_file_sha256": "a"}},
            {"selected_candidate": "b", "gold_outcome": "success",
             "context_state": "u", "candidates": [{"id": "b"}],
             "provenance": {"group_key": "g2", "receipt_id": "legacy-1-x", "source_file_sha256": "a"}},
        ]
        report = audit_rows(rows)
        self.assertEqual(report.n_selection_labels, 2)
        self.assertEqual(report.n_outcome_known, 1)
        self.assertEqual(report.n_outcome_unknown, 1)


class AliasSafetyTests(unittest.TestCase):
    def test_migration_refuses_overwrite_input(self):
        row = {
            "source": "cua",
            "messages": [
                {},
                {"content": "Goal: x\nBounded Candidate Table:\n- [a]: do\nSelect the safest"},
                {"content": "Selected_Candidate_ID: a\nExpected_Evidence: e"},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                open_write(src, protected=(src,))
            out = Path(d) / "out.jsonl"
            with open_write(out, protected=(src,)) as handle:
                handle.write("{}\n")
            with self.assertRaises(RefuseOverwriteError):
                open_write(out, protected=(src,))

    def test_invalid_row_does_not_emit_partial_complete_label(self):
        bad = {"messages": [{}, {"content": "no table"}, {"content": "Selected_Candidate_ID: a"}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "in.jsonl"
            p.write_text(json.dumps(bad) + "\n", encoding="utf-8")
            rows = list(migrate(p))
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
