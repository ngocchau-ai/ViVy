"""WP-6 / T9 — no fabricated labels.  [NEW 29/09/2026 · O-10]

Nghiệm thu WP-6 (T9):
    0 nhãn bịa; 0 rò rỉ theo nhóm; mọi mẫu có ``evidence_receipt_id`` hoặc bị loại.

This file is the enforcement, not the documentation.  ``training/dataset_audit.py``
owns ``FABRICATED_EVIDENCE_LABELS``; this file fails the build when one of those
strings comes back into live extractor code, or shows up in an SFT set that
anything would train on.

Two halves, and both matter:

* **Source tripwire** — the extractor must not emit the strings.  Comments and
  docstrings are history ("cô lập, không xóa") and are skipped; a string that
  lands in a sample is code and is scanned.
* **Dataset sweep** — every SFT set on disk is classified.  A clean set must
  have no fabricated labels and every row receipt-backed.  A dirty set must be
  quarantined *and* refused by ``training.smoke_train``.  Neither alone is
  enough: quarantine without refusal is a comment, and refusal without a named
  quarantine is invisible.

INV-01: every patch carries a test.  If one of these fails, fix the code, not
this file (plan hard rule #4).  The assertions below are the spec.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Mapping

TRAINING_DIR = Path(__file__).resolve().parent
VIVY_ROOT = TRAINING_DIR.parent
REPO_ROOT = VIVY_ROOT.parent

if str(VIVY_ROOT) not in sys.path:
    sys.path.insert(0, str(VIVY_ROOT))

from training.dataset_audit import (  # noqa: E402
    FABRICATED_EVIDENCE_LABELS,
    UNVERIFIED_EVIDENCE,
    assert_exportable,
    audit_rows,
    detect_schema,
    evidence_receipt_of,
    find_fabricated_labels,
)
from training.dataset_extractor import DatasetExtractor, TrainingSample  # noqa: E402
from training.decision_contract import (  # noqa: E402
    SCHEMA_CHATML,
    SCHEMA_TYPED,
    SchemaMismatchError,
    require_typed,
    validate_decision_input,
)


# ---------------------------------------------------------------------------
# Source scanning — a claim is live only in code
# ---------------------------------------------------------------------------


def live_code_lines(text: str) -> str:
    """Return only Python code lines — ``#`` comments and docstrings removed.

    WP-6 quotes the old fabricated labels in a trailing ``[ISOLATED]`` comment
    block, per "cô lập, không xóa".  That block is history, not behaviour.
    """
    out: list[str] = []
    in_triple: str | None = None
    for line in text.splitlines():
        if in_triple:
            if in_triple in line:
                in_triple = None
            continue
        for q in ('"""', "'''"):
            if q in line:
                before, _, after = line.partition(q)
                if q in after:
                    line = before + after.partition(q)[2]
                    break
                in_triple = q
                line = before
                break
        if line.lstrip().startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


EXTRACTOR_SRC = (TRAINING_DIR / "dataset_extractor.py").read_text(encoding="utf-8")
EXTRACTOR_LIVE = live_code_lines(EXTRACTOR_SRC)


# ---------------------------------------------------------------------------
# Dataset discovery — what is an SFT set, and what is quarantined
# ---------------------------------------------------------------------------


def is_sft_row(row: Mapping[str, Any]) -> bool:
    """A row that something would actually train on.

    Receipt logs (``evidence/shadow_receipts.jsonl``) and audit fixtures are not
    SFT rows and must not be swept as if they were — that would be a fake pass
    and a fake fail at once.
    """
    if "messages" in row or "conversations" in row:
        return True
    return "context_state" in row and "candidates" in row


def load_sft_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if is_sft_row(row):
            rows.append(row)
    return rows


def sft_dataset_files() -> list[Path]:
    """Every on-disk file that holds at least one SFT row."""
    found: list[Path] = []
    for root in (TRAINING_DIR, VIVY_ROOT / "evidence"):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.jsonl")):
            try:
                if load_sft_rows(path):
                    found.append(path)
            except json.JSONDecodeError:
                continue
    return found


