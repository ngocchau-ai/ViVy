"""Deterministic ThoughtEcology index for the thought relationship graph.

Provides ``ThoughtEcology`` frozen dataclass and ``build`` factory for
constructing an immutable ecology snapshot from a PopulationSnapshot and
a collection of relations.  Standard-library only; no I/O.
"""

from __future__ import annotations

import collections
import hashlib
import heapq
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

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
    "thought_ids",
    "dependency_edges",
    "contradiction_edges",
    "overlap_edges",
    "shared_assumption_links",
    "evidence_placements",
    "digest",
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
            f"{field} must match ^THOUGHT-[A-Za-z0-9._-]+$, got {value!r}",
            path=field,
        )


def _canonical_json_bytes(obj: Any) -> bytes:
    """Produce deterministic canonical JSON bytes."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_dependency_cycles(edges: tuple[DependencyEdge, ...]) -> None:
    """Detect cycles in the dependency graph using Kahn's algorithm."""
    if not edges:
        return

    # Build adjacency list and in-degree count
    adj: dict[str, list[str]] = collections.defaultdict(list)
    in_degree: dict[str, int] = collections.defaultdict(int)
    all_nodes: set[str] = set()

    for edge in edges:
        adj[edge.source_id].append(edge.target_id)
        in_degree[edge.target_id] += 1
        all_nodes.add(edge.source_id)
        all_nodes.add(edge.target_id)

    # Initialize queue with nodes having zero in-degree
    queue: list[str] = sorted(n for n in all_nodes if in_degree[n] == 0)
    visited_count = 0

    while queue:
        node = heapq.heappop(queue)
        visited_count += 1
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(queue, neighbor)

    if visited_count != len(all_nodes):
        raise DependencyCycleError(
            "dependency cycle detected in ecology graph",
            cycle=(),
        )


def _check_no_self_references(
    dependencies: tuple[DependencyEdge, ...],
    contradictions: tuple[ContradictionEdge, ...],
    overlaps: tuple[OverlapEdge, ...],
    assumptions: tuple[SharedAssumptionLink, ...],
) -> None:
    """Verify no relation references the same thought at both endpoints."""
    for edge in dependencies:
        if edge.source_id == edge.target_id:
            raise SelfReferenceError(
                "DependencyEdge cannot reference the same thought",
                thought_id=edge.source_id,
                relation_type="DependencyEdge",
            )

    for edge in contradictions:
        if edge.first_id == edge.second_id:
            raise SelfReferenceError(
                "ContradictionEdge cannot reference the same thought",
                thought_id=edge.first_id,
                relation_type="ContradictionEdge",
            )

    for edge in overlaps:
        if edge.first_id == edge.second_id:
            raise SelfReferenceError(
                "OverlapEdge cannot reference the same thought",
                thought_id=edge.first_id,
                relation_type="OverlapEdge",
            )

    for link in assumptions:
        if link.first_thought_id == link.second_thought_id:
            raise SelfReferenceError(
                "SharedAssumptionLink cannot reference the same thought",
                thought_id=link.first_thought_id,
                relation_type="SharedAssumptionLink",
            )


def _check_unknown_thoughts(
    thought_ids: frozenset[str],
    dependencies: tuple[DependencyEdge, ...],
    contradictions: tuple[ContradictionEdge, ...],
    overlaps: tuple[OverlapEdge, ...],
    assumptions: tuple[SharedAssumptionLink, ...],
    placements: tuple[EvidencePlacement, ...],
) -> None:
    """Verify all referenced thought IDs exist in the ecology."""

    def _check_tid(tid: str, source: str) -> None:
        if tid not in thought_ids:
            raise UnknownThoughtError(
                f"unknown thought {tid!r} referenced in {source}",
                thought_id=tid,
                reference_source=source,
            )

    for edge in dependencies:
        _check_tid(edge.source_id, "DependencyEdge.source_id")
        _check_tid(edge.target_id, "DependencyEdge.target_id")

    for edge in contradictions:
        _check_tid(edge.first_id, "ContradictionEdge.first_id")
        _check_tid(edge.second_id, "ContradictionEdge.second_id")

    for edge in overlaps:
        _check_tid(edge.first_id, "OverlapEdge.first_id")
        _check_tid(edge.second_id, "OverlapEdge.second_id")

    for link in assumptions:
        _check_tid(link.first_thought_id, "SharedAssumptionLink.first_thought_id")
        _check_tid(link.second_thought_id, "SharedAssumptionLink.second_thought_id")

    for placement in placements:
        _check_tid(placement.thought_id, "EvidencePlacement.thought_id")


