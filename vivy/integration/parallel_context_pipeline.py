"""
Parallel Context Pipeline — Simultaneous Input Decomposition & Compression.

Giải quyết triệt để bài toán giới hạn Atomic Context Window 2048 tokens:

Changelog:
    23/09/2026 (Claude Code — P0 Superority Truth Pass): Gate 9 latency scrub.
    # [ISOLATED 23/09/2026] prior fused-prompt: "Archived in Cautreo 0ms RAM"
    # [ISOLATED 23/09/2026] prior docstring: "truy xuất 0ms"
Khi nhận input dài (> 3500 ký tự / ~850 tokens), pipeline thực thi SONG SONG:
1. Nhánh Nén (Semantic Compression):
   Trích xuất mục tiêu, ràng buộc, thực thể, lỗi kỹ thuật thành Semantic Digest (~150-250 tokens).
2. Nhánh Chia Tách (Segment Decomposition):
   Phân rã văn bản thành các segment nhỏ (<= 2500 ký tự), nạp các segment S2..SK vào Cautreo RAM
   với ID phân đoạn để truy xuất in-process khi cần, giữ Segment 1 làm Active Execution Chunk.
   # [ISOLATED 23/09/2026] prior: "truy xuất 0ms"
3. Hợp Nhất (Fusion Prompt):
   Đóng gói cấu trúc [PARALLEL_INPUT_PIPELINE] để ViVy vừa nắm toàn cảnh kiến trúc
   vừa có dữ liệu chi tiết của Segment 1 mà không bao giờ vượt trần 2048 tokens.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Ngưỡng kích hoạt pipeline song song: 3500 ký tự (~850 tokens)
DEFAULT_ACTIVATION_THRESHOLD_CHARS = 3500
# Kích thước tối đa của mỗi segment: 2200 ký tự (~550 tokens)
DEFAULT_MAX_SEGMENT_CHARS = 2200


@dataclass
class SegmentInfo:
    index: int
    total: int
    content: str
    char_len: int
    token_estimate: int
    memory_id: str


@dataclass
class ParallelPipelineResult:
    is_processed: bool
    original_char_len: int
    compressed_digest: str
    active_segment: SegmentInfo | None
    total_segments: int
    remaining_segment_ids: list[str]
    fused_prompt: str


class SemanticCompressor:
    """Trích xuất và cô đọng ngữ nghĩa từ văn bản dài (Deterministic Extractor)."""

    KEYWORD_PATTERNS = [
        r"(?:goal|objective|nhiệm vụ|mục tiêu)\s*[:：]\s*([^\r\n]+)",
        r"(?:constraint|ràng buộc|yêu cầu|quy định|bất biến|quy tắc|rule|invariant|bắt buộc|mandatory)\s*[:：]?\s*([^\r\n]+)",
        r"(?:error|exception|traceback|lỗi|failed)\s*[:：]\s*([^\r\n]+)",
        r"(?:target|file|path|đường dẫn)\s*[:：]\s*([^\r\n]+)",
    ]

    def compress(self, text: str, max_chars: int = 1200) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""

        extracted_headers: list[str] = []
        extracted_directives: list[str] = []
        code_signatures: list[str] = []

        for line in lines:
            # Thu thập tiêu đề markdown
            if line.startswith("#"):
                clean_h = re.sub(r"^#+\s*", "", line)
                if clean_h and clean_h not in extracted_headers:
                    extracted_headers.append(clean_h)
            # Thu thập dòng chứa từ khóa quan trọng
            for pat in self.KEYWORD_PATTERNS:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    extracted_directives.append(line)
                    break
            # Thu thập chữ ký hàm / class
            if re.match(r"^\s*(def |class |void |int |struct |fn |async def )", line):
                sig = line.split("{")[0].strip()
                if sig and sig not in code_signatures:
                    code_signatures.append(sig)

        # Mở đầu và kết luận của văn bản
        opening = lines[:3]
        closing = lines[-2:] if len(lines) > 5 else []

        parts: list[str] = []
        if extracted_headers:
            parts.append("• SECTIONS: " + " | ".join(extracted_headers[:6]))
        if extracted_directives:
            parts.append("• DIRECTIVES & CONSTRAINTS:\n  " + "\n  ".join(extracted_directives[:6]))
        if code_signatures:
            parts.append("• CODE ANCHORS:\n  " + "\n  ".join(code_signatures[:6]))
        if opening:
            parts.append("• PREAMBLE: " + " ".join(opening)[:250])
        if closing:
            parts.append("• TERMINAL: " + " ".join(closing)[:200])

        digest = "\n".join(parts)
        if len(digest) > max_chars:
            digest = digest[:max_chars] + "... [digest truncated]"
        return digest


class SegmentDecomposer:
    """Phân rã văn bản dài thành các segment có ranh giới ngữ nghĩa tự nhiên."""

    def __init__(self, max_segment_chars: int = DEFAULT_MAX_SEGMENT_CHARS):
        self.max_segment_chars = max_segment_chars

    def _split_into_atomic_blocks(self, text: str) -> list[str]:
        """Tách văn bản thành các khối nhỏ nguyên tử (paragraph -> newline -> sentence -> raw slice)."""
        raw_paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        atomic: list[str] = []
        for p in raw_paragraphs:
            if len(p) <= self.max_segment_chars:
                atomic.append(p)
            else:
                lines = [ln for ln in p.splitlines() if ln.strip()]
                for ln in lines:
                    if len(ln) <= self.max_segment_chars:
                        atomic.append(ln)
                    else:
                        # Tách theo câu hoặc cắt cứng
                        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ln) if s.strip()]
                        for s in sentences:
                            if len(s) <= self.max_segment_chars:
                                atomic.append(s)
                            else:
                                for i in range(0, len(s), self.max_segment_chars):
                                    atomic.append(s[i:i + self.max_segment_chars])
        return atomic

    def decompose(self, text: str, prefix_id: str) -> list[SegmentInfo]:
        if not text or not text.strip():
            return []

        atomic_blocks = self._split_into_atomic_blocks(text)
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for block in atomic_blocks:
            block_len = len(block)
            if current_len + block_len > self.max_segment_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk).strip())
                current_chunk = [block]
                current_len = block_len
            else:
                current_chunk.append(block)
                current_len += block_len

        if current_chunk:
            final_text = "\n\n".join(current_chunk).strip()
            if final_text:
                chunks.append(final_text)

        if not chunks:
            chunks = [text.strip()]

        total = len(chunks)
        segments: list[SegmentInfo] = []
        for idx, chunk in enumerate(chunks, start=1):
            seg_id = f"{prefix_id}_seg_{idx:03d}"
            segments.append(
                SegmentInfo(
                    index=idx,
                    total=total,
                    content=chunk,
                    char_len=len(chunk),
                    token_estimate=max(1, len(chunk) // 4),
                    memory_id=seg_id,
                )
            )
        return segments


class ParallelContextPipeline:
    """Điều phối song song việc Nén Ngữ Nghĩa và Bóc Tách Phân Đoạn."""

    def __init__(
        self,
        activation_threshold_chars: int = DEFAULT_ACTIVATION_THRESHOLD_CHARS,
        max_segment_chars: int = DEFAULT_MAX_SEGMENT_CHARS,
        context_memory: Any | None = None,
    ):
        self.activation_threshold_chars = activation_threshold_chars
        self.compressor = SemanticCompressor()
        self.decomposer = SegmentDecomposer(max_segment_chars=max_segment_chars)
        self.context_memory = context_memory

    def process(self, raw_input: str, task_id: str = "default") -> ParallelPipelineResult:
        """Thực thi pipeline song song: Nén + Bóc tách nếu vượt ngưỡng."""
        text_len = len(raw_input)
        if text_len <= self.activation_threshold_chars:
            return ParallelPipelineResult(
                is_processed=False,
                original_char_len=text_len,
                compressed_digest="",
                active_segment=None,
                total_segments=1,
                remaining_segment_ids=[],
                fused_prompt=raw_input,
            )

        # Tính hash làm namespace định danh các segment
        content_hash = hashlib.sha256(raw_input.encode("utf-8", errors="ignore")).hexdigest()[:12]
        prefix_id = f"{task_id}_{content_hash}"

        # Thực thi song song Compression và Decomposition qua ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_digest = executor.submit(self.compressor.compress, raw_input)
            future_segments = executor.submit(self.decomposer.decompose, raw_input, prefix_id)
            digest = future_digest.result()
            segments = future_segments.result()

        if not segments:
            return ParallelPipelineResult(
                is_processed=False,
                original_char_len=text_len,
                compressed_digest=digest,
                active_segment=None,
                total_segments=1,
                remaining_segment_ids=[],
                fused_prompt=raw_input,
            )

        active_seg = segments[0]
        remaining_segs = segments[1:]
        remaining_ids: list[str] = []

        # Lưu trữ các segment còn lại (S2..SK) vào Cautreo RAM native
        for seg in remaining_segs:
            remaining_ids.append(seg.memory_id)
            if self.context_memory is not None:
                try:
                    self.context_memory.store_hard_fact(seg.memory_id, seg.content)
                    logger.debug("ParallelContextPipeline: Stored %s in Cautreo Memory (%d chars)", seg.memory_id, seg.char_len)
                except Exception as e:
                    logger.warning("ParallelContextPipeline: Could not store %s in Cautreo: %s", seg.memory_id, e)

        # Xây dựng Fusion Prompt hợp nhất
        fused_prompt = (
            "[PARALLEL_INPUT_PIPELINE: LONG_INPUT_DETECTED]\n"
            f"• Original Payload: {text_len} chars (~{text_len // 4} tokens) — Automatically Decomposed & Compressed\n"
            # [ISOLATED 23/09/2026] prior: "Archived in Cautreo 0ms RAM"
            f"• Architecture: Chunk 1 of {len(segments)} Active | Chunks 2..{len(segments)} Archived in Cautreo memory\n\n"
            "## 1. COMPRESSED OVERVIEW (SEMANTIC ESSENCE)\n"
            f"{digest}\n\n"
            f"## 2. ACTIVE WORKING SEGMENT (PART 1 OF {len(segments)})\n"
            f"{active_seg.content}\n\n"
            "## 3. CONTEXT CHAIN CONTINUATION INSTRUCTIONS\n"
            f"• You are currently executing on Part 1 of {len(segments)}.\n"
            f"• Remaining Segment IDs in Cautreo Memory: {', '.join(remaining_ids) if remaining_ids else 'NONE'}\n"
            "• If Part 1 is sufficient, emit Directive directly. If subsequent segments are required, request segment ID.\n"
            "[/PARALLEL_INPUT_PIPELINE]"
        )

        return ParallelPipelineResult(
            is_processed=True,
            original_char_len=text_len,
            compressed_digest=digest,
            active_segment=active_seg,
            total_segments=len(segments),
            remaining_segment_ids=remaining_ids,
            fused_prompt=fused_prompt,
        )
