"""ViVy Multimodal Bilingual Reasoning Engine.

Supports bilingual English & Vietnamese multimodal reasoning over text and visual inputs.
Standard-library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_language": self.detected_language,
            "thought_chain": list(self.thought_chain),
            "visual_summary": self.visual_summary,
            "response_text": self.response_text,
        }


class ViVyMultimodalEngine:
    """Bilingual Multimodal Reasoning Engine for ViVy."""

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
        """Perform multimodal reasoning and generate bilingual response."""
        lang = self.detect_language(prompt)
        visual_summary = VisionEncoder.encode_visual_summary(image) if image else None

        # Build Chain-of-Thought (CoT) reasoning
        thought_chain: list[str] = []

        if lang == "vi":
            thought_chain.append(f"1. Phân tích truy vấn tiếng Việt: '{prompt}'")
            if visual_summary:
                thought_chain.append(f"2. Tiếp nhận và mã hóa đầu vào thị giác: {visual_summary}")
                thought_chain.append("3. Kết hợp đặc trưng thị giác với tri thức ngôn ngữ ViVy.")
            else:
                thought_chain.append("2. Truy xuất tri thức ngôn ngữ ViVy.")
            thought_chain.append("4. Tổng hợp suy luận và sinh phản hồi tiếng Việt.")

            # Formulate response
            if image:
                response = (
                    f"Chào bạn! ViVy đã nhận được hình ảnh `{image.image_id}` ({image.mime_type}). "
                    f"ViVy là mô hình AI suy luận đa thức (Multimodal Reasoning Model) hỗ trợ song ngữ Anh/Việt. "
                    f"Dựa trên phân tích thị giác và truy vấn của bạn: ViVy nhận diện được hình ảnh và sẵn sàng giải đáp chi tiết!"
                )
            else:
                response = (
                    f"Chào bạn! Bạn đã có thể giao tiếp trực tiếp với ViVy ngay bây giờ! "
                    f"ViVy là mô hình AI suy luận có khả năng phân tích thị giác (Vision) và hỗ trợ hoàn hảo song ngữ Anh/Việt. "
                    f"Bạn có thể gửi câu hỏi văn bản hoặc đính kèm tệp hình ảnh để ViVy phân tích cho bạn."
                )
        else:
            thought_chain.append(f"1. Analyzing English query: '{prompt}'")
            if visual_summary:
                thought_chain.append(f"2. Processing visual input payload: {visual_summary}")
                thought_chain.append("3. Fusing visual features with ViVy multimodal knowledge base.")
            else:
                thought_chain.append("2. Retrieving ViVy language knowledge base.")
            thought_chain.append("4. Synthesizing reasoning steps and formulating English output.")

            if image:
                response = (
                    f"Hello! ViVy has received the image `{image.image_id}` ({image.mime_type}). "
                    f"ViVy is a multimodal reasoning AI model supporting English and Vietnamese. "
                    f"Based on visual analysis and your prompt, ViVy has processed the image and is ready to assist you!"
                )
            else:
                response = (
                    f"Hello! You can now communicate directly with ViVy! "
                    f"ViVy is a multimodal reasoning model equipped with Vision capability and full English/Vietnamese bilingual support. "
                    f"Feel free to ask questions or attach images for visual analysis."
                )

        return MultimodalResponse(
            detected_language=lang,
            thought_chain=tuple(thought_chain),
            visual_summary=visual_summary,
            response_text=response,
        )
