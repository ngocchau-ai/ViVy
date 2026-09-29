"""WP-4 / T10 — RiskGate adversarial acceptance (paper trading only).

[NEW 29/09/2026 · WP-4 / O-13 / G-01,G-02,G-03]

Nghiệm thu T10: **60 đầu ra LLM đối kháng → 0 lệnh lọt qua RiskGate.**  Every
case below is a shape a model actually produced, or a shape the review's
G-01/G-02/G-03 section predicts it will produce once it learns no check
exists.  Nothing here is live trading: the gate defaults to
``paper_trading=True`` and this file never flips it except in one explicit,
asserted test.

This file is the **live** copy of the acceptance.  ``tests/unit/test_eyes_hands.py``
carries the same executor assertions for the historical record, but that
directory was ``[ISOLATED]`` and uncollectable until ``pythonpath=["src"]``
landed — see the receipt in ``tests/unit/conftest.py``.
"""

from __future__ import annotations

import math

import pytest

from vivy.hands.mt5_executor import MT5Executor, paper_executor
from vivy.hands.risk_gate import (
    RiskGate,
    RiskGateError,
    RiskLimits,
    UnparseableFieldError,
    default_gate,
    parse_finite_float,
    parse_optional_finite_float,
)

PRICE = 2385.0

#: A well-formed BUY the gate must accept.  Everything adversarial below is a
#: mutation of this one dict, so a rejection is always about the mutation.
GOOD_BUY = {
    "action": "BUY",
    "symbol": "GOLD",
    "volume": 0.5,
    "stop_loss": 2340.0,
    "take_profit": 2400.0,
    "confidence": 0.7,
}


def _gate() -> RiskGate:
    return RiskGate(RiskLimits(paper_trading=True))


def _mutated(**changes):
    return {**GOOD_BUY, **changes}


def _without(*keys):
    return {k: v for k, v in GOOD_BUY.items() if k not in keys}


# ---------------------------------------------------------------------------
# Parsing — the second line of defence.  No defaults, ever.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [1.0, 0.0, -3.25, 10, "2.5", "  1,234.5  ", "-0.001"],
)
def test_parse_finite_float_accepts_real_numbers(value):
    assert math.isfinite(parse_finite_float(value, field_name="volume"))


@pytest.mark.parametrize(
    ("value", "label"),
    [
        (None, "missing"),
        (True, "bool-true"),
        (False, "bool-false"),
        (float("nan"), "nan"),
        (float("inf"), "inf"),
        (float("-inf"), "-inf"),
        ("", "empty-string"),
        ("   ", "whitespace"),
        ("abc", "not-a-number"),
        ("1/2", "fraction-string"),
        ("nan", "string-nan"),
        ("inf", "string-inf"),
        ([1.0], "list"),
        ({"v": 1}, "dict"),
    ],
)
def test_parse_finite_float_rejects_garbage(value, label):
    with pytest.raises(UnparseableFieldError):
        parse_finite_float(value, field_name="volume")


def test_parse_optional_allows_absent_but_not_invalid():
    assert parse_optional_finite_float(None, field_name="stop_loss") is None
    assert parse_optional_finite_float(3.5, field_name="stop_loss") == 3.5
    with pytest.raises(UnparseableFieldError):
        parse_optional_finite_float("nope", field_name="stop_loss")


def test_unparseable_is_a_risk_gate_error():
    # A caller that only catches RiskGateError still fails closed.
    assert issubclass(UnparseableFieldError, RiskGateError)


# ---------------------------------------------------------------------------
# T10 — the adversarial matrix.  Every one must be refused.
# ---------------------------------------------------------------------------

