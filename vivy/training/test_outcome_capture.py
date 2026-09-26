"""C04 tests — observed-outcome capture. Expected postcondition ≠ observed success."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.io_guard import RefuseOverwriteError, open_write
from training.outcome_capture import (
    OUTCOME_ACTION_FAILURE,
    OUTCOME_FOCUS_CHANGE,
    OUTCOME_PARTIAL,
    OUTCOME_RETRY,
    OUTCOME_ROLLBACK,
    OUTCOME_STALE_CAPTURE,
    OUTCOME_SUCCESS,
    OUTCOME_TIMEOUT,
    OUTCOME_UNKNOWN,
    OUTCOME_WRONG_STATE,
    CaptureError,
    derive_outcome,
    make_capture_id,
    record_capture,
    write_capture,
)


def _base(**overrides):
    record = {
        "task_id": "task-1",
        "goal": "Save the document to workspace.",
        "candidate_set": ["cand_save", "cand_halt"],
        "chosen_action": "cand_save",
        "permission": "sandbox",
        "tool_result": {"ok": True, "tool": "click", "detail": "clicked save"},
        "capture_before": {
            "capture_id": "cap-before-1",
            "captured_at": "2026-09-24T10:00:00+00:00",
            "state_fingerprint": "aaa111",
            "state_kind": "before",
        },
        "capture_after": {
            "capture_id": "cap-after-1",
            "captured_at": "2026-09-24T10:00:02+00:00",
            "state_fingerprint": "bbb222",
            "state_kind": "after",
        },
        "expected_postcondition": ["file persisted at workspace/doc.md"],
        "observed_postcondition": ["file persisted at workspace/doc.md"],
        "independent_checker": {
            "checker_id": "filesystem-checker-v1",
            "checked_at": "2026-09-24T10:00:03+00:00",
            "verdict": "met",
            "evidence": "stat() returned size>0 at workspace/doc.md",
        },
    }
    record.update(overrides)
    return record


class ExpectedIsNotObservedTests(unittest.TestCase):
    def test_expected_postcondition_alone_is_not_success(self):
        """A written expected postcondition never yields success by itself."""
        record = _base(
            tool_result={"ok": False, "tool": "click", "detail": "timeout"},
            capture_after=None,
            observed_postcondition=[],
            independent_checker={
                "checker_id": "filesystem-checker-v1",
                "checked_at": "2026-09-24T10:00:03+00:00",
                "verdict": "timeout",
                "evidence": "no after capture",
            },
            expected_postcondition=["file persisted at workspace/doc.md"],
        )
        outcome = derive_outcome(record)
        self.assertNotEqual(outcome, OUTCOME_SUCCESS)
        self.assertEqual(outcome, OUTCOME_TIMEOUT)

    def test_checker_not_met_with_ok_tool_is_wrong_state(self):
        record = _base(
            tool_result={"ok": True, "tool": "click", "detail": "clicked"},
            observed_postcondition=[],
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "not_met",
                "evidence": "file missing",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_WRONG_STATE)

    def test_model_self_claim_is_not_an_independent_checker(self):
        record = _base(
            independent_checker={
                "checker_id": "the-acting-model",
                "checked_at": "t",
                "verdict": "met",
                "evidence": "I think it worked",
                "is_acting_model": True,
            },
        )
        with self.assertRaises(CaptureError):
            record_capture(record)


class ScenarioOutcomeTests(unittest.TestCase):
    def test_timeout(self):
        record = _base(
            tool_result={"ok": False, "error": "timeout"},
            capture_after=None,
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "timeout", "evidence": "e",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_TIMEOUT)

    def test_focus_change(self):
        record = _base(
            tool_result={"ok": True, "detail": "window lost focus"},
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "focus_change", "evidence": "e",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_FOCUS_CHANGE)

    def test_stale_capture(self):
        record = _base(
            capture_after={
                "capture_id": "cap-after-1",
                "captured_at": "2026-09-24T09:59:00+00:00",  # BEFORE the action
                "state_fingerprint": "aaa111",
                "state_kind": "after",
            },
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "stale", "evidence": "e",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_STALE_CAPTURE)

    def test_partial(self):
        record = _base(
            observed_postcondition=["file created"],
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "partial", "evidence": "e",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_PARTIAL)

    def test_retry(self):
        record = _base(
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "retry", "evidence": "e",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_RETRY)

    def test_rollback(self):
        record = _base(
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "rolled_back", "evidence": "e",
            },
        )
        self.assertEqual(derive_outcome(record), OUTCOME_ROLLBACK)

    def test_action_failure_is_negative_outcome_not_bad_selection(self):
        """Tool failure is a negative outcome; it does not judge the candidate choice."""
        record = _base(
            tool_result={"ok": False, "error": "permission denied"},
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "tool_error", "evidence": "e",
            },
        )
        outcome = derive_outcome(record)
        self.assertEqual(outcome, OUTCOME_ACTION_FAILURE)
        record2 = record_capture(record)
        self.assertEqual(record2["gold_outcome"], OUTCOME_ACTION_FAILURE)
        self.assertNotIn("selection_was_wrong", record2)
        self.assertFalse(record2.get("outcome_indicts_selection", False))

    def test_success_requires_checker_met_and_observed(self):
        record = _base()
        self.assertEqual(derive_outcome(record), OUTCOME_SUCCESS)
        stamped = record_capture(record)
        self.assertEqual(stamped["gold_outcome"], OUTCOME_SUCCESS)
        self.assertTrue(stamped["outcome_known"])
        self.assertIsNotNone(stamped["action_observed_at"])


class SandboxAndPermissionTests(unittest.TestCase):
    def test_refuses_non_sandbox_permission(self):
        record = _base(permission="production")
        with self.assertRaises(CaptureError):
            record_capture(record)

    def test_allows_approved_dangerous_with_token(self):
        record = _base(permission="approved-sandbox", approval_token="task-1:run")
        stamped = record_capture(record, approved_task_ids=["task-1"])
        self.assertEqual(stamped["permission"], "approved-sandbox")

    def test_approved_without_token_still_refused(self):
        record = _base(permission="approved-sandbox")
        with self.assertRaises(CaptureError):
            record_capture(record, approved_task_ids=["task-1"])


class RecordShapeTests(unittest.TestCase):
    def test_capture_id_links_action_and_captures(self):
        cid = make_capture_id(
            task_id="task-1",
            chosen_action="cand_save",
            capture_before_id="cap-before-1",
            tool_result_hash="deadbeef",
        )
        self.assertTrue(cid.startswith("outcome-"))
        other = make_capture_id(
            task_id="task-1",
            chosen_action="cand_halt",
            capture_before_id="cap-before-1",
            tool_result_hash="deadbeef",
        )
        self.assertNotEqual(cid, other)

    def test_record_requires_before_capture(self):
        record = _base(capture_before=None)
        with self.assertRaises(CaptureError):
            record_capture(record)

    def test_record_stores_expected_separately_from_observed(self):
        stamped = record_capture(_base(
            expected_postcondition=["should persist"],
            observed_postcondition=[],
            independent_checker={
                "checker_id": "fs", "checked_at": "t", "verdict": "not_met", "evidence": "e",
            },
        ))
        self.assertEqual(stamped["expected_postcondition"], ["should persist"])
        self.assertEqual(stamped["observed_postcondition"], [])
        self.assertEqual(stamped["gold_outcome"], OUTCOME_WRONG_STATE)
        self.assertFalse(stamped["expected_used_as_outcome"])

    def test_missing_checker_means_unknown(self):
        record = _base(independent_checker=None, observed_postcondition=[])
        self.assertEqual(derive_outcome(record), OUTCOME_UNKNOWN)
        stamped = record_capture(record)
        self.assertFalse(stamped["outcome_known"])


class WriteGuardTests(unittest.TestCase):
    def test_write_capture_refuses_overwrite(self):
        stamped = record_capture(_base())
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "outcomes.jsonl"
            write_capture(out, stamped, protected=())
            with self.assertRaises(RefuseOverwriteError):
                write_capture(out, stamped, protected=())

    def test_write_capture_refuses_clobbering_source(self):
        stamped = record_capture(_base())
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.jsonl"
            src.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                write_capture(src, stamped, protected=(src,))


if __name__ == "__main__":
    unittest.main()
