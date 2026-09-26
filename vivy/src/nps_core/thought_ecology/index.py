"""Deterministic ThoughtEcology index for the thought relationship graph.

Provides ``ThoughtEcology`` frozen dataclass and ``build`` factory for
constructing an immutable ecology snapshot from a PopulationSnapshot.
Standard-library only; no I/O.
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

__all__ = [
    "ThoughtEcology",
    "build",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")

_ECOLOGY_KEYS = frozenset({
    "snapshot_digest",
    "thought_ids",
    "dependencies",
    "contradictions",
    "overlaps",
    "shared_assumptions",
    "evidence_placements",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ecology_err(msg: str, **kwargs: Any) -> EcologyValidationError:
    return EcologyValidationError(msg, **kwargs)


def _validate_thought_id(value: str, *, field: str) -> None:
    if not isinstance(value, str):
        raise _ecology_err(
            f"{field} must be a string, got {type(value).__name__}",
            path=field,
        )
    if not _THOUGHT_ID_RE.match(value):
        raise _ecology_err(
            f"{field} must match ^THOUGHT-[A-Za-z0-9._-]+$",
            path=field,
        )


def _check_unknown_thoughts(
    thought_ids: frozenset[str],
    deps: tuple[DependencyEdge, ...],
    contras: tuple[ContradictionEdge, ...],
    overlaps: tuple[OverlapEdge, ...],
    assumptions: tuple[SharedAssumptionLink, ...],
    placements: tuple[EvidencePlacement, ...],
) -> None:
    def _check(tid: str, source: str) -> None:
        if tid not in thought_ids:
            raise UnknownThoughtError(
                f"thought {tid!r} not in thought_ids for {source}",
                thought_id=tid,
                reference_source=source,
            )

    for e in deps:
        _check(e.source_id, "DependencyEdge.source_id")
        _check(e.target_id, "DependencyEdge.target_id")
    for e in contras:
        _check(e.first_id, "ContradictionEdge.first_id")
        _check(e.second_id, "ContradictionEdge.second_id")
    for e in overlaps:
        _check(e.first_id, "OverlapEdge.first_id")
        _check(e.second_id, "OverlapEdge.second_id")
    for link in assumptions:
        _check(link.first_thought_id, "SharedAssumptionLink.first_thought_id")
        _check(link.second_thought_id, "SharedAssumptionLink.second_thought_id")
    for p in placements:
        _check(p.thought_id, "EvidencePlacement.thought_id")


def _check_no_self_references(
    deps: tuple[DependencyEdge, ...],
    contras: tuple[ContradictionEdge, ...],
    overlaps: tuple[OverlapEdge, ...],
    assumptions: tuple[SharedAssumptionLink, ...],
) -> None:
    for e in deps:
        if e.source_id == e.target_id:
            raise SelfReferenceError(
                "DependencyEdge cannot reference the same thought",
                thought_id=e.source_id,
                relation_type="DependencyEdge",
            )
    for e in contras:
        if e.first_id == e.second_id:
            raise SelfReferenceError(
                "ContradictionEdge cannot reference the same thought",
                thought_id=e.first_id,
                relation_type="ContradictionEdge",
            )
    for e in overlaps:
        if e.first_id == e.second_id:
            raise SelfReferenceError(
                "OverlapEdge cannot reference the same thought",
                thought_id=e.first_id,
                relation_type="OverlapEdge",
            )
    for link in assumptions:
        if link.first_thought_id == link.second_thought_id:
            raise SelfReferenceError(
                "SharedAssumptionLink cannot reference the same thought",
                thought_id=link.first_thought_id,
                relation_type="SharedAssumptionLink",
            )


def _check_dependency_cycles(edges: tuple[DependencyEdge, ...]) -> None:
    """Detect dependency cycles using DFS with cycle path recording."""
    if not edges:
        return

    adj: dict[str, list[str]] = {}
    all_nodes: set[str] = set()
    for edge in edges:
        adj.setdefault(edge.source_id, []).append(edge.target_id)
        all_nodes.add(edge.source_id)
        all_nodes.add(edge.target_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in all_nodes}
    parent: dict[str, str | None] = {n: None for n in all_nodes}

    def dfs(node: str) -> tuple[str, ...] | None:
        color[node] = GRAY
        for neighbor in sorted(adj.get(node, [])):
            if color.get(neighbor) == GRAY:
                cycle: list[str] = []
                cur = node
                while True:
                    cycle.append(cur)
                    if cur == neighbor:
                        break
                    cur = parent[cur]  # type: ignore[assignment]
                cycle.reverse()
                cycle.append(neighbor)
                return tuple(cycle)
            if color.get(neighbor) == WHITE:
                parent[neighbor] = node
                result = dfs(neighbor)
                if result is not None:
                    return result
        color[node] = BLACK
        return None

    for node in sorted(all_nodes):
        if color[node] == WHITE:
            cycle = dfs(node)
            if cycle is not None:
                raise DependencyCycleError(
                    "dependency cycle detected in ecology graph",
                    cycle=cycle,
                )


def _check_ambiguous_evidence_buckets(
    placements: tuple[EvidencePlacement, ...],
) -> None:
    bucket_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    for p in placements:
        bucket_map[(p.evidence_id, p.thought_id)].append(p.bucket)
    for (eid, tid), buckets in bucket_map.items():
        unique = sorted(set(buckets))
        if len(unique) > 1:
            raise AmbiguousEvidenceBucketError(
                f"evidence {eid!r} appears in multiple buckets "
                f"for thought {tid!r}",
                evidence_id=eid,
                thought_id=tid,
                buckets=tuple(unique),
            )


def _check_duplicate_edges(
    deps: tuple[DependencyEdge, ...],
    contras: tuple[ContradictionEdge, ...],
    overlaps: tuple[OverlapEdge, ...],
) -> None:
    seen_deps: set[tuple[str, str]] = set()
    for e in deps:
        key = (e.source_id, e.target_id)
        if key in seen_deps:
            raise _ecology_err(
                f"duplicate dependency: {key!r}",
            )
        seen_deps.add(key)

    seen_contras: set[tuple[str, str]] = set()
    for e in contras:
        key = (e.first_id, e.second_id)
        if key in seen_contras:
            raise _ecology_err(
                f"duplicate contradiction: {key!r}",
            )
        seen_contras.add(key)

    seen_overlaps: set[tuple[str, str]] = set()
    for e in overlaps:
        key = (e.first_id, e.second_id)
        if key in seen_overlaps:
            raise _ecology_err(
                f"duplicate overlap: {key!r}",
            )
        seen_overlaps.add(key)


# ---------------------------------------------------------------------------
# ThoughtEcology
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ThoughtEcology:
    """Frozen ecology with seven deterministic fields.

    All tuple fields are immutable. ``thought_ids`` is auto-sorted
    lexicographically. ``snapshot_digest`` is a SHA-256 hex hash of the
    source PopulationSnapshot's canonical JSON.
    """

    snapshot_digest: str
    thought_ids: tuple[str, ...]
    dependencies: tuple[DependencyEdge, ...]
    contradictions: tuple[ContradictionEdge, ...]
    overlaps: tuple[OverlapEdge, ...]
    shared_assumptions: tuple[SharedAssumptionLink, ...]
    evidence_placements: tuple[EvidencePlacement, ...]

    def __post_init__(self) -> None:
        # snapshot_digest
        if not isinstance(self.snapshot_digest, str) or not self.snapshot_digest:
            raise _ecology_err(
                "snapshot_digest must be a non-empty string",
                path="snapshot_digest",
            )

        # thought_ids
        if not isinstance(self.thought_ids, tuple):
            raise _ecology_err(
                f"thought_ids must be a tuple, "
                f"got {type(self.thought_ids).__name__}",
                path="thought_ids",
            )
        for i, tid in enumerate(self.thought_ids):
            _validate_thought_id(tid, field=f"thought_ids[{i}]")
        sorted_ids = tuple(sorted(self.thought_ids))
        if sorted_ids is not self.thought_ids:
            object.__setattr__(self, "thought_ids", sorted_ids)

        thought_id_set = frozenset(self.thought_ids)

        # Validate relation tuples
        for field_name, expected_type in (
            ("dependencies", DependencyEdge),
            ("contradictions", ContradictionEdge),
            ("overlaps", OverlapEdge),
            ("shared_assumptions", SharedAssumptionLink),
            ("evidence_placements", EvidencePlacement),
        ):
            val = getattr(self, field_name)
            if not isinstance(val, tuple):
                raise _ecology_err(
                    f"{field_name} must be a tuple, "
                    f"got {type(val).__name__}",
                    path=field_name,
                )
            for i, item in enumerate(val):
                if not isinstance(item, expected_type):
                    raise _ecology_err(
                        f"{field_name}[{i}] must be a "
                        f"{expected_type.__name__}, "
                        f"got {type(item).__name__}",
                        path=field_name,
                    )

        # Validate endpoints reference existing thought_ids
        _check_unknown_thoughts(
            thought_id_set,
            self.dependencies,
            self.contradictions,
            self.overlaps,
            self.shared_assumptions,
            self.evidence_placements,
        )

        # Check for duplicate edges
        _check_duplicate_edges(
            self.dependencies,
            self.contradictions,
            self.overlaps,
        )

        # Check for dependency cycles
        _check_dependency_cycles(self.dependencies)

        # Check for ambiguous evidence buckets
        _check_ambiguous_evidence_buckets(self.evidence_placements)

    # -- Query methods ------------------------------------------------------

    def _require_tid(self, thought_id: str) -> None:
        if thought_id not in set(self.thought_ids):
            raise UnknownThoughtError(
                f"unknown thought: {thought_id!r}",
                thought_id=thought_id,
                reference_source="ThoughtEcology",
            )

    def dependencies_of(self, thought_id: str) -> tuple[DependencyEdge, ...]:
        """Edges where thought_id is the source (depends on something)."""
        self._require_tid(thought_id)
        return tuple(
            e for e in self.dependencies if e.source_id == thought_id
        )

    def dependents_of(self, thought_id: str) -> tuple[DependencyEdge, ...]:
        """Edges where thought_id is the target (something depends on it)."""
        self._require_tid(thought_id)
        return tuple(
            e for e in self.dependencies if e.target_id == thought_id
        )

    def contradictions_of(
        self, thought_id: str,
    ) -> tuple[ContradictionEdge, ...]:
        """Contradiction edges involving thought_id."""
        self._require_tid(thought_id)
        return tuple(
            e for e in self.contradictions
            if e.first_id == thought_id or e.second_id == thought_id
        )

    def overlaps_of(self, thought_id: str) -> tuple[OverlapEdge, ...]:
        """Overlap edges involving thought_id."""
        self._require_tid(thought_id)
        return tuple(
            e for e in self.overlaps
            if e.first_id == thought_id or e.second_id == thought_id
        )

    def shared_assumptions_of(
        self, thought_id: str,
    ) -> tuple[SharedAssumptionLink, ...]:
        """Shared assumption links involving thought_id."""
        self._require_tid(thought_id)
        return tuple(
            link for link in self.shared_assumptions
            if link.first_thought_id == thought_id
            or link.second_thought_id == thought_id
        )

    def evidence_for(
        self, thought_id: str,
    ) -> tuple[EvidencePlacement, ...]:
        """Evidence placements for thought_id."""
        self._require_tid(thought_id)
        return tuple(
            p for p in self.evidence_placements
            if p.thought_id == thought_id
        )

    def transitive_dependencies(
        self, thought_id: str,
    ) -> tuple[str, ...]:
        """All transitive dependency targets, sorted."""
        self._require_tid(thought_id)
        adj: dict[str, list[str]] = defaultdict(list)
        for e in self.dependencies:
            adj[e.source_id].append(e.target_id)
        visited: set[str] = set()
        queue: list[str] = list(adj.get(thought_id, []))
        while queue:
            cur = queue.pop(0)
            if cur not in visited:
                visited.add(cur)
                queue.extend(
                    t for t in adj.get(cur, []) if t not in visited
                )
        return tuple(sorted(visited))

    def topological_order(self) -> tuple[str, ...]:
        """Thought IDs in topological order (dependencies before dependents)."""
        if not self.thought_ids:
            return ()
        # Reverse edges: target → source (prerequisite before dependent)
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {tid: 0 for tid in self.thought_ids}
        for e in self.dependencies:
            adj[e.target_id].append(e.source_id)
            in_degree[e.source_id] += 1
        queue = [
            tid for tid in self.thought_ids if in_degree[tid] == 0
        ]
        heapq.heapify(queue)
        result: list[str] = []
        while queue:
            node = heapq.heappop(queue)
            result.append(node)
            for neighbor in sorted(adj[node]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    heapq.heappush(queue, neighbor)
        return tuple(result)

    def neighborhood(self, thought_id: str) -> tuple[str, ...]:
        """All thought IDs connected through any relation, sorted."""
        self._require_tid(thought_id)
        neighbors: set[str] = set()

        for e in self.dependencies:
            if e.source_id == thought_id:
                neighbors.add(e.target_id)
            elif e.target_id == thought_id:
                neighbors.add(e.source_id)

        for e in self.contradictions:
            if e.first_id == thought_id:
                neighbors.add(e.second_id)
            elif e.second_id == thought_id:
                neighbors.add(e.first_id)

        for e in self.overlaps:
            if e.first_id == thought_id:
                neighbors.add(e.second_id)
            elif e.second_id == thought_id:
                neighbors.add(e.first_id)

        for link in self.shared_assumptions:
            if link.first_thought_id == thought_id:
                neighbors.add(link.second_thought_id)
            elif link.second_thought_id == thought_id:
                neighbors.add(link.first_thought_id)

        # Evidence sharing
        my_ev = {
            p.evidence_id for p in self.evidence_placements
            if p.thought_id == thought_id
        }
        for p in self.evidence_placements:
            if p.thought_id != thought_id and p.evidence_id in my_ev:
                neighbors.add(p.thought_id)

        neighbors.discard(thought_id)
        return tuple(sorted(neighbors))

    # -- Serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "snapshot_digest": self.snapshot_digest,
            "thought_ids": list(self.thought_ids),
            "dependencies": [e.to_dict() for e in self.dependencies],
            "contradictions": [e.to_dict() for e in self.contradictions],
            "overlaps": [e.to_dict() for e in self.overlaps],
            "shared_assumptions": [
                link.to_dict() for link in self.shared_assumptions
            ],
            "evidence_placements": [
                p.to_dict() for p in self.evidence_placements
            ],
        }

    @classmethod
    def from_dict(cls, data: Any) -> ThoughtEcology:
        """Strict construction from a plain dict."""
        if not isinstance(data, dict):
            raise _ecology_err(
                f"expected dict, got {type(data).__name__}",
                path="root",
            )
        extra = set(data.keys()) - _ECOLOGY_KEYS
        if extra:
            raise _ecology_err(
                f"unexpected keys: {sorted(extra)}",
                path="root",
            )
        missing = _ECOLOGY_KEYS - set(data.keys())
        if missing:
            raise _ecology_err(
                f"missing keys: {sorted(missing)}",
                path="root",
            )

        snapshot_digest = data["snapshot_digest"]
        if not isinstance(snapshot_digest, str):
            raise _ecology_err(
                "snapshot_digest must be a string",
                path="snapshot_digest",
            )

        for key in (
            "thought_ids", "dependencies", "contradictions",
            "overlaps", "shared_assumptions", "evidence_placements",
        ):
            if not isinstance(data[key], list):
                raise _ecology_err(
                    f"{key} must be a JSON list",
                    path=key,
                )

        thought_ids = tuple(sorted(data["thought_ids"]))
        dependencies = tuple(
            DependencyEdge.from_dict(e) for e in data["dependencies"]
        )
        contradictions = tuple(
            ContradictionEdge.from_dict(e) for e in data["contradictions"]
        )
        overlaps = tuple(
            OverlapEdge.from_dict(e) for e in data["overlaps"]
        )
        shared_assumptions = tuple(
            SharedAssumptionLink.from_dict(link)
            for link in data["shared_assumptions"]
        )
        evidence_placements = tuple(
            EvidencePlacement.from_dict(p)
            for p in data["evidence_placements"]
        )

        return cls(
            snapshot_digest=snapshot_digest,
            thought_ids=thought_ids,
            dependencies=dependencies,
            contradictions=contradictions,
            overlaps=overlaps,
            shared_assumptions=shared_assumptions,
            evidence_placements=evidence_placements,
        )

    def to_canonical_json(self) -> str:
        """Serialize to deterministic canonical JSON string."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_canonical_json(cls, text: str) -> ThoughtEcology:
        """Deserialize from a canonical JSON string."""
        if not isinstance(text, str):
            raise _ecology_err(
                f"expected string, got {type(text).__name__}",
                path="root",
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _ecology_err(
                f"invalid JSON: {exc}",
                path="root",
            ) from exc
        if not isinstance(data, dict):
            raise _ecology_err(
                "expected JSON object at root",
                path="root",
            )
        return cls.from_dict(data)

    def validate_for(self, snapshot: PopulationSnapshot) -> None:
        """Revalidate against the supplied snapshot.

        Rebuilds the ecology from the snapshot and compares.
        Raises :class:`SnapshotMismatchError` on any difference.
        """
        expected = build(snapshot)
        if self.to_dict() != expected.to_dict():
            raise SnapshotMismatchError(
                "ecology does not match snapshot",
                expected_digest=expected.snapshot_digest,
                actual_digest=self.snapshot_digest,
            )


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build(snapshot: PopulationSnapshot) -> ThoughtEcology:
    """Construct a validated ThoughtEcology from a PopulationSnapshot.

    Extracts all relations from each ThoughtState's ``graph``,
    ``assumptions``, and ``evidence`` fields.  Validates invariants.
    """
    if not isinstance(snapshot, PopulationSnapshot):
        raise _ecology_err(
            f"expected PopulationSnapshot, "
            f"got {type(snapshot).__name__}",
            path="snapshot",
        )

    thought_ids = frozenset(t.thought_id for t in snapshot.thoughts)

    # --- Extract dependencies ---
    dep_set: set[tuple[str, str]] = set()
    for t in snapshot.thoughts:
        for target_id in t.graph.dependencies:
            dep_set.add((t.thought_id, target_id))
    dep_edges = tuple(
        sorted(
            (DependencyEdge(source_id=s, target_id=t) for s, t in dep_set),
            key=lambda e: (e.source_id, e.target_id),
        )
    )

    # --- Extract contradictions (collapse reciprocal) ---
    contra_pairs: set[tuple[str, str]] = set()
    for t in snapshot.thoughts:
        for other_id in t.graph.contradictions:
            pair = tuple(sorted((t.thought_id, other_id)))
            contra_pairs.add(pair)
    contra_edges = tuple(
        sorted(
            (
                ContradictionEdge(first_id=a, second_id=b)
                for a, b in contra_pairs
            ),
            key=lambda e: (e.first_id, e.second_id),
        )
    )

    # --- Extract overlaps (collapse reciprocal) ---
    overlap_pairs: set[tuple[str, str]] = set()
    for t in snapshot.thoughts:
        for other_id in t.graph.overlaps:
            pair = tuple(sorted((t.thought_id, other_id)))
            overlap_pairs.add(pair)
    overlap_edges = tuple(
        sorted(
            (
                OverlapEdge(first_id=a, second_id=b)
                for a, b in overlap_pairs
            ),
            key=lambda e: (e.first_id, e.second_id),
        )
    )

    # --- Extract shared assumptions ---
    asm_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for t in snapshot.thoughts:
        for a in t.assumptions:
            payload = {
                "statement": a.statement,
                "confidence": a.confidence,
                "source": a.source,
            }
            asm_map[a.assumption_id][t.thought_id] = payload

    asm_links: list[SharedAssumptionLink] = []
    for assumption_id, payloads in asm_map.items():
        unique_payloads = set(
            json.dumps(v, sort_keys=True) for v in payloads.values()
        )
        if len(unique_payloads) > 1:
            raise ConflictingAssumptionError(
                f"assumption {assumption_id!r} has different payloads",
                assumption_id=assumption_id,
                thoughts=tuple(sorted(payloads.keys())),
            )
        tids = sorted(payloads.keys())
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                asm_links.append(
                    SharedAssumptionLink(
                        assumption_id=assumption_id,
                        first_thought_id=tids[i],
                        second_thought_id=tids[j],
                    )
                )
    shared_assumption_links = tuple(
        sorted(
            asm_links,
            key=lambda link: (
                link.assumption_id,
                link.first_thought_id,
                link.second_thought_id,
            ),
        )
    )

    # --- Extract evidence placements ---
    placements: list[EvidencePlacement] = []
    for t in snapshot.thoughts:
        for bucket_name in ("supporting", "opposing", "unresolved"):
            bucket = getattr(t.evidence, bucket_name)
            for eid in bucket:
                placements.append(
                    EvidencePlacement(
                        evidence_id=eid,
                        thought_id=t.thought_id,
                        bucket=bucket_name,
                    )
                )
    evidence_placements = tuple(
        sorted(
            placements,
            key=lambda p: (p.evidence_id, p.thought_id, p.bucket),
        )
    )

    # --- Validate ---
    _check_no_self_references(
        dep_edges, contra_edges, overlap_edges, shared_assumption_links,
    )
    _check_unknown_thoughts(
        thought_ids,
        dep_edges,
        contra_edges,
        overlap_edges,
        shared_assumption_links,
        evidence_placements,
    )
    _check_dependency_cycles(dep_edges)
    _check_ambiguous_evidence_buckets(evidence_placements)

    # --- Compute snapshot digest ---
    snapshot_digest = hashlib.sha256(
        snapshot.to_canonical_json().encode("utf-8"),
    ).hexdigest()

    return ThoughtEcology(
        snapshot_digest=snapshot_digest,
        thought_ids=tuple(sorted(thought_ids)),
        dependencies=dep_edges,
        contradictions=contra_edges,
        overlaps=overlap_edges,
        shared_assumptions=shared_assumption_links,
        evidence_placements=evidence_placements,
    )
