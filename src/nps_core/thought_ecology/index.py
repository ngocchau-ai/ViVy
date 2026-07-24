"""Thought ecology index: frozen snapshot digest and relation extraction.

Builds a deterministic, immutable ThoughtEcology from a PopulationSnapshot.
All fields are sorted and deduplicated for canonical comparison.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from nps_core.hypothesis_population.lifecycle import PopulationSnapshot
from nps_core.thought_ecology.errors import (
    AmbiguousEvidenceBucketError,
    ConflictingAssumptionError,
    DependencyCycleError,
    EcologyValidationError,
    SelfReferenceError,
    SnapshotMismatchError,
    UnknownThoughtError,
)
from nps_core.thought_ecology.relations import (
    ContradictionEdge,
    DependencyEdge,
    EvidencePlacement,
    OverlapEdge,
    SharedAssumptionLink,
)

__all__ = ["ThoughtEcology", "build"]

_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _check_thought_id(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise EcologyValidationError(f"{field} must be a string", path=field)
    if not _THOUGHT_ID_RE.match(value):
        raise EcologyValidationError(
            f"{field} must match THOUGHT-* pattern", path=field
        )
    return value


def _check_non_empty_str(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise EcologyValidationError(f"{field} must be a string", path=field)
    if not value or value.isspace():
        raise EcologyValidationError(f"{field} must be non-empty", path=field)
    return value


def _detect_cycle(adj: dict[str, tuple[str, ...]]) -> tuple[str, ...] | None:
    """Return a cycle path if one exists, else None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in adj}
    parent: dict[str, str | None] = {n: None for n in adj}

    def _dfs(node: str) -> tuple[str, ...] | None:
        color[node] = GRAY
        for nb in adj.get(node, ()):
            if nb not in color:
                continue
            if color[nb] == GRAY:
                cycle = [nb, node]
                cur = node
                while parent[cur] is not None and parent[cur] != nb:
                    cur = parent[cur]  # type: ignore[assignment]
                    cycle.append(cur)
                cycle.append(nb)
                cycle.reverse()
                return tuple(cycle)
            if color[nb] == WHITE:
                parent[nb] = node
                result = _dfs(nb)
                if result is not None:
                    return result
        color[node] = BLACK
        return None

    for n in sorted(adj):
        if color[n] == WHITE:
            result = _dfs(n)
            if result is not None:
                return result
    return None


