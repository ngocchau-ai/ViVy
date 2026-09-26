"""
ViVy Structured Reasoning & Inference Engine
Generates transparent, structured JSON decisions for market actions.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from vivy.core.model_loader import LocalModelEngine
from vivy.core.prompts import get_system_prompt

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

    def __init__(self, engine: LocalModelEngine, system_prompt: str | None = None):
        self.engine = engine
        self.system_prompt = system_prompt or get_system_prompt("trading")

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

        return DecisionResult(
            thought=raw_json.get("thought", "No reasoning provided"),
            action=raw_json.get("action", "HOLD").upper(),
            symbol=raw_json.get("symbol", market_data.get("symbol", "UNKNOWN")),
            volume=float(raw_json.get("volume", 0.01)),
            stop_loss=float(raw_json.get("stop_loss", 0.0)),
            take_profit=float(raw_json.get("take_profit", 0.0)),
            confidence=float(raw_json.get("confidence", 0.5)),
            raw_response=raw_json
        )
