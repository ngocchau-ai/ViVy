"""Unit tests for ViVy Multimodal Bilingual Chat Interface.

[REWRITTEN TO SPEC 29/09/2026 · WP-5 / O-12 / F-F01…F-F03 / Gate 9]
====================================================================

Receipt for the rewrite (plan hard rule #4 — "Không sửa test để khớp code;
test sai thì sửa theo đặc tả, có receipt"):

The previous version of this file **pinned the fabrication** the review
flagged.  It asserted, against a path that does not exist:

    payload = VisionEncoder.from_file("test_chart.png")
    assert payload.width == 1024

and

    session.send_message("Analyze this visual input", image_path="sample.jpg")

Both paths were imaginary.  The test passed because ``from_file`` invented a
1024x1024 payload for any string.  That is exactly finding F-F01.

The old assertion is not weakened — it is **replaced by stronger ones**: the
missing path must now *raise*, the resolution must be *unknown* rather than a
fake 1024, and the simulated opt-in must be *visibly flagged* so no summary
can dress it up as perception.  Nothing here accepts a fabricated number.
"""

from __future__ import annotations

import pytest

from nps_core.vivy_interface import (
    ImagePayload,
    VisionEncoder,
    ViVyChatSession,
    ViVyMultimodalEngine,
)
from nps_core.vivy_interface.vision import ImagePayload as _ImagePayload

# ---------------------------------------------------------------------------
# F-F01 — a missing file must not produce a payload
# ---------------------------------------------------------------------------


def test_missing_file_raises_by_default() -> None:
    """[REPLACED 29/09/2026 · WP-5 / F-F01] was: silently fabricate a payload."""
    with pytest.raises(FileNotFoundError):
        VisionEncoder.from_file("test_chart.png")  # still an imaginary path


def test_missing_file_can_opt_into_a_flagged_simulation() -> None:
    payload = VisionEncoder.from_file("test_chart.png", allow_simulated=True)
    assert isinstance(payload, ImagePayload)
    assert payload.image_id.startswith("IMG-VIVY-")
    assert payload.simulated is True
    assert payload.resolution_known is False
    assert payload.width is None and payload.height is None
    # The hash is of the path string, and the payload says so.
    assert payload.is_content_hash is False


def test_real_file_hashes_bytes_and_still_reports_no_resolution(tmp_path) -> None:
    """A real file gets a real content hash — but we still do not decode it."""
    f = tmp_path / "chart.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\nNOT-A-REAL-PNG-BUT-REAL-BYTES")

    payload = VisionEncoder.from_file(f)
    assert payload.simulated is False
    assert payload.is_content_hash is True
    # The old test asserted width == 1024 here.  Truth: unknown.
    assert payload.width is None
    assert payload.height is None
    assert payload.resolution_known is False
    # Different bytes must give a different hash (the path-hash bug did not).
    f.write_bytes(b"\x89PNG\r\n\x1a\nDIFFERENT-BYTES")
    other = VisionEncoder.from_file(f)
    assert other.content_hash != payload.content_hash


def test_resolution_is_never_invented_in_the_summary() -> None:
    payload = VisionEncoder.from_file("nope.jpg", allow_simulated=True)
    summary = VisionEncoder.encode_visual_summary(payload)
    assert "1024" not in summary
    assert "UNKNOWN (not decoded)" in summary
    assert "SIMULATED" in summary
    assert "mime inferred from extension" in summary


# ---------------------------------------------------------------------------
# F-F02 — the reply must not claim perception or a model call
# ---------------------------------------------------------------------------


def test_language_detection() -> None:
    assert ViVyMultimodalEngine.detect_language("Chào ViVy, bạn đã có thể giao tiếp chưa?") == "vi"
    assert ViVyMultimodalEngine.detect_language("Hello ViVy, can we talk in English?") == "en"


def test_response_never_claims_the_image_was_processed() -> None:
    """[REPLACED 29/09/2026 · WP-5 / F-F02] was: "ViVy has processed the image"."""
    payload = VisionEncoder.from_file("x.jpg", allow_simulated=True)

    en = ViVyMultimodalEngine.process("Analyze this", image=payload)
    assert "has processed the image" not in en.response_text
    assert "ready to assist you" not in en.response_text
    assert "did NOT decode" in en.response_text
    assert en.model_call_made is False
    assert en.pixels_decoded is False
    assert en.from_template is True

    vi = ViVyMultimodalEngine.process("Phân tích cái này", image=payload)
    assert "nhận diện được hình ảnh" not in vi.response_text
    assert "CHƯA giải mã" in vi.response_text
    assert vi.model_call_made is False


def test_response_without_image_does_not_claim_vision_capability() -> None:
    en = ViVyMultimodalEngine.process("Hello")
    assert "Vision capability" not in en.response_text
    assert en.visual_summary is None

    vi = ViVyMultimodalEngine.process("Chào bạn")
    assert "phân tích thị giác (Vision)" not in vi.response_text


def test_thought_chain_admits_nothing_was_extracted() -> None:
    payload = VisionEncoder.from_file("x.jpg", allow_simulated=True)
    res = ViVyMultimodalEngine.process("hi", image=payload)
    joined = " ".join(res.thought_chain)
    assert "KHÔNG được giải mã" in joined or "were NOT decoded" in joined
    assert "Fusing visual features" not in joined
    assert "Kết hợp đặc trưng thị giác" not in joined
    assert "No model call" in joined or "Không gọi model" in joined


# ---------------------------------------------------------------------------
# chat session — blast radius for from_file's new contract
# ---------------------------------------------------------------------------


def test_vivy_chat_session_multimodal() -> None:
    session = ViVyChatSession()
    resp_vi = session.send_message("Chào ViVy!")
    assert resp_vi.detected_language == "vi"
    assert "ViVy" in resp_vi.response_text
    assert resp_vi.model_call_made is False

    # [REPLACED 29/09/2026] was: image_path="sample.jpg" against a fake path,
    # which silently produced a 1024x1024 payload.  Now the imaginary path is
    # an explicit, flagged simulation.
    resp_en = session.send_message(
        "Analyze this visual input", image_path="sample.jpg", allow_simulated=True
    )
    assert resp_en.detected_language == "en"
    assert resp_en.visual_summary is not None
    assert "SIMULATED" in resp_en.visual_summary
    assert len(session.get_history()) == 4

    stored = session.get_history()[2]  # the second *user* message carried the image
    assert stored.image is not None
    assert stored.image.simulated is True


def test_chat_session_rejects_a_missing_image_by_default() -> None:
    session = ViVyChatSession()
    with pytest.raises(FileNotFoundError):
        session.send_message("look at this", image_path="ghost.jpg")


def test_payload_to_dict_carries_the_honesty_flags() -> None:
    payload: ImagePayload = VisionEncoder.from_file("ghost.png", allow_simulated=True)
    d = payload.to_dict()
    assert d["simulated"] is True
    assert d["resolution_known"] is False
    assert d["mime_source"] == "extension"
    assert d["width"] is None and d["height"] is None
    assert _ImagePayload is ImagePayload
