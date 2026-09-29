"""
ViVy Structured Reasoning & Inference Engine
Generates transparent, structured JSON decisions for market actions.

[REPLACED 29/09/2026 · WP-4 / G-02] numeric fields used to be read with a bare
``float(...)`` and a silent default (``volume`` → ``0.01``, ``stop_loss`` →
``0.0``).  Inventing a Stop Loss of ``0.0`` is precisely the hazard G-02
describes, and ``float("nan")`` parsed cleanly into a decision.  Parsing is now
strict (``vivy.hands.risk_gate.parse_finite_float``): missing, non-numeric, NaN
or Inf fields raise instead of being papered over.  RiskGate is the second line
of defence and independently refuses anything that slips through.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from vivy.core.model_loader import LocalModelEngine
from vivy.core.prompts import get_system_prompt
from vivy.hands.risk_gate import parse_finite_float

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    thought: str
    action: str
    symbol: str
    volume: float
    stop_loss: float
    take_profit: float
    confidence: float
    raw_response: dict[str, Any]


class ViVyInferenceEngine:
    """High-level reasoning & inference engine for 91sViVy."""

    def __init__(
        self,
        engine: LocalModelEngine,
        system_prompt: str | None = None,
        *,
        require_sl_tp: bool = True,
    ):
        self.engine = engine
        self.system_prompt = system_prompt or get_system_prompt("trading")
        self._require_sl_tp = require_sl_tp
        """Entries must name their SL/TP.  Mirrors ``RiskLimits.require_sl_tp``."""

    def reason_and_decide(
        self,
        market_data: dict[str, Any],
        past_lessons: list[str] | None = None
    ) -> DecisionResult:
        """Constructs prompt from market data + lessons, executes inference, returns structured decision."""

        prompt_parts = ["### REAL-TIME MARKET CONTEXT:"]
        prompt_parts.append(json.dumps(market_data, indent=2))

        if past_lessons:
            prompt_parts.append("\n### PAST LESSONS & RECALL MEMORY:")
            for idx, lesson in enumerate(past_lessons, 1):
                prompt_parts.append(f"{idx}. {lesson}")

        prompt_parts.append("\n### YOUR TASK:")
        prompt_parts.append("Analyze the context above and output your final JSON decision.")

        user_prompt = "\n".join(prompt_parts)

        raw_json = self.engine.generate_json(user_prompt, system_prompt=self.system_prompt)

        # Strict parse (G-02): nothing non-finite reaches a DecisionResult, and
        # an entry order must actually specify its numbers — no invented
        # ``volume=0.01`` / ``stop_loss=0.0``.  HOLD carries no volume/level by
        # definition, so absence is fine there.
        action = str(raw_json.get("action", "HOLD")).strip().upper()
        symbol = str(
            raw_json.get("symbol", market_data.get("symbol", "UNKNOWN"))
        ).strip().upper()

        is_entry = action in ("BUY", "SELL")

        def _num(key: str, required: bool) -> float:
            raw = raw_json.get(key)
            if raw is None:
                if required:
                    raise ValueError(f"{key}: entry order must specify {key} (got nothing)")
                return 0.0
            return parse_finite_float(raw, field_name=key)

        volume = _num("volume", required=is_entry)
        stop_loss = _num("stop_loss", required=is_entry and self._require_sl_tp)
        take_profit = _num("take_profit", required=is_entry and self._require_sl_tp)

        raw_confidence = raw_json.get("confidence")
        if raw_confidence is None:
            logger.warning("decision did not supply confidence; recording 0.5 and flagging it")
            confidence = 0.5
        else:
            confidence = parse_finite_float(raw_confidence, field_name="confidence")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"confidence out of range [0, 1]: {confidence}")

        return DecisionResult(
            thought=raw_json.get("thought", "No reasoning provided"),
            action=action,
            symbol=symbol,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            raw_response=raw_json,
        )
