"""Unit tests for ViVy Multimodal Bilingual Chat Interface."""

from __future__ import annotations

from nps_core.vivy_interface import (
    ImagePayload,
    ViVyChatSession,
    ViVyMultimodalEngine,
    VisionEncoder,
)


def test_vision_encoder() -> None:
    payload = VisionEncoder.from_file("test_chart.png")
    assert isinstance(payload, ImagePayload)
    assert payload.image_id.startswith("IMG-VIVY-")
    assert payload.width == 1024


def test_language_detection() -> None:
    assert ViVyMultimodalEngine.detect_language("Chào ViVy, bạn đã có thể giao tiếp chưa?") == "vi"
    assert ViVyMultimodalEngine.detect_language("Hello ViVy, can we talk in English?") == "en"


def test_vivy_chat_session_multimodal() -> None:
    session = ViVyChatSession()
    resp_vi = session.send_message("Chào ViVy!")
    assert resp_vi.detected_language == "vi"
    assert "ViVy" in resp_vi.response_text

    resp_en = session.send_message("Analyze this visual input", image_path="sample.jpg")
    assert resp_en.detected_language == "en"
    assert resp_en.visual_summary is not None
    assert len(session.get_history()) == 4
