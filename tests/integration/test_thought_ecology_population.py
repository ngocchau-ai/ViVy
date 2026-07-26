"""Integration test: thought ecology building from a population snapshot.

Validates the full pipeline from ThoughtState creation through
ThoughtEcology construction with all relation types, using the
``build(snapshot)`` extraction path.
"""

from __future__ import annotations

import hashlib

from nps_core.hypothesis_population import (
    PopulationSnapshot,
    ThoughtState,
    create,
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
# ThoughtState factory with graph fields
# ---------------------------------------------------------------------------

_SHARED_ASSUMPTION = {
    "assumption_id": "ASM-001",
    "statement": "shared axiom",
    "confidence": 0.9,
    "source": "manual",
}


def _make_thought(
    thought_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    contradictions: tuple[str, ...] = (),
    overlaps: tuple[str, ...] = (),
    assumptions: list[dict] | None = None,
    supporting: tuple[str, ...] = (),
    opposing: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> ThoughtState:
    """Create a ThoughtState with graph, assumptions, and evidence."""
    return ThoughtState.from_dict({
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2025-01-01T00:00:00Z",
        "interpretation": {
            "summary": f"s-{thought_id}",
            "scope": "global",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": f"c-{thought_id}",
            "predicted_observations": ["obs1"],
            "falsification_conditions": ["fail1"],
        },
        "assumptions": assumptions or [],
        "evidence": {
            "supporting": list(supporting),
            "opposing": list(opposing),
            "unresolved": list(unresolved),
        },
        "metrics": {
            "confidence": 0.5, "novelty": 0.5, "diversity": 0.5,
            "expected_value": 0.5, "information_need": 0.5,
            "risk_if_wrong": 0.5, "execution_cost": 0.5,
        },
        "verification_plan": {
            "questions": ["q1"], "required_experiments": ["exp1"],
            "acceptable_evidence": ["ev1"], "rejection_threshold": 0.1,
        },
        "executor_profile": {
            "skills": ["analysis"], "tool_requirements": ["tool1"],
            "preferred_model_class": "reasoning",
            "independence_requirements": ["indep1"],
        },
        "graph": {
            "dependencies": list(dependencies),
            "contradictions": list(contradictions),
            "overlaps": list(overlaps),
        },
        "status": {
            "state": "active",
            "allowed_values": [
                "active", "queued", "testing", "partially_verified",
                "verified", "rejected", "merged", "dormant",
            ],
        },
    })


def _add(
    snap: PopulationSnapshot,
    state: ThoughtState,
    event_id: str,
) -> PopulationSnapshot:
    return create(
        snap, state,
        event_id=event_id,
        timestamp="2025-01-01T00:00:00Z",
        actor="tester",
    )


# ---------------------------------------------------------------------------
# Deterministic snapshot with rich ecology
# ---------------------------------------------------------------------------

def _snapshot() -> PopulationSnapshot:
    """Build a deterministic snapshot with six thoughts.

    Dependency graph (source depends on target):
        B→A, C→A, D→B, D→C, E→D

    Contradictions: B↔C (reciprocal), A→E (one-sided)
    Overlaps: A→D, B→D (both one-sided)
    Shared assumption ASM-001 across A, B, C
    Evidence: EV-X in A-supporting + B-opposing;
              EV-Y in C-unresolved + D-supporting
    Isolated: F
    """
    snap = PopulationSnapshot.empty()

    snap = _add(snap, _make_thought(
        "THOUGHT-A",
        contradictions=("THOUGHT-E",),
        overlaps=("THOUGHT-D",),
        assumptions=[_SHARED_ASSUMPTION],
        supporting=("EV-X",),
    ), "EVT-001")

    snap = _add(snap, _make_thought(
        "THOUGHT-B",
        dependencies=("THOUGHT-A",),
        contradictions=("THOUGHT-C",),
        overlaps=("THOUGHT-D",),
        assumptions=[_SHARED_ASSUMPTION],
        opposing=("EV-X",),
    ), "EVT-002")

    snap = _add(snap, _make_thought(
        "THOUGHT-C",
        dependencies=("THOUGHT-A",),
        contradictions=("THOUGHT-B",),
        assumptions=[_SHARED_ASSUMPTION],
        unresolved=("EV-Y",),
    ), "EVT-003")

    snap = _add(snap, _make_thought(
        "THOUGHT-D",
        dependencies=("THOUGHT-B", "THOUGHT-C"),
        overlaps=("THOUGHT-B", "THOUGHT-A"),
        supporting=("EV-Y",),
    ), "EVT-004")

    snap = _add(snap, _make_thought(
        "THOUGHT-E",
        dependencies=("THOUGHT-D",),
    ), "EVT-005")

    snap = _add(snap, _make_thought(
        "THOUGHT-F",
    ), "EVT-006")

    return snap


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_build_twice_byte_identical() -> None:
    snap = _snapshot()
    eco1 = build(snap)
    eco2 = build(snap)
    assert eco1.to_canonical_json() == eco2.to_canonical_json()


def test_expected_thought_ids() -> None:
    eco = build(_snapshot())
    assert eco.thought_ids == (
        "THOUGHT-A", "THOUGHT-B", "THOUGHT-C",
        "THOUGHT-D", "THOUGHT-E", "THOUGHT-F",
    )


def test_expected_dependency_edges() -> None:
    eco = build(_snapshot())
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
    eco = build(_snapshot())
    expected = (
        ContradictionEdge(first_id="THOUGHT-A", second_id="THOUGHT-E"),
        ContradictionEdge(first_id="THOUGHT-B", second_id="THOUGHT-C"),
    )
    assert eco.contradictions == expected


def test_expected_overlap_edges() -> None:
    eco = build(_snapshot())
    expected = (
        OverlapEdge(first_id="THOUGHT-A", second_id="THOUGHT-D"),
        OverlapEdge(first_id="THOUGHT-B", second_id="THOUGHT-D"),
    )
    assert eco.overlaps == expected


def test_expected_shared_assumption_links() -> None:
    """ASM-001 shared by A, B, C produces three pair links."""
    eco = build(_snapshot())
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
    eco = build(_snapshot())
    expected = (
        EvidencePlacement(
            evidence_id="EV-X", thought_id="THOUGHT-A",
            bucket="supporting",
        ),
        EvidencePlacement(
            evidence_id="EV-X", thought_id="THOUGHT-B",
            bucket="opposing",
        ),
        EvidencePlacement(
            evidence_id="EV-Y", thought_id="THOUGHT-C",
            bucket="unresolved",
        ),
        EvidencePlacement(
            evidence_id="EV-Y", thought_id="THOUGHT-D",
            bucket="supporting",
        ),
    )
    assert eco.evidence_placements == expected


def test_snapshot_digest() -> None:
    snap = _snapshot()
    eco = build(snap)
    expected = hashlib.sha256(
        snap.to_canonical_json().encode("utf-8"),
    ).hexdigest()
    assert eco.snapshot_digest == expected


def test_validate_for_exact_snapshot() -> None:
    snap = _snapshot()
    eco = build(snap)
    eco.validate_for(snap)  # must not raise


def test_changed_snapshot_fails_validate_for() -> None:
    snap = _snapshot()
    eco = build(snap)
    changed = create(
        snap,
        _make_thought("THOUGHT-G"),
        event_id="EVT-007",
        timestamp="2025-01-01T00:00:00Z",
        actor="tester",
    )
    try:
        eco.validate_for(changed)
        raise AssertionError("expected SnapshotMismatchError")
    except SnapshotMismatchError:
        pass


def test_forged_ecology_fails_validate_for() -> None:
    """Forge ecology with same digest but removed contradiction."""
    snap = _snapshot()
    eco = build(snap)
    forged = ThoughtEcology(
        snapshot_digest=eco.snapshot_digest,
        thought_ids=eco.thought_ids,
        dependencies=eco.dependencies,
        contradictions=eco.contradictions[1:],
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


def test_build_does_not_mutate_snapshot() -> None:
    snap = _snapshot()
    before = snap.to_canonical_json()
    _ = build(snap)
    assert snap.to_canonical_json() == before


def test_rebuild_from_reconstructed_snapshot() -> None:
    snap = _snapshot()
    eco1 = build(snap)
    snap2 = PopulationSnapshot.from_canonical_json(
        snap.to_canonical_json(),
    )
    eco2 = build(snap2)
    assert eco1.to_canonical_json() == eco2.to_canonical_json()


def test_dict_json_round_trip() -> None:
    eco = build(_snapshot())
    d = eco.to_dict()
    eco2 = ThoughtEcology.from_dict(d)
    assert eco2.to_canonical_json() == eco.to_canonical_json()
    j = eco.to_canonical_json()
    eco3 = ThoughtEcology.from_canonical_json(j)
    assert eco3.to_canonical_json() == j


def test_query_methods() -> None:
    eco = build(_snapshot())

    # dependencies_of
    assert len(eco.dependencies_of("THOUGHT-D")) == 2

    # dependents_of
    assert len(eco.dependents_of("THOUGHT-A")) == 2

    # contradictions_of
    assert len(eco.contradictions_of("THOUGHT-B")) == 1

    # overlaps_of
    assert len(eco.overlaps_of("THOUGHT-D")) == 2

    # shared_assumptions_of
    assert len(eco.shared_assumptions_of("THOUGHT-A")) == 2

    # evidence_for
    assert len(eco.evidence_for("THOUGHT-A")) == 1

    # transitive_dependencies
    td = eco.transitive_dependencies("THOUGHT-E")
    assert set(td) == {"THOUGHT-A", "THOUGHT-B", "THOUGHT-C", "THOUGHT-D"}

    # topological_order
    topo = eco.topological_order()
    pos = {tid: i for i, tid in enumerate(topo)}
    for edge in eco.dependencies:
        assert pos[edge.target_id] < pos[edge.source_id]

    # neighborhood
    n_a = eco.neighborhood("THOUGHT-A")
    assert "THOUGHT-B" in n_a
    assert "THOUGHT-D" in n_a
    assert "THOUGHT-E" in n_a
    assert "THOUGHT-A" not in n_a

    # isolated
    assert eco.neighborhood("THOUGHT-F") == ()
