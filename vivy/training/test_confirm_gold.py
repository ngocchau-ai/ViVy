import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from training.confirm_gold import confirm


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _queue_row(rid: str, selected: str, candidates: list[dict]) -> dict:
    return {
        "decision_type": "choice",
        "context_state": "Task Goal: X\nObservation Context: Y",
        "candidates": candidates,
        "selected_candidate": selected,
        "confidence": 0.0,
        "evidence_required": ["- capture_id_matched: True"],
        "provenance": {
            "source": "cua_bounded_trajectory",
            "producer": "legacy_to_typed",
            "receipt_id": rid,
            "timestamp": "extracted-not-observed",
        },
        "label_quality": "unverified",
        "split": "train",
        "review": {
            "gold_selected_candidate": None,
            "gold_outcome": None,
            "reviewer": None,
            "reviewed_at": None,
            "independent_receipt_id": None,
            "status": "PENDING",
        },
    }


def _triage_row(row_index: int, rid: str, proposed: str | None, category: str, tier: str, disagrees: bool = False) -> dict:
    return {
        "row_index": row_index,
        "legacy_receipt_id": rid,
        "proposed_selected_candidate": proposed,
        "category": category,
        "tier": tier,
        "disagrees_with_legacy": disagrees,
        "proposal_receipt_id": f"oracle-{'x' * 16}",
        "rule_version": "gold_rules_v1",
    }


CANDS = [
    {"id": "cand_a", "description": "- [cand_a]: Do A (action: click)"},
    {"id": "cand_b", "description": "- [cand_b]: Do B (action: click)"},
]