def _check_conflicting_assumptions(
    assumptions: tuple[SharedAssumptionLink, ...],
    snapshot: PopulationSnapshot,
) -> None:
    """Verify that shared assumptions have identical payloads."""
    # Group links by assumption_id
    assumption_groups: dict[str, list[SharedAssumptionLink]] = collections.defaultdict(list)
    for link in assumptions:
        assumption_groups[link.assumption_id].append(link)

    for assumption_id, links in assumption_groups.items():
        # Gather all thoughts sharing this assumption
        thoughts_involved: set[str] = set()
        for link in links:
            thoughts_involved.add(link.first_thought_id)
            thoughts_involved.add(link.second_thought_id)

        # Extract the assumption payload from each thought
        payloads: dict[str, dict[str, Any]] = {}
        for tid in thoughts_involved:
            thought = snapshot.get(tid)
            if thought is None:
                continue
            for assumption in thought.assumptions:
                if assumption.assumption_id == assumption_id:
                    payloads[tid] = {
                        "statement": assumption.statement,
                        "confidence": assumption.confidence,
                        "source": assumption.source,
                    }
                    break

        # Check all payloads are identical
        if len(payloads) > 1:
            unique_payloads = set(
                json.dumps(v, sort_keys=True) for v in payloads.values()
            )
            if len(unique_payloads) > 1:
                raise ConflictingAssumptionError(
                    f"assumption {assumption_id!r} has different payloads across thoughts",
                    assumption_id=assumption_id,
                    thoughts=tuple(sorted(payloads.keys())),
                )


def _check_ambiguous_evidence_buckets(
    placements: tuple[EvidencePlacement, ...],
) -> None:
    """Verify no evidence ID appears in multiple buckets for one thought."""
    # Group by (evidence_id, thought_id)
    bucket_map: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for placement in placements:
        key = (placement.evidence_id, placement.thought_id)
        bucket_map[key].append(placement.bucket)

    for (eid, tid), buckets in bucket_map.items():
        if len(buckets) > 1:
            unique_buckets = tuple(sorted(set(buckets)))
            if len(unique_buckets) > 1:
                raise AmbiguousEvidenceBucketError(
                    f"evidence {eid!r} appears in multiple buckets for thought {tid!r}",
                    evidence_id=eid,
                    thought_id=tid,
                    buckets=unique_buckets,
                )


def _compute_digest(data: dict[str, Any]) -> str:
    """Compute SHA-256 hex digest of the ecology data (excluding digest field)."""
    return _sha256_hex(_canonical_json_bytes(data))


