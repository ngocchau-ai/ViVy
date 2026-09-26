"""Tests for cautreo_session_log (Wave 1B — append-only + scoring).

Changelog:
    25/09/2026 (Claude Code — Wave 1B): Initial.
"""
from __future__ import annotations

import unittest

from training.cautreo_session_log import (
    Decision,
    SessionEntry,
    SessionLog,
)


class TestDecision(unittest.TestCase):
    def test_defaults(self) -> None:
        d = Decision(input_context="ctx", strategy="route", model_target="gemma4")
        self.assertEqual(d.output, "")
        self.assertEqual(d.score, 0.5)

    def test_to_dict(self) -> None:
        d = Decision(
            input_context="ctx", strategy="route", model_target="m",
            output="out", score=0.9,
        )
        d2 = d.to_dict()
        self.assertEqual(d2["score"], 0.9)
        self.assertEqual(d2["output"], "out")


class TestSessionEntry(unittest.TestCase):
    def test_aggregate_score_empty(self) -> None:
        e = SessionEntry(session_id="s1")
        self.assertAlmostEqual(e.aggregate_score, 0.0)
        self.assertEqual(e.decision_count, 0)

    def test_aggregate_score_mean(self) -> None:
        e = SessionEntry(
            session_id="s1",
            decisions=[
                Decision("i1", "r", "m", score=0.8),
                Decision("i2", "r", "m", score=0.6),
            ],
        )
        self.assertAlmostEqual(e.aggregate_score, 0.7)
        self.assertEqual(e.decision_count, 2)

    def test_to_dict(self) -> None:
        e = SessionEntry(session_id="s1", timestamp="2026-09-25")
        d = e.to_dict()
        self.assertEqual(d["session_id"], "s1")
        self.assertEqual(d["decision_count"], 0)


class TestSessionLogAppend(unittest.TestCase):
    def test_append_and_get(self) -> None:
        log = SessionLog()
        log.append(SessionEntry(session_id="s1"))
        self.assertEqual(log.size, 1)
        self.assertIsNotNone(log.get("s1"))

    def test_get_missing(self) -> None:
        log = SessionLog()
        self.assertIsNone(log.get("nope"))


class TestSessionLogQuery(unittest.TestCase):
    def setUp(self) -> None:
        self.log = SessionLog()
        self.log.append(SessionEntry(
            session_id="s1",
            decisions=[Decision("i", "route", "gemma4", score=0.9)],
        ))
        self.log.append(SessionEntry(
            session_id="s2",
            decisions=[Decision("i", "abstain", "qwen", score=0.3)],
        ))

    def test_query_by_model(self) -> None:
        results = self.log.query(model_target="gemma4")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].session_id, "s1")

    def test_query_by_strategy(self) -> None:
        results = self.log.query(strategy="abstain")
        self.assertEqual(len(results), 1)

    def test_query_by_min_score(self) -> None:
        results = self.log.query(min_score=0.5)
        self.assertEqual(len(results), 1)

    def test_query_by_session_id(self) -> None:
        results = self.log.query(session_id="s2")
        self.assertEqual(len(results), 1)

    def test_query_empty(self) -> None:
        results = self.log.query(model_target="nonexistent")
        self.assertEqual(results, [])


class TestSessionLogReplay(unittest.TestCase):
    def test_replay_empty(self) -> None:
        log = SessionLog()
        r = log.replay()
        self.assertEqual(r["total_sessions"], 0)
        self.assertEqual(r["avg_score"], 0.0)

    def test_replay_with_data(self) -> None:
        log = SessionLog()
        log.append(SessionEntry(
            session_id="s1",
            decisions=[
                Decision("i1", "route", "gemma4", score=0.8),
                Decision("i2", "route", "gemma4", score=0.9),
            ],
        ))
        log.append(SessionEntry(
            session_id="s2",
            decisions=[Decision("i3", "abstain", "qwen", score=0.4)],
        ))
        r = log.replay()
        self.assertEqual(r["total_sessions"], 2)
        self.assertEqual(r["total_decisions"], 3)
        self.assertAlmostEqual(r["avg_score"], (0.8 + 0.9 + 0.4) / 3)
        self.assertIn("route", [s["strategy"] for s in r["top_strategies"]])
        self.assertEqual(r["model_usage"]["gemma4"], 2)
        self.assertEqual(len(r["score_trend"]), 2)


class TestSessionLogSerialization(unittest.TestCase):
    def test_round_trip(self) -> None:
        log = SessionLog()
        log.append(SessionEntry(
            session_id="s1",
            decisions=[Decision("i", "r", "m", score=0.7)],
            state_delta={"node": "updated"},
        ))
        d = log.to_dict()
        log2 = SessionLog.from_dict(d)
        self.assertEqual(log2.size, 1)
        entry = log2.get("s1")
        assert entry is not None
        self.assertAlmostEqual(entry.aggregate_score, 0.7)
        self.assertEqual(entry.state_delta, {"node": "updated"})

    def test_empty_round_trip(self) -> None:
        log = SessionLog()
        log2 = SessionLog.from_dict(log.to_dict())
        self.assertEqual(log2.size, 0)


if __name__ == "__main__":
    unittest.main()
