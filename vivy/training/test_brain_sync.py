"""C11 tests — 2brain sync fail → pending + idempotent retry (no false synced=true)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from training.brain_sync import SyncResult, sync_lessons, sync_status


class SyncGateTests(unittest.TestCase):
    def test_success_requires_readback_hash_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "brain"
            result = sync_lessons(
                lessons=[{"lesson_id": "l1", "value": "x"}],
                brain_root=brain,
                content_hash="h1",
            )
            self.assertTrue(result.synced)
            self.assertEqual(result.status, "synced")
            self.assertEqual(result.readback_hash, "h1")
            self.assertTrue(result.files)

    def test_hash_mismatch_is_pending_not_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "brain"
            result = sync_lessons(
                lessons=[{"lesson_id": "l1", "value": "x"}],
                brain_root=brain,
                content_hash="h-expected",
                force_readback_hash="h-different",
            )
            self.assertFalse(result.synced)
            self.assertEqual(result.status, "pending")
            self.assertEqual(sync_status(brain), "pending")

    def test_brain_root_failure_is_pending(self):
        result = sync_lessons(
            lessons=[{"lesson_id": "l1"}],
            brain_root=Path("Z:\\definitely\\missing\\brain-root-xyz"),
            content_hash="h1",
        )
        self.assertFalse(result.synced)
        self.assertEqual(result.status, "pending")
        self.assertIsNotNone(result.error)

    def test_retry_after_failure_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "brain"
            fail = sync_lessons(
                lessons=[{"lesson_id": "l1", "value": "x"}],
                brain_root=brain,
                content_hash="h1",
                force_readback_hash="wrong",
            )
            self.assertEqual(fail.status, "pending")

            ok = sync_lessons(
                lessons=[{"lesson_id": "l1", "value": "x"}],
                brain_root=brain,
                content_hash="h1",
            )
            self.assertTrue(ok.synced)

            again = sync_lessons(
                lessons=[{"lesson_id": "l1", "value": "x"}],
                brain_root=brain,
                content_hash="h1",
            )
            self.assertTrue(again.synced)
            self.assertTrue(again.idempotent_replay)
            # one landing file set, not doubled
            lesson_files = list((brain / "projects" / "vivy-v5" / "lessons").glob("*.jsonl"))
            self.assertEqual(len(lesson_files), 1)

    def test_never_synced_true_before_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "brain"
            result = sync_lessons(
                lessons=[{"lesson_id": "l1"}],
                brain_root=brain,
                content_hash="h1",
                force_readback_hash="mismatch",
            )
            self.assertNotEqual(result.synced, True)
            self.assertNotIn("synced_files", result.as_dict() if result.synced else {})


if __name__ == "__main__":
    unittest.main()
