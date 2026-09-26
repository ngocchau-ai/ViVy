"""Cautreo Session Log — Append-only audit trail + scoring (TD-3, TD-7).

Records every orchestration session with decisions, scores, and state deltas.
Provides replay for experience extraction and self-improve data.

Structure:
    SessionLog
    ├── entries: list[SessionEntry]
    │   ├── session_id, timestamp
    │   ├── decisions: list[{input, strategy, model, output, score}]
    │   ├── state_delta: dict (weight_map changes)
    │   └── aggregate_score: float
    ├── append(entry), query(filter) -> list[SessionEntry]
    └── replay() -> experience summary

Session log = dữ liệu thời gian (audit + self-improve). Tree map = cấu trúc
truy vấn (tốc độ). Together they form the Cautreo memory layer.

Changelog:
    25/09/2026 (Claude Code — Wave 1B): Initial.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Decision:
    """One orchestration decision within a session."""

    input_context: str
    strategy: str
    model_target: str
    output: str = ""
    score: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_context": self.input_context,
            "strategy": self.strategy,
            "model_target": self.model_target,
            "output": self.output,
            "score": self.score,
            "metadata": dict(self.metadata),
        }


@dataclass
class SessionEntry:
    """One orchestration session record."""

    session_id: str
    decisions: list[Decision] = field(default_factory=list)
    state_delta: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def aggregate_score(self) -> float:
        """Mean score across all decisions in this session."""
        if not self.decisions:
            return 0.0
        return sum(d.score for d in self.decisions) / len(self.decisions)

    @property
    def decision_count(self) -> int:
        return len(self.decisions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "decisions": [d.to_dict() for d in self.decisions],
            "state_delta": dict(self.state_delta),
            "timestamp": self.timestamp,
            "aggregate_score": self.aggregate_score,
            "decision_count": self.decision_count,
            "metadata": dict(self.metadata),
        }


class SessionLog:
    """Append-only session log with query and replay.

    Every orchestration session is recorded immutably. Query filters by
    session_id, model_target, strategy, or score threshold. Replay extracts
    patterns for experience accumulation and self-improve.
    """

    def __init__(self) -> None:
        self._entries: list[SessionEntry] = []

    @property
    def size(self) -> int:
        return len(self._entries)

    def append(self, entry: SessionEntry) -> None:
        """Append a session entry. Once appended, entries are immutable."""
        self._entries.append(entry)

    def get(self, session_id: str) -> SessionEntry | None:
        for e in self._entries:
            if e.session_id == session_id:
                return e
        return None

    def query(
        self,
        *,
        model_target: str = "",
        strategy: str = "",
        min_score: float = 0.0,
        session_id: str = "",
    ) -> list[SessionEntry]:
        """Filter entries by optional criteria."""
        results = []
        for e in self._entries:
            if session_id and e.session_id != session_id:
                continue
            if model_target and not any(
                d.model_target == model_target for d in e.decisions
            ):
                continue
            if strategy and not any(d.strategy == strategy for d in e.decisions):
                continue
            if e.aggregate_score < min_score:
                continue
            results.append(e)
        return results

    def replay(self) -> dict[str, Any]:
        """Extract experience summary from all logged sessions.

        Returns patterns for self-improve: top strategies, model usage,
        score trends, and state change summary.
        """
        if not self._entries:
            return {
                "total_sessions": 0,
                "total_decisions": 0,
                "avg_score": 0.0,
                "top_strategies": [],
                "model_usage": {},
                "score_trend": [],
            }

        strategy_scores: dict[str, list[float]] = {}
        model_counts: dict[str, int] = {}
        all_scores: list[float] = []
        score_trend: list[float] = []

        for entry in self._entries:
            score_trend.append(entry.aggregate_score)
            for d in entry.decisions:
                all_scores.append(d.score)
                strategy_scores.setdefault(d.strategy, []).append(d.score)
                model_counts[d.model_target] = model_counts.get(d.model_target, 0) + 1

        strategy_summaries: list[dict[str, Any]] = [
            {"strategy": s, "avg_score": sum(v) / len(v), "count": len(v)}
            for s, v in strategy_scores.items()
        ]
        strategy_summaries.sort(key=lambda x: x["avg_score"], reverse=True)
        top_strategies = strategy_summaries[:10]

        return {
            "total_sessions": len(self._entries),
            "total_decisions": len(all_scores),
            "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0.0,
            "top_strategies": top_strategies,
            "model_usage": model_counts,
            "score_trend": score_trend,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self._entries],
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionLog:
        log = cls()
        for ed in data.get("entries", []):
            decisions = [
                Decision(
                    input_context=d["input_context"],
                    strategy=d["strategy"],
                    model_target=d["model_target"],
                    output=d.get("output", ""),
                    score=d.get("score", 0.5),
                    metadata=dict(d.get("metadata", {})),
                )
                for d in ed.get("decisions", [])
            ]
            entry = SessionEntry(
                session_id=ed["session_id"],
                decisions=decisions,
                state_delta=dict(ed.get("state_delta", {})),
                timestamp=ed.get("timestamp", ""),
                metadata=dict(ed.get("metadata", {})),
            )
            log._entries.append(entry)
        return log
