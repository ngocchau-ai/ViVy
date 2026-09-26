"""
Tests for memory/cognitive_graph.py — ViVy Final V1.0 Sprint 2.

Covers: node CRUD, edge operations, Error-Dampening (VM-11),
FALSIFIED edge semantics, LRU eviction, thread safety.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import threading
import time

import pytest

from memory.cognitive_graph import (
    CognitiveStateGraph,
    EdgeType,
    NodeType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph():
    return CognitiveStateGraph(max_nodes=100)


# ---------------------------------------------------------------------------
# NodeType & EdgeType enum
# ---------------------------------------------------------------------------


class TestEnums:
    def test_node_types_exist(self):
        assert NodeType.HYPOTHESIS == "HYPOTHESIS"
        assert NodeType.INVARIANT == "INVARIANT"
        assert NodeType.RCA_ROOT == "RCA_ROOT"

    def test_edge_types_exist(self):
        assert EdgeType.SUPPORTS == "SUPPORTS"
        assert EdgeType.FALSIFIED == "FALSIFIED"
        assert EdgeType.DERIVED_FROM == "DERIVED_FROM"


# ---------------------------------------------------------------------------
# Node operations
# ---------------------------------------------------------------------------


class TestAddNode:
    def test_add_hypothesis_node(self, graph):
        node = graph.add_node("h1", NodeType.HYPOTHESIS, "test hypothesis")
        assert node.node_id == "h1"
        assert node.node_type == NodeType.HYPOTHESIS
        assert node.content == "test hypothesis"

    def test_add_invariant_node(self, graph):
        node = graph.add_node("inv1", NodeType.INVARIANT, "invariant truth")
        assert node.node_type == NodeType.INVARIANT

    def test_add_rca_root_node(self, graph):
        node = graph.add_node("rca1", NodeType.RCA_ROOT, "root cause")
        assert node.node_type == NodeType.RCA_ROOT

    def test_add_node_with_string_type(self, graph):
        node = graph.add_node("n1", "HYPOTHESIS", "content")
        assert node.node_type == NodeType.HYPOTHESIS

    def test_add_node_confidence_clamped(self, graph):
        n1 = graph.add_node("n1", NodeType.HYPOTHESIS, "x", confidence=2.0)
        assert n1.confidence == 1.0
        n2 = graph.add_node("n2", NodeType.HYPOTHESIS, "x", confidence=-0.5)
        assert n2.confidence == 0.0

    def test_add_node_with_embedding(self, graph):
        node = graph.add_node("e1", NodeType.HYPOTHESIS, "x", embedding=[0.1, 0.2, 0.3])
        assert node.embedding == [0.1, 0.2, 0.3]

    def test_add_node_empty_id_raises(self, graph):
        with pytest.raises(ValueError):
            graph.add_node("", NodeType.HYPOTHESIS, "content")

    def test_add_node_update_existing(self, graph):
        graph.add_node("n1", NodeType.HYPOTHESIS, "original", confidence=0.5)
        graph.add_node("n1", NodeType.HYPOTHESIS, "updated", confidence=0.9)
        node = graph.get_node("n1")
        assert node.content == "updated"
        assert abs(node.confidence - 0.9) < 1e-6

    def test_get_node_returns_none_for_missing(self, graph):
        assert graph.get_node("nonexistent") is None

    def test_len_tracks_node_count(self, graph):
        assert len(graph) == 0
        graph.add_node("a", NodeType.HYPOTHESIS, "x")
        graph.add_node("b", NodeType.HYPOTHESIS, "y")
        assert len(graph) == 2

    def test_remove_node_ok(self, graph):
        graph.add_node("r1", NodeType.HYPOTHESIS, "x")
        result = graph.remove_node("r1")
        assert result is True
        assert graph.get_node("r1") is None

    def test_remove_nonexistent_node_returns_false(self, graph):
        assert graph.remove_node("nope") is False

    def test_promote_to_invariant(self, graph):
        graph.add_node("p1", NodeType.HYPOTHESIS, "x", confidence=0.5)
        result = graph.promote_to_invariant("p1")
        assert result is True
        node = graph.get_node("p1")
        assert node.node_type == NodeType.INVARIANT

    def test_promote_non_hypothesis_returns_false(self, graph):
        graph.add_node("inv1", NodeType.INVARIANT, "x")
        assert graph.promote_to_invariant("inv1") is False

    def test_promote_missing_node_returns_false(self, graph):
        assert graph.promote_to_invariant("ghost") is False

    def test_metadata_stored(self, graph):
        graph.add_node("m1", NodeType.HYPOTHESIS, "x", metadata={"key": "val"})
        node = graph.get_node("m1")
        assert node.metadata["key"] == "val"


# ---------------------------------------------------------------------------
# Edge operations
# ---------------------------------------------------------------------------


class TestEdgeOperations:
    def test_add_support_edge(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.HYPOTHESIS, "b")
        edge = graph.add_edge("a", "b", EdgeType.SUPPORTS)
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.edge_type == EdgeType.SUPPORTS

    def test_add_falsified_edge_increments_falsified_count(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.RCA_ROOT, "b")
        graph.add_edge_falsified("a", "b")
        node = graph.get_node("a")
        assert node.falsified_count == 1

    def test_double_falsification(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.RCA_ROOT, "b")
        graph.add_node("c", NodeType.RCA_ROOT, "c")
        graph.add_edge_falsified("a", "b")
        graph.add_edge_falsified("a", "c")
        node = graph.get_node("a")
        assert node.falsified_count == 2

    def test_auto_create_stub_nodes_for_edges(self, graph):
        graph.add_edge("x", "y", EdgeType.DERIVED_FROM)
        assert graph.get_node("x") is not None
        assert graph.get_node("y") is not None

    def test_get_outgoing_edges(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.HYPOTHESIS, "b")
        graph.add_node("c", NodeType.HYPOTHESIS, "c")
        graph.add_edge("a", "b", EdgeType.SUPPORTS)
        graph.add_edge("a", "c", EdgeType.SUPPORTS)
        edges = graph.get_outgoing_edges("a")
        assert len(edges) == 2

    def test_get_incoming_edges(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.HYPOTHESIS, "b")
        graph.add_edge("a", "b", EdgeType.SUPPORTS)
        edges = graph.get_incoming_edges("b")
        assert len(edges) == 1

    def test_edge_weight_clamped(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.HYPOTHESIS, "b")
        edge = graph.add_edge("a", "b", EdgeType.SUPPORTS, weight=5.0)
        assert edge.weight == 1.0


# ---------------------------------------------------------------------------
# Error-Dampening (VM-11)
# ---------------------------------------------------------------------------


class TestErrorDampening:
    def test_dampen_factor_no_falsification(self, graph):
        node = graph.add_node("n1", NodeType.HYPOTHESIS, "x")
        assert node.dampen_factor() == 1.0
        assert not node.is_dampened()

    def test_dampen_factor_one_falsification(self, graph):
        graph.add_node("n1", NodeType.HYPOTHESIS, "x")
        graph.add_edge_falsified("n1", "rca1")
        node = graph.get_node("n1")
        assert abs(node.dampen_factor() - 0.5) < 1e-6
        assert node.is_dampened()

    def test_dampen_factor_two_falsifications(self, graph):
        graph.add_node("n1", NodeType.HYPOTHESIS, "x")
        graph.add_edge_falsified("n1", "rca1")
        graph.add_edge_falsified("n1", "rca2")
        node = graph.get_node("n1")
        assert abs(node.dampen_factor() - 0.25) < 1e-6

    def test_get_dampened_candidates_sorted(self, graph):
        graph.add_node("good", NodeType.HYPOTHESIS, "x", confidence=0.8)
        graph.add_node("bad", NodeType.HYPOTHESIS, "y", confidence=0.8)
        graph.add_edge_falsified("bad", "rca1")

        results = graph.get_dampened_candidates(["good", "bad"])
        assert len(results) == 2
        # "good" should have higher effective weight
        assert results[0][0] == "good"
        assert results[1][0] == "bad"

    def test_get_dampened_candidates_filters_below_min_weight(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "x", confidence=0.8)
        graph.add_edge_falsified("a", "rca1")
        graph.add_edge_falsified("a", "rca2")
        graph.add_edge_falsified("a", "rca3")  # dampen=0.125, effective=0.8*0.125=0.1

        results = graph.get_dampened_candidates(["a"], min_weight=0.5)
        assert len(results) == 0  # filtered out

    def test_vm11_mock_100_tasks(self):
        """VM-11 gate: error repeat rate ≤ 10% across 100-task simulation.

        Setup: 20 nodes are falsified (dampen=0.5). Simulate 100 selection
        events. At each event, choose between a fresh node (undampened, w=0.8)
        and the falsified node (w=0.8*0.5=0.4). Count how often the falsified
        node would win (it should never win when competing with fresh node).
        """
        g = CognitiveStateGraph()
        repeated_errors = 0
        total = 100

        # Create 1 "bad" node that will be falsified
        g.add_node("bad", NodeType.HYPOTHESIS, "bad action", confidence=0.8)
        g.add_edge_falsified("bad", "rca_0")  # dampen=0.5

        for i in range(total):
            # Fresh alternative
            fresh_id = f"fresh_{i}"
            g.add_node(fresh_id, NodeType.HYPOTHESIS, f"fresh {i}", confidence=0.8)

            # Get dampened candidates: bad (w=0.4) vs fresh (w=0.8)
            candidates = g.get_dampened_candidates(["bad", fresh_id], min_weight=0.0)

            # If bad node wins (higher dampened weight than fresh), that's a repeat error
            if candidates and candidates[0][0] == "bad":
                repeated_errors += 1

        repeat_rate = repeated_errors / total
        assert repeat_rate <= 0.10, f"VM-11 FAIL: repeat_rate={repeat_rate:.2%} > 10%"


# ---------------------------------------------------------------------------
# Iteration & statistics
# ---------------------------------------------------------------------------


class TestGraphStats:
    def test_stats_empty(self, graph):
        s = graph.stats()
        assert s.node_count == 0
        assert s.edge_count == 0

    def test_stats_counts_node_types(self, graph):
        graph.add_node("h1", NodeType.HYPOTHESIS, "x")
        graph.add_node("h2", NodeType.HYPOTHESIS, "y")
        graph.add_node("i1", NodeType.INVARIANT, "z")
        graph.add_node("r1", NodeType.RCA_ROOT, "w")
        s = graph.stats()
        assert s.hypothesis_count == 2
        assert s.invariant_count == 1
        assert s.rca_root_count == 1

    def test_stats_counts_falsified_edges(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.RCA_ROOT, "b")
        graph.add_edge_falsified("a", "b")
        s = graph.stats()
        assert s.falsified_edge_count == 1
        assert s.dampened_node_count == 1

    def test_iter_nodes_all(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.INVARIANT, "b")
        nodes = list(graph.iter_nodes())
        assert len(nodes) == 2

    def test_iter_nodes_filtered(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.INVARIANT, "b")
        hypos = list(graph.iter_nodes(NodeType.HYPOTHESIS))
        assert len(hypos) == 1
        assert hypos[0].node_id == "a"

    def test_iter_edges_filtered(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.RCA_ROOT, "b")
        graph.add_node("c", NodeType.HYPOTHESIS, "c")
        graph.add_edge("a", "c", EdgeType.SUPPORTS)
        graph.add_edge_falsified("a", "b")
        falsified = list(graph.iter_edges(EdgeType.FALSIFIED))
        assert len(falsified) == 1

    def test_clear(self, graph):
        graph.add_node("a", NodeType.HYPOTHESIS, "a")
        graph.add_node("b", NodeType.HYPOTHESIS, "b")
        graph.clear()
        assert len(graph) == 0


# ---------------------------------------------------------------------------
# LRU eviction (max_nodes cap)
# ---------------------------------------------------------------------------


class TestMaxNodesEviction:
    def test_eviction_on_overflow(self):
        g = CognitiveStateGraph(max_nodes=3)
        g.add_node("a", NodeType.HYPOTHESIS, "a")
        g.add_node("b", NodeType.HYPOTHESIS, "b")
        g.add_node("c", NodeType.HYPOTHESIS, "c")
        # Adding 4th should evict oldest HYPOTHESIS (a)
        g.add_node("d", NodeType.HYPOTHESIS, "d")
        assert len(g) == 3

    def test_invariant_not_evicted(self):
        g = CognitiveStateGraph(max_nodes=3)
        g.add_node("a", NodeType.INVARIANT, "protected invariant")
        time.sleep(0.001)
        g.add_node("b", NodeType.HYPOTHESIS, "b")
        time.sleep(0.001)
        g.add_node("c", NodeType.HYPOTHESIS, "c")
        # Adding 4th: should evict oldest HYPOTHESIS (b or c), not invariant "a"
        g.add_node("d", NodeType.HYPOTHESIS, "d")
        assert g.get_node("a") is not None, "INVARIANT must not be evicted"

    def test_no_oom_at_10000_nodes(self):
        """Gate 2: graph must not OOM with 10,000 nodes."""
        g = CognitiveStateGraph(max_nodes=10_000)
        for i in range(10_000):
            g.add_node(f"node_{i}", NodeType.HYPOTHESIS, f"content {i}")
        assert len(g) == 10_000


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_add_nodes(self, graph):
        errors = []

        def add_nodes(prefix: str):
            try:
                for i in range(50):
                    graph.add_node(f"{prefix}_{i}", NodeType.HYPOTHESIS, f"node {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_nodes, args=(f"t{j}",)) for j in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
