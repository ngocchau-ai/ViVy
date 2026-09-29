"""
FastAPI Main Application Router for 91sViVy AI Engine & Agent System.
"""

import os
from typing import Any

from vivy.core.inference import ViVyInferenceEngine
from vivy.core.model_loader import (
    LocalModelEngine,
    LocalModelLoader,
    ModelBackend,
    ModelConfig,
    UnsupportedBackendError,
)
from vivy.eyes.mt5_collector import MT5DataCollector
from vivy.hands.mt5_executor import MT5Executor
from vivy.memory.vector_store import ViVyVectorMemory


def _load_production_engine() -> LocalModelEngine:
    """Resolve the trade-cycle engine from config — never silently from mock.

    [REPLACED 29/09/2026] the old module-level body hardcoded
    ``ModelBackend.MOCK`` and constructed the engine at import, so the live
    trade cycle always ran on a canned BUY/GOLD answer (F-A07 / G-02).
    """
    backend_name = os.getenv("VIVY_MODEL_BACKEND", "ollama_api").strip().lower()
    model_name = os.getenv("VIVY_MODEL_NAME", "gemma4:e4b")
    try:
        backend = ModelBackend(backend_name)
    except ValueError as exc:
        raise UnsupportedBackendError(
            f"VIVY_MODEL_BACKEND={backend_name!r} is not a known backend; "
            f"expected one of {', '.join(b.value for b in ModelBackend)}"
        ) from exc
    config = ModelConfig(backend=backend, model_path_or_name=model_name)
    # Mock is refused here unless VIVY_ALLOW_MOCK_ENGINE is deliberately set.
    return LocalModelLoader.load_engine(config)


# Initialize core services
local_engine = _load_production_engine()
inference_engine = ViVyInferenceEngine(local_engine)

collector = MT5DataCollector(symbol="GOLD")
executor = MT5Executor(connected=True)
memory = ViVyVectorMemory()


def handle_health_check() -> dict[str, Any]:
    return {
        "status": "online",
        "system": "91sViVy Local AI Engine",
        "version": "2.0.0",
        # [REPLACED 29/09/2026 · WP-4 / D-3 / ADR-008] prior value
        # "Eyes & Hands (No Gatekeepers)" — the gatekeeper ban was deliberately
        # replaced by a fail-closed RiskGate (safety ally, not strategy filter).
        "architecture": "Eyes & Hands + RiskGate",
        "risk_gate": executor.gate.limits.describe(),
        "paper_trading": executor.is_paper,
    }


def handle_trade_cycle(symbol: str = "GOLD") -> dict[str, Any]:
    """Runs a complete autonomous reasoning & execution cycle for ViVy."""

    # 1. Mắt (Eyes): Collect market context
    market_snapshot = collector.get_market_snapshot()

    # 2. Memory: Retrieve past lessons
    past_lessons = memory.query_lessons(symbol=symbol)

    # 3. Central Brain (ViVy): Reason and decide
    decision = inference_engine.reason_and_decide(market_snapshot, past_lessons)

    # 4. Tay (Hands): RiskGate then execute.  The reference price comes from
    #    the same snapshot the model just reasoned over — without it the gate
    #    must reject an entry rather than guess (ADR-008, fail-closed).
    receipt = executor.execute_decision(
        decision.raw_response,
        price=market_snapshot.get("current_price"),
    )

    return {
        "market_snapshot": market_snapshot,
        "past_lessons_count": len(past_lessons),
        "vivy_thought": decision.thought,
        "action_decision": decision.action,
        "execution_receipt": {
            "status": receipt.status,
            "order_id": receipt.order_id,
            "message": receipt.message,
            "live": receipt.live,
            "risk": receipt.risk,
        }
    }