ADVERSARIAL: list[tuple[str, dict]] = [
    # --- volume: not a number, or physically impossible (G-02) ----------
    ("vol-negative", _mutated(volume=-0.5)),
    ("vol-zero", _mutated(volume=0.0)),
    ("vol-nan", _mutated(volume=float("nan"))),
    ("vol-inf", _mutated(volume=float("inf"))),
    ("vol-neg-inf", _mutated(volume=float("-inf"))),
    ("vol-none", _mutated(volume=None)),
    ("vol-missing", _without("volume")),
    ("vol-bool-true", _mutated(volume=True)),
    ("vol-bool-false", _mutated(volume=False)),
    ("vol-string-garbage", _mutated(volume="lots")),
    ("vol-empty-string", _mutated(volume="")),
    ("vol-list", _mutated(volume=[0.1])),
    ("vol-dict", _mutated(volume={"lots": 1})),
    # --- volume: outside the declared envelope --------------------------
    ("vol-below-min", _mutated(volume=0.0001)),
    ("vol-above-ceil", _mutated(volume=50.0)),
    ("vol-absurd-ceil", _mutated(volume=1e9)),
    # --- stop loss / take profit missing or zero (G-03) -----------------
    ("sl-missing", _without("stop_loss")),
    ("tp-missing", _without("take_profit")),
    ("sl-none", _mutated(stop_loss=None)),
    ("tp-none", _mutated(take_profit=None)),
    ("sl-zero", _mutated(stop_loss=0.0)),
    ("tp-zero", _mutated(take_profit=0.0)),
    ("sl-nan", _mutated(stop_loss=float("nan"))),
    ("tp-inf", _mutated(take_profit=float("inf"))),
    ("sl-string", _mutated(stop_loss="low")),
    ("tp-list", _mutated(take_profit=[2400.0])),
    ("sl-and-tp-both-missing", _without("stop_loss", "take_profit")),
    ("sl-and-tp-both-zero", _mutated(stop_loss=0.0, take_profit=0.0)),
    ("sl-bool", _mutated(stop_loss=True)),
    ("tp-bool", _mutated(take_profit=False)),
    # --- SL/TP on the wrong side of price (G-03) -----------------------
    ("buy-sl-above-price", _mutated(stop_loss=2390.0)),
    ("buy-sl-equal-price", _mutated(stop_loss=PRICE)),
    ("buy-tp-below-price", _mutated(take_profit=2380.0)),
    ("buy-tp-equal-price", _mutated(take_profit=PRICE)),
    ("buy-both-wrong-side", _mutated(stop_loss=2390.0, take_profit=2380.0)),
    ("buy-inverted", _mutated(stop_loss=2400.0, take_profit=2340.0)),
    ("sell-sl-below-price", _mutated(action="SELL", stop_loss=2380.0)),
    ("sell-sl-equal-price", _mutated(action="SELL", stop_loss=PRICE)),
    ("sell-tp-above-price", _mutated(action="SELL", take_profit=2390.0)),
    ("sell-tp-equal-price", _mutated(action="SELL", take_profit=PRICE)),
    (
        "sell-both-wrong-side",
        _mutated(action="SELL", stop_loss=2380.0, take_profit=2390.0),
    ),
    (
        "sell-inverted",
        _mutated(action="SELL", stop_loss=2340.0, take_profit=2400.0),
    ),
    # --- symbol (allow-list) -------------------------------------------
    ("sym-missing", _without("symbol")),
    ("sym-none", _mutated(symbol=None)),
    ("sym-empty", _mutated(symbol="")),
    ("sym-whitespace", _mutated(symbol="   ")),
    ("sym-unknown", _mutated(symbol="DOGEUSDT")),
    ("sym-lowercase-unknown", _mutated(symbol="dogeusdt")),
    ("sym-too-long", _mutated(symbol="A" * 200)),
    ("sym-numeric", _mutated(symbol=12345)),
    ("sym-injection", _mutated(symbol="GOLD; DROP TABLE orders")),
    ("sym-list", _mutated(symbol=["GOLD"])),
    # --- action --------------------------------------------------------
    ("act-missing", _without("action")),
    ("act-unknown", _mutated(action="YOLO")),
    ("act-empty", _mutated(action="")),
    ("act-none", _mutated(action=None)),
    ("act-number", _mutated(action=1)),
    ("act-list", _mutated(action=["BUY"])),
    ("act-garbled-pair", _mutated(action="buy sell")),
    # --- multi-fault orders (what real LLM output actually looks like) --
    ("multi-vol-neg-and-missing-sl", _without("stop_loss", "volume")),
    ("multi-unknown-sym-and-nan-tp", _mutated(symbol="X", take_profit=float("nan"))),
    ("multi-zero-everything", _mutated(volume=0.0, stop_loss=0.0, take_profit=0.0)),
    (
        "multi-garbled-everything",
        _mutated(action="LONG", symbol="", volume="x", stop_loss="y", take_profit="z"),
    ),
    (
        "multi-inverted-and-oversized",
        _mutated(volume=99.0, stop_loss=2500.0, take_profit=2200.0),
    ),
    ("multi-empty-everything", {"action": "", "symbol": "", "volume": None}),
]


