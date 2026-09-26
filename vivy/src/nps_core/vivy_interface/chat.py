"""ViVy Interactive Chat Session Manager.

Maintains multi-turn chat sessions with vision and bilingual support.
Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nps_core.vivy_interface.reasoning_engine import (
    MultimodalResponse,
    ViVyMultimodalEngine,
)
from nps_core.vivy_interface.vision import ImagePayload, VisionEncoder

__all__ = [
    "ChatMessage",
    "ViVyChatSession",
]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Frozen value object capturing a message in ViVy chat session."""

    role: str
    content: str
    image: ImagePayload | None
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "image": self.image.to_dict() if self.image else None,
            "timestamp": self.timestamp,
        }


class ViVyChatSession:
    """Multi-turn interactive chat session with ViVy."""

    def __init__(self, session_id: str = "SESSION-VIVY-001") -> None:
        self.session_id = session_id
        self._history: list[ChatMessage] = []

    def send_message(
        self,
        text: str,
        image_path: str | None = None,
        timestamp: str = "2026-07-25T10:42:00Z",
    ) -> MultimodalResponse:
        """Send user message (with optional image) and return ViVy response."""
        image_payload = VisionEncoder.from_file(image_path) if image_path else None

        # Record user message
        user_msg = ChatMessage(
            role="user",
            content=text,
            image=image_payload,
            timestamp=timestamp,
        )
        self._history.append(user_msg)

        # Process through ViVy Multimodal Engine
        history_dicts = [m.to_dict() for m in self._history]
        response = ViVyMultimodalEngine.process(text, image=image_payload, history=history_dicts)

        # Record assistant response
        assistant_msg = ChatMessage(
            role="assistant",
            content=response.response_text,
            image=None,
            timestamp=timestamp,
        )
        self._history.append(assistant_msg)

        return response

    def get_history(self) -> tuple[ChatMessage, ...]:
        """Get copy of conversation history."""
        return tuple(self._history)
