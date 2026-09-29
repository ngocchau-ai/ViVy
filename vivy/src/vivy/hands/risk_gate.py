"""RiskGate — fail-closed safety layer in front of order execution.

[ADR-008 · D-3 · 29/09/2026] — WP-4 / O-13 / G-01, G-02, G-03.

WHAT THIS IS
    A **safety ally**, not a strategy.  It never decides *whether* to trade,
    *when* to enter, or *how much edge* an idea has.  ViVy's reasoning still
    picks the action, the symbol, the volume and the SL/TP.

WHAT THIS DOES
    Refuses orders that are physically invalid or outside the declared risk
    envelope, before anything reaches the terminal:

    * volume <= 0, NaN, Inf, or otherwise unparseable
    * volume outside ``[min_volume, max_volume]``
    * missing / zero Stop Loss or Take Profit on an entry order
    * a symbol outside the allow-list
    * SL/TP on the wrong side of the reference price
    * any field the gate cannot parse  → reject (fail-closed, never "best effort")

WHY THIS OVERRIDES "CẤM GÁC CỔNG LẬP TRÌNH"
    ``docs/TECHNICAL_DIRECTION.md`` used to forbid any programmatic gate in the
    Hands layer ("CẤM tuyệt đối bộ lọc cản hay gác cổng lập trình cứng").
    The project owner **deliberately replaced** that rule on 29/09/2026 (D-3)
    after the review measured 0/30 adversarial order attempts being stopped.
    See ``docs/adr/ADR-008-risk-gate.md`` for the scope of the override: it
    applies to *safety validation only*, never to strategy filtering.

DEFAULTS
    ``paper_trading=True``.  Live trading requires an explicit opt-in, so an
    accidental ``execute_decision`` call cannot place a real order.

The gate is **LLM-independent**: it never calls a model, and it must keep
working when the model backend is down (in that case the executor should
already be refusing to execute — see ``mt5_executor``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RiskGateError(ValueError):
    """A decision could not be validated.  Always means: do not execute."""


class UnparseableFieldError(RiskGateError):
    """A numeric field was missing, non-finite, or not a number."""


# ---------------------------------------------------------------------------
# Parsing — one strict parser, used by inference and by the gate
# ---------------------------------------------------------------------------


def parse_finite_float(value: Any, *, field_name: str) -> float:
    """Parse a numeric decision field, rejecting anything non-finite.

    Fail-closed: there is **no default**.  A missing or garbage number is an
    error, not an invitation to invent ``0.01`` or ``0.0`` — inventing a Stop
    Loss of ``0.0`` is exactly the hazard G-02 describes.

    Raises
    ------
    UnparseableFieldError
        If ``value`` is None, not a number, NaN, or +/-Inf.
    """
    if value is None:
        raise UnparseableFieldError(f"{field_name}: missing (None)")
    if isinstance(value, bool):
        # bool is an int subclass; True/False must never stand in for a price.
        raise UnparseableFieldError(f"{field_name}: got bool {value!r}, expected a number")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            raise UnparseableFieldError(f"{field_name}: empty string")
        try:
            number = float(text)
        except ValueError as exc:
            raise UnparseableFieldError(f"{field_name}: not a number ({value!r})") from exc
    else:
        raise UnparseableFieldError(f"{field_name}: unsupported type {type(value).__name__}")

    if not math.isfinite(number):
        raise UnparseableFieldError(f"{field_name}: non-finite ({number})")
    return number


def parse_optional_finite_float(value: Any, *, field_name: str) -> float | None:
    """Like :func:`parse_finite_float` but a missing value returns ``None``.

    A *present* but invalid value still raises — silence is not consent.
    """
    if value is None:
        return None
    return parse_finite_float(value, field_name=field_name)


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

#: Symbols the shipped configuration knows about.  Extend explicitly.
DEFAULT_ALLOWED_SYMBOLS: frozenset[str] = frozenset({"EURUSD", "GOLD", "XAUUSD"})

#: Hard ceiling on a single order, in lots.  G-02.
DEFAULT_MAX_VOLUME: float = 1.0
DEFAULT_MIN_VOLUME: float = 0.01

ENTRY_ACTIONS: frozenset[str] = frozenset({"BUY", "SELL"})


@dataclass(frozen=True)
class RiskLimits:
    """The declared risk envelope.  Nothing outside it is executed."""

    allowed_symbols: frozenset[str] = DEFAULT_ALLOWED_SYMBOLS
    min_volume: float = DEFAULT_MIN_VOLUME
    max_volume: float = DEFAULT_MAX_VOLUME
    require_sl_tp: bool = True
    """Entry orders (BUY/SELL) must carry a non-zero SL and TP (G-03)."""
    require_price_for_side_check: bool = True
    """Without a reference price the SL/TP side cannot be verified → reject."""
    paper_trading: bool = True
    """Live trading needs an explicit opt-in (``paper_trading=False``)."""
    max_sl_distance: float | None = None
    """Optional cap on |price - SL|, in price units.  ``None`` = no cap."""
    max_tp_distance: float | None = None

    def describe(self) -> str:
        return (
            f"RiskLimits(symbols={sorted(self.allowed_symbols)}, "
            f"volume=[{self.min_volume}, {self.max_volume}], "
            f"require_sl_tp={self.require_sl_tp}, paper={self.paper_trading})"
        )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskVerdict:
    """Why an order was allowed or refused.  Never silent."""

    allowed: bool
    action: str
    symbol: str
    volume: float
    reasons: tuple[str, ...] = ()
    paper_trading: bool = True
    checks_run: tuple[str, ...] = field(default_factory=tuple)

    @property
    def rejected(self) -> bool:
        return not self.allowed

    def summary(self) -> str:
        if self.allowed:
            mode = "PAPER" if self.paper_trading else "LIVE"
            return f"ALLOWED[{mode}] {self.action} {self.volume} {self.symbol}"
        return f"REJECTED {self.action} {self.symbol}: " + "; ".join(self.reasons)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "symbol": self.symbol,
            "volume": self.volume,
            "reasons": list(self.reasons),
            "paper_trading": self.paper_trading,
            "checks_run": list(self.checks_run),
        }


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


class RiskGate:
    """Fail-closed safety validation for a decision dict.

    LLM-independent and side-effect free: ``check`` only reads the decision.

    Usage::

        gate = RiskGate()                      # paper trading
        verdict = gate.check(decision, price=2383.0)
        if not verdict.allowed:
            raise RiskGateError(verdict.summary())
    """

    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    # ------------------------------------------------------------------

    def check(
        self,
        decision: Mapping[str, Any],
        *,
        price: float | None = None,
    ) -> RiskVerdict:
        """Validate one decision.  Returns a verdict; never raises on reject.

        Requirements scale with the action — refusing a ``HOLD`` for having no
        volume would be nonsense, and requiring a volume on a ``CLOSE`` would
        block closing the whole position:

        ============  ==========================================
        action        required
        ============  ==========================================
        ``HOLD``      a valid action name only
        ``CLOSE``     symbol; volume optional
        ``MODIFY``    symbol; at least one of SL/TP non-zero
        ``BUY/SELL``  symbol, volume, SL, TP, and SL/TP side vs price
        ============  ==========================================

        Raises only if the *decision itself* is not a mapping — that is a
        programming error, not a trade rejection.
        """
        if not isinstance(decision, Mapping):
            raise TypeError(f"decision must be a mapping, got {type(decision).__name__}")

        checks: list[str] = ["action"]
        reasons: list[str] = []

        # --- action -------------------------------------------------
        raw_action = decision.get("action")
        action = str(raw_action).strip().upper() if raw_action is not None else ""
        if not action:
            reasons.append("action: missing")
        elif action not in ENTRY_ACTIONS | {"MODIFY", "CLOSE", "HOLD"}:
            reasons.append(f"action: unknown {action!r}")

        # --- HOLD places no order at all ----------------------------
        if action == "HOLD" and not reasons:
            return RiskVerdict(
                allowed=True,
                action="HOLD",
                symbol=str(decision.get("symbol", "")).strip().upper(),
                volume=0.0,
                reasons=(),
                paper_trading=self.limits.paper_trading,
                checks_run=("action",),
            )

        is_entry = action in ENTRY_ACTIONS
        needs_symbol = action != "HOLD"

        # --- symbol -------------------------------------------------
        symbol = ""
        if needs_symbol:
            checks.append("symbol")
            raw_symbol = decision.get("symbol")
            symbol = str(raw_symbol).strip().upper() if raw_symbol is not None else ""
            if not symbol:
                reasons.append("symbol: missing")
            elif symbol not in self.limits.allowed_symbols:
                reasons.append(
                    f"symbol: {symbol!r} not in allow-list {sorted(self.limits.allowed_symbols)}"
                )

        # --- volume (G-02) — required only for entries -------------
        volume = 0.0
        checks.append("volume")
        raw_volume = decision.get("volume")
        if raw_volume is None and not is_entry:
            volume = 0.0  # CLOSE-all / MODIFY: volume is not the point
        else:
            try:
                volume = parse_finite_float(raw_volume, field_name="volume")
            except UnparseableFieldError as exc:
                reasons.append(f"volume: {exc}")
            else:
                if volume <= 0:
                    reasons.append(f"volume: must be > 0 (got {volume})")
                elif volume < self.limits.min_volume:
                    reasons.append(
                        f"volume: below minimum {self.limits.min_volume} (got {volume})"
                    )
                elif volume > self.limits.max_volume:
                    reasons.append(
                        f"volume: above ceiling {self.limits.max_volume} (got {volume})"
                    )

        # --- stop loss / take profit (G-03) -------------------------
        stop_loss: float | None = None
        take_profit: float | None = None
        checks.append("stop_loss")
        try:
            stop_loss = parse_optional_finite_float(
                decision.get("stop_loss"), field_name="stop_loss"
            )
        except UnparseableFieldError as exc:
            reasons.append(f"stop_loss: {exc}")
        checks.append("take_profit")
        try:
            take_profit = parse_optional_finite_float(
                decision.get("take_profit"), field_name="take_profit"
            )
        except UnparseableFieldError as exc:
            reasons.append(f"take_profit: {exc}")

        if is_entry and self.limits.require_sl_tp:
            if stop_loss is None or stop_loss == 0.0:
                reasons.append("stop_loss: entry order requires a non-zero stop loss")
            if take_profit is None or take_profit == 0.0:
                reasons.append("take_profit: entry order requires a non-zero take profit")
        elif action == "MODIFY":
            # MODIFY sets protection levels; refusing to set either one is a
            # risk change, so at least one must be a real level.
            if not ((stop_loss not in (None, 0.0)) or (take_profit not in (None, 0.0))):
                reasons.append("modify: needs a non-zero stop_loss or take_profit")

        # --- SL/TP side vs reference price (entries only) -----------
        ref_price: float | None = None
        if is_entry:
            checks.append("price_side")
            if price is not None:
                try:
                    ref_price = parse_finite_float(price, field_name="price")
                except UnparseableFieldError as exc:
                    reasons.append(f"price: {exc}")
            elif self.limits.require_price_for_side_check:
                reasons.append(
                    "price: no reference price — cannot verify SL/TP side (fail-closed)"
                )

            if ref_price is not None:
                reasons.extend(
                    self._check_sides(
                        action=action,
                        price=ref_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                    )
                )

        checks.append("trading_mode")
        allowed = not reasons
        return RiskVerdict(
            allowed=allowed,
            action=action,
            symbol=symbol,
            volume=volume,
            reasons=tuple(reasons),
            paper_trading=self.limits.paper_trading,
            checks_run=tuple(checks),
        )

    # Alias so call-sites can read naturally without a second name to learn.
    guard = check

    # ------------------------------------------------------------------

    def _check_sides(
        self,
        *,
        action: str,
        price: float,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> list[str]:
        """SL/TP must sit on the correct side of the reference price (G-03)."""
        out: list[str] = []
        if stop_loss is not None:
            distance = abs(price - stop_loss)
            if self.limits.max_sl_distance is not None and distance > self.limits.max_sl_distance:
                out.append(
                    f"stop_loss: {stop_loss} is {distance:.6g} from price "
                    f">{self.limits.max_sl_distance} (too far)"
                )
            if action == "BUY" and stop_loss >= price:
                out.append(f"stop_loss: BUY needs SL below price ({stop_loss} >= {price})")
            elif action == "SELL" and stop_loss <= price:
                out.append(f"stop_loss: SELL needs SL above price ({stop_loss} <= {price})")

        if take_profit is not None:
            distance = abs(take_profit - price)
            if self.limits.max_tp_distance is not None and distance > self.limits.max_tp_distance:
                out.append(
                    f"take_profit: {take_profit} is {distance:.6g} from price "
                    f">{self.limits.max_tp_distance} (too far)"
                )
            if action == "BUY" and take_profit <= price:
                out.append(
                    f"take_profit: BUY needs TP above price ({take_profit} <= {price})"
                )
            elif action == "SELL" and take_profit >= price:
                out.append(
                    f"take_profit: SELL needs TP below price ({take_profit} >= {price})"
                )
        return out

    # ------------------------------------------------------------------

    def require(
        self,
        decision: Mapping[str, Any],
        *,
        price: float | None = None,
    ) -> RiskVerdict:
        """Like :meth:`check` but raises ``RiskGateError`` when refused.

        Use at the execution boundary so a refused order cannot fall through
        to the terminal by ignoring a boolean.
        """
        verdict = self.check(decision, price=price)
        if not verdict.allowed:
            raise RiskGateError(verdict.summary())
        return verdict


def default_gate(*, paper_trading: bool = True) -> RiskGate:
    """The gate the executor uses.  Paper unless explicitly asked otherwise."""
    return RiskGate(RiskLimits(paper_trading=paper_trading))
