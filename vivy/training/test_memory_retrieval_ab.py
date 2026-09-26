"""C10 tests — memory retrieval quality + memory-on/off A/B on held-out tasks."""
from __future__ import annotations

import unittest

from training.memory_retrieval_ab import (
    MemoryCase,
    RetrievalTask,
    retrieve_memories,
    run_memory_on_off,
)


class RetrievalQualityTests(unittest.TestCase):
    def _store(self):
        return [
            MemoryCase(
                memory_id="m-rel",
                content="workspace window #3 is focused",
                tags={"relevant", "current"},
                session_id="s1",
                created_at_ms=1000,
                expires_at_ms=0,
            ),
            MemoryCase(
                memory_id="m-contra",
                content="workspace window #3 is focused",
                tags={"contradictory", "stale-source"},
                session_id="s1",
                created_at_ms=500,
                expires_at_ms=0,
                contradicts="m-rel",
            ),
            MemoryCase(
                memory_id="m-stale",
                content="old focus was window #1",
                tags={"stale"},
                session_id="s1",
                created_at_ms=100,
                expires_at_ms=200,
            ),
        ]

    def test_retrieves_relevant_and_flags_contradictory_and_stale(self):
        out = retrieve_memories(
            "workspace window focus",
            self._store(),
            now_ms=1000,
            session_id="s1",
        )
        ids = {m.memory_id for m in out["active"]}
        self.assertIn("m-rel", ids)
        self.assertIn("m-contra", ids)
        self.assertIn("m-stale", out["stale_ids"])
        self.assertIn("m-contra", out["contradiction_ids"])
        self.assertNotIn("m-stale", ids)

    def test_cross_session_memory_not_retrieved(self):
        store = self._store()
        store[0] = MemoryCase(
            memory_id="m-other-session",
            content="workspace window #3 is focused",
            tags={"relevant"},
            session_id="OTHER",
            created_at_ms=1000,
            expires_at_ms=0,
        )
        out = retrieve_memories("workspace", store, now_ms=1000, session_id="s1")
        self.assertNotIn("m-other-session", {m.memory_id for m in out["active"]})


class MemoryOnOffTests(unittest.TestCase):
    def _tasks(self):
        return [
            RetrievalTask(
                task_id="t1",
                query="which window is focused",
                gold_memory_id="m-focus",
                candidates=("m-focus", "m-other"),
            ),
            RetrievalTask(
                task_id="t2",
                query="what is the trade prohibition",
                gold_memory_id="m-policy",
                candidates=("m-policy", "m-other"),
            ),
            RetrievalTask(
                task_id="t3",
                query="unrelated question with no memory",
                gold_memory_id=None,
                candidates=("m-focus", "m-policy"),
            ),
        ]

    def _memories(self):
        return [
            MemoryCase(
                memory_id="m-focus",
                content="focused window is #3",
                tags={"relevant"},
                session_id="s1",
                created_at_ms=1,
                expires_at_ms=0,
            ),
            MemoryCase(
                memory_id="m-policy",
                content="do not place unauthorized trades",
                tags={"relevant"},
                session_id="s1",
                created_at_ms=1,
                expires_at_ms=0,
            ),
            MemoryCase(
                memory_id="m-other",
                content="unrelated filler",
                tags={},
                session_id="s1",
                created_at_ms=1,
                expires_at_ms=0,
            ),
        ]

    def test_memory_on_vs_off_uses_same_backend_and_reports_denominator(self):
        result = run_memory_on_off(
            self._tasks(),
            self._memories(),
            session_id="s1",
            seed=0,
        )
        self.assertEqual(result["backend_id"], result["backend_id_on"])
        self.assertEqual(result["backend_id"], result["backend_id_off"])
        self.assertEqual(result["n_tasks"], 3)
        self.assertEqual(result["arm_on"]["denominator"], 3)
        self.assertEqual(result["arm_off"]["denominator"], 3)
        self.assertIn("gain", result)
        self.assertIn("harm", result)
        self.assertEqual(
            result["gain"] + result["harm"] + result["tie"],
            result["n_tasks"],
        )

    def test_memory_off_cannot_read_memory(self):
        result = run_memory_on_off(
            self._tasks(),
            self._memories(),
            session_id="s1",
            seed=0,
        )
        self.assertTrue(result["arm_off"]["memory_visible"] is False)
        self.assertTrue(result["arm_on"]["memory_visible"] is True)

    def test_no_absolute_zero_latency_claim(self):
        result = run_memory_on_off(
            self._tasks(),
            self._memories(),
            session_id="s1",
            seed=0,
        )
        self.assertIn("latency_claim", result)
        self.assertEqual(result["latency_claim"], "NOT_A_PHYSICAL_ZERO")
        self.assertIn("status_label", result)
        self.assertEqual(result["status_label"], "PROVISIONAL_RESULT")


if __name__ == "__main__":
    unittest.main()
