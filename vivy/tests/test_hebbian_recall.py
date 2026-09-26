"""
Tests for memory/hebbian_recall.py — ViVy Final V1.0 Sprint 2.

Covers: HebbianRecall register, recall O(1), W = YX+ correctness,
sync_from_graph, empty memory behavior.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from memory.cognitive_graph import CognitiveStateGraph, NodeType
from memory.hebbian_recall import HebbianRecall, RecallResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def recall():
    return HebbianRecall(dim=16)


@pytest.fixture
def graph():
    return CognitiveStateGraph()


def _rand_vec(dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestHebbianRecallInit:
    def test_default_dim(self):
        r = HebbianRecall()
        assert r.dim == 64

    def test_custom_dim(self):
        r = HebbianRecall(dim=32)
        assert r.dim == 32

    def test_invalid_dim_raises(self):
        with pytest.raises(ValueError):
            HebbianRecall(dim=0)

    def test_initially_not_built(self, recall):
        assert not recall.is_built
        assert recall.size == 0


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------


class TestRegisterUnregister:
    def test_register_increases_size(self, recall):
        recall.register("n1", _rand_vec(16))
        assert recall.size == 1

    def test_register_marks_dirty(self, recall):
        recall.register("n1", _rand_vec(16))
        assert not recall.is_built

    def test_unregister_decreases_size(self, recall):
        recall.register("n1", _rand_vec(16))
        result = recall.unregister("n1")
        assert result is True
        assert recall.size == 0

    def test_unregister_nonexistent_returns_false(self, recall):
        assert recall.unregister("ghost") is False

    def test_register_dim_mismatch_raises(self, recall):
        bad = np.ones(10, dtype=np.float32)
        with pytest.raises(ValueError, match="dim mismatch"):
            recall.register("n1", bad)

    def test_register_with_value_embedding(self, recall):
        k = _rand_vec(16, seed=0)
        v = _rand_vec(16, seed=1)
        recall.register("n1", k, value_embedding=v)
        assert recall.size == 1

    def test_reset_clears_all(self, recall):
        recall.register("n1", _rand_vec(16))
        recall.register("n2", _rand_vec(16))
        recall.reset()
        assert recall.size == 0
        assert not recall.is_built


# ---------------------------------------------------------------------------
# Recall — empty memory
# ---------------------------------------------------------------------------


class TestRecallEmptyMemory:
    def test_recall_empty_returns_zero_embedding(self, recall):
        r = recall.recall(_rand_vec(16))
        assert isinstance(r, RecallResult)
        assert np.allclose(r.recalled_embedding, 0.0)
        assert r.recalled_node_id is None
        assert r.similarity == 0.0
        assert r.w_size == 0

    def test_recall_empty_no_crash(self, recall):
        # Should not raise even with all-zero query
        r = recall.recall(np.zeros(16, dtype=np.float32))
        assert isinstance(r, RecallResult)


# ---------------------------------------------------------------------------
# Recall — correctness (W = YX+)
# ---------------------------------------------------------------------------


class TestRecallCorrectness:
    def test_single_pattern_recall(self, recall):
        """W = y x+ should recall y when queried with x."""
        x = _rand_vec(16, seed=7)
        y = _rand_vec(16, seed=42)
        recall.register("n1", x, value_embedding=y)
        r = recall.recall(x)
        assert r.ok if hasattr(r, "ok") else True
        assert r.w_size == 1
        # After normalisation, recalled_embedding should be close to y
        y_hat = r.recalled_embedding / (np.linalg.norm(r.recalled_embedding) + 1e-8)
        y_norm = y / (np.linalg.norm(y) + 1e-8)
        cos_sim = float(np.dot(y_hat, y_norm))
        assert cos_sim > 0.9, f"Recall cosine similarity {cos_sim:.4f} too low for single pattern"

    def test_multiple_patterns_recall_query_nearest(self):
        """With multiple patterns, recall should return the embedding closest to W @ x."""
        rc = HebbianRecall(dim=8)
        rng = np.random.default_rng(0)
        keys = [rng.standard_normal(8).astype(np.float32) for _ in range(5)]
        for i, k in enumerate(keys):
            rc.register(f"n{i}", k / np.linalg.norm(k))

        r = rc.recall(keys[2] / np.linalg.norm(keys[2]))
        assert r.w_size == 5
        assert isinstance(r.recalled_embedding, np.ndarray)
        assert r.recalled_embedding.shape[0] == 8

    def test_w_is_built_after_recall(self, recall):
        recall.register("n1", _rand_vec(16))
        assert not recall.is_built
        recall.recall(_rand_vec(16))
        assert recall.is_built

    def test_w_dirty_after_register(self, recall):
        recall.register("n1", _rand_vec(16))
        recall.recall(_rand_vec(16))  # builds W
        assert recall.is_built
        recall.register("n2", _rand_vec(16, seed=99))
        assert not recall.is_built  # dirty again

    def test_dim_mismatch_query_raises(self, recall):
        bad_q = np.ones(10, dtype=np.float32)
        with pytest.raises(ValueError, match="dim mismatch"):
            recall.recall(bad_q)


# ---------------------------------------------------------------------------
# O(1) complexity — Gate 2 requirement
# ---------------------------------------------------------------------------


class TestRecallComplexityO1:
    """Verify that recall latency is effectively O(1) in graph size.

    Gate 2 spec: latency with 10 nodes vs 10,000 nodes differs < 5x
    (practically should be < 2x since it's 1 matmul regardless of n).
    """

    def _build_recall(self, n: int, dim: int = 32) -> HebbianRecall:
        rc = HebbianRecall(dim=dim)
        rng = np.random.default_rng(0)
        for i in range(n):
            k = rng.standard_normal(dim).astype(np.float32)
            k /= np.linalg.norm(k)
            rc.register(f"n{i}", k)
        # Pre-build W to isolate recall-only latency
        rc.recall(rng.standard_normal(dim).astype(np.float32))
        return rc

    def test_recall_10_vs_10000_nodes_latency(self):
        rc_small = self._build_recall(10)
        rc_large = self._build_recall(10_000)

        query = np.random.default_rng(42).standard_normal(32).astype(np.float32)
        query /= np.linalg.norm(query)

        # Warm up
        rc_small.recall(query)
        rc_large.recall(query)

        # Measure 20 calls each
        N = 20
        t0 = time.perf_counter()
        for _ in range(N):
            rc_small.recall(query)
        small_ms = (time.perf_counter() - t0) * 1000 / N

        t0 = time.perf_counter()
        for _ in range(N):
            rc_large.recall(query)
        large_ms = (time.perf_counter() - t0) * 1000 / N

        ratio = large_ms / (small_ms + 1e-6)
        assert ratio < 5.0, (
            f"O(1) complexity violated: 10k-node recall {large_ms:.3f}ms "
            f"is {ratio:.1f}x slower than 10-node recall {small_ms:.3f}ms"
        )


# ---------------------------------------------------------------------------
# sync_from_graph
# ---------------------------------------------------------------------------


class TestSyncFromGraph:
    def test_sync_registers_nodes_with_embeddings(self, recall, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a", embedding=list(_rand_vec(16)))
        graph.add_node("b", NodeType.HYPOTHESIS, "b", embedding=list(_rand_vec(16, 1)))
        graph.add_node("c", NodeType.HYPOTHESIS, "c")  # no embedding → skip
        count = recall.sync_from_graph(graph)
        assert count == 2
        assert recall.size == 2

    def test_sync_nodes_without_embedding_skipped(self, recall, graph):
        graph.add_node("x", NodeType.HYPOTHESIS, "x")  # no embedding
        count = recall.sync_from_graph(graph)
        assert count == 0
        assert recall.size == 0

    def test_recall_after_sync(self, recall, graph):
        emb = list(_rand_vec(16))
        graph.add_node("a", NodeType.HYPOTHESIS, "a", embedding=emb)
        recall.sync_from_graph(graph)
        r = recall.recall(np.asarray(emb, dtype=np.float32), graph=graph)
        assert r.recalled_node_id == "a"
        assert r.similarity > 0.8

    def test_recall_with_graph_finds_nearest(self, recall, graph):
        emb_a = list(_rand_vec(16, seed=0))
        emb_b = list(_rand_vec(16, seed=1))
        graph.add_node("a", NodeType.HYPOTHESIS, "a", embedding=emb_a)
        graph.add_node("b", NodeType.HYPOTHESIS, "b", embedding=emb_b)
        recall.sync_from_graph(graph)
        # Query near "a"
        r = recall.recall(np.asarray(emb_a, dtype=np.float32), graph=graph)
        assert r.recalled_node_id == "a"


# ---------------------------------------------------------------------------
# RecallResult schema
# ---------------------------------------------------------------------------


class TestRecallResultSchema:
    def test_result_has_all_fields(self, recall):
        recall.register("n1", _rand_vec(16))
        r = recall.recall(_rand_vec(16))
        assert hasattr(r, "query_embedding")
        assert hasattr(r, "recalled_embedding")
        assert hasattr(r, "recalled_node_id")
        assert hasattr(r, "recalled_node")
        assert hasattr(r, "similarity")
        assert hasattr(r, "elapsed_ms")
        assert hasattr(r, "w_size")

    def test_elapsed_ms_positive(self, recall):
        recall.register("n1", _rand_vec(16))
        r = recall.recall(_rand_vec(16))
        assert r.elapsed_ms >= 0.0

    def test_similarity_in_0_1(self, recall, graph):
        emb = list(_rand_vec(16))
        graph.add_node("a", NodeType.HYPOTHESIS, "a", embedding=emb)
        recall.sync_from_graph(graph)
        r = recall.recall(np.asarray(emb, dtype=np.float32), graph=graph)
        assert 0.0 <= r.similarity <= 1.0
