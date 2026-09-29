"""ViVy Multimodal Bilingual Reasoning Engine.

Claims bilingual English & Vietnamese reasoning over text and image **metadata**.
Standard-library only.

[REPLACED 29/09/2026 · WP-5 / O-12 / F-F02] — honest interfaces
=================================================================

WHAT THIS MODULE USED TO CLAIM
    With an image attached it answered, in both languages: *"ViVy has processed
    the image and is ready to assist you!"* / *"ViVy nhận diện được hình ảnh và
    sẵn sàng giải đáp chi tiết!"*  Its chain-of-thought said it was
    *"Fusing visual features with ViVy multimodal knowledge base"*.  Without an
    image it claimed the model is *"equipped with Vision capability"*.

    None of that is true.  This module never decodes a pixel, never calls a
    model, and never extracts a visual feature.  The whole response is a
    bilingual template built from a filename.  The review called it F-F02.

WHAT IT ACTUALLY DOES NOW
    * Reports the **metadata receipt** it was handed and says, plainly, that
      pixels were not decoded and no model was called.
    * Drops the "fusing visual features" / "Vision capability" language from
      the live chain-of-thought and response strings.
    * Still detects language, still formats a bilingual reply, still returns a
      ``MultimodalResponse`` — the shape is unchanged; only the claims are.

The old claim strings are preserved verbatim in the **[ISOLATED]** block near
the bottom of this file (cô lập, không xóa).  See ``docs/CAPABILITY_LEDGER.md``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from nps_core.vivy_interface.vision import ImagePayload, VisionEncoder

__all__ = [
    "MultimodalResponse",
    "ViVyMultimodalEngine",
]


@dataclass(frozen=True, slots=True)
class MultimodalResponse:
    """Frozen value object holding ViVy multimodal response."""

    detected_language: str
    thought_chain: tuple[str, ...]
    visual_summary: str | None
    response_text: str

    #: [ADDED 29/09/2026 · WP-5] True when this reply came from a template
    #: and no model call took place.  A caller must not mistake this for
    #: model output.  See ``docs/CAPABILITY_LEDGER.md`` row "ViVyMultimodalEngine".
    from_template: bool = True
    model_call_made: bool = False
    pixels_decoded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_language": self.detected_language,
            "thought_chain": list(self.thought_chain),
            "visual_summary": self.visual_summary,
            "response_text": self.response_text,
            "from_template": self.from_template,
            "model_call_made": self.model_call_made,
            "pixels_decoded": self.pixels_decoded,
        }


class ViVyMultimodalEngine:
    """Bilingual template engine over text + image **metadata**.

    Despite the historical name this is not a reasoning engine and it is not
    multimodal in the perception sense.  It is a deterministic formatter.
    """

    VIETNAMESE_KEYWORDS = (
        "bạn", "chào", "vy", "vivy", "cho", "tôi", "mình", "suy", "luận",
        "thị", "giác", "hình", "ảnh", "tiếng", "việt", "anh", "được", "chưa",
        "hãy", "giao", "tiếp", "này", "là", "gì"
    )

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detect whether input is Vietnamese or English."""
        lower_text = text.lower()
        # Count vietnamese accent marks or keywords
        has_accents = bool(re.search(r"[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", lower_text))
        if has_accents:
            return "vi"

        match_count = sum(1 for kw in cls.VIETNAMESE_KEYWORDS if kw in lower_text.split())
        return "vi" if match_count >= 2 else "en"

    @classmethod
    def process(
        self,
        prompt: str,
        image: ImagePayload | None = None,
        history: Sequence[dict[str, Any]] = (),
    ) -> MultimodalResponse:
        """Format a bilingual reply over the prompt and any image *metadata*.

        This makes **no model call**.  The returned ``MultimodalResponse`` is
        template output and says so in its flags.
        """
        del history  # Accepted for API compatibility; not consulted.
        lang = self.detect_language(prompt)
        visual_summary = VisionEncoder.encode_visual_summary(image) if image else None

        thought_chain: list[str] = []

        if lang == "vi":
            thought_chain.append(f"1. Phân tích truy vấn tiếng Việt: '{prompt}'")
            if visual_summary:
                thought_chain.append(f"2. Tiếp nhận **siêu dữ liệu** đầu vào thị giác: {visual_summary}")
                thought_chain.append(
                    "3. Ghi nhận: pixel KHÔNG được giải mã, không có đặc trưng thị giác nào được trích xuất."
                )
            else:
                thought_chain.append("2. Không có đầu vào hình ảnh — chỉ dùng văn bản.")
            thought_chain.append("4. Sinh phản hồi từ mẫu cố định (template). Không gọi model.")
            response = self._vi_response(image)
        else:
            thought_chain.append(f"1. Analyzing English query: '{prompt}'")
            if visual_summary:
                thought_chain.append(f"2. Accepted image **metadata** payload: {visual_summary}")
                thought_chain.append(
                    "3. Note: pixels were NOT decoded, no visual feature was extracted."
                )
            else:
                thought_chain.append("2. No image input — text only.")
            thought_chain.append("4. Formulating output from a fixed template. No model call.")
            response = self._en_response(image)

        return MultimodalResponse(
            detected_language=lang,
            thought_chain=tuple(thought_chain),
            visual_summary=visual_summary,
            response_text=response,
            from_template=True,
            model_call_made=False,
            pixels_decoded=False,
        )

    # --- live response templates (29/09/2026) -----------------------------
    #
    # These say what actually happened.  The pre-WP-5 strings that claimed
    # image recognition are archived at the bottom of this file.

    @staticmethod
    def _vi_response(image: ImagePayload | None) -> str:
        if image is not None:
            origin = "SIMULATED" if image.simulated else "đã hash theo byte"
            return (
                f"Chào bạn! ViVy đã nhận được **siêu dữ liệu** của hình ảnh `{image.image_id}` "
                f"({image.mime_type}, nguồn: {origin}). "
                f"ViVy CHƯA giải mã pixel của ảnh này — chỉ ghi nhận đường dẫn và hash. "
                f"Muốn ViVy phân tích nội dung ảnh, cần một model thị giác thật; hiện chưa có."
            )
        return (
            "Chào bạn! Đây là phản hồi từ mẫu cố định của giao diện ViVy, "
            "không phải đầu ra của model. "
            "ViVy chưa có năng lực phân tích thị giác trong bản này — "
            "bạn có thể gửi câu hỏi văn bản, hoặc đính kèm ảnh để ViVy ghi nhận siêu dữ liệu."
        )

    @staticmethod
    def _en_response(image: ImagePayload | None) -> str:
        if image is not None:
            origin = "SIMULATED" if image.simulated else "bytes-hashed"
            return (
                f"Hello! ViVy received the image **metadata** `{image.image_id}` "
                f"({image.mime_type}, provenance: {origin}). "
                f"ViVy did NOT decode this image's pixels — only the path and hash were recorded. "
                f"Analysing the picture itself needs a real vision model; this build has none."
            )
        return (
            "Hello! This reply comes from ViVy's fixed interface template, "
            "not from a model. "
            "This build has no vision-analysis capability — "
            "you can ask a text question, or attach an image so ViVy can record its metadata."
        )


