"""
Unit tests for ViVy Eyes (Data Collector) & Hands (MT5 Action Executor).
"""

import pytest
from vivy.eyes.mt5_collector import MT5DataCollector, TechnicalIndicatorEngine, Candle
from vivy.eyes.news_bridge import NewsBridge
from vivy.hands.mt5_executor import MT5Executor


def test_technical_indicator_engine():
    closes = [10.0 + i for i in range(30)]
    rsi = TechnicalIndicatorEngine.calculate_rsi(closes)
    assert 0.0 <= rsi <= 100.0

    ema = TechnicalIndicatorEngine.calculate_ema(closes, period=10)
    assert ema > 0.0


def test_mt5_data_collector():
    collector = MT5DataCollector(symbol="EURUSD")
    snapshot = collector.get_market_snapshot()
    assert snapshot["symbol"] == "EURUSD"
    assert "indicators" in snapshot
    assert "rsi_14" in snapshot["indicators"]


def test_news_bridge():
    bridge = NewsBridge()
    events = bridge.get_upcoming_events("USD")
    assert len(events) > 0
    assert events[0]["currency"] == "USD"


def test_mt5_executor_no_gatekeepers():
    executor = MT5Executor(connected=True)

    # Test BUY action
    buy_decision = {
        "action": "BUY",
        "symbol": "GOLD",
        "volume": 0.5,
        "stop_loss": 2340.0,
        "take_profit": 2400.0
    }
    receipt = executor.execute_decision(buy_decision)
    assert receipt.status == "EXECUTED"
    assert receipt.action == "BUY"
    assert receipt.volume == 0.5
    assert receipt.order_id is not None

    # Test HOLD action
    hold_decision = {"action": "HOLD", "symbol": "GOLD"}
    receipt_hold = executor.execute_decision(hold_decision)
    assert receipt_hold.status == "HOLD"