class ConfirmBulkAcceptTests(unittest.TestCase):
    def test_bulk_accept_stamps_all_matching_rows(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [
                _queue_row("legacy-1", "cand_a", CANDS),
                _queue_row("legacy-2", "cand_a", CANDS),
                _queue_row("legacy-3", "cand_b", CANDS),
            ]
            triage_rows = [
                _triage_row(0, "legacy-1", "cand_a", "A", "A_strong"),
                _triage_row(1, "legacy-2", "cand_a", "A", "A_strong"),
                _triage_row(2, "legacy-3", "cand_b", "A", "A_strong"),
            ]
            manifest = [
                {"action": "bulk_accept", "where": {"category": "A"}, "reviewer": "user1", "reviewed_at": "2026-09-23T10:00:00Z"},
            ]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            counts = confirm(t, q, m, o)
            out_rows = [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(counts["reviewed"], 3)
            self.assertEqual(counts["pending"], 0)
            receipt_ids = {r["review"]["independent_receipt_id"] for r in out_rows}
            self.assertEqual(len(receipt_ids), 3)  # each row unique
            for r in out_rows:
                self.assertEqual(r["review"]["status"], "REVIEWED")
                self.assertEqual(r["review"]["reviewer"], "user1")
                self.assertEqual(r["review"]["reviewed_at"], "2026-09-23T10:00:00Z")

    def test_bulk_accept_with_agrees_with_legacy_field(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [_queue_row("legacy-1", "cand_a", CANDS)]
            triage_rows = [
                {**_triage_row(0, "legacy-1", "cand_a", "A", "A_strong"), "agrees_with_legacy": True},
            ]
            manifest = [
                {"action": "bulk_accept", "where": {"category": "A", "agrees_with_legacy": True}, "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"},
            ]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            counts = confirm(t, q, m, o)
            self.assertEqual(counts["reviewed"], 1)

    def test_per_row_entry_overrides_bulk(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [_queue_row("legacy-1", "cand_a", CANDS), _queue_row("legacy-2", "cand_a", CANDS)]
            triage_rows = [
                _triage_row(0, "legacy-1", "cand_a", "A", "A_strong"),
                _triage_row(1, "legacy-2", "cand_a", "A", "A_strong"),
            ]
            manifest = [
                {"action": "bulk_accept", "where": {"category": "A"}, "reviewer": "bulk_user", "reviewed_at": "2026-09-23T10:00:00Z"},
                {"row": 1, "action": "override", "override_candidate": "cand_b", "reviewer": "per_row", "reviewed_at": "2026-09-23T11:00:00Z"},
            ]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            confirm(t, q, m, o)
            out_rows = [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(out_rows[0]["review"]["reviewer"], "bulk_user")
            self.assertEqual(out_rows[1]["review"]["reviewer"], "per_row")
            self.assertEqual(out_rows[1]["review"]["gold_selected_candidate"], "cand_b")


class ConfirmPerRowTests(unittest.TestCase):
    def _run(self, manifest):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [_queue_row("legacy-1", "cand_a", CANDS)]
            triage_rows = [_triage_row(0, "legacy-1", "cand_a", "A", "A_strong")]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            counts = confirm(t, q, m, o)
            out_rows = [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]
            return counts, out_rows

    def test_accept_sets_proposed_candidate(self):
        counts, rows = self._run([{"row": 0, "action": "accept", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}])
        self.assertEqual(rows[0]["review"]["gold_selected_candidate"], "cand_a")
        self.assertEqual(rows[0]["review"]["status"], "REVIEWED")

    def test_override_sets_override_candidate(self):
        counts, rows = self._run([{"row": 0, "action": "override", "override_candidate": "cand_b", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}])
        self.assertEqual(rows[0]["review"]["gold_selected_candidate"], "cand_b")

    def test_skip_leaves_pending(self):
        counts, rows = self._run([{"row": 0, "action": "skip", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}])
        self.assertEqual(rows[0]["review"]["status"], "PENDING")
        self.assertEqual(counts["pending"], 1)

    def test_gold_outcome_defaults_unknown(self):
        counts, rows = self._run([{"row": 0, "action": "accept", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}])
        self.assertEqual(rows[0]["review"]["gold_outcome"], "unknown")

    def test_accept_rejected_for_category_c(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [_queue_row("legacy-1", "cand_a", CANDS)]
            triage_rows = [_triage_row(0, "legacy-1", None, "C", "C")]
            manifest = [{"row": 0, "action": "accept", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            with self.assertRaises(ValueError):
                confirm(t, q, m, o)

    def test_queue_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [_queue_row("legacy-1", "cand_a", CANDS)]
            triage_rows = [_triage_row(0, "legacy-1", "cand_a", "A", "A_strong")]
            manifest = [{"row": 0, "action": "accept", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            before = hashlib.sha256(q.read_bytes()).hexdigest()
            confirm(t, q, m, o)
            after = hashlib.sha256(q.read_bytes()).hexdigest()
            self.assertEqual(before, after)


class ConfirmOracleAuthorityTests(unittest.TestCase):
    def _setup(self):
        queue_rows = [
            _queue_row("legacy-1", "cand_a", CANDS),
            _queue_row("legacy-2", "cand_a", CANDS),
        ]
        triage_rows = [
            _triage_row(0, "legacy-1", "cand_a", "A", "A_strong"),
            _triage_row(1, "legacy-2", "cand_b", "A", "A_strong", disagrees=True),
        ]
        return queue_rows, triage_rows

    def test_variant1_never_auto_reviews(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows, triage_rows = self._setup()
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, [])  # no manifest entries
            counts = confirm(t, q, m, o, oracle_authority="propose-only")
            out_rows = [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(counts["reviewed"], 0)
            for r in out_rows:
                self.assertEqual(r["review"]["status"], "PENDING")

    def test_variant2_auto_reviews_agreeing_rows_only(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows, triage_rows = self._setup()
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, [])
            counts = confirm(t, q, m, o, oracle_authority="auto-reviewed")
            out_rows = [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(counts["reviewed"], 1)  # only the agreeing row
            self.assertEqual(out_rows[0]["review"]["status"], "REVIEWED")
            self.assertEqual(out_rows[1]["review"]["status"], "PENDING")  # disagreement stays PENDING
            self.assertIn("oracle_gold_rules_v1", out_rows[0]["review"]["reviewer"])


class ConfirmEndToEndTests(unittest.TestCase):
    def test_promote_rejects_pending_rows(self):
        from training.promote_reviewed import promote

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            queue_rows = [
                _queue_row("legacy-1", "cand_a", CANDS),
                _queue_row("legacy-2", "cand_a", CANDS),
            ]
            triage_rows = [
                _triage_row(0, "legacy-1", "cand_a", "A", "A_strong"),
                _triage_row(1, "legacy-2", "cand_a", "A", "A_strong"),
            ]
            manifest = [{"row": 0, "action": "accept", "reviewer": "u", "reviewed_at": "2026-09-23T10:00:00Z"}]
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            gold = d / "gold.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            confirm(t, q, m, o)
            counts = promote(o, gold)
            self.assertEqual(counts["promoted"], 1)
            self.assertEqual(counts["pending"], 1)


if __name__ == "__main__":
    unittest.main()
