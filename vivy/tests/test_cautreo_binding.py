"""
Tests for Cautreo C-ABI ctypes binding (ViVy In-Process Memory & Score Graph).

10 tests for CautreoContextMemory, CautreoScoreGraph, and intuition digest.
"""

from __future__ import annotations

from integration.cautreo_binding import (
    CautreoContextMemory,
    CautreoMemoryKind,
    CautreoScoreGraph,
    CautreoScoreType,
    is_native_cautreo_available,
)


def test_native_cautreo_available() -> None:
    """Verify that native cautreo.dll is discovered and loaded."""
    assert is_native_cautreo_available() is True


def test_context_memory_lifecycle() -> None:
    """Open and close native context memory."""
    mem = CautreoContextMemory(max_items=100)
    assert mem is not None
    mem.close()


def test_context_memory_put_and_get_hard_fact() -> None:
    """Store and retrieve a hard fact via native memory."""
    with CautreoContextMemory(max_items=100) as mem:
        fact_id = "fact_001"
        fact_content = "Vivy is the central mind, Cautreo is the engine habitat"
        ver = mem.store_hard_fact(fact_id, fact_content)
        assert ver >= 0

        item = mem.get(fact_id)
        assert item is not None
        assert item.id == fact_id
        assert item.kind == CautreoMemoryKind.HARD_FACT
        assert item.content == fact_content


def test_context_memory_put_and_get_constraint() -> None:
    """Store and retrieve an epistemic constraint."""
    with CautreoContextMemory(max_items=100) as mem:
        cid = "const_001"
        ccontent = "Never repeat falsified epistemic errors (VM-11: 0%)"
        ver = mem.store_constraint(cid, ccontent)
        assert ver >= 0

        item = mem.get(cid)
        assert item is not None
        assert item.kind == CautreoMemoryKind.CONSTRAINT
        assert item.content == ccontent


def test_context_memory_put_task() -> None:
    """Store and retrieve an active task directive."""
    with CautreoContextMemory(max_items=100) as mem:
        tid = "task_001"
        tcontent = "Refactor Cautreo memory bridge with zero latency"
        ver = mem.store_task(tid, tcontent)
        assert ver >= 0

        item = mem.get(tid)
        assert item is not None
        assert item.kind == CautreoMemoryKind.TASK
        assert item.content == tcontent


def test_context_memory_intuition_digest() -> None:
    """Verify build_intuition_digest produces structured markdown."""
    with CautreoContextMemory(max_items=100) as mem:
        mem.store_constraint("c1", "Error rate = 0%")
        mem.store_task("t1", "Execute 2048-token context without soft-hang")
        digest = mem.build_intuition_digest()
        assert "VIVY INTUITION DIGEST" in digest
        assert len(digest) > 20


def test_score_graph_lifecycle() -> None:
    """Create and destroy native score graph."""
    graph = CautreoScoreGraph()
    assert graph is not None
    graph.destroy()


def test_score_graph_update_and_query() -> None:
    """Update context efficiency and verify score query."""
    with CautreoScoreGraph() as graph:
        ret = graph.update(CautreoScoreType.CONTEXT_EFFICIENCY, 0.85, evidence_weight=1.0)
        assert ret == 0

        eff = graph.context_efficiency
        assert 0.0 <= eff <= 1.0


def test_score_graph_task_progress() -> None:
    """Update and verify task progress metric."""
    with CautreoScoreGraph() as graph:
        graph.update(CautreoScoreType.TASK_PROGRESS, 0.92, evidence_weight=1.0)
        prog = graph.task_progress
        assert 0.0 <= prog <= 1.0


def test_score_graph_memory_quality() -> None:
    """Update and verify memory quality metric."""
    with CautreoScoreGraph() as graph:
        graph.update(CautreoScoreType.MEMORY_QUALITY, 0.99, evidence_weight=1.0)
        mq = graph.memory_quality
        assert 0.0 <= mq <= 1.0
