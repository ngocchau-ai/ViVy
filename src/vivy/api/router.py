"""
FastAPI Main Application Router for 91sViVy AI Engine & Agent System.
"""

from typing import Any, Dict
from vivy.core.inference import ViVyInferenceEngine
from vivy.core.model_loader import LocalModelEngine, LocalModelLoader, ModelBackend, ModelConfig
from vivy.eyes.mt5_collector import MT5DataCollector
from vivy.hands.mt5_executor import MT5Executor
from vivy.memory.vector_store import ViVyVectorMemory

# Initialize core services
model_config = ModelConfig(backend=ModelBackend.MOCK, model_path_or_name="vivy-mock")
local_engine = LocalModelLoader.load_engine(model_config)
inference_engine = ViVyInferenceEngine(local_engine)

collector = MT5DataCollector(symbol="GOLD")
executor = MT5Executor(connected=True)
memory = ViVyVectorMemory()


def handle_health_check() -> Dict[str, Any]:
    return {
        "status": "online",
        "system": "91sViVy Local AI Engine",
        "version": "2.0.0",
        "architecture": "Eyes & Hands (No Gatekeepers)"
    }


def handle_trade_cycle(symbol: str = "GOLD") -> Dict[str, Any]:
    """Runs a complete autonomous reasoning & execution cycle for ViVy."""

    # 1. Mắt (Eyes): Collect market context
    market_snapshot = collector.get_market_snapshot()

    # 2. Memory: Retrieve past lessons
    past_lessons = memory.query_lessons(symbol=symbol)

    # 3. Central Brain (ViVy): Reason and decide
    decision = inference_engine.reason_and_decide(market_snapshot, past_lessons)

    # 4. Tay (Hands): Execute raw decision
    receipt = executor.execute_decision(decision.raw_response)

    return {
        "market_snapshot": market_snapshot,
        "past_lessons_count": len(past_lessons),
        "vivy_thought": decision.thought,
        "action_decision": decision.action,
        "execution_receipt": {
            "status": receipt.status,
            "order_id": receipt.order_id,
            "message": receipt.message
        }
    }
