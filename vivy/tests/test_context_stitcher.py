"""
Unit tests for ContextStitcher (Lossless Output Stitching & Boundary Deduplication).
"""

from unittest.mock import MagicMock

from integration.context_stitcher import (
    ContextStitcher,
    find_boundary_overlap,
    stitch_chunks,
)
from integration.llama_cpp_bridge import ChatMessage, ChatResponse


def test_find_boundary_overlap():
    # Trường hợp 1: Trùng lặp câu giáp ranh
    t1 = "Đây là kết quả phân tích hệ thống."
    t2 = "hệ thống. Chúng ta cần triển khai tiếp bước 2."
    overlap = find_boundary_overlap(t1, t2)
    assert overlap == len("hệ thống.")
    assert t2[:overlap] == "hệ thống."

    # Trường hợp 2: Không trùng lặp
    t3 = "Kết thúc chương 1."
    t4 = "Bắt đầu chương 2."
    assert find_boundary_overlap(t3, t4) == 0

    # Trường hợp 3: Rỗng
    assert find_boundary_overlap("", "abc") == 0
    assert find_boundary_overlap("abc", "") == 0


def test_stitch_chunks():
    # Ghép hai đoạn code bị đứt ở giữa từ khóa
    chunk1 = "def calculate_hash(data: str) -> int:\n    h = 5381\n    for c in data:\n        h = ((h << 5) + h) + ord(c)"
    chunk2 = "        h = ((h << 5) + h) + ord(c)\n    return h & 0xFFFFFFFF\n"

    stitched = stitch_chunks(chunk1, chunk2)
    expected = (
        "def calculate_hash(data: str) -> int:\n"
        "    h = 5381\n"
        "    for c in data:\n"
        "        h = ((h << 5) + h) + ord(c)\n"
        "    return h & 0xFFFFFFFF\n"
    )
    assert stitched == expected
    # Đảm bảo không bị lặp lại dòng code giáp ranh
    assert stitched.count("h = ((h << 5) + h) + ord(c)") == 1


def test_context_stitcher_bypass_on_stop():
    stitcher = ContextStitcher()
    mock_chat = MagicMock()

    resp = ChatResponse(
        content="Hoàn thành phân tích nhiệm vụ.",
        tool_calls=[],
        finish_reason="stop",
        prompt_tokens=100,
        completion_tokens=50,
        elapsed_ms=500.0,
        raw={},
    )

    res = stitcher.stitch_chat_response(
        chat_func=mock_chat,
        messages=[],
        initial_response=resp,
        chat_message_cls=ChatMessage,
    )

    assert res.content == "Hoàn thành phân tích nhiệm vụ."
    assert res.finish_reason == "stop"
    mock_chat.assert_not_called()


def test_context_stitcher_recursive_continuation():
    stitcher = ContextStitcher(max_stitches=3, anchor_chars=64)

    # Round 1: Cắt cụt do chạm trần token
    resp1 = ChatResponse(
        content="Đoạn 1 của tài liệu kiến trúc. Chúng ta thiết lập cấu trúc",
        tool_calls=[],
        finish_reason="length",
        prompt_tokens=50,
        completion_tokens=20,
        elapsed_ms=200.0,
        raw={},
    )

    # Round 2: Tiếp nối và kết thúc hoàn chỉnh
    resp2 = ChatResponse(
        content="thiết lập cấu trúc dữ liệu và triển khai hàm hoàn chỉnh.",
        tool_calls=[],
        finish_reason="stop",
        prompt_tokens=60,
        completion_tokens=25,
        elapsed_ms=250.0,
        raw={},
    )

    mock_chat = MagicMock(return_value=resp2)
    init_messages = [ChatMessage(role="user", content="Viết tài liệu kiến trúc")]

    stitched_resp = stitcher.stitch_chat_response(
        chat_func=mock_chat,
        messages=init_messages,
        initial_response=resp1,
        chat_message_cls=ChatMessage,
    )

    # Kiểm tra gọi chat tiếp nối 1 lần
    assert mock_chat.call_count == 1
    call_args = mock_chat.call_args[0][0]
    assert call_args[-1].role == "user"
    assert "[CONTINUE_GENERATION: STRICT_ANCHOR_CONTINUATION]" in call_args[-1].content

    # Kiểm tra nội dung ghép nối liền mạch
    assert "Đoạn 1 của tài liệu kiến trúc. Chúng ta thiết lập cấu trúc dữ liệu và triển khai hàm hoàn chỉnh." == stitched_resp.content
    assert stitched_resp.finish_reason == "stop"
    assert stitched_resp.completion_tokens == 45