#: Sets that are known dirty and must stay out of training.  Keep this list
#: short and honest: anything here has to also be refused by smoke_train.
QUARANTINED_SFT_SETS = frozenset({
    "vivy_train_dataset.jsonl",
})


# ---------------------------------------------------------------------------
# 1. The extractor must not emit fabricated labels
# ---------------------------------------------------------------------------


class ExtractorSourceTests(unittest.TestCase):
    def test_no_fabricated_label_in_live_extractor_code(self):
        for label in FABRICATED_EVIDENCE_LABELS:
            self.assertNotIn(
                label,
                EXTRACTOR_LIVE,
                f"{label!r} is LIVE CODE again in dataset_extractor.py. It was "
                f"removed in WP-6 because nothing ever measured it. Fix the "
                f"extractor, not this test. See training/dataset_audit.py.",
            )

    def test_no_unconditional_capture_check_assertion_in_live_code(self):
        self.assertNotIn(
            "capture_id_matched: True",
            EXTRACTOR_LIVE,
            "capture_id_matched must come from the record via _check_line(), "
            "never as a literal that claims the check passed",
        )

    def test_isolated_block_preserves_the_history(self):
        """Cô lập, không xóa — the old strings must still be readable."""
        for label in FABRICATED_EVIDENCE_LABELS:
            self.assertIn(label, EXTRACTOR_SRC, f"{label!r} was deleted outright")
        self.assertIn("[ISOLATED 29/09/2026", EXTRACTOR_SRC)

    def test_unverified_is_the_only_default_evidence_label(self):
        self.assertIn(f'UNVERIFIED_EVIDENCE = "{UNVERIFIED_EVIDENCE}"',
                      (TRAINING_DIR / "dataset_audit.py").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 2. Dataset sweep — clean sets clean, dirty sets quarantined AND refused
# ---------------------------------------------------------------------------


class DatasetSweepTests(unittest.TestCase):
    def test_every_sft_set_is_classified(self):
        files = sft_dataset_files()
        self.assertTrue(files, "expected at least one SFT set on disk to sweep")

    def test_no_unquarantined_sft_set_carries_a_fabricated_label(self):
        dirty = []
        for path in sft_dataset_files():
            if path.name in QUARANTINED_SFT_SETS:
                continue
            for index, row in enumerate(load_sft_rows(path)):
                if detect_schema(row) == SCHEMA_CHATML:
                    haystack = "\n".join(
                        str(m.get("content", m.get("value", "")))
                        for m in (row.get("messages") or row.get("conversations") or [])
                        if isinstance(m, Mapping) and (m.get("role") or m.get("from")) in ("assistant", "gpt")
                    )
                else:
                    haystack = "\n".join(str(e) for e in (row.get("evidence_required") or []))
                found = find_fabricated_labels(haystack)
                if found:
                    dirty.append(f"{path.name}:row{index}:{found}")
        self.assertEqual(dirty, [], f"fabricated labels in a live SFT set: {dirty}")

    def test_quarantined_set_is_still_refused_by_smoke_train(self):
        from training.smoke_train import SmokeTrainBlocked, run_smoke

        for name in QUARANTINED_SFT_SETS:
            path = TRAINING_DIR / name
            self.assertTrue(path.exists(), f"quarantine entry points at nothing: {name}")
            with self.assertRaises(SmokeTrainBlocked, msg=f"{name} is no longer refused"):
                run_smoke(path, steps=1, root=VIVY_ROOT, require_preflight=False)

    def test_quarantine_is_not_a_comment_only_measure(self):
        """A dirty set that smoke_train would accept is a hole in the gate."""
        from training.smoke_train import LEGACY_DATASET_NAMES, SmokeTrainBlocked

        for path in sft_dataset_files():
            rows = load_sft_rows(path)
            dirty = any(
                find_fabricated_labels(
                    "\n".join(str(e) for e in (r.get("evidence_required") or []))
                    + "\n"
                    + json.dumps(r, ensure_ascii=False)
                )
                for r in rows
            )
            if not dirty:
                continue
            self.assertIn(
                path.name,
                LEGACY_DATASET_NAMES | QUARANTINED_SFT_SETS,
                f"{path.name} carries fabricated labels but nothing quarantines it",
            )
            with self.assertRaises(SmokeTrainBlocked):
                from training.smoke_train import run_smoke

                run_smoke(path, steps=1, root=VIVY_ROOT, require_preflight=False)

    def test_gold_train_is_clean_and_receipt_backed(self):
        gold = VIVY_ROOT / "evidence" / "gold_train.jsonl"
        self.assertTrue(gold.exists(), "evidence/gold_train.jsonl is the only set smoke may use")
        rows = load_sft_rows(gold)
        self.assertTrue(rows)
        for index, row in enumerate(rows):
            haystack = "\n".join(str(e) for e in (row.get("evidence_required") or []))
            self.assertEqual(
                find_fabricated_labels(haystack), [],
                f"gold_train row {index} asserts a fabricated label",
            )
            self.assertIsNotNone(
                evidence_receipt_of(row),
                f"gold_train row {index} has no backing receipt",
            )

    def test_no_group_crosses_splits_in_gold_train(self):
        """T9 also requires 0 rò rỉ theo nhóm."""
        rows = load_sft_rows(VIVY_ROOT / "evidence" / "gold_train.jsonl")
        report = audit_rows(rows)
        self.assertEqual(report.group_cross_split, [], "a group spans more than one split")


# ---------------------------------------------------------------------------
# 3. The audit gate
# ---------------------------------------------------------------------------


class AuditGateTests(unittest.TestCase):
    def test_fabricated_label_in_chatml_assistant_is_flagged(self):
        row = {
            "messages": [
                {"role": "system", "content": "s"},
                {"role": "user", "content": "u"},
                {"role": "assistant",
                 "content": "<vivy_thought>\nExpected_Evidence: COGNITIVE_CONSENSUS_VERIFIED\n</vivy_thought>"},
            ],
            "source": "x",
            "reward": 1.0,
            "evidence_receipt_id": "oracle-abc12345",
        }
        report = audit_rows([row])
        self.assertEqual(report.n_schema_chatml, 1)
        self.assertTrue(report.has_fabricated_labels)
        self.assertFalse(report.exportable)
        self.assertIn("COGNITIVE_CONSENSUS_VERIFIED", report.fabricated_evidence_rows[0])

    def test_fabricated_label_in_typed_evidence_is_flagged(self):
        row = {
            "context_state": "t",
            "candidates": [{"id": "a"}],
            "evidence_required": ["- capture_ok", "AST_VALID_AND_TEST_PASS"],
            "provenance": {"receipt_id": "oracle-abc12345"},
        }
        report = audit_rows([row])
        self.assertEqual(report.n_schema_typed, 1)
        self.assertTrue(report.has_fabricated_labels)

    def test_assert_exportable_rejects_fabricated_labels(self):
        row = {
            "messages": [
                {"role": "system", "content": "s"},
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "Expected_Evidence: MULTIMODAL_GROUNDING_VERIFIED"},
            ],
            "evidence_receipt_id": "oracle-abc12345",
        }
        with self.assertRaises(Exception) as ctx:
            assert_exportable([row])
        self.assertIn("fabricated", str(ctx.exception).lower())

    def test_assert_exportable_rejects_missing_receipt(self):
        row = {
            "messages": [
                {"role": "system", "content": "s"},
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "Expected_Evidence: UNVERIFIED"},
            ],
        }
        with self.assertRaises(Exception) as ctx:
            assert_exportable([row])
        self.assertIn("evidence_receipt_id", str(ctx.exception))

    def test_assert_exportable_accepts_clean_receipt_backed_rows(self):
        row = {
            "messages": [
                {"role": "system", "content": "s"},
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "Expected_Evidence: UNVERIFIED"},
            ],
            "evidence_receipt_id": "oracle-abc12345",
            "reward": 1.0,
        }
        report = assert_exportable([row])
        self.assertTrue(report.exportable)

    def test_migration_legacy_id_does_not_satisfy_the_receipt_rule(self):
        """Every migrated row has a legacy-* id; counting it would gut T9."""
        row = {
            "context_state": "t",
            "candidates": [{"id": "a"}],
            "provenance": {"receipt_id": "legacy-451-8d1e68421572"},
        }
        self.assertIsNone(evidence_receipt_of(row))
        report = audit_rows([row])
        self.assertEqual(report.n_missing_evidence_receipt, 1)
        self.assertFalse(report.exportable)

    def test_review_receipt_does_satisfy_the_rule(self):
        row = {
            "context_state": "t",
            "candidates": [{"id": "a"}],
            "provenance": {
                "receipt_id": "legacy-451-8d1e68421572",
                "review_receipt_id": "human-accept-4b654781243f6b08",
            },
        }
        self.assertEqual(evidence_receipt_of(row), "human-accept-4b654781243f6b08")


