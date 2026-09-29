"""
Unit tests for ViVy Core Local AI Engine & Inference System.

Note (29/09/2026, WP-1/O-01): ``MockLocalEngine`` is now gated behind an explicit
opt-in.  These tests pass ``allow_mock=True`` because a deterministic engine is
exactly what a unit test needs.  The production ban is asserted in
``test_mock_engine_banned_without_opt_in``.
"""

import pytest

from vivy.core.inference import ViVyInferenceEngine
from vivy.core.model_loader import (
    EngineUnavailableError,
    LocalModelLoader,
    MockLocalEngine,
    ModelBackend,
    ModelConfig,
    UnsupportedBackendError,
)
from vivy.core.prompts import VIVY_TRADING_SYSTEM_PROMPT, get_system_prompt


def test_model_loader_mock_engine():
    config = ModelConfig(backend=ModelBackend.MOCK, model_path_or_name="vivy-test")
    engine = LocalModelLoader.load_engine(config, allow_mock=True)
    assert isinstance(engine, MockLocalEngine)

    output = engine.generate("Analyze GOLD market context")
    assert "thought" in output
    assert "action" in output


def test_mock_engine_banned_without_opt_in() -> None:
    """WP-1: a production load must not reach the canned BUY/GOLD double."""
    config = ModelConfig(backend=ModelBackend.MOCK, model_path_or_name="vivy-test")
    with pytest.raises(EngineUnavailableError):
        LocalModelLoader.load_engine(config)


def test_unknown_backend_raises_instead_of_mock() -> None:
    """WP-1: an unrecognised backend used to return MockLocalEngine."""
    config = ModelConfig(backend="not-a-backend", model_path_or_name="x")  # type: ignore[arg-type]
    with pytest.raises(UnsupportedBackendError):
        LocalModelLoader.load_engine(config, allow_mock=True)


def test_isolated_prompts():
    """The live trading prompt must tell the model about RiskGate.

    [REPLACED 29/09/2026 · WP-4 / D-3 / ADR-008] this test used to pin the
    header ``"Eyes & Hands Philosophy"`` and, indirectly, the line
    ``"CẤM GÁC CỔNG LẬP TRÌNH: No hardcoded filters … exist in code"``.  The
    project owner deliberately replaced that philosophy (D-3) after the review
    measured 0/30 adversarial orders stopped.

    Per plan hard rule #4 the test is rewritten **to the spec**, and the new
    assertions are stronger than the old ones: they require the prompt to name
    the gate AND forbid the old lie that no check exists.
    """
    prompt = get_system_prompt("trading")
    assert "91sViVy" in prompt
    assert prompt == VIVY_TRADING_SYSTEM_PROMPT

    # The model must be told a check exists and that it is an ally.
    assert "RiskGate" in prompt
    assert "ally, not a gatekeeper" in prompt
    assert "ALWAYS refuse" in prompt or "WILL refuse" in prompt

    # The old lie must not come back.
    assert "No hardcoded filters" not in prompt
    assert "CẤM GÁC CỔNG LẬP TRÌNH" not in prompt
    assert "originate 100% from your intelligence" not in prompt


def test_inference_engine_reason_and_decide():
    config = ModelConfig(backend=ModelBackend.MOCK, model_path_or_name="vivy-test")
    engine = LocalModelLoader.load_engine(config, allow_mock=True)
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
