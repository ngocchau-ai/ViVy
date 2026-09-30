"""Context Cache Controller — V5.0 Sprint 2C.

Giải quyết RÀO CẢN 3: Context Window Exhaustion khi Foraging.
Cung cấp cơ chế Purge & Reload KV Cache (Python in-memory implementation).

Architecture:
    ViVy nạp raw chunks (doc/video/audio) → Foraging →
    ContextCacheController.purge_raw_chunks() → Knowledge Artifact →
    load_artifact(artifact_path) → continue reasoning

Sprint 2: Python dict KV store (Ollama không lộ cache_control).
Sprint 3+: Tích hợp với Knowledge Artifact Writer.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2C): Initial implementation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_ARTIFACT_TOKENS = 8192  # Giới hạn tokens khi load artifact vào context


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CacheChunk:
    """Một raw chunk trong KV store."""

    chunk_id: str
    content: str
    source: str = ""
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0

    def __post_init__(self) -> None:
        if not self.size_bytes:
            self.size_bytes = len(self.content.encode("utf-8"))


@dataclass
class CacheSnapshot:
    """Checkpoint của cache state trước khi Purge."""

    snapshot_id: str
    chunk_ids: list[str]
    timestamp: float = field(default_factory=time.time)
    total_bytes: int = 0


@dataclass
class PurgeResult:
    """Kết quả của thao tác purge_raw_chunks()."""

    chunks_removed: int
    bytes_freed: int
    remaining_chunks: int


# ---------------------------------------------------------------------------
# ContextCacheController
# ---------------------------------------------------------------------------


class ContextCacheController:
    """Quản lý KV cache cho Active In-Context Epistemic Foraging.

    Cung cấp 3 primitives cốt lõi:
      1. purge_raw_chunks(chunk_ids) — giải phóng raw data khỏi cache
      2. load_artifact(path) — nạp Knowledge Brief vào active context
      3. snapshot_context() — tạo checkpoint trước khi Purge

    Usage::

        cache = ContextCacheController()
        # Store raw chunks during foraging
        cache.store_chunk("c001", "raw document text...", source="doc.pdf")
        cache.store_chunk("c002", "more raw text...", source="doc.pdf")
        # Snapshot before purge
        snap = cache.snapshot_context()
        # Purge raw chunks after Knowledge Artifact has been written
        result = cache.purge_raw_chunks(["c001", "c002"])
        # Load Knowledge Brief into active context
        artifact_text = cache.load_artifact("scratchpad/knowledge_brief_001.md")
    """

    def __init__(self, max_artifact_tokens: int = _MAX_ARTIFACT_TOKENS) -> None:
        self._kv: dict[str, CacheChunk] = {}
        self._snapshots: dict[str, CacheSnapshot] = {}
        self._active_artifact: str | None = None
        self._max_artifact_tokens = max_artifact_tokens
        self._total_bytes_stored = 0
        self._total_bytes_freed = 0

    # ------------------------------------------------------------------
    # Public API — 3 Core Primitives
    # ------------------------------------------------------------------

    def store_chunk(
        self,
        chunk_id: str,
        content: str,
        source: str = "",
    ) -> CacheChunk:
        """Lưu một raw chunk vào KV store.

        Parameters
        ----------
        chunk_id:
            ID duy nhất cho chunk (e.g. "doc_page_3", "video_frame_42").
        content:
            Nội dung raw text của chunk.
        source:
            Nguồn gốc chunk (file path, URL, v.v.).

        Returns
        -------
        CacheChunk
        """
        chunk = CacheChunk(chunk_id=chunk_id, content=content, source=source)
        self._kv[chunk_id] = chunk
        self._total_bytes_stored += chunk.size_bytes
        logger.debug("CacheController: stored chunk=%s size=%d bytes", chunk_id, chunk.size_bytes)
        return chunk

    def purge_raw_chunks(self, chunk_ids: list[str]) -> PurgeResult:
        """Giải phóng raw chunks khỏi KV store.

        Phải gọi SAU KHI Knowledge Artifact đã được ghi xuống đĩa.
        Không thể hoàn tác — dùng snapshot_context() trước nếu cần.

        Parameters
        ----------
        chunk_ids:
            Danh sách chunk IDs cần xóa. IDs không tồn tại sẽ bị bỏ qua.

        Returns
        -------
        PurgeResult
            chunks_removed, bytes_freed, remaining_chunks
        """
        bytes_freed = 0
        removed = 0

        for cid in chunk_ids:
            if cid in self._kv:
                bytes_freed += self._kv[cid].size_bytes
                del self._kv[cid]
                removed += 1
                logger.debug("CacheController: purged chunk=%s", cid)
            else:
                logger.debug("CacheController: chunk=%s not found (skip)", cid)

        self._total_bytes_freed += bytes_freed
        result = PurgeResult(
            chunks_removed=removed,
            bytes_freed=bytes_freed,
            remaining_chunks=len(self._kv),
        )
        logger.info(
            "CacheController.purge: removed=%d bytes_freed=%d remaining=%d",
            removed,
            bytes_freed,
            len(self._kv),
        )
        return result

    def load_artifact(self, artifact_path: str) -> str:
        """Nạp Knowledge Brief từ đĩa vào active context.

        Cắt ngắn nội dung nếu vượt quá max_artifact_tokens.

        Parameters
        ----------
        artifact_path:
            Đường dẫn tới file Knowledge Brief (.md).

        Returns
        -------
        str
            Nội dung artifact (truncated nếu cần).

        Raises
        ------
        FileNotFoundError
            Nếu artifact_path không tồn tại.
        """
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        content = path.read_text(encoding="utf-8")

        # Simple token approximation: 1 token ≈ 4 chars
        max_chars = self._max_artifact_tokens * 4
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[ARTIFACT TRUNCATED — max_artifact_tokens exceeded]"
            logger.warning(
                "CacheController: artifact truncated to %d chars (%s)",
                max_chars,
                artifact_path,
            )

        self._active_artifact = artifact_path
        logger.info("CacheController: loaded artifact=%s (%d chars)", artifact_path, len(content))
        return content

    def snapshot_context(self) -> CacheSnapshot:
        """Tạo checkpoint của cache state hiện tại.

        Dùng trước khi Purge để có thể kiểm tra lại nếu cần.

        Returns
        -------
        CacheSnapshot
        """
        snap_id = f"snap_{int(time.time())}"
        total_bytes = sum(c.size_bytes for c in self._kv.values())
        snap = CacheSnapshot(
            snapshot_id=snap_id,
            chunk_ids=list(self._kv.keys()),
            total_bytes=total_bytes,
        )
        self._snapshots[snap_id] = snap
        logger.info(
            "CacheController: snapshot=%s chunks=%d bytes=%d",
            snap_id,
            len(snap.chunk_ids),
            total_bytes,
        )
        return snap

    # ------------------------------------------------------------------
    # Diagnostic helpers
    # ------------------------------------------------------------------

    def get_chunk(self, chunk_id: str) -> CacheChunk | None:
        """Truy vấn một chunk theo ID."""
        return self._kv.get(chunk_id)

    def list_chunks(self) -> list[str]:
        """Danh sách tất cả chunk IDs hiện có trong cache."""
        return list(self._kv.keys())

    def stats(self) -> dict[str, int]:
        """Thống kê cache hiện tại."""
        return {
            "chunks_in_cache": len(self._kv),
            "total_bytes_stored": self._total_bytes_stored,
            "total_bytes_freed": self._total_bytes_freed,
            "current_bytes": sum(c.size_bytes for c in self._kv.values()),
            "snapshots": len(self._snapshots),
        }

    def purge_all(self) -> PurgeResult:
        """Xóa toàn bộ cache (emergency purge)."""
        all_ids = list(self._kv.keys())
        return self.purge_raw_chunks(all_ids)