# ---------------------------------------------------------------------------
# 4. Extractor behaviour
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")


class ExtractorBehaviourTests(unittest.TestCase):
    def test_activity_log_without_receipt_yields_nothing(self):
        """[REPLACED 29/09/2026] was: reward 1.0 and a fabricated label."""
        import tempfile

        records = [
            {"event": "inference_start", "session_id": "s1", "input_type": "str"},
            {"event": "inference_end", "session_id": "s1", "status": "OBSERVED",
             "decision": "EXECUTE_DIRECTLY", "rounds": 1},
        ]
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "activity.jsonl"
            _write_jsonl(log, records)
            samples = DatasetExtractor.extract_from_activity_log(str(log))
        self.assertEqual(samples, [], "no receipt means no sample")

    def test_activity_log_with_receipt_copies_the_records_evidence(self):
        import tempfile

        records = [
            {"event": "inference_start", "session_id": "s1", "input_type": "str"},
            {"event": "inference_end", "session_id": "s1", "status": "OBSERVED",
             "decision": "EXECUTE_DIRECTLY", "rounds": 2,
             "evidence_receipt_id": "oracle-deadbeefcafe",
             "expected_evidence": "pytest passed (42 tests)"},
        ]
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "activity.jsonl"
            _write_jsonl(log, records)
            samples = DatasetExtractor.extract_from_activity_log(str(log))
        self.assertEqual(len(samples), 1)
        sample = samples[0]
        self.assertEqual(sample.evidence_receipt_id, "oracle-deadbeefcafe")
        self.assertIn("pytest passed (42 tests)", sample.assistant_response)
        self.assertNotIn("AST_VALID_AND_TEST_PASS", sample.assistant_response)
        self.assertEqual(sample.reward_score, 1.0)

    def test_activity_log_with_no_evidence_field_says_unverified(self):
        import tempfile

        records = [
            {"event": "inference_start", "session_id": "s1", "input_type": "str"},
            {"event": "inference_end", "session_id": "s1", "status": "OBSERVED",
             "decision": "HALT", "rounds": 1,
             "evidence_receipt_id": "oracle-deadbeefcafe",
             "expected_evidence": True},
        ]
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "activity.jsonl"
            _write_jsonl(log, records)
            samples = DatasetExtractor.extract_from_activity_log(str(log))
        self.assertEqual(len(samples), 1)
        self.assertIn(f"Expected_Evidence: {UNVERIFIED_EVIDENCE}", samples[0].assistant_response)

    def test_record_supplying_a_fabricated_label_is_downgraded_to_unverified(self):
        """A source record cannot smuggle the constant back in either."""
        import tempfile

        records = [
            {"event": "inference_start", "session_id": "s1", "input_type": "str"},
            {"event": "inference_end", "session_id": "s1", "status": "OBSERVED",
             "decision": "EXECUTE_DIRECTLY", "rounds": 1,
             "evidence_receipt_id": "oracle-deadbeefcafe",
             "expected_evidence": "AST_VALID_AND_TEST_PASS"},
        ]
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "activity.jsonl"
            _write_jsonl(log, records)
            samples = DatasetExtractor.extract_from_activity_log(str(log))
        self.assertEqual(len(samples), 1)
        self.assertNotIn("AST_VALID_AND_TEST_PASS", samples[0].assistant_response)
        self.assertIn(UNVERIFIED_EVIDENCE, samples[0].assistant_response)

    def test_llava_traces_never_claim_multimodal_grounding(self):
        samples = DatasetExtractor.ingest_llava_traces([
            {"instruction": "look", "response": "ok", "evidence_receipt_id": "oracle-abc12345"},
            {"instruction": "look2", "response": "ok2"},   # no receipt -> dropped
        ])
        self.assertEqual(len(samples), 1)
        self.assertNotIn("MULTIMODAL_GROUNDING_VERIFIED", samples[0].assistant_response)
        self.assertIn(UNVERIFIED_EVIDENCE, samples[0].assistant_response)
        self.assertEqual(samples[0].evidence_receipt_id, "oracle-abc12345")

    def test_2brain_traces_never_claim_cognitive_consensus(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "2brain.jsonl"
            _write_jsonl(src, [
                {"problem": "p", "decision": "d", "confidence": 0.9,
                 "evidence_receipt_id": "oracle-abc12345"},
                {"problem": "p2", "decision": "d2", "confidence": 0.9},  # no receipt
            ])
            samples = DatasetExtractor.ingest_2brain_reasoning(str(src))
        self.assertEqual(len(samples), 1)
        self.assertNotIn("COGNITIVE_CONSENSUS_VERIFIED", samples[0].assistant_response)
        self.assertIn(UNVERIFIED_EVIDENCE, samples[0].assistant_response)

    def test_cua_does_not_assert_a_capture_check_it_never_ran(self):
        samples = DatasetExtractor.ingest_cua_trajectories([
            {
                "goal": "click", "screen_context": "s",
                "candidates": [{"id": "cand_01", "description": "d", "action": "click"}],
                "selected_id": "cand_01",
                "postcondition": "done",
                "postcondition_passed": True,
                "reward": 0.95,
                "evidence_receipt_id": "oracle-abc12345",
            },
            {
                "goal": "click2", "screen_context": "s",
                "candidates": [{"id": "cand_01", "description": "d", "action": "click"}],
                "selected_id": "cand_01",
                "reward": 0.95,   # no receipt -> dropped
            },
        ])
        self.assertEqual(len(samples), 1)
        self.assertIn("capture_id_matched: NOT_CHECKED", samples[0].assistant_response)
        self.assertNotIn("capture_id_matched: True", samples[0].assistant_response)

    def test_cua_reports_a_real_capture_result_from_the_record(self):
        samples = DatasetExtractor.ingest_cua_trajectories([
            {
                "goal": "click", "screen_context": "s",
                "candidates": [{"id": "cand_01", "description": "d", "action": "click"}],
                "selected_id": "cand_01",
                "postcondition": "done",
                "reward": 0.95,
                "capture_id_matched": False,
                "evidence_receipt_id": "oracle-abc12345",
            },
        ])
        self.assertEqual(len(samples), 1)
        self.assertIn("capture_id_matched: False", samples[0].assistant_response)

    def test_verdict_without_a_gate_says_unverified_not_deterministic_pass(self):
        samples = DatasetExtractor.ingest_verdict_pairs([
            {"context_state": "s", "proposed_action": "a", "verdict": "PASS",
             "score": 0.9, "evidence_receipt_id": "oracle-abc12345"},
        ])
        self.assertEqual(len(samples), 1)
        self.assertNotIn("DETERMINISTIC_PASS", samples[0].assistant_response)
        self.assertIn(UNVERIFIED_EVIDENCE, samples[0].assistant_response)

    def test_verdict_copies_a_real_gate_from_the_record(self):
        samples = DatasetExtractor.ingest_verdict_pairs([
            {"context_state": "s", "proposed_action": "a", "verdict": "PASS",
             "score": 0.9, "acceptance_gate": "MQL5_COMPILER_PASS",
             "evidence_receipt_id": "oracle-abc12345"},
        ])
        self.assertEqual(len(samples), 1)
        self.assertIn("MQL5_COMPILER_PASS", samples[0].assistant_response)

    def test_export_refuses_a_hand_built_sample_without_a_receipt(self):
        import tempfile

        sample = TrainingSample(
            system_prompt="s", user_prompt="u", assistant_response="a",
        )
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Exception):
                DatasetExtractor.export_jsonl([sample], str(Path(d) / "out.jsonl"))

    def test_export_accepts_a_receipt_backed_sample(self):
        import tempfile

        sample = TrainingSample(
            system_prompt="s", user_prompt="u",
            assistant_response=f"Expected_Evidence: {UNVERIFIED_EVIDENCE}",
            evidence_receipt_id="oracle-abc12345",
        )
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.jsonl"
            count = DatasetExtractor.export_jsonl([sample], str(out))
            rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(count, 1)
        self.assertEqual(rows[0]["evidence_receipt_id"], "oracle-abc12345")

    def test_is_exportable_names_the_reason(self):
        ok, reason = DatasetExtractor.is_exportable(
            TrainingSample(system_prompt="s", user_prompt="u", assistant_response="a")
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_evidence_receipt_id")


# ---------------------------------------------------------------------------
# 5. F-H02 / F-H04 — the oracle is not a human, an unreferenced limit is not a pass
# ---------------------------------------------------------------------------


class OracleStampTests(unittest.TestCase):
    def _run_confirm(self, d: Path, oracle_authority: str) -> list[dict[str, Any]]:
        from training.confirm_gold import confirm

        cands = [{"id": "cand_a", "description": "a"}, {"id": "cand_b", "description": "b"}]
        queue_rows = [{
            "candidates": cands,
            "review": {"status": "PENDING"},
            "provenance": {"receipt_id": "legacy-0-x"},
        }]
        triage_rows = [{
            "proposed_selected_candidate": "cand_a",
            "category": "A",
            "disagrees_with_legacy": False,
            "proposal_receipt_id": "p-1",
            "legacy_receipt_id": "legacy-0-x",
            "rule_version": "v1",
        }]
        q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
        _write_jsonl(q, queue_rows)
        _write_jsonl(t, triage_rows)
        _write_jsonl(m, [])
        confirm(t, q, m, o, oracle_authority=oracle_authority)
        return [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_oracle_does_not_stamp_a_human_accept_receipt(self):
        """[REPLACED 29/09/2026 · WP-6 / F-H02] was kind='human-accept'."""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            out_rows = self._run_confirm(Path(d), "auto-reviewed")
        self.assertEqual(len(out_rows), 1)
        review = out_rows[0]["review"]
        self.assertTrue(review["independent_receipt_id"].startswith("oracle-"),
                        f"oracle stamped {review['independent_receipt_id']!r} as a human sign-off")
        self.assertFalse(review["independent_receipt_id"].startswith("human-accept"))
        self.assertEqual(review["label_quality"], "oracle_confirmed")

    def test_oracle_receipt_still_passes_the_contract_format(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            out_rows = self._run_confirm(Path(d), "auto-reviewed")
        from training.decision_contract import RECEIPT_ID_RE

        self.assertRegex(out_rows[0]["review"]["independent_receipt_id"], RECEIPT_ID_RE)

    def test_human_path_still_stamps_human_accept(self):
        from training.confirm_gold import confirm
        import tempfile

        cands = [{"id": "cand_a", "description": "a"}, {"id": "cand_b", "description": "b"}]
        queue_rows = [{"candidates": cands, "review": {"status": "PENDING"}}]
        triage_rows = [{
            "proposed_selected_candidate": "cand_a", "category": "A",
            "disagrees_with_legacy": False, "rule_version": "v1",
        }]
        manifest = [{
            "row": 0, "action": "accept", "outcome": "success",
            "reviewer": "vinguyen", "reviewed_at": "2026-09-29T00:00:00Z",
        }]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            q, t, m, o = d / "q.jsonl", d / "t.jsonl", d / "m.jsonl", d / "o.jsonl"
            _write_jsonl(q, queue_rows)
            _write_jsonl(t, triage_rows)
            _write_jsonl(m, manifest)
            confirm(t, q, m, o, oracle_authority="propose-only")
            out_rows = [json.loads(line) for line in o.read_text(encoding="utf-8").splitlines() if line.strip()]
        review = out_rows[0]["review"]
        self.assertTrue(review["independent_receipt_id"].startswith("human-accept"))
        self.assertEqual(review["label_quality"], "independently_reviewed")


class KnownLimitsTests(unittest.TestCase):
    def test_entry_without_any_receipt_reference_fails(self):
        """[REPLACED 29/09/2026 · WP-6 / F-H04] was: silent pass."""
        import tempfile

        from training.check_known_limits import check_known_limits

        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            receipts = dp / "evidence"
            receipts.mkdir()
            (receipts / "receipt-001.json").write_text("{}", encoding="utf-8")
            limits = dp / "KNOWN_LIMITATIONS.md"
            limits.write_text(
                "| L-01 | NOT_RUN | Receipt `evidence/receipt-001.json` down. | C01 |\n"
                "| L-30 | INCONCLUSIVE | gold_outcome is unknown on all rows. | action-success |\n",
                encoding="utf-8",
            )
            result = check_known_limits(limits, receipts)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("L-30" in p and "no receipt reference" in p for p in result["problems"]),
                        f"unreferenced entry was not flagged: {result['problems']}")

    def test_entries_with_resolved_receipts_still_pass(self):
        import tempfile

        from training.check_known_limits import check_known_limits

        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            receipts = dp / "evidence"
            receipts.mkdir()
            (receipts / "receipt-001.json").write_text("{}", encoding="utf-8")
            limits = dp / "KNOWN_LIMITATIONS.md"
            limits.write_text(
                "| L-01 | NOT_RUN | Receipt `evidence/receipt-001.json` down. | C01 |\n",
                encoding="utf-8",
            )
            result = check_known_limits(limits, receipts)
        self.assertEqual(result["status"], "PASS")


# ---------------------------------------------------------------------------
# 6. F-H03 — the two schemas must not be confused
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_chatml_and_typed_are_told_apart(self):
        self.assertEqual(detect_schema({"messages": [], "source": "x", "reward": 1.0}), SCHEMA_CHATML)
        self.assertEqual(detect_schema({"context_state": "s", "candidates": [{"id": "a"}]}), SCHEMA_TYPED)

    def test_typed_apis_refuse_a_chatml_row_by_name(self):
        chatml = {"messages": [{"role": "user", "content": "hi"}], "source": "x", "reward": 1.0}
        with self.assertRaises(SchemaMismatchError) as ctx:
            require_typed(chatml, api="validate_decision_input")
        self.assertIn("ChatML", str(ctx.exception))
        self.assertIn("legacy_to_typed", str(ctx.exception))

        with self.assertRaises(SchemaMismatchError):
            validate_decision_input(chatml)

    def test_a_typed_row_still_validates(self):
        row = {
            "task_id": "t1",
            "decision_type": "choice",
            "context_state": "s",
            "candidates": [{"id": "a", "description": "do it"}],
        }
        require_typed(row)
        parsed = validate_decision_input(row)
        self.assertEqual(parsed.task_id, "t1")


if __name__ == "__main__":
    unittest.main()