@dataclass(frozen=True, slots=True)
class ThoughtEcology:
    """Frozen ecology with seven deterministic fields."""

    snapshot_digest: str
    thought_ids: tuple[str, ...]
    dependencies: tuple[DependencyEdge, ...]
    contradictions: tuple[ContradictionEdge, ...]
    overlaps: tuple[OverlapEdge, ...]
    shared_assumptions: tuple[SharedAssumptionLink, ...]
    evidence_placements: tuple[EvidencePlacement, ...]

    def __post_init__(self) -> None:
        # Validate thought_ids and all five relation collections are tuples
        if not isinstance(self.thought_ids, tuple):
            raise EcologyValidationError(
                "thought_ids must be a tuple", path="thought_ids"
            )
        for name in ("dependencies", "contradictions", "overlaps",
                      "shared_assumptions", "evidence_placements"):
            if not isinstance(getattr(self, name), tuple):
                raise EcologyValidationError(f"{name} must be a tuple", path=name)

        # Validate digest
        if not isinstance(self.snapshot_digest, str):
            raise EcologyValidationError(
                "snapshot_digest must be a string", path="snapshot_digest"
            )
        if not _DIGEST_RE.match(self.snapshot_digest):
            raise EcologyValidationError(
                "snapshot_digest must be a 64-char hex string", path="snapshot_digest"
            )

        # Validate thought_ids: unique, normalized lexical
        seen_ids: set[str] = set()
        for i, tid in enumerate(self.thought_ids):
            _check_thought_id(tid, field=f"thought_ids[{i}]")
            if tid in seen_ids:
                raise EcologyValidationError(
                    f"duplicate thought_id: {tid}", path=f"thought_ids[{i}]"
                )
            seen_ids.add(tid)
        # Normalize lexical order
        if list(self.thought_ids) != sorted(self.thought_ids):
            object.__setattr__(self, "thought_ids", tuple(sorted(self.thought_ids)))

        # Validate exact relation element types and endpoints
        for name, cls in (
            ("dependencies", DependencyEdge),
            ("contradictions", ContradictionEdge),
            ("overlaps", OverlapEdge),
            ("shared_assumptions", SharedAssumptionLink),
            ("evidence_placements", EvidencePlacement),
        ):
            val = getattr(self, name)
            for i, item in enumerate(val):
                if not isinstance(item, cls):
                    raise EcologyValidationError(
                        f"{name}[{i}] must be a {cls.__name__}", path=f"{name}[{i}]"
                    )

        # Validate endpoints in thought_ids
        id_set = frozenset(self.thought_ids)
        for i, edge in enumerate(self.dependencies):
            if edge.source_id not in id_set:
                raise EcologyValidationError(
                    f"dependencies[{i}].source_id {edge.source_id!r} not in thought_ids",
                    path=f"dependencies[{i}]",
                )
            if edge.target_id not in id_set:
                raise EcologyValidationError(
                    f"dependencies[{i}].target_id {edge.target_id!r} not in thought_ids",
                    path=f"dependencies[{i}]",
                )
        for i, edge in enumerate(self.contradictions):
            if edge.first_id not in id_set:
                raise EcologyValidationError(
                    f"contradictions[{i}].first_id {edge.first_id!r} not in thought_ids",
                    path=f"contradictions[{i}]",
                )
            if edge.second_id not in id_set:
                raise EcologyValidationError(
                    f"contradictions[{i}].second_id {edge.second_id!r} not in thought_ids",
                    path=f"contradictions[{i}]",
                )
        for i, edge in enumerate(self.overlaps):
            if edge.first_id not in id_set:
                raise EcologyValidationError(
                    f"overlaps[{i}].first_id {edge.first_id!r} not in thought_ids",
                    path=f"overlaps[{i}]",
                )
            if edge.second_id not in id_set:
                raise EcologyValidationError(
                    f"overlaps[{i}].second_id {edge.second_id!r} not in thought_ids",
                    path=f"overlaps[{i}]",
                )
        for i, link in enumerate(self.shared_assumptions):
            if link.first_thought_id not in id_set:
                raise EcologyValidationError(
                    f"shared_assumptions[{i}].first_thought_id {link.first_thought_id!r} not in thought_ids",
                    path=f"shared_assumptions[{i}]",
                )
            if link.second_thought_id not in id_set:
                raise EcologyValidationError(
                    f"shared_assumptions[{i}].second_thought_id {link.second_thought_id!r} not in thought_ids",
                    path=f"shared_assumptions[{i}]",
                )
        for i, ep in enumerate(self.evidence_placements):
            if ep.thought_id not in id_set:
                raise EcologyValidationError(
                    f"evidence_placements[{i}].thought_id {ep.thought_id!r} not in thought_ids",
                    path=f"evidence_placements[{i}]",
                )

        # Reject duplicate keys in dependencies
        dep_keys: set[tuple[str, str]] = set()
        for i, edge in enumerate(self.dependencies):
            key = (edge.source_id, edge.target_id)
            if key in dep_keys:
                raise EcologyValidationError(
                    f"duplicate dependency: {key}", path=f"dependencies[{i}]"
                )
            dep_keys.add(key)

        # Reject duplicate keys in contradictions
        contra_keys: set[tuple[str, str]] = set()
        for i, edge in enumerate(self.contradictions):
            key = (edge.first_id, edge.second_id)
            if key in contra_keys:
                raise EcologyValidationError(
                    f"duplicate contradiction: {key}", path=f"contradictions[{i}]"
                )
            contra_keys.add(key)

        # Reject duplicate keys in overlaps
        overlap_keys: set[tuple[str, str]] = set()
        for i, edge in enumerate(self.overlaps):
            key = (edge.first_id, edge.second_id)
            if key in overlap_keys:
                raise EcologyValidationError(
                    f"duplicate overlap: {key}", path=f"overlaps[{i}]"
                )
            overlap_keys.add(key)

        # Reject duplicate keys in shared_assumptions
        shared_keys: set[tuple[str, str, str]] = set()
        for i, link in enumerate(self.shared_assumptions):
            key = (link.assumption_id, link.first_thought_id, link.second_thought_id)
            if key in shared_keys:
                raise EcologyValidationError(
                    f"duplicate shared_assumption: {key}", path=f"shared_assumptions[{i}]"
                )
            shared_keys.add(key)

        # Reject duplicate evidence placements
        ep_keys: set[tuple[str, str, str]] = set()
        for i, ep in enumerate(self.evidence_placements):
            key = (ep.evidence_id, ep.thought_id, ep.bucket)
            if key in ep_keys:
                raise EcologyValidationError(
                    f"duplicate evidence placement: {key}", path=f"evidence_placements[{i}]"
                )
            ep_keys.add(key)

        # Check ambiguous evidence buckets
        evidence_buckets: dict[tuple[str, str], set[str]] = {}
        for i, ep in enumerate(self.evidence_placements):
            key = (ep.thought_id, ep.evidence_id)
            if key not in evidence_buckets:
                evidence_buckets[key] = set()
            evidence_buckets[key].add(ep.bucket)
        for (tid, eid), buckets in evidence_buckets.items():
            if len(buckets) > 1:
                raise AmbiguousEvidenceBucketError(
                    f"evidence {eid!r} in thought {tid} appears in buckets {sorted(buckets)}",
                    evidence_id=eid,
                    thought_id=tid,
                    buckets=tuple(sorted(buckets)),
                )

        # Check dependency cycles
        dep_adj: dict[str, list[str]] = {tid: [] for tid in self.thought_ids}
        for edge in self.dependencies:
            dep_adj[edge.source_id].append(edge.target_id)
        dep_adj_tuple = {k: tuple(sorted(v)) for k, v in dep_adj.items()}
        cycle = _detect_cycle(dep_adj_tuple)
        if cycle is not None:
            raise DependencyCycleError(
                f"dependency cycle detected: {' -> '.join(cycle)}",
                cycle=cycle,
            )

        # Normalize all relation tuples via object.__setattr__ with ADR sort keys
        object.__setattr__(
            self,
            "dependencies",
            tuple(sorted(self.dependencies, key=lambda e: (e.source_id, e.target_id))),
        )
        object.__setattr__(
            self,
            "contradictions",
            tuple(sorted(self.contradictions, key=lambda e: (e.first_id, e.second_id))),
        )
        object.__setattr__(
            self,
            "overlaps",
            tuple(sorted(self.overlaps, key=lambda e: (e.first_id, e.second_id))),
        )
        object.__setattr__(
            self,
            "shared_assumptions",
            tuple(sorted(
                self.shared_assumptions,
                key=lambda a: (a.assumption_id, a.first_thought_id, a.second_thought_id),
            )),
        )
        object.__setattr__(
            self,
            "evidence_placements",
            tuple(sorted(
                self.evidence_placements,
                key=lambda p: (p.evidence_id, p.thought_id, p.bucket),
            )),
        )

    def _require_known(self, thought_id: str, source: str) -> str:
        """Validate thought_id type/pattern and presence in ecology.

        Raises EcologyValidationError for wrong type/pattern.
        Raises UnknownThoughtError for valid-pattern but absent ID.
        """
        if not isinstance(thought_id, str):
            raise EcologyValidationError(
                f"{source}: thought_id must be a string", path=source
            )
        if not _THOUGHT_ID_RE.match(thought_id):
            raise EcologyValidationError(
                f"{source}: thought_id must match THOUGHT-* pattern", path=source
            )
        if thought_id not in self._id_set:
            raise UnknownThoughtError(
                f"{source}: unknown thought {thought_id!r}",
                thought_id=thought_id,
                reference_source=source,
            )
        return thought_id

    def dependencies_of(self, thought_id: str) -> tuple[DependencyEdge, ...]:
        """Return dependency edges where source matches, sorted by target lexical."""
        self._require_known(thought_id, "dependencies_of")
        return tuple(
            sorted(
                (e for e in self.dependencies if e.source_id == thought_id),
                key=lambda e: e.target_id,
            )
        )

    def dependents_of(self, thought_id: str) -> tuple[DependencyEdge, ...]:
        """Return dependency edges where target matches, sorted by source lexical."""
        self._require_known(thought_id, "dependents_of")
        return tuple(
            sorted(
                (e for e in self.dependencies if e.target_id == thought_id),
                key=lambda e: e.source_id,
            )
        )

    def contradictions_of(self, thought_id: str) -> tuple[ContradictionEdge, ...]:
        """Return incident contradiction edges sorted by the other endpoint."""
        self._require_known(thought_id, "contradictions_of")

        def _other(e: ContradictionEdge) -> str:
            return e.second_id if e.first_id == thought_id else e.first_id

        return tuple(
            sorted(
                (e for e in self.contradictions if thought_id in (e.first_id, e.second_id)),
                key=lambda e: _other(e),
            )
        )

    def overlaps_of(self, thought_id: str) -> tuple[OverlapEdge, ...]:
        """Return incident overlap edges sorted by the other endpoint."""
        self._require_known(thought_id, "overlaps_of")

        def _other(e: OverlapEdge) -> str:
            return e.second_id if e.first_id == thought_id else e.first_id

        return tuple(
            sorted(
                (e for e in self.overlaps if thought_id in (e.first_id, e.second_id)),
                key=lambda e: _other(e),
            )
        )

    def shared_assumptions_of(self, thought_id: str) -> tuple[SharedAssumptionLink, ...]:
        """Return incident shared assumption links sorted by (assumption_id, other ID)."""
        self._require_known(thought_id, "shared_assumptions_of")

        def _other(link: SharedAssumptionLink) -> str:
            return (
                link.second_thought_id
                if link.first_thought_id == thought_id
                else link.first_thought_id
            )

        return tuple(
            sorted(
                (
                    link
                    for link in self.shared_assumptions
                    if thought_id in (link.first_thought_id, link.second_thought_id)
                ),
                key=lambda link: (link.assumption_id, _other(link)),
            )
        )

    def evidence_for(self, thought_id: str) -> tuple[EvidencePlacement, ...]:
        """Return evidence placements for thought sorted by (evidence_id, bucket)."""
        self._require_known(thought_id, "evidence_for")
        return tuple(
            sorted(
                (ep for ep in self.evidence_placements if ep.thought_id == thought_id),
                key=lambda ep: (ep.evidence_id, ep.bucket),
            )
        )

    def neighborhood(self, thought_id: str) -> tuple[str, ...]:
        """Return sorted unique thought IDs connected to thought_id.

        Connections include: outgoing/incoming dependency, contradiction, overlap,
        shared assumption, OR sharing at least one evidence_id across thoughts
        regardless of bucket. Excludes self. Never treats evidence IDs as thought IDs.
        """
        self._require_known(thought_id, "neighborhood")
        connected: set[str] = set()

        # Dependencies (outgoing and incoming)
        for edge in self.dependencies:
            if edge.source_id == thought_id:
                connected.add(edge.target_id)
            elif edge.target_id == thought_id:
                connected.add(edge.source_id)

        # Contradictions
        for edge in self.contradictions:
            if edge.first_id == thought_id:
                connected.add(edge.second_id)
            elif edge.second_id == thought_id:
                connected.add(edge.first_id)

        # Overlaps
        for edge in self.overlaps:
            if edge.first_id == thought_id:
                connected.add(edge.second_id)
            elif edge.second_id == thought_id:
                connected.add(edge.first_id)

        # Shared assumptions
        for link in self.shared_assumptions:
            if link.first_thought_id == thought_id:
                connected.add(link.second_thought_id)
            elif link.second_thought_id == thought_id:
                connected.add(link.first_thought_id)

        # Evidence sharing: thoughts sharing at least one evidence_id
        # Build evidence_id -> set of thought_ids mapping
        evidence_to_thoughts: dict[str, set[str]] = defaultdict(set)
        for ep in self.evidence_placements:
            evidence_to_thoughts[ep.evidence_id].add(ep.thought_id)

        # Find thoughts sharing evidence with thought_id
        thought_evidence = {
            ep.evidence_id
            for ep in self.evidence_placements
            if ep.thought_id == thought_id
        }
        for eid in thought_evidence:
            for tid in evidence_to_thoughts[eid]:
                if tid != thought_id:
                    connected.add(tid)

        connected.discard(thought_id)
        return tuple(sorted(connected))

    def transitive_dependencies(self, thought_id: str) -> tuple[str, ...]:
        """Follow source->target edges, deterministic lexical traversal.

        Returns unique reachable thought IDs lexical, excluding self.
        """
        self._require_known(thought_id, "transitive_dependencies")

        # Build adjacency: source -> sorted targets
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in self.dependencies:
            adj[edge.source_id].append(edge.target_id)
        for k in adj:
            adj[k].sort()

        visited: set[str] = set()
        result: list[str] = []
        # Use stack for DFS with lexical order
        stack = [thought_id]
        while stack:
            node = stack.pop()
            for target in adj.get(node, ()):
                if target not in visited:
                    visited.add(target)
                    result.append(target)
                    stack.append(target)

        return tuple(sorted(result))

    def topological_order(self) -> tuple[str, ...]:
        """Return all nodes in topological order using Kahn's algorithm.

        Every target before dependent source. Lexical tie-break using heapq.
        Empty -> (). Defensive cycle -> DependencyCycleError deterministic metadata.
        """
        if not self.thought_ids:
            return ()

        # Build adjacency and in-degree
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {tid: 0 for tid in self.thought_ids}

        for edge in self.dependencies:
            adj[edge.target_id].append(edge.source_id)
            in_degree[edge.source_id] += 1

        # Sort adjacency lists for deterministic traversal
        for k in adj:
            adj[k].sort()

        # Initialize ready queue with nodes having in-degree 0
        ready = [tid for tid in self.thought_ids if in_degree[tid] == 0]
        heapq.heapify(ready)

        result: list[str] = []
        while ready:
            node = heapq.heappop(ready)
            result.append(node)

            for target in adj.get(node, ()):
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    heapq.heappush(ready, target)

        if len(result) != len(self.thought_ids):
            # Find a cycle for deterministic metadata
            dep_adj: dict[str, tuple[str, ...]] = {
                k: tuple(v) for k, v in adj.items()
            }
            cycle = _detect_cycle(dep_adj)
            if cycle is None:
                # Fallback: construct minimal cycle from remaining nodes
                remaining = sorted(set(self.thought_ids) - set(result))
                cycle = tuple(remaining[:2]) if len(remaining) >= 2 else (remaining[0], remaining[0])
            raise DependencyCycleError(
                f"dependency cycle detected: {' -> '.join(cycle)}",
                cycle=cycle,
            )

        return tuple(result)

    @property
    def _id_set(self) -> frozenset[str]:
        """Computed frozenset of thought IDs for membership tests."""
        return frozenset(self.thought_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_digest": self.snapshot_digest,
            "thought_ids": list(self.thought_ids),
            "dependencies": [e.to_dict() for e in self.dependencies],
            "contradictions": [e.to_dict() for e in self.contradictions],
            "overlaps": [e.to_dict() for e in self.overlaps],
            "shared_assumptions": [a.to_dict() for a in self.shared_assumptions],
            "evidence_placements": [p.to_dict() for p in self.evidence_placements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThoughtEcology:
        if not isinstance(data, dict):
            raise EcologyValidationError("data must be a dict", path="root")
        required = {
            "snapshot_digest",
            "thought_ids",
            "dependencies",
            "contradictions",
            "overlaps",
            "shared_assumptions",
            "evidence_placements",
        }
        missing = required - data.keys()
        if missing:
            raise EcologyValidationError(
                f"missing keys: {sorted(missing)}", path="root"
            )
        extra = data.keys() - required
        if extra:
            raise EcologyValidationError(
                f"unexpected keys: {sorted(extra)}", path="root"
            )

        # Explicitly require list for thought_ids and every relation collection
        if not isinstance(data["thought_ids"], list):
            raise EcologyValidationError(
                "thought_ids must be a list", path="thought_ids"
            )
        for name in ("dependencies", "contradictions", "overlaps",
                      "shared_assumptions", "evidence_placements"):
            if not isinstance(data[name], list):
                raise EcologyValidationError(f"{name} must be a list", path=name)

        return cls(
            snapshot_digest=data["snapshot_digest"],
            thought_ids=tuple(data["thought_ids"]),
            dependencies=tuple(
                DependencyEdge.from_dict(e) for e in data["dependencies"]
            ),
            contradictions=tuple(
                ContradictionEdge.from_dict(e) for e in data["contradictions"]
            ),
            overlaps=tuple(
                OverlapEdge.from_dict(e) for e in data["overlaps"]
            ),
            shared_assumptions=tuple(
                SharedAssumptionLink.from_dict(a) for a in data["shared_assumptions"]
            ),
            evidence_placements=tuple(
                EvidencePlacement.from_dict(p) for p in data["evidence_placements"]
            ),
        )

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @classmethod
    def from_canonical_json(cls, text: str) -> ThoughtEcology:
        if not isinstance(text, str):
            raise EcologyValidationError(
                f"expected string, got {type(text).__name__}", path="json"
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EcologyValidationError(f"invalid JSON: {exc}", path="json") from exc
        if not isinstance(data, dict):
            raise EcologyValidationError(
                f"expected object root, got {type(data).__name__}", path="json"
            )
        return cls.from_dict(data)

    def validate_for(self, snapshot: PopulationSnapshot) -> None:
        """Validate this ecology against a snapshot by rebuilding and comparing."""
        if not isinstance(snapshot, PopulationSnapshot):
            raise EcologyValidationError(
                f"expected PopulationSnapshot, got {type(snapshot).__name__}",
                path="snapshot",
            )
        rebuilt = build(snapshot)
        if self.to_canonical_json() != rebuilt.to_canonical_json():
            raise SnapshotMismatchError(
                "snapshot mismatch: ecology does not match rebuilt from snapshot",
                expected_digest=self.snapshot_digest,
                actual_digest=rebuilt.snapshot_digest,
            )


def build(snapshot: PopulationSnapshot) -> ThoughtEcology:
    """Build a ThoughtEcology from a PopulationSnapshot.

    Validates all relations, detects cycles, and produces a deterministic index.
    """
    if not isinstance(snapshot, PopulationSnapshot):
        raise EcologyValidationError(
            f"expected PopulationSnapshot, got {type(snapshot).__name__}",
            path="snapshot",
        )

    # Collect thought IDs
    thought_ids = tuple(sorted(t.thought_id for t in snapshot.thoughts))
    id_set = frozenset(thought_ids)

    # Build dependency adjacency for cycle detection
    dep_adj: dict[str, list[str]] = {tid: [] for tid in thought_ids}

    # Collect raw relations
    raw_deps: list[DependencyEdge] = []
    raw_contras: list[ContradictionEdge] = []
    raw_overlaps: list[OverlapEdge] = []
    raw_evidence: list[EvidencePlacement] = []

    # Track assumptions: assumption_id -> {thought_id: (statement, confidence, source)}
    assumption_map: dict[str, dict[str, tuple[str, float, str]]] = {}

    for thought in snapshot.thoughts:
        source_id = thought.thought_id

        # Dependencies (directed)
        for target_id in thought.graph.dependencies:
            if target_id == source_id:
                raise SelfReferenceError(
                    f"self-referencing dependency: {source_id}",
                    thought_id=source_id,
                    relation_type="dependency",
                )
            if target_id not in id_set:
                raise UnknownThoughtError(
                    f"unknown thought {target_id!r} in dependencies of {source_id}",
                    thought_id=target_id,
                    reference_source=source_id,
                )
            _check_thought_id(target_id, field=f"graph.dependencies[{target_id}]")
            edge = DependencyEdge(source_id=source_id, target_id=target_id)
            raw_deps.append(edge)
            dep_adj[source_id].append(target_id)

        # Contradictions (undirected, symmetric pair collapse)
        for target_id in thought.graph.contradictions:
            if target_id == source_id:
                raise SelfReferenceError(
                    f"self-referencing contradiction: {source_id}",
                    thought_id=source_id,
                    relation_type="contradiction",
                )
            if target_id not in id_set:
                raise UnknownThoughtError(
                    f"unknown thought {target_id!r} in contradictions of {source_id}",
                    thought_id=target_id,
                    reference_source=source_id,
                )
            _check_thought_id(target_id, field=f"graph.contradictions[{target_id}]")
            edge = ContradictionEdge(first_id=source_id, second_id=target_id)
            raw_contras.append(edge)

        # Overlaps (undirected, symmetric pair collapse)
        for target_id in thought.graph.overlaps:
            if target_id == source_id:
                raise SelfReferenceError(
                    f"self-referencing overlap: {source_id}",
                    thought_id=source_id,
                    relation_type="overlap",
                )
            if target_id not in id_set:
                raise UnknownThoughtError(
                    f"unknown thought {target_id!r} in overlaps of {source_id}",
                    thought_id=target_id,
                    reference_source=source_id,
                )
            _check_thought_id(target_id, field=f"graph.overlaps[{target_id}]")
            edge = OverlapEdge(first_id=source_id, second_id=target_id)
            raw_overlaps.append(edge)

        # Assumptions
        for assumption in thought.assumptions:
            aid = assumption.assumption_id
            payload = (assumption.statement, assumption.confidence, assumption.source)
            if aid not in assumption_map:
                assumption_map[aid] = {}
            thought_payloads = assumption_map[aid]
            if source_id in thought_payloads:
                pass
            thought_payloads[source_id] = payload

        # Evidence placements
        for bucket in ("supporting", "opposing", "unresolved"):
            for evidence_id in getattr(thought.evidence, bucket):
                _check_non_empty_str(
                    evidence_id, field=f"evidence.{bucket}[{evidence_id}]"
                )
                raw_evidence.append(
                    EvidencePlacement(
                        evidence_id=evidence_id,
                        thought_id=source_id,
                        bucket=bucket,
                    )
                )

    # Detect dependency cycles
    dep_adj_tuple = {k: tuple(sorted(v)) for k, v in dep_adj.items()}
    cycle = _detect_cycle(dep_adj_tuple)
    if cycle is not None:
        raise DependencyCycleError(
            f"dependency cycle detected: {' -> '.join(cycle)}",
            cycle=cycle,
        )

    # Deduplicate dependency edges (directed, unique source+target)
    dep_set: set[tuple[str, str]] = set()
    unique_deps: list[DependencyEdge] = []
    for edge in raw_deps:
        key = (edge.source_id, edge.target_id)
        if key not in dep_set:
            dep_set.add(key)
            unique_deps.append(edge)

    # Deduplicate contradiction edges (undirected symmetric pair collapse)
    contra_set: set[tuple[str, str]] = set()
    unique_contras: list[ContradictionEdge] = []
    for edge in raw_contras:
        key = (edge.first_id, edge.second_id)
        if key not in contra_set:
            contra_set.add(key)
            unique_contras.append(edge)

    # Deduplicate overlap edges (undirected symmetric pair collapse)
    overlap_set: set[tuple[str, str]] = set()
    unique_overlaps: list[OverlapEdge] = []
    for edge in raw_overlaps:
        key = (edge.first_id, edge.second_id)
        if key not in overlap_set:
            overlap_set.add(key)
            unique_overlaps.append(edge)

    # Validate shared assumptions: same assumption_id must have identical payload
    for aid, thought_payloads in sorted(assumption_map.items()):
        payloads = set(thought_payloads.values())
        if len(payloads) > 1:
            tids = tuple(sorted(thought_payloads.keys()))
            raise ConflictingAssumptionError(
                f"assumption {aid!r} has conflicting payloads across thoughts {tids}",
                assumption_id=aid,
                thoughts=tids,
            )

    # Build shared assumption links (all pairs of thoughts sharing same assumption)
    shared_links: list[SharedAssumptionLink] = []
    for aid, thought_payloads in sorted(assumption_map.items()):
        tids = sorted(thought_payloads.keys())
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                link = SharedAssumptionLink(
                    assumption_id=aid,
                    first_thought_id=tids[i],
                    second_thought_id=tids[j],
                )
                shared_links.append(link)

    # Validate evidence ambiguity: same (thought_id, evidence_id) cannot appear
    # in multiple buckets
    evidence_buckets: dict[tuple[str, str], set[str]] = {}
    for ep in raw_evidence:
        key = (ep.thought_id, ep.evidence_id)
        if key not in evidence_buckets:
            evidence_buckets[key] = set()
        evidence_buckets[key].add(ep.bucket)

    for (tid, eid), buckets in evidence_buckets.items():
        if len(buckets) > 1:
            raise AmbiguousEvidenceBucketError(
                f"evidence {eid!r} in thought {tid} appears in buckets {sorted(buckets)}",
                evidence_id=eid,
                thought_id=tid,
                buckets=tuple(sorted(buckets)),
            )

    # Sort all collections deterministically with ADR sort keys
    sorted_deps = tuple(
        sorted(unique_deps, key=lambda e: (e.source_id, e.target_id))
    )
    sorted_contras = tuple(
        sorted(unique_contras, key=lambda e: (e.first_id, e.second_id))
    )
    sorted_overlaps = tuple(
        sorted(unique_overlaps, key=lambda e: (e.first_id, e.second_id))
    )
    sorted_shared = tuple(
        sorted(
            shared_links,
            key=lambda a: (a.assumption_id, a.first_thought_id, a.second_thought_id),
        )
    )
    sorted_evidence = tuple(
        sorted(
            raw_evidence,
            key=lambda p: (p.evidence_id, p.thought_id, p.bucket),
        )
    )

    # Compute snapshot digest from canonical JSON of the snapshot
    snapshot_json = snapshot.to_canonical_json()
    digest = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

    return ThoughtEcology(
        snapshot_digest=digest,
        thought_ids=thought_ids,
        dependencies=sorted_deps,
        contradictions=sorted_contras,
        overlaps=sorted_overlaps,
        shared_assumptions=sorted_shared,
        evidence_placements=sorted_evidence,
    )
