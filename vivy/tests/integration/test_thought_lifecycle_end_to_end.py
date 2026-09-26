"""End-to-end deterministic ThoughtState lifecycle integration test."""

from __future__ import annotations

import json

from nps_core.hypothesis_population import (
    PopulationSnapshot,
    ThoughtState,
    TransitionEvent,
    branch,
    create,
    merge,
    prune,
    thought_state_from_dict,
    thought_state_to_dict,
)

# ---------------------------------------------------------------------------
# Local ThoughtState factory (full V1 dict, via from_dict)
# ---------------------------------------------------------------------------

def _state(
    thought_id: str,
    *,
    parents: tuple[str, ...] = (),
    status: str = "active",
    claim: str = "c",
    confidence: float = 0.5,
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
        "assumptions": [],
        "evidence": {"supporting": [], "opposing": [], "unresolved": []},
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
        "graph": {"dependencies": [], "contradictions": [], "overlaps": []},
        "status": {
            "state": status,
            "allowed_values": [
                "active", "queued", "testing", "partially_verified",
                "verified", "rejected", "merged", "dormant",
            ],
        },
    })


# ---------------------------------------------------------------------------
# Deterministic replay helper â returns (final_snapshot, prior_snapshots_json)
# ---------------------------------------------------------------------------

def _replay() -> tuple[PopulationSnapshot, tuple[tuple[PopulationSnapshot, str], ...]]:
    """Execute a deterministic 5-step lifecycle.

    Returns (final_snapshot, tuple_of_(snapshot, canonical_json)_pairs) where
    each entry is the snapshot and its canonical JSON *after* that transition.
    """
    snaps: list[tuple[PopulationSnapshot, str]] = []
    snap = PopulationSnapshot.empty()

    # 1. Create root A
    snap = create(
        snap,
        _state("THOUGHT-A", claim="root hypothesis", confidence=0.5),
        event_id="EVT-001",
        timestamp="2025-01-01T00:00:01Z",
        actor="alice",
    )
    snaps.append((snap, snap.to_canonical_json()))

    # 2. Branch B from A
    snap = branch(
        snap,
        _state("THOUGHT-B", parents=("THOUGHT-A",), claim="branch B", confidence=0.6),
        parent_id="THOUGHT-A",
        event_id="EVT-002",
        timestamp="2025-01-01T00:00:02Z",
        actor="bob",
    )
    snaps.append((snap, snap.to_canonical_json()))

    # 3. Branch C from A
    snap = branch(
        snap,
        _state("THOUGHT-C", parents=("THOUGHT-A",), claim="branch C", confidence=0.7),
        parent_id="THOUGHT-A",
        event_id="EVT-003",
        timestamp="2025-01-01T00:00:03Z",
        actor="carol",
    )
    snaps.append((snap, snap.to_canonical_json()))

    # 4. Merge B and C into M (reversed source order)
    snap = merge(
        snap,
        _state(
            "THOUGHT-M",
            parents=("THOUGHT-B", "THOUGHT-C"),
            claim="merged claim",
            confidence=0.85,
        ),
        source_ids=["THOUGHT-C", "THOUGHT-B"],
        event_id="EVT-004",
        timestamp="2025-01-01T00:00:04Z",
        actor="alice",
    )
    snaps.append((snap, snap.to_canonical_json()))

    # 5. Prune A dormant
    snap = prune(
        snap,
        "THOUGHT-A",
        reason="superseded by merge",
        disposition="dormant",
        event_id="EVT-005",
        timestamp="2025-01-01T00:00:05Z",
        actor="alice",
    )
    snaps.append((snap, snap.to_canonical_json()))

    return snap, tuple(snaps)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_replay_byte_identity() -> None:
    s1, _ = _replay()
    s2, _ = _replay()
    assert s1.to_canonical_json() == s2.to_canonical_json()
    json.loads(s1.to_canonical_json())  # valid JSON


def test_history_order_and_event_fields() -> None:
    snap, _ = _replay()
    assert len(snap.history) == 5
    ops = [e.operation for e in snap.history]
    assert ops == ["create", "branch", "branch", "merge", "prune"]
    ids = [e.event_id for e in snap.history]
    assert ids == ["EVT-001", "EVT-002", "EVT-003", "EVT-004", "EVT-005"]
    actors = [e.actor for e in snap.history]
    assert actors == ["alice", "bob", "carol", "alice", "alice"]
    merge_evt = snap.history[3]
    assert merge_evt.input_ids == ("THOUGHT-B", "THOUGHT-C")
    prune_evt = snap.history[4]
    assert prune_evt.reason == "superseded by merge"
    assert prune_evt.disposition == "dormant"


def test_final_statuses_and_merged_claim_confidence() -> None:
    snap, _ = _replay()
    assert snap.get("THOUGHT-A").status.state == "dormant"
    assert snap.get("THOUGHT-B").status.state == "merged"
    assert snap.get("THOUGHT-C").status.state == "merged"
    m = snap.get("THOUGHT-M")
    assert m.status.state == "active"
    assert m.hypothesis.claim == "merged claim"
    assert m.metrics.confidence == 0.85


def test_lineage_and_no_dangling_references() -> None:
    snap, _ = _replay()
    assert snap.get("THOUGHT-A").parent_ids == ()
    assert snap.get("THOUGHT-B").parent_ids == ("THOUGHT-A",)
    assert snap.get("THOUGHT-C").parent_ids == ("THOUGHT-A",)
    assert snap.get("THOUGHT-M").parent_ids == ("THOUGHT-B", "THOUGHT-C")
    assert snap.lineage.children_of("THOUGHT-A") == ("THOUGHT-B", "THOUGHT-C")
    assert snap.lineage.parents_of("THOUGHT-M") == ("THOUGHT-B", "THOUGHT-C")
    assert snap.lineage.ids() == tuple(sorted(t.thought_id for t in snap.thoughts))
    all_ids = {t.thought_id for t in snap.thoughts}
    for t in snap.thoughts:
        for pid in t.parent_ids:
            assert pid in all_ids, f"{t.thought_id} references missing parent {pid}"


def test_prior_snapshots_round_trip_unchanged() -> None:
    _, prior_pairs = _replay()
    for i, (retained, captured_json) in enumerate(prior_pairs):
        assert retained.to_canonical_json() == captured_json, (
            f"retained snapshot at step {i} JSON differs from captured JSON"
        )
        restored = PopulationSnapshot.from_canonical_json(captured_json)
        assert restored.to_canonical_json() == captured_json, (
            f"snapshot at step {i} changed after later transitions"
        )


def test_snapshot_dict_json_round_trip() -> None:
    snap, _ = _replay()
    d = snap.to_dict()
    assert PopulationSnapshot.from_dict(d).to_canonical_json() == snap.to_canonical_json()
    j = snap.to_canonical_json()
    assert PopulationSnapshot.from_canonical_json(j).to_canonical_json() == j


def test_thought_state_dict_round_trip() -> None:
    snap, _ = _replay()
    for t in snap.thoughts:
        d = thought_state_to_dict(t)
        assert thought_state_to_dict(thought_state_from_dict(d)) == d


def test_transition_event_dict_round_trip() -> None:
    snap, _ = _replay()
    for e in snap.history:
        d = e.to_dict()
        assert TransitionEvent.from_dict(d).to_dict() == d


def test_sorted_thought_ids() -> None:
    snap, _ = _replay()
    ids = [t.thought_id for t in snap.thoughts]
    assert ids == sorted(ids)