# [ISOLATED 29/09/2026 · WP-5 / F-F02] — preserved verbatim, not deleted.
#
# These are the pre-WP-5 claim strings.  They must never be restored to the
# live templates above: they assert image recognition and a vision capability
# that this module has never had.  Kept for the changelog / review trail.
#
# VI image branch (was reasoning_engine.py:85-90):
#     f"Chào bạn! ViVy đã nhận được hình ảnh `{image.image_id}` ({image.mime_type}). "
#     f"ViVy là mô hình AI suy luận đa thức (Multimodal Reasoning Model) hỗ trợ song ngữ Anh/Việt. "
#     f"Dựa trên phân tích thị giác và truy vấn của bạn: ViVy nhận diện được hình ảnh và sẵn sàng giải đáp chi tiết!"
#
# EN image branch (was reasoning_engine.py:106-111):
#     f"Hello! ViVy has received the image `{image.image_id}` ({image.mime_type}). "
#     f"ViVy is a multimodal reasoning AI model supporting English and Vietnamese. "
#     f"Based on visual analysis and your prompt, ViVy has processed the image and is ready to assist you!"
#
# VI no-image branch (claimed Vision capability it lacks):
#     "Chào bạn! Bạn đã có thể giao tiếp trực tiếp với ViVy ngay bây giờ! "
#     "ViVy là mô hình AI suy luận có khả năng phân tích thị giác (Vision) và hỗ trợ hoàn hảo song ngữ Anh/Việt. "
#     "Bạn có thể gửi câu hỏi văn bản hoặc đính kèm tệp hình ảnh để ViVy phân tích cho bạn."
#
# EN no-image branch:
#     "Hello! You can now communicate directly with ViVy! "
#     "ViVy is a multimodal reasoning model equipped with Vision capability and full English/Vietnamese bilingual support. "
#     "Feel free to ask questions or attach images for visual analysis."
#
# Chain-of-thought claims removed (no features were ever extracted):
#     VI: "3. Kết hợp đặc trưng thị giác với tri thức ngôn ngữ ViVy."
#     EN: "3. Fusing visual features with ViVy multimodal knowledge base."
#     VI: "2. Tiếp nhận và mã hóa đầu vào thị giác: ..."   ("mã hóa" = encoded)
#     EN: "2. Processing visual input payload: ..."