def test_t10_adversarial_matrix_is_at_least_60_strong():
    """The T10 number is the point of this file — keep it honest."""
    assert len(ADVERSARIAL) >= 60, (
        f"T10 needs >= 60 adversarial shapes, found {len(ADVERSARIAL)}"
    )


@pytest.mark.parametrize(("case_id", "decision"), ADVERSARIAL, ids=[c[0] for c in ADVERSARIAL])
def test_t10_adversarial_order_is_refused(case_id, decision):
    gate = _gate()
    verdict = gate.check(decision, price=PRICE)
    assert verdict.allowed is False, (
        f"{case_id}: order leaked through RiskGate → {verdict.summary()}"
    )
    assert verdict.reasons, f"{case_id}: rejected with no stated reason"
    # The executor must agree — no path may ignore the verdict.
    receipt = MT5Executor(connected=True).execute_decision(decision, price=PRICE)
    assert receipt.status == "REJECTED", f"{case_id}: executor overrode the gate"
    assert receipt.order_id is None
    assert receipt.live is False
    assert receipt.risk is not None


def test_t10_entry_without_reference_price_is_refused():
    """Fail-closed: no price means the SL/TP side cannot be verified."""
    verdict = _gate().check(GOOD_BUY, price=None)
    assert verdict.allowed is False
    assert any("price" in r for r in verdict.reasons)

    receipt = MT5Executor(connected=True).execute_decision(GOOD_BUY)
    assert receipt.status == "REJECTED"
    assert receipt.order_id is None


def test_t10_unparseable_decision_never_reaches_the_terminal():
    executor = MT5Executor(connected=True)
    for bad in (None, "BUY", 42, ["BUY"], (1, 2), object()):
        receipt = executor.execute_decision(bad)  # type: ignore[arg-type]
        assert receipt.status == "REJECTED", f"{bad!r} reached the terminal"
        assert receipt.order_id is None


# ---------------------------------------------------------------------------
# What the gate must NOT do — it is a safety ally, not a strategy.
# ---------------------------------------------------------------------------


def test_gate_accepts_a_correctly_formed_entry():
    verdict = _gate().check(GOOD_BUY, price=PRICE)
    assert verdict.allowed is True, verdict.summary()
    assert verdict.action == "BUY"
    assert verdict.volume == 0.5
    assert verdict.paper_trading is True


def test_gate_accepts_a_correctly_formed_sell():
    decision = _mutated(
        action="SELL", symbol="EURUSD", stop_loss=1.11, take_profit=1.09
    )
    verdict = _gate().check(decision, price=1.10)
    assert verdict.allowed is True, verdict.summary()
    assert verdict.action == "SELL"


def test_gate_checks_side_against_the_price_it_is_given_not_instrument_realism():
    """ADR-008 boundary: the gate does not know what EURUSD "should" cost.

    ``stop_loss=2420`` is a valid *side* for a SELL against ``price=2385``
    and an invalid side against ``price=1.10``.  The gate answers only that
    question.  Judging whether 2420 is a sensible EURUSD level is strategy,
    and ADR-008 forbids the gate from touching strategy.
    """
    decision = _mutated(
        action="SELL", symbol="EURUSD", stop_loss=2420.0, take_profit=2350.0
    )
    assert _gate().check(decision, price=2385.0).allowed is True
    refused = _gate().check(decision, price=1.10)  # TP is above the price
    assert refused.allowed is False


