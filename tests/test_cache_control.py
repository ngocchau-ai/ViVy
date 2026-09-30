"""Tests for ContextCacheController — V5.0 Sprint 2C.

10 tests cho cache_control.py primitives.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2C tests): Initial implementation.
"""

from __future__ import annotations

import tempfile

import pytest

from engine.cache_control import ContextCacheController


def test_store_chunk_adds_to_cache() -> None:
    """store_chunk() correctly adds a chunk to the cache."""
    cache = ContextCacheController()
    chunk = cache.store_chunk("c001", "Some raw document text", source="doc.pdf")
    assert chunk.chunk_id == "c001"
    assert "c001" in cache.list_chunks()


def test_store_chunk_tracks_bytes() -> None:
    """store_chunk() correctly tracks byte size."""
    cache = ContextCacheController()
    content = "Hello, world!"
    chunk = cache.store_chunk("c002", content)
    assert chunk.size_bytes == len(content.encode("utf-8"))


def test_purge_removes_chunks() -> None:
    """purge_raw_chunks() removes specified chunks."""
    cache = ContextCacheController()
    cache.store_chunk("c001", "text A")
    cache.store_chunk("c002", "text B")
    result = cache.purge_raw_chunks(["c001"])
    assert result.chunks_removed == 1
    assert "c001" not in cache.list_chunks()
    assert "c002" in cache.list_chunks()


def test_purge_returns_bytes_freed() -> None:
    """purge_raw_chunks() returns correct bytes_freed count."""
    cache = ContextCacheController()
    content = "ABC" * 100
    cache.store_chunk("c001", content)
    result = cache.purge_raw_chunks(["c001"])
    assert result.bytes_freed == len(content.encode("utf-8"))


def test_purge_nonexistent_chunk_ignored() -> None:
    """Purging a non-existent chunk ID is silently ignored."""
    cache = ContextCacheController()
    result = cache.purge_raw_chunks(["does_not_exist"])
    assert result.chunks_removed == 0
    assert result.bytes_freed == 0


def test_snapshot_captures_state() -> None:
    """snapshot_context() captures the current chunk IDs."""
    cache = ContextCacheController()
    cache.store_chunk("c001", "text A")
    cache.store_chunk("c002", "text B")
    snap = cache.snapshot_context()
    assert "c001" in snap.chunk_ids
    assert "c002" in snap.chunk_ids
    assert snap.total_bytes > 0


def test_load_artifact_reads_file() -> None:
    """load_artifact() reads content from a file on disk."""
    cache = ContextCacheController()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Knowledge Brief\nCore mechanics here.")
        tmp_path = f.name
    content = cache.load_artifact(tmp_path)
    assert "Knowledge Brief" in content
    assert "Core mechanics" in content


def test_load_artifact_raises_for_missing_file() -> None:
    """load_artifact() raises FileNotFoundError for missing path."""
    cache = ContextCacheController()
    with pytest.raises(FileNotFoundError):
        cache.load_artifact("/nonexistent/path/artifact.md")


def test_stats_reflects_cache_state() -> None:
    """stats() correctly reports chunk count and byte totals."""
    cache = ContextCacheController()
    cache.store_chunk("c001", "AAAA")
    cache.store_chunk("c002", "BBBB")
    cache.purge_raw_chunks(["c001"])
    s = cache.stats()
    assert s["chunks_in_cache"] == 1
    assert s["total_bytes_freed"] > 0


def test_purge_all_clears_cache() -> None:
    """purge_all() removes every chunk from the cache."""
    cache = ContextCacheController()
    cache.store_chunk("c001", "text A")
    cache.store_chunk("c002", "text B")
    cache.store_chunk("c003", "text C")
    result = cache.purge_all()
    assert result.chunks_removed == 3
    assert cache.list_chunks() == []
