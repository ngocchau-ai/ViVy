"""End-to-end deterministic ThoughtEcology population integration test."""

from __future__ import annotations

import hashlib
import json

from nps_core.hypothesis_population import (
    PopulationSnapshot,
    ThoughtState,
)
from nps_core.thought_ecology import (
    ContradictionEdge,
    DependencyEdge,
    EvidencePlacement,
    OverlapEdge,
    SharedAssumptionLink,
    SnapshotMismatchError,
    ThoughtEcology,
    build,
)


# ---------------------------------------------------------------------------
# Local ThoughtState V1 factory (full dict, via from_dict)
# ---------------------------------------------------------------------------

def _state(
    thought_id: str,
    *,
    parents: tuple[str, ...] = (),
    status: str = "active",
    claim: str = "c",
    confidence: float = 0.5,
    dependencies: tuple[str, ...] = (),
    contradictions: tuple[str, ...] = (),
    overlaps: tuple[str, ...] = (),
    assumptions: tuple[dict[str, object], ...] = (),
    supporting: tuple[str, ...] = (),
    opposing: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> ThoughtState:
    return ThoughtState.from_dict({
        "thought_id": thought_id,
        "parent_ids": list(parents),
        "created_at": "2025-01-01T00:00:00Z",
        "interpretation": {"summary": "s", "scope": "sc", "excluded_scope": []},
        "hypothesis": {
            "claim": claim,
            "predicted_observations": [],
            "falsification_conditions": [],
        },
        "assumptions": list(assumptions),
        "evidence": {
            "supporting": list(supporting),
            "opposing": list(opposing),
            "unresolved": list(unresolved),
        },
        "metrics": {
            "confidence": confidence,
            "novelty": 0.5,
            "diversity": 0.5,
            "expected_value": 0.5,
            "information_need": 0.5,
            "risk_if_wrong": 0.5,
            "execution_cost": 0.5,
        },
        "verification_plan": {
            "questions": [],
            "required_experiments": [],
            "acceptable_evidence": [],
            "rejection_threshold": 0.5,
        },
        "executor_profile": {
            "skills": [],
            "tool_requirements": [],
            "preferred_model_class": "default",
            "independence_requirements": [],
        },
        "graph": {
            "dependencies": list(dependencies),
            "contradictions": list(contradictions),
            "overlaps": list(overlaps),
        },
        "status": {
            "state": status,
            "allowed_values": [
                "active", "queued", "testing", "partially_verified",
                "verified", "rejected", "merged", "dormant",
            ],
        },
    })


# ---------------------------------------------------------------------------
# Deterministic PopulationSnapshot factory with rich ecology
# ---------------------------------------------------------------------------

_SHARED_ASSUMPTION = {
    "assumption_id": "ASM-001",
    "statement": "shared axiom",
    "confidence": 0.9,
    "source": "manual",
}


def _snapshot() -> PopulationSnapshot:
    """Build a deterministic snapshot with six thoughts and rich relations.

    Dependency edges (source depends on target):
        B->A
        C->A
        D->B
        D->C
        E->D

    Contradictions:
        THOUGHT-B <-> THOUGHT-C  (reciprocal: both declare)
        THOUGHT-A -> THOUGHT-E   (one-sided: only A declares)

    Overlaps:
        THOUGHT-B <-> THOUGHT-D  (reciprocal)
        THOUGHT-A -> THOUGHT-D   (one-sided)

    Shared assumption ASM-001 across THOUGHT-A, THOUGHT-B, THOUGHT-C.

    Evidence co-placement:
        EV-X in THOUGHT-A supporting, THOUGHT-B opposing
        EV-Y in THOUGHT-C unresolved, THOUGHT-D supporting

    Isolated thought: THOUGHT-F (no relations except shared assumption
    is NOT on F; F has no edges at all).
    """
    snap = PopulationSnapshot.empty()

    # THOUGHT-A: depends on nothing, contradicts E, overlaps D
    snap = _add(
        snap,
        _state(
            "THOUGHT-A",
            claim="root",
            dependencies=(),
            contradictions=("THOUGHT-E",),
            overlaps=("THOUGHT-D",),
            assumptions=(_SHARED_ASSUMPTION,),
            supporting=("EV-X",),
        ),
        event_id="EVT-001",
    )

    # THOUGHT-B: depends on A, contradicts C, overlaps D
    snap = _add(
        snap,
        _state(
            "THOUGHT-B",
            claim="branch B",
            dependencies=("THOUGHT-A",),
            contradictions=("THOUGHT-C",),
            overlaps=("THOUGHT-D",),
            assumptions=(_SHARED_ASSUMPTION,),
            opposing=("EV-X",),
        ),
        event_id="EVT-002",
    )

    # THOUGHT-C: depends on A, contradicts B, no overlaps
    snap = _add(
        snap,
        _state(
            "THOUGHT-C",
            claim="branch C",
            dependencies=("THOUGHT-A",),
            contradictions=("THOUGHT-B",),
            assumptions=(_SHARED_ASSUMPTION,),
            unresolved=("EV-Y",),
        ),
        event_id="EVT-003",
    )

    # THOUGHT-D: depends on B and C, overlaps B and A
    snap = _add(
        snap,
        _state(
            "THOUGHT-D",
            claim="merge D",
            dependencies=("THOUGHT-B", "THOUGHT-C"),
            overlaps=("THOUGHT-B", "THOUGHT-A"),
            supporting=("EV-Y",),
        ),
        event_id="EVT-004",
    )

    # THOUGHT-E: depends on D, contradicted by A (one-sided)
    snap = _add(
        snap,
        _state(
            "THOUGHT-E",
            claim="leaf E",
            dependencies=("THOUGHT-D",),
        ),
        event_id="EVT-005",
    )

    # THOUGHT-F: isolated
    snap = _add(
        snap,
        _state("THOUGHT-F", claim="isolated"),
        event_id="EVT-006",
    )

    return snap


def _add(
    snap: PopulationSnapshot,
    state: ThoughtState,
    *,
    event_id: str,
) -> PopulationSnapshot:
    """Add a thought to the snapshot via create."""
    from nps_core.hypothesis_population import create

    return create(
        snap,
        state,
        event_id=event_id,
        timestamp="2025-01-01T00:00:00Z",
        actor="tester",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_build_twice_canonical_json_byte_identical() -> None:
    """Two independently built ecologies from the same snapshot are identical."""
    snap = _snapshot()
    eco1 = build(snap)
    eco2 = build(snap)
    assert eco1.to_canonical_json() == eco2.to_canonical_json()


def test_expected_thought_ids() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.thought_ids == (
        "THOUGHT-A", "THOUGHT-B", "THOUGHT-C",
        "THOUGHT-D", "THOUGHT-E", "THOUGHT-F",
    )


def test_expected_dependency_edges() -> None:
    snap = _snapshot()
    eco = build(snap)
    expected = (
        DependencyEdge(source_id="THOUGHT-B", target_id="THOUGHT-A"),
        DependencyEdge(source_id="THOUGHT-C", target_id="THOUGHT-A"),
        DependencyEdge(source_id="THOUGHT-D", target_id="THOUGHT-B"),
        DependencyEdge(source_id="THOUGHT-D", target_id="THOUGHT-C"),
        DependencyEdge(source_id="THOUGHT-E", target_id="THOUGHT-D"),
    )
    assert eco.dependencies == expected


def test_expected_contradiction_edges() -> None:
    """Reciprocal declarations collapse to one canonical undirected pair."""
    snap = _snapshot()
    eco = build(snap)
    expected = (
        ContradictionEdge(first_id="THOUGHT-A", second_id="THOUGHT-E"),
        ContradictionEdge(first_id="THOUGHT-B", second_id="THOUGHT-C"),
    )
    assert eco.contradictions == expected


def test_expected_overlap_edges() -> None:
    """Reciprocal declarations collapse; one-sided accepted and normalized."""
    snap = _snapshot()
    eco = build(snap)
    expected = (
        OverlapEdge(first_id="THOUGHT-A", second_id="THOUGHT-D"),
        OverlapEdge(first_id="THOUGHT-B", second_id="THOUGHT-D"),
    )
    assert eco.overlaps == expected


def test_expected_shared_assumption_links() -> None:
    """ASM-001 shared by A, B, C produces three pair links."""
    snap = _snapshot()
    eco = build(snap)
    expected = (
        SharedAssumptionLink(
            assumption_id="ASM-001",
            first_thought_id="THOUGHT-A",
            second_thought_id="THOUGHT-B",
        ),
        SharedAssumptionLink(
            assumption_id="ASM-001",
            first_thought_id="THOUGHT-A",
            second_thought_id="THOUGHT-C",
        ),
        SharedAssumptionLink(
            assumption_id="ASM-001",
            first_thought_id="THOUGHT-B",
            second_thought_id="THOUGHT-C",
        ),
    )
    assert eco.shared_assumptions == expected


def test_expected_evidence_placements() -> None:
    """Evidence co-placed across different buckets and thoughts."""
    snap = _snapshot()
    eco = build(snap)
    expected = (
        EvidencePlacement(evidence_id="EV-X", thought_id="THOUGHT-A", bucket="supporting"),
        EvidencePlacement(evidence_id="EV-X", thought_id="THOUGHT-B", bucket="opposing"),
        EvidencePlacement(evidence_id="EV-Y", thought_id="THOUGHT-C", bucket="unresolved"),
        EvidencePlacement(evidence_id="EV-Y", thought_id="THOUGHT-D", bucket="supporting"),
    )
    assert eco.evidence_placements == expected


def test_dependencies_of_query() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.dependencies_of("THOUGHT-A") == ()
    assert eco.dependencies_of("THOUGHT-D") == (
        DependencyEdge(source_id="THOUGHT-D", target_id="THOUGHT-B"),
        DependencyEdge(source_id="THOUGHT-D", target_id="THOUGHT-C"),
    )
    assert eco.dependencies_of("THOUGHT-F") == ()


def test_dependents_of_query() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.dependents_of("THOUGHT-D") == (
        DependencyEdge(source_id="THOUGHT-E", target_id="THOUGHT-D"),
    )
    assert eco.dependents_of("THOUGHT-A") == (
        DependencyEdge(source_id="THOUGHT-B", target_id="THOUGHT-A"),
        DependencyEdge(source_id="THOUGHT-C", target_id="THOUGHT-A"),
    )


def test_contradictions_of_query() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.contradictions_of("THOUGHT-B") == (
        ContradictionEdge(first_id="THOUGHT-B", second_id="THOUGHT-C"),
    )
    assert eco.contradictions_of("THOUGHT-E") == (
        ContradictionEdge(first_id="THOUGHT-A", second_id="THOUGHT-E"),
    )


def test_overlaps_of_query() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.overlaps_of("THOUGHT-D") == (
        OverlapEdge(first_id="THOUGHT-A", second_id="THOUGHT-D"),
        OverlapEdge(first_id="THOUGHT-B", second_id="THOUGHT-D"),
    )


def test_shared_assumptions_of_query() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.shared_assumptions_of("THOUGHT-A") == (
        SharedAssumptionLink(
            assumption_id="ASM-001",
            first_thought_id="THOUGHT-A",
            second_thought_id="THOUGHT-B",
        ),
        SharedAssumptionLink(
            assumption_id="ASM-001",
            first_thought_id="THOUGHT-A",
            second_thought_id="THOUGHT-C",
        ),
    )


def test_evidence_for_query() -> None:
    snap = _snapshot()
    eco = build(snap)
    assert eco.evidence_for("THOUGHT-A") == (
        EvidencePlacement(evidence_id="EV-X", thought_id="THOUGHT-A", bucket="supporting"),
    )
    assert eco.evidence_for("THOUGHT-F") == ()


def test_topological_order_targets_precede_sources() -> None:
    """Every dependency target appears before its source in topo order."""
    snap = _snapshot()
    eco = build(snap)
    topo = eco.topological_order()
    pos = {tid: i for i, tid in enumerate(topo)}
    for edge in eco.dependencies:
        assert pos[edge.target_id] < pos[edge.source_id], (
            f"target {edge.target_id} should precede source {edge.source_id}"
        )


def test_topological_order_contains_all_thoughts() -> None:
    snap = _snapshot()
    eco = build(snap)
    topo = eco.topological_order()
    assert set(topo) == set(eco.thought_ids)


def test_transitive_dependencies() -> None:
    snap = _snapshot()
    eco = build(snap)
    # A has no deps
    assert eco.transitive_dependencies("THOUGHT-A") == ()
    # B depends on A
    assert eco.transitive_dependencies("THOUGHT-B") == ("THOUGHT-A",)
    # D depends on B, C, A transitively
    assert eco.transitive_dependencies("THOUGHT-D") == (
        "THOUGHT-A", "THOUGHT-B", "THOUGHT-C",
    )
    # E depends on D, B, C, A transitively
    assert eco.transitive_dependencies("THOUGHT-E") == (
        "THOUGHT-A", "THOUGHT-B", "THOUGHT-C", "THOUGHT-D",
    )
    # F is isolated
    assert eco.transitive_dependencies("THOUGHT-F") == ()


def test_neighborhood_unions_all_relation_types() -> None:
    """Neighborhood includes all relation types but excludes self and evidence IDs."""
    snap = _snapshot()
    eco = build(snap)

    # THOUGHT-A: deps to B,C; contradicts E; overlaps D; shared assumption with B,C
    # evidence EV-X shared with B
    # Union: B, C, D, E
    assert eco.neighborhood("THOUGHT-A") == ("THOUGHT-B", "THOUGHT-C", "THOUGHT-D", "THOUGHT-E")

    # THOUGHT-D: deps from B,C; dep to E; overlaps A,B; evidence EV-Y shared with C
    # Union: A, B, C, E
    assert eco.neighborhood("THOUGHT-D") == ("THOUGHT-A", "THOUGHT-B", "THOUGHT-C", "THOUGHT-E")

    # THOUGHT-F: isolated
    assert eco.neighborhood("THOUGHT-F") == ()


def test_ecology_dict_json_round_trip() -> None:
    snap = _snapshot()
    eco = build(snap)
    d = eco.to_dict()
    eco2 = ThoughtEcology.from_dict(d)
    assert eco2.to_canonical_json() == eco.to_canonical_json()
    j = eco.to_canonical_json()
    eco3 = ThoughtEcology.from_canonical_json(j)
    assert eco3.to_canonical_json() == j


def test_validate_for_exact_snapshot() -> None:
    snap = _snapshot()
    eco = build(snap)
    eco.validate_for(snap)  # must not raise


def test_snapshot_digest_equals_sha256_of_snapshot_canonical_json() -> None:
    snap = _snapshot()
    eco = build(snap)
    expected_digest = hashlib.sha256(
        snap.to_canonical_json().encode("utf-8")
    ).hexdigest()
    assert eco.snapshot_digest == expected_digest


def test_source_snapshots_and_lifecycle_history_byte_identical() -> None:
    """Building ecology does not mutate the source snapshot or its history."""
    snap = _snapshot()
    snap_json_before = snap.to_canonical_json()
    history_json_before = json.dumps(
        [e.to_dict() for e in snap.history],
        sort_keys=True,
        separators=(",", ":"),
    )
    _ = build(snap)
    assert snap.to_canonical_json() == snap_json_before
    history_json_after = json.dumps(
        [e.to_dict() for e in snap.history],
        sort_keys=True,
        separators=(",", ":"),
    )
    assert history_json_after == history_json_before


def test_changed_snapshot_makes_old_ecology_validate_for_raise() -> None:
    """A separately reconstructed changed snapshot fails validate_for."""
    snap = _snapshot()
    eco = build(snap)

    # Build a different snapshot (add one more thought)
    from nps_core.hypothesis_population import create

    changed = create(
        snap,
        _state("THOUGHT-G", claim="extra"),
        event_id="EVT-007",
        timestamp="2025-01-01T00:00:00Z",
        actor="tester",
    )
    assert changed.to_canonical_json() != snap.to_canonical_json()

    try:
        eco.validate_for(changed)
        raise AssertionError("expected SnapshotMismatchError")
    except SnapshotMismatchError:
        pass


def test_forged_ecology_with_removed_relation_fails_validate_for() -> None:
    """Direct structurally forged ecology with same digest but removed relation fails."""
    snap = _snapshot()
    eco = build(snap)

    # Forge: same digest, same thought_ids, but remove one contradiction
    forged = ThoughtEcology(
        snapshot_digest=eco.snapshot_digest,
        thought_ids=eco.thought_ids,
        dependencies=eco.dependencies,
        contradictions=eco.contradictions[1:],  # remove first contradiction
        overlaps=eco.overlaps,
        shared_assumptions=eco.shared_assumptions,
        evidence_placements=eco.evidence_placements,
    )
    assert forged.snapshot_digest == eco.snapshot_digest

    try:
        forged.validate_for(snap)
        raise AssertionError("expected SnapshotMismatchError")
    except SnapshotMismatchError:
        pass


def test_rebuild_from_independently_reconstructed_snapshot() -> None:
    """Reconstruct snapshot from JSON, build ecology, compare byte-identical."""
    snap = _snapshot()
    eco1 = build(snap)

    # Reconstruct from canonical JSON
    snap_json = snap.to_canonical_json()
    snap2 = PopulationSnapshot.from_canonical_json(snap_json)
    eco2 = build(snap2)

    assert eco1.to_canonical_json() == eco2.to_canonical_json()
