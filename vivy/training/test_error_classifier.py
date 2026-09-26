"""C11 tests — repeated-error taxonomy (root cause / action / outcome)."""
from __future__ import annotations

import unittest

from training.error_classifier import (
    ErrorSignature,
    TrialContext,
    classify_trial,
    record_error,
)


class RepeatErrorDefinitionTests(unittest.TestCase):
    def test_new_error_when_signature_unseen(self):
        sig = ErrorSignature(root_cause="timeout", action="retry_backoff", outcome="timeout")
        verdict = classify_trial([], TrialContext(signature=sig, failed=True, condition_changed=False))
        self.assertEqual(verdict, "new_error")

    def test_repeat_error_when_same_signature_fails_again_unchanged(self):
        sig = ErrorSignature(root_cause="poisoned_cache", action="force_confirm", outcome="wrong_state")
        history = [record_error(sig, task_id=1)]
        verdict = classify_trial(
            history,
            TrialContext(signature=sig, failed=True, condition_changed=False),
        )
        self.assertEqual(verdict, "repeat_error")

    def test_valid_reattempt_when_condition_changed(self):
        sig = ErrorSignature(root_cause="timeout", action="retry_backoff", outcome="timeout")
        history = [record_error(sig, task_id=1)]
        verdict = classify_trial(
            history,
            TrialContext(signature=sig, failed=True, condition_changed=True),
        )
        self.assertEqual(verdict, "valid_reattempt")

    def test_success_after_recorded_error_is_not_repeat(self):
        sig = ErrorSignature(root_cause="timeout", action="retry_backoff", outcome="timeout")
        history = [record_error(sig, task_id=1)]
        verdict = classify_trial(
            history,
            TrialContext(signature=sig, failed=False, condition_changed=False),
        )
        self.assertEqual(verdict, "recovered")

    def test_same_action_different_root_cause_is_new(self):
        old = ErrorSignature(root_cause="timeout", action="click", outcome="timeout")
        new = ErrorSignature(root_cause="focus_lost", action="click", outcome="timeout")
        history = [record_error(old, task_id=1)]
        verdict = classify_trial(
            history,
            TrialContext(signature=new, failed=True, condition_changed=False),
        )
        self.assertEqual(verdict, "new_error")

    def test_signature_covers_all_three_axes(self):
        a = ErrorSignature(root_cause="r", action="a", outcome="success")
        b = ErrorSignature(root_cause="r", action="a", outcome="wrong_state")
        self.assertNotEqual(a, b)


class FalseInhibitionTests(unittest.TestCase):
    def test_blocking_a_valid_reattempt_is_false_inhibition(self):
        from training.error_classifier import is_false_inhibition

        sig = ErrorSignature(root_cause="timeout", action="retry_backoff", outcome="timeout")
        history = [record_error(sig, task_id=1)]
        ctx = TrialContext(signature=sig, failed=False, condition_changed=True)
        # dampener still blocked the action even though condition changed
        self.assertTrue(
            is_false_inhibition(history, ctx, action_blocked_by_dampener=True)
        )
        self.assertFalse(
            is_false_inhibition(history, ctx, action_blocked_by_dampener=False)
        )


if __name__ == "__main__":
    unittest.main()
