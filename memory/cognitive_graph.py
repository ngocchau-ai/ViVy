"""
Cognitive State Graph — ViVy Final V1.0 Sprint 2.

Triển khai Thought Ecology Topology (Cognitive State Graph) theo
ARCHITECTURE_V5.md Mục 6. Graph lưu trữ và truy vết các trạng thái
nhận thức của ViVy theo thời gian, độc lập hoàn toàn với KV Cache.

Node types (ARCH §6.1):
  - HYPOTHESIS: Một giả thuyết hành động chưa được xác minh.
  - INVARIANT:  Một nguyên lý đã được xác nhận là đúng (promoted từ HYPOTHESIS).
  - RCA_ROOT:   Root Cause của một chuỗi lỗi lặp lại.

Edge types (ARCH §6.2):
  - SUPPORTS:   Bằng chứng ủng hộ một node khác.
  - FALSIFIED:  Node đã bị bác bỏ (Error-Dampening — VM-11).
  - DERIVED_FROM: Node được suy diễn từ một node khác.

Design:
  - Adjacency list representation → O(1) node lookup by ID.
  - FALSIFIED edges trigger Error-Dampening: giảm xác suất chọn
    lại một hành động đã bị bác bỏ (VM-11: repeat rate ≤ 10%).
  - Graph KHÔNG lưu raw token sequences (no KV cache coupling).
  - Thread-safe cho concurrent ViVy reasoning sessions.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2 — HOH-VIVY-FINAL-V1): Initial implementation.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeType(StrEnum):
    """Semantic role of a node in the Cognitive State Graph."""

    HYPOTHESIS = "HYPOTHESIS"
    INVARIANT = "INVARIANT"
    RCA_ROOT = "RCA_ROOT"


class EdgeType(StrEnum):
    """Relationship type between two nodes."""

    SUPPORTS = "SUPPORTS"
    FALSIFIED = "FALSIFIED"
    DERIVED_FROM = "DERIVED_FROM"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GraphNode:
    """A single node in the Cognitive State Graph.

    Attributes
    ----------
    node_id:
        Unique string identifier.
    node_type:
        HYPOTHESIS | INVARIANT | RCA_ROOT.
    content:
        Human-readable description of this cognitive state.
    embedding:
        Optional float vector embedding (from ElasticNCore hidden state).
        Used by HebbianRecall for O(1) lookup.
    confidence:
        Current confidence score in [0, 1].
    created_at:
        UNIX timestamp of node creation.
    metadata:
        Arbitrary key-value metadata.
    falsified_count:
        Number of times this node has been connected to a FALSIFIED edge.
    """

    node_id: str
    node_type: NodeType
    content: str
    embedding: list[float] | None = None
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    falsified_count: int = 0

    def is_dampened(self) -> bool:
        """True when this node has been falsified ≥ 1 time (Error-Dampening)."""
        return self.falsified_count > 0

    def dampen_factor(self) -> float:
        """Multiplicative penalty applied to this node's selection probability.

        Formula: 0.5 ^ falsified_count (halves each successive falsification).
        Ensures error repeat rate converges well below 10% (VM-11).
        """
        return 0.5 ** self.falsified_count


@dataclass
class GraphEdge:
    """A directed edge in the Cognitive State Graph.

    Attributes
    ----------
    source_id:
        Source node ID.
    target_id:
        Target node ID.
    edge_type:
        SUPPORTS | FALSIFIED | DERIVED_FROM.
    weight:
        Edge weight (relevance strength) in [0, 1].
    created_at:
        UNIX timestamp of edge creation.
    """

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class GraphStats:
    """Snapshot of CognitiveStateGraph metrics."""

    node_count: int
    edge_count: int
    hypothesis_count: int
    invariant_count: int
    rca_root_count: int
    falsified_edge_count: int
    dampened_node_count: int


# ---------------------------------------------------------------------------
# CognitiveStateGraph
# ---------------------------------------------------------------------------


class CognitiveStateGraph:
    """In-memory directed graph representing ViVy's Cognitive State.

    Implements the Thought Ecology Topology (ARCH §6):
      - Nodes hold cognitive states (hypotheses, invariants, RCA roots).
      - FALSIFIED edges trigger Error-Dampening on source nodes (VM-11).
      - Graph is independent of KV Cache — stores structural state only,
        never raw token sequences.

    Thread-safe: all mutations are protected by an internal RLock.

    Parameters
    ----------
    max_nodes:
        Hard cap on graph size to prevent unbounded memory growth.
        When exceeded, oldest HYPOTHESIS nodes are evicted (LRU-lite).
    """

    def __init__(self, max_nodes: int = 10_000) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        # Adjacency: node_id → list of outgoing edge indices
        self._adj_out: dict[str, list[int]] = {}
        # Reverse adjacency: node_id → list of incoming edge indices
        self._adj_in: dict[str, list[int]] = {}
        self._max_nodes = max_nodes
        self._lock = threading.RLock()
        logger.debug("CognitiveStateGraph: initialised max_nodes=%d", max_nodes)

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(
        self,
        node_id: str,
        node_type: NodeType | str,
        content: str,
        embedding: list[float] | None = None,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> GraphNode:
        """Add a new node to the graph (or update if it already exists).

        Parameters
        ----------
        node_id:
            Unique string identifier. Must be non-empty.
        node_type:
            NodeType enum value or string.
        content:
            Semantic description of this cognitive state.
        embedding:
            Optional float vector (from ElasticNCore hidden state).
        confidence:
            Initial confidence score in [0, 1].
        metadata:
            Optional key-value metadata.

        Returns
        -------
        GraphNode
            The created (or updated) node.
        """
        if not node_id:
            raise ValueError("node_id must be non-empty")
        node_type = NodeType(node_type)
        confidence = float(max(0.0, min(1.0, confidence)))

        with self._lock:
            if node_id in self._nodes:
                # Update existing node
                node = self._nodes[node_id]
                node.content = content
                node.confidence = confidence
                if embedding is not None:
                    node.embedding = embedding
                if metadata:
                    node.metadata.update(metadata)
                logger.debug("CognitiveStateGraph: updated node=%s type=%s", node_id, node_type)
                return node

            # Enforce max_nodes cap by evicting oldest HYPOTHESIS nodes
            if len(self._nodes) >= self._max_nodes:
                self._evict_oldest_hypothesis()

            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                content=content,
                embedding=embedding,
                confidence=confidence,
                metadata=metadata or {},
            )
            self._nodes[node_id] = node
            self._adj_out[node_id] = []
            self._adj_in[node_id] = []
            logger.debug("CognitiveStateGraph: added node=%s type=%s", node_id, node_type)
            return node

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by ID. Returns None if not found."""
        with self._lock:
            return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its incident edges.

        Returns True if the node existed, False otherwise.
        """
        with self._lock:
            if node_id not in self._nodes:
                return False
            # Remove incident edges (rebuild edge list)
            incident = set(self._adj_out.get(node_id, []) + self._adj_in.get(node_id, []))
            self._edges = [e for i, e in enumerate(self._edges) if i not in incident]
            # Rebuild adjacency lists for remaining nodes
            self._rebuild_adjacency()
            del self._nodes[node_id]
            self._adj_out.pop(node_id, None)
            self._adj_in.pop(node_id, None)
            logger.debug("CognitiveStateGraph: removed node=%s", node_id)
            return True

    def promote_to_invariant(self, node_id: str) -> bool:
        """Promote a HYPOTHESIS node to INVARIANT.

        Returns True if promotion occurred, False if node not found or
        already an INVARIANT/RCA_ROOT.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None or node.node_type != NodeType.HYPOTHESIS:
                return False
            node.node_type = NodeType.INVARIANT
            node.confidence = min(1.0, node.confidence + 0.2)
            logger.info("CognitiveStateGraph: promoted node=%s → INVARIANT", node_id)
            return True

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType | str,
        weight: float = 1.0,
    ) -> GraphEdge:
        """Add a directed edge between two existing nodes.

        If source_id or target_id does not exist, they are auto-created
        as HYPOTHESIS nodes with empty content (stub nodes).

        Parameters
        ----------
        source_id:
            Source node ID.
        target_id:
            Target node ID.
        edge_type:
            EdgeType enum value or string.
        weight:
            Edge weight in [0, 1].

        Returns
        -------
        GraphEdge
        """
        edge_type = EdgeType(edge_type)
        weight = float(max(0.0, min(1.0, weight)))

        with self._lock:
            # Auto-create stub nodes if needed
            if source_id not in self._nodes:
                self.add_node(source_id, NodeType.HYPOTHESIS, content="[auto-stub]")
            if target_id not in self._nodes:
                self.add_node(target_id, NodeType.HYPOTHESIS, content="[auto-stub]")

            edge = GraphEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
            )
            edge_idx = len(self._edges)
            self._edges.append(edge)
            self._adj_out[source_id].append(edge_idx)
            self._adj_in[target_id].append(edge_idx)

            # Error-Dampening: if FALSIFIED edge, increment source's falsified_count
            if edge_type == EdgeType.FALSIFIED:
                self._nodes[source_id].falsified_count += 1
                logger.info(
                    "CognitiveStateGraph: FALSIFIED edge %s→%s; node falsified_count=%d",
                    source_id,
                    target_id,
                    self._nodes[source_id].falsified_count,
                )

            return edge

    def add_edge_falsified(
        self,
        source_id: str,
        target_id: str,
        weight: float = 1.0,
    ) -> GraphEdge:
        """Convenience: add a FALSIFIED edge and trigger Error-Dampening.

        This is the primary VM-11 mechanism: when ViVy detects a repeated
        error, it calls add_edge_falsified() to reduce the source node's
        selection probability via dampen_factor().
        """
        return self.add_edge(source_id, target_id, EdgeType.FALSIFIED, weight=weight)

    def get_outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        """Return all outgoing edges from a node."""
        with self._lock:
            return [self._edges[i] for i in self._adj_out.get(node_id, [])]

    def get_incoming_edges(self, node_id: str) -> list[GraphEdge]:
        """Return all incoming edges to a node."""
        with self._lock:
            return [self._edges[i] for i in self._adj_in.get(node_id, [])]

    # ------------------------------------------------------------------
    # Dampened candidate selection (VM-11 mechanism)
    # ------------------------------------------------------------------

    def get_dampened_candidates(
        self,
        candidates: list[str],
        min_weight: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Return (node_id, effective_weight) for a list of candidates,
        applying Error-Dampening for falsified nodes.

        Parameters
        ----------
        candidates:
            List of node IDs to score.
        min_weight:
            Minimum weight threshold below which candidates are excluded.

        Returns
        -------
        list of (node_id, effective_weight) sorted descending by weight.
        """
        with self._lock:
            results: list[tuple[str, float]] = []
            for nid in candidates:
                node = self._nodes.get(nid)
                if node is None:
                    continue
                effective_w = node.confidence * node.dampen_factor()
                if effective_w >= min_weight:
                    results.append((nid, effective_w))
            results.sort(key=lambda x: x[1], reverse=True)
            return results

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def iter_nodes(self, node_type: NodeType | None = None) -> Iterator[GraphNode]:
        """Iterate over all nodes, optionally filtered by type."""
        with self._lock:
            nodes = list(self._nodes.values())
        for node in nodes:
            if node_type is None or node.node_type == node_type:
                yield node

    def iter_edges(self, edge_type: EdgeType | None = None) -> Iterator[GraphEdge]:
        """Iterate over all edges, optionally filtered by type."""
        with self._lock:
            edges = list(self._edges)
        for edge in edges:
            if edge_type is None or edge.edge_type == edge_type:
                yield edge

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> GraphStats:
        """Return a snapshot of graph metrics."""
        with self._lock:
            hypothesis_count = sum(1 for n in self._nodes.values() if n.node_type == NodeType.HYPOTHESIS)
            invariant_count = sum(1 for n in self._nodes.values() if n.node_type == NodeType.INVARIANT)
            rca_root_count = sum(1 for n in self._nodes.values() if n.node_type == NodeType.RCA_ROOT)
            falsified_count = sum(1 for e in self._edges if e.edge_type == EdgeType.FALSIFIED)
            dampened_count = sum(1 for n in self._nodes.values() if n.is_dampened())
            return GraphStats(
                node_count=len(self._nodes),
                edge_count=len(self._edges),
                hypothesis_count=hypothesis_count,
                invariant_count=invariant_count,
                rca_root_count=rca_root_count,
                falsified_edge_count=falsified_count,
                dampened_node_count=dampened_count,
            )

    def clear(self) -> None:
        """Remove all nodes and edges."""
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._adj_out.clear()
            self._adj_in.clear()
        logger.debug("CognitiveStateGraph: cleared")

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_oldest_hypothesis(self) -> None:
        """Evict the oldest HYPOTHESIS node to make room (LRU-lite).

        INVARIANT and RCA_ROOT nodes are never evicted.
        """
        oldest_id: str | None = None
        oldest_time = float("inf")
        for nid, node in self._nodes.items():
            if node.node_type == NodeType.HYPOTHESIS and node.created_at < oldest_time:
                oldest_time = node.created_at
                oldest_id = nid
        if oldest_id is not None:
            self.remove_node(oldest_id)
            logger.debug("CognitiveStateGraph: evicted oldest HYPOTHESIS=%s", oldest_id)

    def _rebuild_adjacency(self) -> None:
        """Rebuild adjacency maps after node/edge removal."""
        for nid in self._nodes:
            self._adj_out[nid] = []
            self._adj_in[nid] = []
        for i, edge in enumerate(self._edges):
            if edge.source_id in self._adj_out and edge.target_id in self._adj_in:
                self._adj_out[edge.source_id].append(i)
                self._adj_in[edge.target_id].append(i)
