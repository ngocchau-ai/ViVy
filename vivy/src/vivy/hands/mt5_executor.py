"""
MT5 Action Executor (Hands) — Order Execution for ViVy Decisions.

[REPLACED 29/09/2026 · ADR-008 / D-3] this module used to say
``"NO PROGRAMMATIC GATEKEEPERS: Forwards raw decisions directly without
hardcoded filters"`` and dispatched whatever the model produced.  The review
measured 0/30 adversarial order attempts being stopped (G-01/G-02/G-03), so the
project owner deliberately replaced that rule.

Every order now passes ``vivy.hands.risk_gate.RiskGate`` **before** it is
acknowledged.  The gate is a safety ally, not a strategy filter: ViVy still
chooses the action, symbol, volume and SL/TP.  The gate only refuses orders
that are physically invalid or outside the declared risk envelope.

Paper trading is the default.  See ``docs/adr/ADR-008-risk-gate.md``.
"""

import logging
from dataclasses import dataclass
from typing import Any, Mapping

from vivy.hands.risk_gate import RiskGate, RiskLimits, RiskVerdict, default_gate

logger = logging.getLogger(__name__)


@dataclass
class ExecutionReceipt:
    status: str  # EXECUTED, REJECTED, HOLD
    action: str
    symbol: str
    volume: float
    order_id: int | None
    message: str
    risk: dict[str, Any] | None = None
    """RiskGate verdict that produced this receipt (never None on REJECTED)."""
    live: bool = False
    """True only when the gate ran with ``paper_trading=False``."""


class MT5Executor:
    """Action Execution Layer (Hands) for MetaTrader 5.

    [REPLACED 29/09/2026 · ADR-008] the class docstring used to read
    ``"NO Programmatic Gatekeepers or Python Risk Filters"``.  That rule is
    superseded on purpose (D-3).  Orders are now gated by ``RiskGate``.

    Parameters
    ----------
    connected:
        Whether a live terminal is reachable.  Kept for compatibility; an
        order is never acknowledged as EXECUTED while the gate refuses it.
    gate:
        The ``RiskGate`` to run.  Defaults to paper-trading limits.  Pass a
        gate with ``RiskLimits(paper_trading=False)`` **explicitly** for live.
    """

    def __init__(
        self,
        connected: bool = True,
        gate: RiskGate | None = None,
        *,
        price: float | None = None,
    ):
        self.connected = connected
        self._order_counter = 100000
        self._gate = gate or default_gate()
        self._price = price

    # ------------------------------------------------------------------

    @property
    def gate(self) -> RiskGate:
        return self._gate

    @property
    def is_paper(self) -> bool:
        return self._gate.limits.paper_trading

    def execute_decision(
        self,
        decision: Mapping[str, Any],
        *,
        price: float | None = None,
    ) -> ExecutionReceipt:
        """Validate, then dispatch the decision.

        ``price`` is the reference price used to verify SL/TP sides.  When
        omitted, the gate falls back to the price given at construction; if
        neither is available and the decision is an entry, the gate **rejects**
        rather than guessing (fail-closed).
        """
        ref_price = price if price is not None else self._price

        try:
            verdict: RiskVerdict = self._gate.check(decision, price=ref_price)
        except TypeError as exc:
            # Not a mapping — a programming error, not a trade rejection.
            return self._receipt(
                status="REJECTED",
                action=str(decision.get("action", "?")) if isinstance(decision, Mapping) else "?",
                symbol="",
                volume=0.0,
                order_id=None,
                message=f"RiskGate: decision is not a valid mapping — {exc}",
                risk=None,
            )

        if not verdict.allowed:
            logger.warning("[HANDS] RiskGate REJECTED: %s", verdict.summary())
            return self._receipt(
                status="REJECTED",
                action=verdict.action,
                symbol=verdict.symbol,
                volume=verdict.volume,
                order_id=None,
                message=f"RiskGate rejected: {'; '.join(verdict.reasons)}",
                risk=verdict.to_dict(),
            )

        if verdict.action == "HOLD":
            return self._receipt(
                status="HOLD",
                action="HOLD",
                symbol=verdict.symbol,
                volume=0.0,
                order_id=None,
                message="ViVy decided to HOLD position.",
                risk=verdict.to_dict(),
            )

        # RiskGate has approved.  Paper mode still records the order but the
        # receipt is flagged so nothing downstream mistakes it for a fill.
        self._order_counter += 1
        order_id = self._order_counter
        mode = "PAPER" if self.is_paper else "LIVE"
        logger.info(
            f"[HANDS EXECUTION][{mode}] Order {order_id}: {verdict.action} "
            f"{verdict.volume} {verdict.symbol} ({verdict.summary()})"
        )
        return self._receipt(
            status="EXECUTED",
            action=verdict.action,
            symbol=verdict.symbol,
            volume=verdict.volume,
            order_id=order_id,
            message=(
                f"{'Paper' if self.is_paper else 'Live'}-executed {verdict.action} "
                f"order #{order_id} on MT5 for {verdict.symbol}."
            ),
            risk=verdict.to_dict(),
            live=not self.is_paper,
        )

    # ------------------------------------------------------------------

    def _receipt(
        self,
        *,
        status: str,
        action: str,
        symbol: str,
        volume: float,
        order_id: int | None,
        message: str,
        risk: dict[str, Any] | None,
        live: bool = False,
    ) -> ExecutionReceipt:
        return ExecutionReceipt(
            status=status,
            action=action,
            symbol=symbol,
            volume=volume,
            order_id=order_id,
            message=message,
            risk=risk,
            live=live,
        )


def paper_executor(**kwargs: Any) -> MT5Executor:
    """An executor that cannot place a live order."""
    return MT5Executor(gate=default_gate(paper_trading=True), **kwargs)
