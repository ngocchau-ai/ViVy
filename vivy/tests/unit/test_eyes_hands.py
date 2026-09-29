"""
Unit tests for ViVy Eyes (Data Collector) & Hands (MT5 Action Executor).
"""

from vivy.eyes.mt5_collector import MT5DataCollector, TechnicalIndicatorEngine
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


def test_mt5_executor_runs_the_risk_gate():
    """A valid paper order is executed; the gate is not a strategy filter.

    [REPLACED 29/09/2026 · WP-4 / D-3 / ADR-008] this test used to be named
    ``test_mt5_executor_no_gatekeepers`` and asserted that a BUY with **no
    reference price** was ``EXECUTED`` unconditionally.  That pinned exactly
    the behaviour the project owner deliberately replaced (D-3): an entry with
    no price cannot have its SL/TP side verified, so the gate refuses it.

    Per plan hard rule #4 the test was rewritten **to the spec**, not the code
    weakened: the BUY below now carries the reference price its SL/TP were
    written against (``stop_loss=2340`` < 2385 < ``take_profit=2400``) and
    still asserts the same strengths as before (status, action, volume,
    order_id) plus the risk verdict the old test never looked at.  The
    rejection cases at the bottom are new and were previously impossible —
    nothing refused anything.
    """
    executor = MT5Executor(connected=True)
    assert executor.is_paper is True  # paper by default (ADR-008)

    # Test BUY action — valid, and the reference price is supplied.
    buy_decision = {
        "action": "BUY",
        "symbol": "GOLD",
        "volume": 0.5,
        "stop_loss": 2340.0,
        "take_profit": 2400.0
    }
    receipt = executor.execute_decision(buy_decision, price=2385.0)
    assert receipt.status == "EXECUTED"
    assert receipt.action == "BUY"
    assert receipt.volume == 0.5
    assert receipt.order_id is not None
    assert receipt.live is False  # paper execution is not a fill
    assert receipt.risk is not None and receipt.risk["allowed"] is True

    # Test HOLD action
    hold_decision = {"action": "HOLD", "symbol": "GOLD"}
    receipt_hold = executor.execute_decision(hold_decision)
    assert receipt_hold.status == "HOLD"

    # --- rejections the "no gatekeepers" rule used to let through -----------

    # Entry with no reference price: SL/TP side cannot be verified → refuse.
    no_price = executor.execute_decision(buy_decision)
    assert no_price.status == "REJECTED"
    assert "price" in no_price.message

    # Volume outside the declared envelope → refuse.
    oversized = executor.execute_decision(
        {**buy_decision, "volume": 50.0}, price=2385.0
    )
    assert oversized.status == "REJECTED"
    assert "volume" in oversized.message

    # Unknown symbol → refuse.
    foreign = executor.execute_decision(
        {**buy_decision, "symbol": "DOGEUSDT"}, price=2385.0
    )
    assert foreign.status == "REJECTED"
    assert "symbol" in foreign.message

    # A rejected order never becomes a fill.
    assert no_price.order_id is None
    assert oversized.order_id is None
