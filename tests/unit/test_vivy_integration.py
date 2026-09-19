"""
End-to-End Integration test for 91sViVy AI Engine & Agent System.
"""

import pytest
from vivy.api.router import handle_health_check, handle_trade_cycle
from vivy.memory.vector_store import ViVyVectorMemory
from vivy.self_improvement.feedback_logger import FeedbackLogger, TradeOutcome


def test_api_health_check():
    health = handle_health_check()
    assert health["status"] == "online"
    assert health["system"] == "91sViVy Local AI Engine"


def test_full_trade_cycle_execution():
    cycle_result = handle_trade_cycle(symbol="GOLD")
    assert "market_snapshot" in cycle_result
    assert "vivy_thought" in cycle_result
    assert "action_decision" in cycle_result
    assert "execution_receipt" in cycle_result
    assert cycle_result["execution_receipt"]["status"] in ("EXECUTED", "HOLD")


def test_self_improvement_feedback_loop():
    memory = ViVyVectorMemory(db_path=":memory:")
    logger = FeedbackLogger(memory)

    outcome = TradeOutcome(
        order_id=10001,
        symbol="GOLD",
        action="BUY",
        entry_price=2380.0,
        exit_price=2395.0,
        pnl=150.0,
        reasoning_thought="RSI oversold + EMA20 Golden Cross"
    )

    entry = logger.log_trade_outcome(outcome)
    assert entry.outcome_pnl == 150.0

    lessons = memory.query_lessons("GOLD")
    assert len(lessons) == 1
    assert "WIN" in lessons[0]
