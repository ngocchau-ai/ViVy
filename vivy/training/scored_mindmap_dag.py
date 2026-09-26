"""Scored Mindmap DAG — Planning + QC for orchestration decisions (TD-6).

Vivy plans decision structure BEFORE generation to reduce mid-generation
drift, then scores each node for confidence. When a node's score drops
below threshold, the DAG re-routes to a better path.

Structure:
    MindmapDAG
    ├── nodes: dict[node_id -> DecisionNode]
    │   ├── node_id, input_context, strategy
    │   ├── model_target: alias
    │   ├── score: float (confidence 0-1)
    │   └── children: list[child node_ids]
    ├── plan(input_context) -> DAGPath — best-scored root-to-leaf path
    ├── score_path(path) -> float — mean score along path
    └── reroute(node_id, new_score) -> DAGPath — re-plan after score change

DAG = Directed Acyclic Graph. Cycle detection on edge insertion.
Plan before generate. Score nodes. Re-route on low confidence.

Changelog:
    25/09/2026 (Claude Code — Wave 3A): Initial.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DecisionNode:
    """One decision node in the mindmap DAG."""

    node_id: str
    input_context: str = ""
    strategy: str = ""
    model_target: str = ""
    score: float = 0.5
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "input_context": self.input_context,
            "strategy": self.strategy,
            "model_target": self.model_target,
            "score": self.score,
            "children": list(self.children),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DAGPath:
    """A path through the DAG from root to leaf."""

    node_ids: tuple[str, ...]
    score: float
    rationale: str

    @property
    def length(self) -> int:
        return len(self.node_ids)

    @property
    def leaf_id(self) -> str:
        return self.node_ids[-1] if self.node_ids else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_ids": list(self.node_ids),
            "score": self.score,
            "rationale": self.rationale,
            "length": self.length,
        }


class MindmapDAG:
    """Scored DAG for orchestration planning and quality control.

    Nodes represent decisions (strategy + model target). Edges represent
    sequential flow. The DAG enforces acyclicity, computes path scores,
    and re-routes when confidence drops below threshold.
    """

    def __init__(self, *, score_threshold: float = 0.3) -> None:
        self._nodes: dict[str, DecisionNode] = {}
        self._parents: dict[str, list[str]] = {}  # child_id -> [parent_ids]
        self._score_threshold = score_threshold

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def score_threshold(self) -> float:
        return self._score_threshold

    # --- graph construction ---

    def add_node(self, node: DecisionNode) -> None:
        """Add a node. Raises ValueError on duplicate id."""
        if node.node_id in self._nodes:
            raise ValueError(f"duplicate node_id: {node.node_id}")
        self._nodes[node.node_id] = node
        self._parents.setdefault(node.node_id, [])

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Connect from_id → to_id. Raises ValueError on cycle or missing node."""
        if from_id not in self._nodes:
            raise KeyError(f"node not found: {from_id}")
        if to_id not in self._nodes:
            raise KeyError(f"node not found: {to_id}")
        if from_id == to_id:
            raise ValueError(f"self-loop: {from_id}")
        if self._would_cycle(from_id, to_id):
            raise ValueError(f"cycle detected: {from_id} -> {to_id}")
        parent = self._nodes[from_id]
        if to_id not in parent.children:
            parent.children.append(to_id)
        self._parents.setdefault(to_id, [])
        if from_id not in self._parents[to_id]:
            self._parents[to_id].append(from_id)

    def _would_cycle(self, from_id: str, to_id: str) -> bool:
        """Check if edge from_id→to_id would create a cycle."""
        if from_id == to_id:
            return True
        # BFS from to_id: if we can reach from_id, adding the edge cycles.
        visited: set[str] = set()
        queue = [to_id]
        while queue:
            current = queue.pop(0)
            if current == from_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self._nodes[current].children)
        return False

    def get_node(self, node_id: str) -> DecisionNode | None:
        return self._nodes.get(node_id)

    def roots(self) -> list[DecisionNode]:
        """Nodes with no parents (entry points)."""
        return [
            n for nid, n in self._nodes.items()
            if not self._parents.get(nid)
        ]

    def leaves(self) -> list[DecisionNode]:
        return [n for n in self._nodes.values() if n.is_leaf()]

    # --- planning ---

    def plan(self, input_context: str = "") -> DAGPath:
        """Find the best-scored root-to-leaf path.

        Scoring: greedy best-first. At each node, pick the child with the
        highest score. Starts from root nodes matching input_context (or
        all roots if no match). Raises ValueError if DAG is empty.
        """
        if not self._nodes:
            raise ValueError("empty DAG")

        candidates = self._matching_roots(input_context)
        if not candidates:
            candidates = self.roots()
        if not candidates:
            raise ValueError("no root nodes")

        best_path: DAGPath | None = None
        for root in candidates:
            path = self._greedy_path(root.node_id)
            if best_path is None or path.score > best_path.score:
                best_path = path

        assert best_path is not None
        return best_path

    def _matching_roots(self, input_context: str) -> list[DecisionNode]:
        if not input_context:
            return self.roots()
        return [
            r for r in self.roots()
            if input_context in r.input_context or not r.input_context
        ]

    def _greedy_path(self, start_id: str) -> DAGPath:
        """Greedy best-scored path from start_id to a leaf."""
        node_ids: list[str] = []
        scores: list[float] = []
        current = start_id
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            node = self._nodes[current]
            node_ids.append(current)
            scores.append(node.score)
            if node.is_leaf():
                break
            # Pick highest-scored child.
            best_child = max(
                node.children,
                key=lambda cid: self._nodes[cid].score,
            )
            current = best_child

        avg_score = sum(scores) / len(scores) if scores else 0.0
        return DAGPath(
            node_ids=tuple(node_ids),
            score=avg_score,
            rationale=f"greedy path from {start_id}, {len(node_ids)} nodes",
        )

    def score_path(self, node_ids: tuple[str, ...] | list[str]) -> float:
        """Mean score across nodes in the path.

        Raises KeyError if any node is missing.
        """
        if not node_ids:
            return 0.0
        scores = [self._nodes[nid].score for nid in node_ids]
        return sum(scores) / len(scores)

    # --- quality control ---

    def reroute(self, node_id: str, new_score: float) -> DAGPath:
        """Update a node's score and re-plan.

        If the new score drops below threshold, the greedy planner will
        naturally avoid this node (if alternatives exist). Returns the
        new best path after the score change.

        Raises KeyError if node not found.
        Raises ValueError if new_score out of [0, 1].
        """
        if node_id not in self._nodes:
            raise KeyError(f"node not found: {node_id}")
        if not 0.0 <= new_score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {new_score}")

        self._nodes[node_id].score = new_score

        # Find the root that leads here and re-plan.
        root_id = self._find_root_for(node_id)
        if root_id is None:
            return self.plan()
        return self._greedy_path(root_id)

    def _find_root_for(self, node_id: str) -> str | None:
        """Walk parents up to the first root ancestor."""
        visited: set[str] = set()
        current = node_id
        while current and current not in visited:
            visited.add(current)
            parents = self._parents.get(current, [])
            if not parents:
                return current
            current = parents[0]
        return None

    def check_threshold(self) -> list[str]:
        """Return node_ids whose score is below the threshold."""
        return [
            nid for nid, n in self._nodes.items()
            if n.score < self._score_threshold
        ]

    # --- tracing ---

    def trace(self, node_ids: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
        """Extract decision records for a path (input → decision → output trace)."""
        records = []
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node is None:
                continue
            records.append({
                "node_id": node.node_id,
                "input_context": node.input_context,
                "strategy": node.strategy,
                "model_target": node.model_target,
                "score": node.score,
            })
        return records

    # --- serialization ---

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "score_threshold": self._score_threshold,
            "node_count": self.node_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MindmapDAG:
        dag = cls(score_threshold=data.get("score_threshold", 0.3))
        for nd in data.get("nodes", []):
            node = DecisionNode(
                node_id=nd["node_id"],
                input_context=nd.get("input_context", ""),
                strategy=nd.get("strategy", ""),
                model_target=nd.get("model_target", ""),
                score=nd.get("score", 0.5),
                children=list(nd.get("children", [])),
                metadata=dict(nd.get("metadata", {})),
            )
            dag._nodes[node.node_id] = node
            dag._parents.setdefault(node.node_id, [])
        # Drop ghost children (referenced but absent from nodes) to prevent
        # KeyError in _greedy_path / score_path on untrusted input.
        for node in dag._nodes.values():
            node.children = [c for c in node.children if c in dag._nodes]
        for node in dag._nodes.values():
            for cid in node.children:
                dag._parents.setdefault(cid, [])
                if node.node_id not in dag._parents[cid]:
                    dag._parents[cid].append(node.node_id)
        return dag
