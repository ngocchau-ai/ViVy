"""
Trade Feedback Logger & Lesson Synthesizer for ViVy Continuous Self-Improvement.
"""

from dataclasses import dataclass
import uuid
from typing import Any, Dict
from vivy.memory.vector_store import TradeMemoryEntry, ViVyVectorMemory


@dataclass
class TradeOutcome:
    order_id: int
    symbol: str
    action: str
    entry_price: float
    exit_price: float
    pnl: float
    reasoning_thought: str


class FeedbackLogger:
    """Evaluates trade results and synthesizes static lessons into persistent memory."""

    def __init__(self, memory: ViVyVectorMemory):
        self.memory = memory

    def log_trade_outcome(self, outcome: TradeOutcome) -> TradeMemoryEntry:
        """Processes trade outcome, extracts lesson, and saves to memory."""
        is_win = outcome.pnl >= 0.0

        if is_win:
            lesson = (
                f"Successful {outcome.action} trade on {outcome.symbol}. "
                f"Entry={outcome.entry_price}, Exit={outcome.exit_price}, PnL=+${outcome.pnl:.2f}. "
                f"Reasoning validated: {outcome.reasoning_thought[:100]}"
            )
        else:
            lesson = (
                f"Loss on {outcome.action} trade for {outcome.symbol}. "
                f"Entry={outcome.entry_price}, Exit={outcome.exit_price}, PnL=-${abs(outcome.pnl):.2f}. "
                f"Cautionary note: Re-evaluating entry timing against ATR."
            )

        entry = TradeMemoryEntry(
            entry_id=str(uuid.uuid4())[:8],
            symbol=outcome.symbol,
            action=outcome.action,
            market_context={"entry_price": outcome.entry_price, "exit_price": outcome.exit_price},
            lesson=lesson,
            outcome_pnl=outcome.pnl,
            confidence=0.9 if is_win else 0.4
        )

        self.memory.add_lesson(entry)
        return entry
