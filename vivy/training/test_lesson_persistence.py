"""C11 tests — lesson persistence, restart, held-out behavior, memory-on/off."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from training.lesson_persistence import (
    Lesson,
    LessonStore,
    apply_lessons,
    run_memory_on_off_lessons,
)


def _lesson(lid: str, key: str, value: str) -> Lesson:
    return Lesson(
        lesson_id=lid,
        scope="routing",
        key=key,
        value=value,
        confidence=0.9,
        provenance="receipt:x",
        created_at_ms=1000,
    )


class PersistenceTests(unittest.TestCase):
    def test_save_load_roundtrip_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lessons.jsonl"
            store = LessonStore(path)
            store.add(_lesson("l1", "avoid", "force_confirm"))
            store.add(_lesson("l2", "prefer", "retry_backoff"))
            store.checkpoint()

            reborn = LessonStore(path)
            self.assertEqual(reborn.count(), 2)
            self.assertEqual(reborn.get("l1").value, "force_confirm")

    def test_duplicate_lesson_id_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lessons.jsonl"
            store = LessonStore(path)
            store.add(_lesson("l1", "avoid", "force_confirm"))
            store.add(_lesson("l1", "avoid", "force_confirm"))
            self.assertEqual(store.count(), 1)


class HeldOutBehaviorTests(unittest.TestCase):
    def test_lessons_change_choice_on_held_out_task(self):
        lessons = [
            Lesson("l1", "routing", "avoid", "force_confirm", 0.9, "r", 1),
            Lesson("l1b", "routing", "prefer", "retry_backoff", 0.9, "r", 1),
        ]
        candidates = ("force_confirm", "retry_backoff", "read_depth")
        without = apply_lessons(candidates, lessons=[], query="should act now")
        with_ = apply_lessons(candidates, lessons=lessons, query="should act now")
        self.assertEqual(without, "force_confirm")  # first-candidate baseline
        self.assertEqual(with_, "retry_backoff")

    def test_memory_on_off_reports_gain_harm_with_denominator(self):
        tasks = [
            ("t1", "should act now", "retry_backoff"),
            ("t2", "should act now", "retry_backoff"),
            ("t3", "look only", "read_depth"),
        ]
        candidates = ("force_confirm", "retry_backoff", "read_depth")
        result = run_memory_on_off_lessons(
            tasks,
            candidates=candidates,
            lessons=[
                Lesson("l1", "routing", "avoid", "force_confirm", 0.9, "r", 1),
                Lesson("l1b", "routing", "prefer", "retry_backoff", 0.9, "r", 1),
                Lesson("l2", "routing", "prefer", "read_depth", 0.9, "r", 1),
            ],
        )
        self.assertEqual(result["n_tasks"], 3)
        self.assertEqual(result["arm_on"]["denominator"], 3)
        self.assertEqual(result["arm_off"]["denominator"], 3)
        self.assertEqual(result["gain"] + result["harm"] + result["tie"], 3)
        self.assertEqual(result["latency_claim"], "NOT_A_PHYSICAL_ZERO")
        self.assertEqual(result["status_label"], "PROVISIONAL_RESULT")


if __name__ == "__main__":
    unittest.main()