def test_gate_does_not_filter_strategy_shapes_it_is_not_allowed_to_touch():
    """A far-away SL is allowed unless max_sl_distance is declared.

    If this test ever fails because someone added a risk-reward ratio or a
    conviction cap, ADR-008 has been violated.
    """
    wide = _mutated(stop_loss=1000.0, take_profit=9000.0)  # absurd R:R
    verdict = _gate().check(wide, price=PRICE)
    assert verdict.allowed is True, verdict.summary()

    # ...but a caller who DECLARES a distance cap gets it enforced.
    capped = RiskGate(
        RiskLimits(paper_trading=True, max_sl_distance=50.0, max_tp_distance=50.0)
    )
    refused = capped.check(wide, price=PRICE)
    assert refused.allowed is False


def test_hold_places_no_order_and_needs_no_numbers():
    verdict = _gate().check({"action": "HOLD"}, price=None)
    assert verdict.allowed is True
    assert verdict.action == "HOLD"
    assert verdict.volume == 0.0

    receipt = MT5Executor(connected=True).execute_decision({"action": "HOLD"})
    assert receipt.status == "HOLD"
    assert receipt.order_id is None


def test_close_allows_an_absent_volume_but_still_needs_a_symbol():
    ok = _gate().check({"action": "CLOSE", "symbol": "GOLD"}, price=None)
    assert ok.allowed is True

    no_symbol = _gate().check({"action": "CLOSE"}, price=None)
    assert no_symbol.allowed is False


def test_modify_needs_at_least_one_real_level():
    ok = _gate().check(
        {"action": "MODIFY", "symbol": "GOLD", "stop_loss": 2300.0}, price=None
    )
    assert ok.allowed is True

    empty = _gate().check(
        {"action": "MODIFY", "symbol": "GOLD", "stop_loss": 0.0, "take_profit": 0.0},
        price=None,
    )
    assert empty.allowed is False


# ---------------------------------------------------------------------------
# Paper by default.  Live is an explicit, loud opt-in.
# ---------------------------------------------------------------------------


def test_executor_is_paper_by_default_and_says_so():
    executor = MT5Executor(connected=True)
    assert executor.is_paper is True

    receipt = executor.execute_decision(GOOD_BUY, price=PRICE)
    assert receipt.status == "EXECUTED"
    assert receipt.live is False
    assert "Paper" in receipt.message
    assert receipt.risk is not None and receipt.risk["paper_trading"] is True


def test_paper_executor_helper_cannot_go_live():
    executor = paper_executor()
    assert executor.is_paper is True


def test_live_requires_an_explicit_limits_object():
    live = MT5Executor(
        connected=True,
        gate=RiskGate(RiskLimits(paper_trading=False)),
    )
    assert live.is_paper is False
    receipt = live.execute_decision(GOOD_BUY, price=PRICE)
    assert receipt.live is True
    # Still not a fill — the executor has no broker connection.  "LIVE" only
    # names the gate's configuration (ADR-008, out-of-scope note).
    assert receipt.status == "EXECUTED"


def test_default_gate_is_paper():
    assert default_gate().limits.paper_trading is True
    assert default_gate(paper_trading=False).limits.paper_trading is False


# ---------------------------------------------------------------------------
# Verdicts are never silent.
# ---------------------------------------------------------------------------


def test_reject_raises_when_the_caller_uses_require():
    gate = _gate()
    with pytest.raises(RiskGateError):
        gate.require(_mutated(volume=-1.0), price=PRICE)
    verdict = gate.require(GOOD_BUY, price=PRICE)
    assert verdict.allowed is True


def test_verdict_to_dict_carries_the_receipt():
    verdict = _gate().check(_mutated(symbol="DOGEUSDT"), price=PRICE)
    payload = verdict.to_dict()
    assert payload["allowed"] is False
    assert payload["symbol"] == "DOGEUSDT"
    assert payload["reasons"]
    assert "action" in payload["checks_run"]
    assert verdict.rejected is True
    assert "REJECTED" in verdict.summary()
