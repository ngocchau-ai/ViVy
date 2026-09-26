"""
Associative Vector Memory & Past Trade Lessons Store for ViVy.
Stores past trade outcomes, market context, and lessons learned for 1-touch intuition recall.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TradeMemoryEntry:
    entry_id: str
    symbol: str
    action: str
    market_context: dict[str, Any]
    lesson: str
    outcome_pnl: float
    confidence: float


class ViVyVectorMemory:
    """Local persistent vector memory for ViVy trade lessons and intuition recall."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or ":memory:"
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_lessons (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    action TEXT,
                    context_json TEXT,
                    lesson TEXT,
                    pnl REAL,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_lesson(self, entry: TradeMemoryEntry):
        """Stores a trade lesson into persistent memory."""
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO trade_lessons (id, symbol, action, context_json, lesson, pnl, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.entry_id,
                    entry.symbol,
                    entry.action,
                    json.dumps(entry.market_context),
                    entry.lesson,
                    entry.outcome_pnl,
                    entry.confidence
                )
            )

    def query_lessons(self, symbol: str, limit: int = 5) -> list[str]:
        """Recalls relevant past lessons for symbol."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT lesson, pnl FROM trade_lessons
            WHERE symbol = ? OR symbol = 'ALL'
            ORDER BY created_at DESC LIMIT ?
            """,
            (symbol, limit)
        )
        rows = cursor.fetchall()
        return [f"[{'WIN' if r[1] >= 0 else 'LOSS'}] {r[0]}" for r in rows]

    def get_all_lessons(self) -> list[TradeMemoryEntry]:
        """Returns all stored memory entries."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT id, symbol, action, context_json, lesson, pnl, confidence FROM trade_lessons")
        rows = cursor.fetchall()
        return [
            TradeMemoryEntry(
                entry_id=r[0],
                symbol=r[1],
                action=r[2],
                market_context=json.loads(r[3]),
                lesson=r[4],
                outcome_pnl=r[5],
                confidence=r[6]
            )
            for r in rows
        ]
