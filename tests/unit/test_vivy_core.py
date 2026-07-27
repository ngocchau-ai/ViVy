"""
Unit tests for ViVy Core Local AI Engine & Inference System.
"""

import pytest
from vivy.core.model_loader import LocalModelLoader, ModelBackend, ModelConfig, MockLocalEngine
from vivy.core.inference import ViVyInferenceEngine
from vivy.core.prompts import get_system_prompt, VIVY_TRADING_SYSTEM_PROMPT


def test_model_loader_mock_engine():
    config = ModelConfig(backend=ModelBackend.MOCK, model_path_or_name="vivy-test")
    engine = LocalModelLoader.load_engine(config)
    assert isinstance(engine, MockLocalEngine)

    output = engine.generate("Analyze GOLD market context")
    assert "thought" in output
    assert "action" in output


def test_isolated_prompts():
    prompt = get_system_prompt("trading")
    assert "91sViVy" in prompt
    assert "Eyes & Hands Philosophy" in prompt
    assert prompt == VIVY_TRADING_SYSTEM_PROMPT


def test_inference_engine_reason_and_decide():
    config = ModelConfig(backend=ModelBackend.MOCK, model_path_or_name="vivy-test")
    engine = LocalModelLoader.load_engine(config)
    inference = ViVyInferenceEngine(engine)

    market_data = {
        "symbol": "GOLD",
        "current_price": 2385.50,
        "indicators": {"rsi_14": 65.4, "trend": "BULLISH"}
    }

    result = inference.reason_and_decide(market_data=market_data, past_lessons=["Past GOLD trade +$120"])
    
    assert result.action in ("BUY", "SELL", "MODIFY", "CLOSE", "HOLD")
    assert result.symbol == "GOLD"
    assert result.confidence >= 0.0
    assert "ViVy Local Brain" in result.thought
