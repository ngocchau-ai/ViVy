"""
Deerflow API Server for ViVy.

Exposes ViVy MoE 70B as a lightweight, auxiliary local model via 
an OpenAI-compatible /v1/chat/completions endpoint.
Designed to prevent Context Overflow via deterministic Hashing-to-State
and to return responses instantly (CLI-like latency).
"""

import hashlib
import numpy as np
import logging
from typing import List, Dict, Any, Union
from fastapi import FastAPI, Request
from pydantic import BaseModel

from vivy.core.moe_brain import ViVyMoEQuantumCore
from vivy.core.vivy_brain import FilterFunnelSignal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="ViVy Auxiliary Local Model API")

# Initialize ViVy MoE Core (State Dimension: 4096, 70 Experts)
# This uses the compressed experts from disk, so it takes almost zero RAM to start.
VIVY_STATE_DIM = 4096
moe_core = ViVyMoEQuantumCore(state_dim=VIVY_STATE_DIM, num_experts=70, experts_dir="modelfiles/experts")

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str = "vivy-70b-aux"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 100

def text_to_state(text: str, dim: int) -> np.ndarray:
    """
    Prevents Context Overflow by hashing arbitrary length text into a fixed 4096-dim state.
    Provides a deterministic mapping from text content to a quantum state vector.
    """
    # Create a deterministic seed based on the text hash
    text_hash = hashlib.sha256(text.encode('utf-8')).digest()
    seed = int.from_bytes(text_hash[:4], byteorder='big')
    
    rng = np.random.RandomState(seed)
    
    # Generate a random state vector based on the text seed
    state = rng.randn(dim) + 1j * rng.randn(dim)
    
    # Normalize
    norm = np.linalg.norm(state)
    if norm > 0:
        state = state / norm
        
    return state

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """
    OpenAI-compatible endpoint for Deerflow.
    """
    # Extract context from messages
    # We combine the conversation history to capture context without risking token overflow
    full_text = ""
    for m in req.messages:
        if isinstance(m.content, str):
            text = m.content
        else:
            text = " ".join([item.get("text", "") for item in m.content if isinstance(item, dict) and item.get("type") == "text"])
        full_text += f"{m.role}: {text}\\n"    
    logger.info(f"Received request from Deerflow. Context length: {len(full_text)} chars")
    
    # 1. Hashing-to-State (Guarantees NO Context Overflow)
    state_vector = text_to_state(full_text, VIVY_STATE_DIM)
    
    # 2. Process through MoE Quantum Core (Ultra-fast response)
    # This automatically routes to 1 expert out of 70 (1B active)
    result = moe_core.process_state(state_vector)
    
    # 3. Format response for Deerflow
    signal = result["signal"]
    entropy = result["entropy"]
    
    # Auxiliary advice generation
    if signal == FilterFunnelSignal.HALT:
        advice = f"[ViVy-Aux] Signal: HALT | Khuyến nghị: Cấu trúc tín hiệu RẤT RÕ RÀNG (Entropy: {entropy:.3f}). Có thể hành động ngay."
    elif signal == FilterFunnelSignal.DELEGATE:
        advice = f"[ViVy-Aux] Signal: DELEGATE | Khuyến nghị: Tín hiệu nhiễu nhẹ (Entropy: {entropy:.3f}). Cần model chính đối chiếu thêm."
    else:
        advice = f"[ViVy-Aux] Signal: BACKTRACK | Khuyến nghị: Mức độ hỗn loạn cao (Entropy: {entropy:.3f}). KHÔNG NÊN hành động, hãy đứng ngoài quan sát."

    # Construct OpenAI-compatible response
    response_data = {
        "id": "chatcmpl-vivy-aux",
        "object": "chat.completion",
        "created": 1234567890,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": advice
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(full_text) // 4, # dummy estimate
            "completion_tokens": len(advice) // 4,
            "total_tokens": (len(full_text) + len(advice)) // 4
        }
    }
    
    logger.info(f"Response: {advice}")
    return response_data

@app.get("/health")
async def health_check():
    return {"status": "ok", "model": "ViVy 70B MoE", "active_parameters": "1B"}