# ---------------------------------------------------------------------------
# ThoughtEcology
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ThoughtEcology:
    """Frozen ecology with seven deterministic fields.

    All fields are immutable tuples or frozensets sorted lexicographically.
    The ``digest`` field is a SHA-256 hex hash of the other six fields.
    """

    thought_ids: tuple[str, ...]
    dependency_edges: tuple[DependencyEdge, ...]
    contradiction_edges: tuple[ContradictionEdge, ...]
    overlap_edges: tuple[OverlapEdge, ...]
    shared_assumption_links: tuple[SharedAssumptionLink, ...]
    evidence_placements: tuple[EvidencePlacement, ...]
    digest: str

    def __post_init__(self) -> None:
        # Validate thought_ids
        if not isinstance(self.thought_ids, tuple):
            raise _ecology_err(
                f"thought_ids must be a tuple, got {type(self.thought_ids).__name__}",
                path="thought_ids",
            )
        for i, tid in enumerate(self.thought_ids):
            _validate_thought_id(tid, field=f"thought_ids[{i}]")

        # Validate tuples
        for field_name in (
            "dependency_edges",
            "contradiction_edges",
            "overlap_edges",
            "shared_assumption_links",
            "evidence_placements",
        ):
            val = getattr(self, field_name)
            if not isinstance(val, tuple):
                raise _ecology_err(
                    f"{field_name} must be a tuple, got {type(val).__name__}",
                    path=field_name,
                )

        # Validate digest
        if not isinstance(self.digest, str) or not self.digest:
            raise _ecology_err(
                "digest must be a non-empty string",
                path="digest",
            )

    def validate_for(self, snapshot: PopulationSnapshot) -> None:
        """Revalidate snapshot-dependent invariants against the supplied snapshot.

        Checks that all thought IDs exist in the snapshot and that the
        ecology digest matches the expected value.

        Raises :class:`SnapshotMismatchError` if the digest does not match.
        Raises :class:`UnknownThoughtError` if a thought ID is missing.
        """
        if not isinstance(snapshot, PopulationSnapshot):
            raise _ecology_err(
                f"expected PopulationSnapshot, got {type(snapshot).__name__}",
                path="snapshot",
            )

        # Check all thought IDs exist in snapshot
        snapshot_ids = {t.thought_id for t in snapshot.thoughts}
        for tid in self.thought_ids:
            if tid not in snapshot_ids:
                raise UnknownThoughtError(
                    f"thought {tid!r} not found in snapshot",
                    thought_id=tid,
                    reference_source="ThoughtEcology.validate_for",
                )

        # Recompute and compare digest
        data = self._to_digest_dict()
        expected_digest = _compute_digest(data)
        if self.digest != expected_digest:
            raise SnapshotMismatchError(
                "ecology digest does not match expected value",
                expected_digest=expected_digest,
                actual_digest=self.digest,
            )

    def _to_digest_dict(self) -> dict[str, Any]:
        """Produce the dict used for digest computation."""
        return {
            "thought_ids": list(self.thought_ids),
            "dependency_edges": [e.to_dict() for e in self.dependency_edges],
            "contradiction_edges": [e.to_dict() for e in self.contradiction_edges],
            "overlap_edges": [e.to_dict() for e in self.overlap_edges],
            "shared_assumption_links": [e.to_dict() for e in self.shared_assumption_links],
            "evidence_placements": [e.to_dict() for e in self.evidence_placements],
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        data = self._to_digest_dict()
        data["digest"] = self.digest
        return data

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

        # Parse thought_ids
        raw_ids = data["thought_ids"]
        if not isinstance(raw_ids, list):
            raise _ecology_err(
                f"thought_ids must be a JSON list, got {type(raw_ids).__name__}",
                path="thought_ids",
            )
        thought_ids = tuple(sorted(raw_ids))

        # Parse dependency_edges
        raw_deps = data["dependency_edges"]
        if not isinstance(raw_deps, list):
            raise _ecology_err(
                f"dependency_edges must be a JSON list, got {type(raw_deps).__name__}",
                path="dependency_edges",
            )
        dependency_edges = tuple(DependencyEdge.from_dict(e) for e in raw_deps)

        # Parse contradiction_edges
        raw_contras = data["contradiction_edges"]
        if not isinstance(raw_contras, list):
            raise _ecology_err(
                f"contradiction_edges must be a JSON list, got {type(raw_contras).__name__}",
                path="contradiction_edges",
            )
        contradiction_edges = tuple(ContradictionEdge.from_dict(e) for e in raw_contras)

        # Parse overlap_edges
        raw_overlaps = data["overlap_edges"]
        if not isinstance(raw_overlaps, list):
            raise _ecology_err(
                f"overlap_edges must be a JSON list, got {type(raw_overlaps).__name__}",
                path="overlap_edges",
            )
        overlap_edges = tuple(OverlapEdge.from_dict(e) for e in raw_overlaps)

        # Parse shared_assumption_links
        raw_assumptions = data["shared_assumption_links"]
        if not isinstance(raw_assumptions, list):
            raise _ecology_err(
                f"shared_assumption_links must be a JSON list, got {type(raw_assumptions).__name__}",
                path="shared_assumption_links",
            )
        shared_assumption_links = tuple(
            SharedAssumptionLink.from_dict(e) for e in raw_assumptions
        )

        # Parse evidence_placements
        raw_placements = data["evidence_placements"]
        if not isinstance(raw_placements, list):
            raise _ecology_err(
                f"evidence_placements must be a JSON list, got {type(raw_placements).__name__}",
                path="evidence_placements",
            )
        evidence_placements = tuple(
            EvidencePlacement.from_dict(e) for e in raw_placements
        )

        # Parse digest
        digest = data["digest"]
        if not isinstance(digest, str) or not digest:
            raise _ecology_err(
                "digest must be a non-empty string",
                path="digest",
            )

        return cls(
            thought_ids=thought_ids,
            dependency_edges=dependency_edges,
            contradiction_edges=contradiction_edges,
            overlap_edges=overlap_edges,
            shared_assumption_links=shared_assumption_links,
            evidence_placements=evidence_placements,
            digest=digest,
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
                f"expected str, got {type(text).__name__}",
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
                f"expected JSON object at root, got {type(data).__name__}",
                path="root",
            )
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build(
    snapshot: PopulationSnapshot,
    *,
    dependencies: Iterable[DependencyEdge] = (),
    contradictions: Iterable[ContradictionEdge] = (),
    overlaps: Iterable[OverlapEdge] = (),
    shared_assumptions: Iterable[SharedAssumptionLink] = (),
    evidence_placements: Iterable[EvidencePlacement] = (),
) -> ThoughtEcology:
    """Construct a validated ThoughtEcology from a snapshot and relations.

    Validates all invariants:
    - All referenced thought IDs exist in the snapshot
    - No self-references in any relation type
    - No dependency cycles
    - No conflicting assumption payloads
    - No ambiguous evidence bucket placements

    Parameters
    ----------
    snapshot:
        The current immutable population snapshot.
    dependencies:
        Directed dependency edges.
    contradictions:
        Undirected contradiction edges.
    overlaps:
        Undirected overlap edges.
    shared_assumptions:
        Shared assumption links between thoughts.
    evidence_placements:
        Evidence bucket placements.

    Returns
    -------
    ThoughtEcology
        A validated, immutable ecology index.

    Raises
    ------
    Various ThoughtEcologyError subclasses on validation failure.
    """
    if not isinstance(snapshot, PopulationSnapshot):
        raise _ecology_err(
            f"expected PopulationSnapshot, got {type(snapshot).__name__}",
            path="snapshot",
        )

    # Collect thought IDs from snapshot
    thought_ids = frozenset(t.thought_id for t in snapshot.thoughts)

    # Normalize relation tuples (sort for determinism)
    dep_tuple = tuple(sorted(dependencies, key=lambda e: (e.source_id, e.target_id)))
    contra_tuple = tuple(
        sorted(contradictions, key=lambda e: (e.first_id, e.second_id))
    )
    overlap_tuple = tuple(
        sorted(overlaps, key=lambda e: (e.first_id, e.second_id))
    )
    assumption_tuple = tuple(
        sorted(
            shared_assumptions,
            key=lambda e: (e.assumption_id, e.first_thought_id, e.second_thought_id),
        )
    )
    placement_tuple = tuple(
        sorted(
            evidence_placements,
            key=lambda e: (e.evidence_id, e.thought_id, e.bucket),
        )
    )

    # Validate: no self-references
    _check_no_self_references(dep_tuple, contra_tuple, overlap_tuple, assumption_tuple)

    # Validate: all referenced thoughts exist
    _check_unknown_thoughts(
        thought_ids,
        dep_tuple,
        contra_tuple,
        overlap_tuple,
        assumption_tuple,
        placement_tuple,
    )

    # Validate: no dependency cycles
    _check_dependency_cycles(dep_tuple)

    # Validate: no conflicting assumptions
    _check_conflicting_assumptions(assumption_tuple, snapshot)

    # Validate: no ambiguous evidence buckets
    _check_ambiguous_evidence_buckets(placement_tuple)

    # Compute digest
    sorted_thought_ids = tuple(sorted(thought_ids))
    digest_data = {
        "thought_ids": list(sorted_thought_ids),
        "dependency_edges": [e.to_dict() for e in dep_tuple],
        "contradiction_edges": [e.to_dict() for e in contra_tuple],
        "overlap_edges": [e.to_dict() for e in overlap_tuple],
        "shared_assumption_links": [e.to_dict() for e in assumption_tuple],
        "evidence_placements": [e.to_dict() for e in placement_tuple],
    }
    digest = _compute_digest(digest_data)

    return ThoughtEcology(
        thought_ids=sorted_thought_ids,
        dependency_edges=dep_tuple,
        contradiction_edges=contra_tuple,
        overlap_edges=overlap_tuple,
        shared_assumption_links=assumption_tuple,
        evidence_placements=placement_tuple,
        digest=digest,
    )
