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
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

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


# ---------------------------------------------------------------------------
# Stateful & Scored Cognitive Mindmap DAG  (PLAN-VIVY-SCORED-MINDMAP-DAG-2026-09-24)
# ---------------------------------------------------------------------------


class TaskBranchStatus(StrEnum):
    """Lifecycle status of a subtask branch in the Mindmap DAG."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    STOPPED = "STOPPED"
    VERIFIED_PASS = "VERIFIED_PASS"
    PIVOTED = "PIVOTED"


@dataclass
class NodeScoreMetrics:
    """Independent score breakdown for a ScoredTaskNode.

    Attributes
    ----------
    progress:
        Completion progress in [0.0, 1.0].
    efficiency:
        Resource / token efficiency in [0.0, 1.0].
    quality:
        Output quality in [0.0, 1.0].
    composite_score:
        Weighted aggregate in [0.0, 10.0] (e.g. 3.0/10, 9.5/10).
    """

    progress: float = 0.0
    efficiency: float = 0.0
    quality: float = 0.0
    composite_score: float = 0.0

    def compute_composite(self) -> float:
        """Derive composite_score from the three sub-metrics (0-10 scale)."""
        self.composite_score = round(
            (self.progress + self.efficiency + self.quality) / 3.0 * 10.0, 2
        )
        return self.composite_score

    def to_dict(self) -> dict[str, float]:
        return {
            "progress": self.progress,
            "efficiency": self.efficiency,
            "quality": self.quality,
            "composite_score": self.composite_score,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NodeScoreMetrics:
        return cls(
            progress=float(d.get("progress", 0.0)),
            efficiency=float(d.get("efficiency", 0.0)),
            quality=float(d.get("quality", 0.0)),
            composite_score=float(d.get("composite_score", 0.0)),
        )


@dataclass
class ScoredTaskNode:
    """A scored subtask node in the Cognitive Mindmap DAG.

    Links 1:1 with a GraphNode in CognitiveStateGraph via ``task_id``.

    Attributes
    ----------
    task_id:
        Unique identifier (e.g. ``subtask-150``).
    parent_id:
        Parent task ID, or None for root.
    intent:
        Human-readable goal of this subtask.
    status:
        Current TaskBranchStatus.
    score:
        Composite score 0.0-10.0 (e.g. 3.0 for 3/10).
    score_metrics:
        Detailed score breakdown.
    rca_reason:
        Root-cause explanation when the branch failed.
    alternative_id:
        ID of the pivot branch that replaced this one.
    evidence_receipt:
        Path or ID of the evidence receipt for verification.
    negative_constraints:
        Forbidden patterns learned from this branch's failure.
    """

    task_id: str
    intent: str
    parent_id: str | None = None
    status: TaskBranchStatus = TaskBranchStatus.PENDING
    score: float = 0.0
    score_metrics: NodeScoreMetrics = field(default_factory=NodeScoreMetrics)
    rca_reason: str | None = None
    alternative_id: str | None = None
    evidence_receipt: str | None = None
    negative_constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "parent_id": self.parent_id,
            "intent": self.intent,
            "status": self.status.value,
            "score": self.score,
            "score_metrics": self.score_metrics.to_dict(),
            "rca_reason": self.rca_reason,
            "alternative_id": self.alternative_id,
            "evidence_receipt": self.evidence_receipt,
            "negative_constraints": list(self.negative_constraints),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScoredTaskNode:
        return cls(
            task_id=d["task_id"],
            parent_id=d.get("parent_id"),
            intent=d["intent"],
            status=TaskBranchStatus(d.get("status", "PENDING")),
            score=float(d.get("score", 0.0)),
            score_metrics=NodeScoreMetrics.from_dict(d.get("score_metrics", {})),
            rca_reason=d.get("rca_reason"),
            alternative_id=d.get("alternative_id"),
            evidence_receipt=d.get("evidence_receipt"),
            negative_constraints=list(d.get("negative_constraints", [])),
        )


class ScoredMindmapDAG:
    """Stateful & Scored Cognitive Mindmap DAG.

    Manages ScoredTaskNode branches with independent scores and statuses.
    Failed branches are never deleted — they persist as Negative Constraints
    to dampen error repeats (VM-11).  Integrates with CognitiveStateGraph
    for FALSIFIED / DERIVED_FROM edges.

    Thread-safe: all mutations protected by an internal RLock.
    """

    def __init__(self, graph: CognitiveStateGraph | None = None) -> None:
        self._nodes: dict[str, ScoredTaskNode] = {}
        self._graph = graph if graph is not None else CognitiveStateGraph()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Node lifecycle
    # ------------------------------------------------------------------

    def create_node(
        self,
        task_id: str,
        intent: str,
        parent_id: str | None = None,
    ) -> ScoredTaskNode:
        """Create a new PENDING subtask node."""
        with self._lock:
            if task_id in self._nodes:
                raise ValueError(f"task_id already exists: {task_id}")
            node = ScoredTaskNode(
                task_id=task_id,
                intent=intent,
                parent_id=parent_id,
                status=TaskBranchStatus.PENDING,
            )
            self._nodes[task_id] = node
            # Mirror into CognitiveStateGraph as a HYPOTHESIS node
            self._graph.add_node(
                node_id=task_id,
                node_type=NodeType.HYPOTHESIS,
                content=intent,
            )
            logger.info("ScoredMindmapDAG: created node=%s parent=%s", task_id, parent_id)
            return node

    def mark_in_progress(self, task_id: str) -> ScoredTaskNode:
        """Transition a PENDING node to IN_PROGRESS."""
        with self._lock:
            node = self._require(task_id)
            node.status = TaskBranchStatus.IN_PROGRESS
            return node

    def score_and_verify(
        self,
        task_id: str,
        score: float,
        evidence_receipt: str | None = None,
        progress: float = 1.0,
        efficiency: float = 1.0,
        quality: float = 1.0,
    ) -> ScoredTaskNode:
        """Mark a branch as VERIFIED_PASS with the given score."""
        with self._lock:
            node = self._require(task_id)
            node.status = TaskBranchStatus.VERIFIED_PASS
            node.score = float(max(0.0, min(10.0, score)))
            node.score_metrics = NodeScoreMetrics(
                progress=progress, efficiency=efficiency, quality=quality
            )
            node.score_metrics.compute_composite()
            node.evidence_receipt = evidence_receipt
            # Promote the corresponding GraphNode to INVARIANT
            self._graph.promote_to_invariant(task_id)
            logger.info(
                "ScoredMindmapDAG: VERIFIED_PASS node=%s score=%.1f", task_id, node.score
            )
            return node

    def stop_and_score(
        self,
        task_id: str,
        score: float,
        rca_reason: str,
        negative_constraint: str,
    ) -> ScoredTaskNode:
        """Stop a failed branch, assign score, record negative constraint.

        Adds a FALSIFIED edge in CognitiveStateGraph to trigger VM-11
        Error-Dampening on the corresponding GraphNode.
        """
        with self._lock:
            node = self._require(task_id)
            node.status = TaskBranchStatus.STOPPED
            node.score = float(max(0.0, min(10.0, score)))
            node.rca_reason = rca_reason
            if negative_constraint and negative_constraint not in node.negative_constraints:
                node.negative_constraints.append(negative_constraint)
            # FALSIFIED edge → Error-Dampening (VM-11)
            self._graph.add_edge_falsified(
                source_id=task_id,
                target_id=f"{task_id}#falsified",
                weight=1.0,
            )
            logger.info(
                "ScoredMindmapDAG: STOPPED node=%s score=%.1f reason=%s",
                task_id, node.score, rca_reason,
            )
            return node

    def pivot_alternative(
        self,
        failed_task_id: str,
        new_task_id: str,
        new_intent: str,
    ) -> ScoredTaskNode:
        """Open a new branch that inherits negative constraints from the failed one.

        Sets ``failed_node.status = PIVOTED``, links ``alternative_id``,
        creates a new IN_PROGRESS node, adds a DERIVED_FROM edge, and
        copies all negative_constraints to the new node.
        """
        with self._lock:
            failed = self._require(failed_task_id)
            failed.status = TaskBranchStatus.PIVOTED
            failed.alternative_id = new_task_id

            new_node = ScoredTaskNode(
                task_id=new_task_id,
                intent=new_intent,
                parent_id=failed.parent_id,
                status=TaskBranchStatus.IN_PROGRESS,
                negative_constraints=list(failed.negative_constraints),
            )
            self._nodes[new_task_id] = new_node

            # Mirror into CognitiveStateGraph
            self._graph.add_node(
                node_id=new_task_id,
                node_type=NodeType.HYPOTHESIS,
                content=new_intent,
            )
            # DERIVED_FROM edge: new ← failed (new is derived from the failure lesson)
            self._graph.add_edge(
                source_id=new_task_id,
                target_id=failed_task_id,
                edge_type=EdgeType.DERIVED_FROM,
                weight=1.0,
            )
            logger.info(
                "ScoredMindmapDAG: PIVOTED %s → %s (inherited %d constraints)",
                failed_task_id, new_task_id, len(new_node.negative_constraints),
            )
            return new_node

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, task_id: str) -> ScoredTaskNode | None:
        with self._lock:
            return self._nodes.get(task_id)

    def get_active_nodes(self) -> list[ScoredTaskNode]:
        """Return all nodes currently IN_PROGRESS."""
        with self._lock:
            return [
                n for n in self._nodes.values()
                if n.status == TaskBranchStatus.IN_PROGRESS
            ]

    def get_negative_constraints(self) -> list[tuple[str, str, float]]:
        """Return (task_id, constraint, score) for every failed branch.

        Includes both STOPPED and PIVOTED nodes — a PIVOTED node still
        carries its failure lessons as Negative Constraints.
        """
        with self._lock:
            results: list[tuple[str, str, float]] = []
            for node in self._nodes.values():
                if node.status in (
                    TaskBranchStatus.STOPPED,
                    TaskBranchStatus.PIVOTED,
                ):
                    for constraint in node.negative_constraints:
                        results.append((node.task_id, constraint, node.score))
            return results

    def all_nodes(self) -> list[ScoredTaskNode]:
        with self._lock:
            return list(self._nodes.values())

    @property
    def graph(self) -> CognitiveStateGraph:
        return self._graph

    # ------------------------------------------------------------------
    # Serialization (Phase 4 — WAL Checkpoint)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "version": 1,
                "nodes": [n.to_dict() for n in self._nodes.values()],
            }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        graph: CognitiveStateGraph | None = None,
    ) -> ScoredMindmapDAG:
        dag = cls(graph=graph)
        for nd in data.get("nodes", []):
            node = ScoredTaskNode.from_dict(nd)
            dag._nodes[node.task_id] = node
        return dag

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require(self, task_id: str) -> ScoredTaskNode:
        node = self._nodes.get(task_id)
        if node is None:
            raise KeyError(f"Unknown task_id: {task_id}")
        return node
