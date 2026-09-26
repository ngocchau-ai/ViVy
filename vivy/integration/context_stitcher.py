"""
ContextStitcher — Lossless Output Stitching & Continuation Engine.
Sprint 3B (HOH-VIVY-FINAL-V1).

Giải quyết triệt để vấn đề output bị cắt cụt do giới hạn token (`finish_reason == 'length'`):
1. Phát hiện tín hiệu cắt cụt (`finish_reason == 'length'`).
2. Trích xuất Semantic Anchor (128-256 ký tự cuối) làm điểm neo tiếp nối.
3. Khởi tạo truy vấn tiếp nối tự động với mỏ neo mà không làm phình context.
4. Khử trùng lặp giáp ranh (Suffix-Prefix LCS / Overlap Deduplication) ở mức ký tự.
5. Hợp nhất các phân đoạn thành ChatResponse hoàn chỉnh liền mạch.

Changelog:
    21/09/2026 (Antigravity IDE): Triển khai theo phê duyệt từ phiên /plan-ceo-review.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def find_boundary_overlap(text1: str, text2: str, max_overlap: int = 512, min_overlap: int = 4) -> int:
    """Tìm độ dài phần hậu tố của text1 trùng với tiền tố của text2.

    Parameters
    ----------
    text1:
        Văn bản đoạn trước.
    text2:
        Văn bản đoạn sau tiếp nối.
    max_overlap:
        Độ dài tối đa cần tìm kiếm.
    min_overlap:
        Độ dài tối thiểu để coi là trùng lặp có nghĩa (tránh trùng ngẫu nhiên 1-3 ký tự).

    Returns
    -------
    int:
        Số lượng ký tự trùng lặp ở biên (0 nếu không có).
    """
    if not text1 or not text2:
        return 0

    t1_tail = text1[-max_overlap:]
    search_len = min(len(t1_tail), len(text2), max_overlap)

    # Quét từ độ dài lớn nhất giảm dần về min_overlap để tìm longest match
    for k in range(search_len, min_overlap - 1, -1):
        if t1_tail.endswith(text2[:k]):
            return k

    return 0


def stitch_chunks(chunk1: str, chunk2: str, max_overlap: int = 512, min_overlap: int = 4) -> str:
    """Ghép nối hai đoạn văn bản liền kề và khử trùng lặp phần giáp ranh.

    Parameters
    ----------
    chunk1:
        Đoạn thứ nhất.
    chunk2:
        Đoạn thứ hai tiếp nối.
    max_overlap:
        Giới hạn tìm kiếm trùng lặp tối đa.
    min_overlap:
        Giới hạn tìm kiếm tối thiểu.

    Returns
    -------
    str:
        Văn bản đã hợp nhất liền mạch.
    """
    if not chunk1:
        return chunk2 or ""
    if not chunk2:
        return chunk1

    overlap_len = find_boundary_overlap(chunk1, chunk2, max_overlap=max_overlap, min_overlap=min_overlap)
    if overlap_len > 0:
        logger.debug("stitch_chunks: Overlap detected (%d chars) -> deduplicating boundary", overlap_len)
        return chunk1 + chunk2[overlap_len:]

    return chunk1 + chunk2


@dataclass
class StitchResult:
    """Kết quả sau khi thực hiện ghép nối chuỗi."""
    stitched_content: str
    total_stitches: int
    prompt_tokens: int
    completion_tokens: int
    elapsed_ms: float
    final_finish_reason: str
    is_stitched: bool


class ContextStitcher:
    """Điều phối tiếp nối đệ quy khi phát hiện finish_reason == 'length'."""

    def __init__(
        self,
        max_stitches: int = 5,
        anchor_chars: int = 256,
        min_overlap: int = 4,
    ) -> None:
        self.max_stitches = max_stitches
        self.anchor_chars = anchor_chars
        self.min_overlap = min_overlap

    def stitch_chat_response(
        self,
        chat_func: Callable[[list[Any]], Any],
        messages: list[Any],
        initial_response: Any,
        chat_message_cls: type,
    ) -> Any:
        """Kiểm tra và tự động ghép nối nếu initial_response bị chạm trần token.

        Parameters
        ----------
        chat_func:
            Hàm gọi LLM (ví dụ bridge.chat_safe hoặc bridge.chat).
        messages:
            Lịch sử hội thoại hiện tại.
        initial_response:
            ChatResponse ban đầu nhận được từ LLM.
        chat_message_cls:
            Class ChatMessage dùng để tạo message tiếp nối.

        Returns
        -------
        ChatResponse:
            ChatResponse hoàn chỉnh đã được ghép nối liền mạch nếu có.
        """
        if getattr(initial_response, "finish_reason", "") != "length":
            return initial_response

        logger.info(
            "ContextStitcher: Detected finish_reason == 'length'. Initial tokens: %d. Activating recursive stitcher...",
            getattr(initial_response, "completion_tokens", 0),
        )

        stitched_content = initial_response.content or ""
        total_prompt_tokens = getattr(initial_response, "prompt_tokens", 0)
        total_completion_tokens = getattr(initial_response, "completion_tokens", 0)
        total_elapsed_ms = getattr(initial_response, "elapsed_ms", 0.0)
        current_finish_reason = initial_response.finish_reason

        stitches = 0
        working_messages = list(messages)

        while current_finish_reason == "length" and stitches < self.max_stitches:
            stitches += 1
            t_stitch_start = time.perf_counter()

            # Trích xuất Semantic Anchor từ cuối đoạn văn bản hiện có
            anchor = stitched_content[-self.anchor_chars:] if len(stitched_content) > self.anchor_chars else stitched_content

            continuation_instruction = (
                "[CONTINUE_GENERATION: STRICT_ANCHOR_CONTINUATION]\n"
                "The previous output was cut off due to maximum token limit. "
                "Please continue the response seamlessly from the following anchor point. "
                "Do not repeat the anchor point, do not include preamble or apology, continue directly:\n"
                f"--- ANCHOR ---\n{anchor}\n--- END ANCHOR ---"
            )

            continuation_messages = [
                *working_messages,
                chat_message_cls(role="assistant", content=stitched_content),
                chat_message_cls(role="user", content=continuation_instruction),
            ]

            logger.info("ContextStitcher: Sending continuation round %d/%d...", stitches, self.max_stitches)
            try:
                next_response = chat_func(continuation_messages)
            except Exception as e:
                logger.error("ContextStitcher: Continuation round %d failed with error: %s", stitches, e)
                break

            new_chunk = getattr(next_response, "content", "") or ""
            current_finish_reason = getattr(next_response, "finish_reason", "stop")
            total_prompt_tokens += getattr(next_response, "prompt_tokens", 0)
            total_completion_tokens += getattr(next_response, "completion_tokens", 0)
            total_elapsed_ms += getattr(next_response, "elapsed_ms", (time.perf_counter() - t_stitch_start) * 1000)

            # Ghép nối với cơ chế khử trùng lặp biên
            stitched_content = stitch_chunks(
                stitched_content,
                new_chunk,
                max_overlap=self.anchor_chars,
                min_overlap=self.min_overlap,
            )

            if not new_chunk.strip():
                logger.warning("ContextStitcher: Received empty continuation chunk. Breaking stitch loop.")
                break

        logger.info(
            "ContextStitcher: Stitching completed (%d rounds). Total tokens: %d. Final finish_reason: %s",
            stitches, total_completion_tokens, current_finish_reason,
        )

        # Cập nhật lại thuộc tính của initial_response
        initial_response.content = stitched_content
        initial_response.prompt_tokens = total_prompt_tokens
        initial_response.completion_tokens = total_completion_tokens
        initial_response.elapsed_ms = total_elapsed_ms
        initial_response.finish_reason = current_finish_reason

        return initial_response
