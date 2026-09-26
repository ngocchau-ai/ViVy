"""Unit tests for TransitionEvent, PopulationSnapshot, and LineageIndex."""

from __future__ import annotations

import pytest

from nps_core.hypothesis_population import (
    CycleDetectedError,
    DuplicateEventError,
    DuplicateIdError,
    InvalidDispositionError,
    InvalidTransitionError,
    LineageIndex,
    MergeSourceError,
    PopulationSnapshot,
    TerminalStateError,
    ThoughtState,
    TransitionEvent,
    UnknownReferenceError,
    ValidationError,
    branch,
    create,
    merge,
    prune,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(
    thought_id: str,
    *,
    parents: tuple[str, ...] = (),
    status: str = "active",
    claim: str | None = None,
    confidence: float = 0.5,
) -> ThoughtState:
    """Return a full valid ThoughtState via from_dict."""
    return ThoughtState.from_dict({
        "thought_id": thought_id,
        "parent_ids": list(parents),
        "created_at": "2025-01-01T00:00:00Z",
        "interpretation": {
            "summary": "s",
            "scope": "sc",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": claim or "c",
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
        "status": {"state": status, "allowed_values": [
            "active", "queued", "testing", "partially_verified",
            "verified", "rejected", "merged", "dormant",
        ]},
    })


def _event(
    *,
    event_id: str = "evt-1",
    operation: str = "create",
    input_ids: tuple[str, ...] = (),
    output_ids: tuple[str, ...] = (),
    reason: str | None = None,
    disposition: str | None = None,
) -> TransitionEvent:
    """Return a valid TransitionEvent for a requested operation."""
    return TransitionEvent(
        event_id=event_id,
        timestamp="2025-01-01T00:00:00Z",
        operation=operation,
        actor="tester",
        input_ids=input_ids,
        output_ids=output_ids,
        reason=reason,
        disposition=disposition,
    )


def _bytes(snapshot: PopulationSnapshot) -> str:
    """Return canonical JSON string for a snapshot."""
    return snapshot.to_canonical_json()


def _kwargs(n: int) -> dict:
    """Return caller-supplied event_id/timestamp/actor keyword dict."""
    return {
        "event_id": f"evt-{n:04d}",
        "timestamp": f"2025-01-{n + 1:02d}T00:00:00Z",
        "actor": f"actor-{n}",
    }


# ---------------------------------------------------------------------------
# Smoke test â state helper round trips
# ---------------------------------------------------------------------------

def test_state_round_trip():
    ts = _state("THOUGHT-0001", parents=("THOUGHT-0000",), claim="hello", confidence=0.9)
    assert ts.thought_id == "THOUGHT-0001"
    assert ts.status.state == "active"
    d = ts.to_dict()
    assert d["parent_ids"] == ["THOUGHT-0000"]
    assert d["hypothesis"]["claim"] == "hello"
    assert d["metrics"]["confidence"] == 0.9
    ts2 = ThoughtState.from_dict(d)
    assert ts2.to_dict() == d


# ===========================================================================
# TransitionEvent tests
# ===========================================================================

class TestTransitionEventEquality:
    def test_equal_events_are_equal(self):
        a = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        b = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        assert a == b

    def test_different_event_ids_not_equal(self):
        a = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        b = _event(event_id="e2", operation="create", output_ids=("THOUGHT-A",))
        assert a != b


class TestTransitionEventFrozen:
    def test_fields_are_frozen(self):
        ev = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        with pytest.raises(AttributeError):
            ev.event_id = "other"  # type: ignore[misc]


class TestTransitionEventRoundTrip:
    def test_to_dict_from_dict_roundtrip(self):
        ev = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        d = ev.to_dict()
        ev2 = TransitionEvent.from_dict(d)
        assert ev == ev2
        assert ev2.to_dict() == d

    def test_prune_with_reason_and_disposition_roundtrip(self):
        ev = _event(
            event_id="e2",
            operation="prune",
            input_ids=("THOUGHT-A",),
            output_ids=("THOUGHT-A",),
            reason="bad",
            disposition="rejected",
        )
        d = ev.to_dict()
        assert d["reason"] == "bad"
        assert d["disposition"] == "rejected"
        ev2 = TransitionEvent.from_dict(d)
        assert ev == ev2


class TestTransitionEventOperationShapes:
    @pytest.mark.parametrize(
        "op,in_ids,out_ids",
        [
            ("create", (), ("THOUGHT-A",)),
            ("branch", ("THOUGHT-A",), ("THOUGHT-B",)),
            ("merge", ("THOUGHT-A", "THOUGHT-B"), ("THOUGHT-C",)),
            ("prune", ("THOUGHT-A",), ("THOUGHT-A",)),
        ],
        ids=["create", "branch", "merge", "prune"],
    )
    def test_valid_operation_shape(self, op, in_ids, out_ids):
        kwargs: dict = {}
        if op == "prune":
            kwargs["reason"] = "r"
            kwargs["disposition"] = "rejected"
        ev = _event(operation=op, input_ids=in_ids, output_ids=out_ids, **kwargs)
        assert ev.operation == op
        assert ev.input_ids == in_ids
        assert ev.output_ids == out_ids


class TestTransitionEventMalformed:
    def test_create_with_inputs_rejected(self):
        with pytest.raises(InvalidTransitionError):
            _event(operation="create", input_ids=("THOUGHT-A",), output_ids=("THOUGHT-B",))

    def test_branch_same_input_output_rejected(self):
        with pytest.raises(InvalidTransitionError):
            _event(operation="branch", input_ids=("THOUGHT-A",), output_ids=("THOUGHT-A",))

    def test_merge_single_input_rejected(self):
        with pytest.raises(InvalidTransitionError):
            _event(operation="merge", input_ids=("THOUGHT-A",), output_ids=("THOUGHT-B",))

    def test_prune_mismatched_ids_rejected(self):
        with pytest.raises(InvalidTransitionError):
            _event(
                operation="prune",
                input_ids=("THOUGHT-A",),
                output_ids=("THOUGHT-B",),
                reason="r",
                disposition="rejected",
            )


class TestTransitionEventDuplicateIds:
    def test_duplicate_input_ids_rejected(self):
        with pytest.raises(ValidationError, match="duplicate"):
            _event(
                operation="merge",
                input_ids=("THOUGHT-A", "THOUGHT-A"),
                output_ids=("THOUGHT-B",),
            )

    def test_duplicate_output_ids_rejected(self):
        with pytest.raises(ValidationError, match="duplicate"):
            _event(
                operation="create",
                output_ids=("THOUGHT-A", "THOUGHT-A"),
            )


class TestTransitionEventKeyValidation:
    def test_missing_required_key_rejected(self):
        d = _event(operation="create", output_ids=("THOUGHT-A",)).to_dict()
        del d["actor"]
        with pytest.raises(ValidationError, match="missing"):
            TransitionEvent.from_dict(d)

    def test_extra_key_rejected(self):
        d = _event(operation="create", output_ids=("THOUGHT-A",)).to_dict()
        d["extra"] = 1
        with pytest.raises(ValidationError, match="unexpected"):
            TransitionEvent.from_dict(d)

    def test_bad_type_for_input_ids_rejected(self):
        d = _event(operation="create", output_ids=("THOUGHT-A",)).to_dict()
        d["input_ids"] = "not-a-list"
        with pytest.raises(ValidationError, match="list"):
            TransitionEvent.from_dict(d)

    def test_bad_timestamp_rejected(self):
        with pytest.raises(ValidationError, match="RFC3339"):
            TransitionEvent(
                event_id="e1",
                timestamp="not-a-timestamp",
                operation="create",
                actor="a",
                input_ids=(),
                output_ids=("THOUGHT-A",),
            )


    @pytest.mark.parametrize(
        "ts",
        [
            "2025-13-01T00:00:00Z",
            "2025-01-32T00:00:00Z",
            "2025-01-01T25:00:00Z",
            "2025-01-01T00:00:00+24:00",
        ],
        ids=["month_13", "day_32", "hour_25", "tz_offset_24"],
    )
    def test_semantically_invalid_rfc3339_rejected(self, ts: str) -> None:
        with pytest.raises(ValidationError):
            TransitionEvent(
                event_id="e1",
                timestamp=ts,
                operation="create",
                actor="a",
                input_ids=(),
                output_ids=("THOUGHT-A",),
            )


class TestTransitionEventReasonDisposition:
    def test_non_prune_with_reason_rejected(self):
        with pytest.raises(ValidationError, match="None for create"):
            _event(operation="create", output_ids=("THOUGHT-A",), reason="r")

    def test_non_prune_with_disposition_rejected(self):
        with pytest.raises(ValidationError, match="None for create"):
            _event(operation="create", output_ids=("THOUGHT-A",), disposition="rejected")

    def test_prune_blank_reason_rejected(self):
        with pytest.raises(ValidationError, match="non-empty reason"):
            _event(
                operation="prune",
                input_ids=("THOUGHT-A",),
                output_ids=("THOUGHT-A",),
                reason="",
                disposition="rejected",
            )

    def test_prune_invalid_disposition_rejected(self):
        with pytest.raises(InvalidDispositionError):
            _event(
                operation="prune",
                input_ids=("THOUGHT-A",),
                output_ids=("THOUGHT-A",),
                reason="r",
                disposition="invalid",
            )


# ===========================================================================
# PopulationSnapshot tests
# ===========================================================================

class TestPopulationSnapshotSorting:
    def test_thoughts_sorted_by_id(self):
        s1 = _state("THOUGHT-B")
        s2 = _state("THOUGHT-A")
        snap = PopulationSnapshot(thoughts=(s1, s2), history=())
        assert snap.thoughts[0].thought_id == "THOUGHT-A"
        assert snap.thoughts[1].thought_id == "THOUGHT-B"


class TestPopulationSnapshotHistoryOrder:
    def test_history_preserves_insertion_order(self):
        s1 = _state("THOUGHT-A")
        s2 = _state("THOUGHT-B")
        e1 = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        e2 = _event(event_id="e2", operation="create", output_ids=("THOUGHT-B",))
        snap = PopulationSnapshot(thoughts=(s1, s2), history=(e1, e2))
        assert snap.history[0].event_id == "e1"
        assert snap.history[1].event_id == "e2"


class TestPopulationSnapshotImmutable:
    def test_tuple_fields_are_frozen(self):
        snap = PopulationSnapshot(thoughts=(), history=())
        with pytest.raises(AttributeError):
            snap.thoughts = ()  # type: ignore[misc]


class TestPopulationSnapshotRoundTrip:
    def test_dict_roundtrip(self):
        s1 = _state("THOUGHT-A")
        e1 = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        snap = PopulationSnapshot(thoughts=(s1,), history=(e1,))
        d = snap.to_dict()
        snap2 = PopulationSnapshot.from_dict(d)
        assert snap2.to_dict() == d

    def test_json_roundtrip_deterministic(self):
        s1 = _state("THOUGHT-A")
        e1 = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        snap = PopulationSnapshot(thoughts=(s1,), history=(e1,))
        j1 = _bytes(snap)
        j2 = _bytes(snap)
        assert j1 == j2
        snap2 = PopulationSnapshot.from_canonical_json(j1)
        assert snap2.to_dict() == snap.to_dict()


@pytest.mark.parametrize(
    "input_,match",
    [
        (123, "expected string"),
        ("{bad json", "invalid JSON"),
        ("[]", "data must be a dict"),
    ],
    ids=["non_string", "malformed_json", "non_object_root"],
)
def test_from_canonical_json_rejects_bad_input(input_, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        PopulationSnapshot.from_canonical_json(input_)


class TestPopulationSnapshotRejects:
    def test_duplicate_thought_id_rejected(self):
        s1 = _state("THOUGHT-A")
        with pytest.raises(DuplicateIdError):
            PopulationSnapshot(thoughts=(s1, s1), history=())

    def test_duplicate_event_id_rejected(self):
        s1 = _state("THOUGHT-A")
        e1 = _event(event_id="e1", operation="create", output_ids=("THOUGHT-A",))
        with pytest.raises(DuplicateEventError):
            PopulationSnapshot(thoughts=(s1,), history=(e1, e1))

    def test_event_unknown_input_ref_rejected(self):
        s1 = _state("THOUGHT-A")
        e1 = _event(
            event_id="e1",
            operation="branch",
            input_ids=("THOUGHT-MISSING",),
            output_ids=("THOUGHT-A",),
        )
        with pytest.raises(UnknownReferenceError):
            PopulationSnapshot(thoughts=(s1,), history=(e1,))

    def test_event_unknown_output_ref_rejected(self):
        s1 = _state("THOUGHT-A")
        e1 = _event(
            event_id="e1",
            operation="create",
            output_ids=("THOUGHT-MISSING",),
        )
        with pytest.raises(UnknownReferenceError):
            PopulationSnapshot(thoughts=(s1,), history=(e1,))


# ===========================================================================
# LineageIndex tests
# ===========================================================================

class TestLineageIndexEmpty:
    def test_empty_index(self):
        idx = LineageIndex.empty()
        assert idx.ids() == ()
        assert idx.to_dict() == {}


class TestLineageIndexFromStates:
    def test_order_independence(self):
        s1 = _state("THOUGHT-B", parents=("THOUGHT-A",))
        s2 = _state("THOUGHT-A")
        idx1 = LineageIndex.from_states([s1, s2])
        idx2 = LineageIndex.from_states([s2, s1])
        assert idx1.ids() == idx2.ids()
        assert idx1.to_dict() == idx2.to_dict()

    def test_canonical_queries(self):
        s1 = _state("THOUGHT-A")
        s2 = _state("THOUGHT-B", parents=("THOUGHT-A",))
        idx = LineageIndex.from_states([s1, s2])
        assert idx.ids() == ("THOUGHT-A", "THOUGHT-B")
        assert idx.parents_of("THOUGHT-A") == ()
        assert idx.parents_of("THOUGHT-B") == ("THOUGHT-A",)
        assert idx.children_of("THOUGHT-A") == ("THOUGHT-B",)
        assert idx.children_of("THOUGHT-B") == ()
        assert idx.contains("THOUGHT-A")
        assert not idx.contains("THOUGHT-Z")

    def test_to_dict(self):
        s1 = _state("THOUGHT-A")
        s2 = _state("THOUGHT-B", parents=("THOUGHT-A",))
        idx = LineageIndex.from_states([s1, s2])
        d = idx.to_dict()
        assert d == {"THOUGHT-A": [], "THOUGHT-B": ["THOUGHT-A"]}


class TestLineageIndexImmutable:
    def test_add_returns_new_instance(self):
        s1 = _state("THOUGHT-A")
        idx = LineageIndex.from_states([s1])
        s2 = _state("THOUGHT-B", parents=("THOUGHT-A",))
        idx2 = idx.add(s2)
        assert idx.ids() == ("THOUGHT-A",)
        assert idx2.ids() == ("THOUGHT-A", "THOUGHT-B")


class TestLineageIndexRejects:
    def test_duplicate_add_rejected(self):
        s1 = _state("THOUGHT-A")
        idx = LineageIndex.from_states([s1])
        with pytest.raises(DuplicateIdError):
            idx.add(s1)

    def test_duplicate_from_states_rejected(self):
        s1 = _state("THOUGHT-A")
        with pytest.raises(DuplicateIdError):
            LineageIndex.from_states([s1, s1])

    def test_unknown_parent_rejected(self):
        s1 = _state("THOUGHT-A", parents=("THOUGHT-MISSING",))
        with pytest.raises(UnknownReferenceError):
            LineageIndex.from_states([s1])

    def test_unknown_parent_add_rejected(self):
        s1 = _state("THOUGHT-A")
        idx = LineageIndex.from_states([s1])
        s2 = _state("THOUGHT-B", parents=("THOUGHT-MISSING",))
        with pytest.raises(UnknownReferenceError):
            idx.add(s2)

    def test_self_reference_rejected(self):
        with pytest.raises(ValidationError, match="own ID"):
            _state("THOUGHT-A", parents=("THOUGHT-A",))

    def test_two_node_cycle_rejected(self):
        s1 = _state("THOUGHT-A", parents=("THOUGHT-B",))
        s2 = _state("THOUGHT-B", parents=("THOUGHT-A",))
        with pytest.raises(CycleDetectedError):
            LineageIndex.from_states([s1, s2])

    def test_unknown_query_rejected(self):
        idx = LineageIndex.empty()
        with pytest.raises(UnknownReferenceError):
            idx.parents_of("THOUGHT-MISSING")
        with pytest.raises(UnknownReferenceError):
            idx.children_of("THOUGHT-MISSING")


# ===========================================================================
# create / branch contract tests
# ===========================================================================

def test_create_success_audit_shape():
    snap = PopulationSnapshot.empty()
    state = _state("THOUGHT-0001")
    new = create(snap, state, **_kwargs(1))
    assert new.contains("THOUGHT-0001")
    assert len(new.history) == 1
    ev = new.history[0]
    assert ev.operation == "create"
    assert ev.input_ids == ()
    assert ev.output_ids == ("THOUGHT-0001",)
    assert ev.event_id == _kwargs(1)["event_id"]
    assert ev.timestamp == _kwargs(1)["timestamp"]
    assert ev.actor == _kwargs(1)["actor"]


def test_create_deterministic_repeat():
    snap = PopulationSnapshot.empty()
    state = _state("THOUGHT-0001")
    a = create(snap, state, **_kwargs(1))
    b = create(snap, state, **_kwargs(1))
    assert _bytes(a) == _bytes(b)


def test_create_root_active_new_requirements():
    snap = PopulationSnapshot.empty()
    with pytest.raises(InvalidTransitionError, match="empty parent_ids"):
        create(snap, _state("THOUGHT-0001", parents=("THOUGHT-0000",)), **_kwargs(1))
    with pytest.raises(InvalidTransitionError, match="active"):
        create(snap, _state("THOUGHT-0001", status="rejected"), **_kwargs(1))


def test_create_duplicate_event_id_rejected():
    snap = PopulationSnapshot.empty()
    state = _state("THOUGHT-0001")
    new = create(snap, state, **_kwargs(1))
    with pytest.raises(DuplicateEventError):
        create(new, _state("THOUGHT-0002"), **_kwargs(1))


def test_create_prior_snapshot_unchanged():
    snap = PopulationSnapshot.empty()
    before = _bytes(snap)
    create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    assert _bytes(snap) == before


def test_create_immutability():
    snap = PopulationSnapshot.empty()
    snap_before = _bytes(snap)
    state = _state("THOUGHT-0001")
    state_before = state.to_dict()
    create(snap, state, **_kwargs(1))
    assert _bytes(snap) == snap_before
    assert state.to_dict() == state_before


def test_branch_success_parent_unchanged():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    before_parent = _bytes(snap)
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    new = branch(snap, child, parent_id="THOUGHT-0001", **_kwargs(2))
    assert new.contains("THOUGHT-0002")
    assert len(new.history) == 2
    assert _bytes(snap) == before_parent


def test_branch_deterministic_event_shape():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    a = branch(snap, child, parent_id="THOUGHT-0001", **_kwargs(2))
    b = branch(snap, child, parent_id="THOUGHT-0001", **_kwargs(2))
    assert _bytes(a) == _bytes(b)
    ev = a.history[-1]
    assert ev.operation == "branch"
    assert ev.input_ids == ("THOUGHT-0001",)
    assert ev.output_ids == ("THOUGHT-0002",)


def test_branch_unknown_parent_rejected():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    with pytest.raises(UnknownReferenceError):
        branch(snap, child, parent_id="THOUGHT-MISSING", **_kwargs(2))


def test_branch_child_id_collision_rejected():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    snap = create(snap, _state("THOUGHT-0002"), **_kwargs(2))
    child2 = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    with pytest.raises(DuplicateIdError):
        branch(snap, child2, parent_id="THOUGHT-0001", **_kwargs(3))


def test_branch_self_parent_rejected():
    with pytest.raises(ValidationError, match="own ID"):
        _state("THOUGHT-X", parents=("THOUGHT-X",))


def test_branch_mismatched_parent_rejected():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    snap = create(snap, _state("THOUGHT-0003"), **_kwargs(2))
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    with pytest.raises(InvalidTransitionError, match="parent_ids"):
        branch(snap, child, parent_id="THOUGHT-0003", **_kwargs(3))


def test_branch_non_active_child_rejected():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",), status="rejected")
    with pytest.raises(InvalidTransitionError, match="active"):
        branch(snap, child, parent_id="THOUGHT-0001", **_kwargs(2))


def test_branch_terminal_parent_rejected():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    snap = prune(
        snap,
        "THOUGHT-0001",
        reason="bad",
        disposition="rejected",
        **_kwargs(2),
    )
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    with pytest.raises(TerminalStateError):
        branch(snap, child, parent_id="THOUGHT-0001", **_kwargs(3))


def test_branch_duplicate_event_rejected():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
    snap = branch(snap, child, parent_id="THOUGHT-0001", **_kwargs(2))
    child2 = _state("THOUGHT-0003", parents=("THOUGHT-0001",))
    with pytest.raises(DuplicateEventError):
        branch(snap, child2, parent_id="THOUGHT-0001", **_kwargs(2))


def test_create_failure_atomicity():
    snap = PopulationSnapshot.empty()
    before = _bytes(snap)
    with pytest.raises(InvalidTransitionError):
        create(snap, _state("THOUGHT-0001", parents=("THOUGHT-0000",)), **_kwargs(1))
    assert _bytes(snap) == before


def test_branch_failure_atomicity():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-0001"), **_kwargs(1))
    before = _bytes(snap)
    with pytest.raises(UnknownReferenceError):
        child = _state("THOUGHT-0002", parents=("THOUGHT-0001",))
        branch(snap, child, parent_id="THOUGHT-MISSING", **_kwargs(2))
    assert _bytes(snap) == before


# ===========================================================================
# merge contract tests
# ===========================================================================

def _two_active_roots():
    snap = PopulationSnapshot.empty()
    snap = create(snap, _state("THOUGHT-A"), **_kwargs(1))
    snap = create(snap, _state("THOUGHT-B"), **_kwargs(2))
    return snap


def test_merge_success_sources_merged_result_active():
    snap = _two_active_roots()
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-B"), claim="mc", confidence=0.7)
    new = merge(snap, merged, source_ids=("THOUGHT-A", "THOUGHT-B"), **_kwargs(3))
    assert new.get("THOUGHT-A").status.state == "merged"
    assert new.get("THOUGHT-B").status.state == "merged"
    assert new.get("THOUGHT-M").status.state == "active"
    assert new.get("THOUGHT-M").hypothesis.claim == "mc"
    assert new.get("THOUGHT-M").metrics.confidence == 0.7
    ev = new.history[-1]
    assert ev.operation == "merge"
    assert ev.input_ids == ("THOUGHT-A", "THOUGHT-B")
    assert ev.output_ids == ("THOUGHT-M",)


def test_merge_list_and_generator_source_ids_byte_identical():
    snap = _two_active_roots()
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-B"))
    a = merge(snap, merged, source_ids=["THOUGHT-A", "THOUGHT-B"], **_kwargs(3))
    b = merge(snap, merged, source_ids=iter(["THOUGHT-B", "THOUGHT-A"]), **_kwargs(3))
    assert _bytes(a) == _bytes(b)


@pytest.mark.parametrize(
    "src,exc",
    [
        (("THOUGHT-A", "THOUGHT-A"), MergeSourceError),
        (("THOUGHT-A",), MergeSourceError),
        ("THOUGHT-A", MergeSourceError),
        (None, MergeSourceError),
    ],
    ids=["duplicate", "lt2", "string", "non-iterable"],
)
def test_merge_bad_source_ids(src, exc):
    snap = _two_active_roots()
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-B"))
    with pytest.raises(exc):
        merge(snap, merged, source_ids=src, **_kwargs(3))


def test_merge_unknown_source_rejected():
    snap = _two_active_roots()
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-Z"))
    with pytest.raises(UnknownReferenceError):
        merge(snap, merged, source_ids=("THOUGHT-A", "THOUGHT-Z"), **_kwargs(3))


def test_merge_terminal_source_rejected():
    snap = _two_active_roots()
    snap = prune(snap, "THOUGHT-A", reason="r", disposition="rejected", **_kwargs(3))
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-B"))
    with pytest.raises(TerminalStateError):
        merge(snap, merged, source_ids=("THOUGHT-A", "THOUGHT-B"), **_kwargs(4))


def test_merge_result_id_collision_rejected():
    snap = _two_active_roots()
    merged = _state("THOUGHT-A", parents=())
    with pytest.raises(DuplicateIdError):
        merge(snap, merged, source_ids=("THOUGHT-A", "THOUGHT-B"), **_kwargs(3))


def test_merge_inactive_result_rejected():
    snap = _two_active_roots()
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-B"), status="rejected")
    with pytest.raises(InvalidTransitionError, match="active"):
        merge(snap, merged, source_ids=("THOUGHT-A", "THOUGHT-B"), **_kwargs(3))


def test_merge_result_parent_mismatch_rejected():
    snap = _two_active_roots()
    merged = _state("THOUGHT-M", parents=("THOUGHT-B",))
    with pytest.raises(MergeSourceError, match="parent_ids"):
        merge(snap, merged, source_ids=("THOUGHT-A", "THOUGHT-B"), **_kwargs(3))


def test_merge_failure_prior_bytes_unchanged():
    snap = _two_active_roots()
    before = _bytes(snap)
    merged = _state("THOUGHT-M", parents=("THOUGHT-A", "THOUGHT-B"))
    with pytest.raises(MergeSourceError):
        merge(snap, merged, source_ids=("THOUGHT-A",), **_kwargs(3))
    assert _bytes(snap) == before


# ===========================================================================
# prune contract tests
# ===========================================================================

def test_prune_success_rejected_and_dormant():
    snap = _two_active_roots()
    r = prune(snap, "THOUGHT-A", reason="bad", disposition="rejected", **_kwargs(3))
    assert r.get("THOUGHT-A").status.state == "rejected"
    assert r.get("THOUGHT-B").status.state == "active"
    d = prune(snap, "THOUGHT-B", reason="sleepy", disposition="dormant", **_kwargs(4))
    assert d.get("THOUGHT-B").status.state == "dormant"
    assert d.get("THOUGHT-A").status.state == "active"


def test_prune_audit_reason_disposition_input_output():
    snap = _two_active_roots()
    new = prune(snap, "THOUGHT-A", reason="r1", disposition="rejected", **_kwargs(3))
    ev = new.history[-1]
    assert ev.operation == "prune"
    assert ev.reason == "r1"
    assert ev.disposition == "rejected"
    assert ev.input_ids == ("THOUGHT-A",)
    assert ev.output_ids == ("THOUGHT-A",)


def test_prune_unknown_target_rejected():
    snap = _two_active_roots()
    with pytest.raises(UnknownReferenceError):
        prune(snap, "THOUGHT-Z", reason="r", disposition="rejected", **_kwargs(3))


def test_prune_blank_reason_rejected():
    snap = _two_active_roots()
    with pytest.raises(InvalidTransitionError, match="reason"):
        prune(snap, "THOUGHT-A", reason="", disposition="rejected", **_kwargs(3))


def test_prune_non_string_reason_rejected():
    snap = _two_active_roots()
    with pytest.raises(InvalidTransitionError, match="reason"):
        prune(snap, "THOUGHT-A", reason=123, disposition="rejected", **_kwargs(3))


def test_prune_invalid_disposition_rejected():
    snap = _two_active_roots()
    with pytest.raises(InvalidDispositionError):
        prune(snap, "THOUGHT-A", reason="r", disposition="invalid", **_kwargs(3))


def test_prune_repeated_terminal_rejected():
    snap = _two_active_roots()
    snap = prune(snap, "THOUGHT-A", reason="r", disposition="rejected", **_kwargs(3))
    with pytest.raises(TerminalStateError):
        prune(snap, "THOUGHT-A", reason="r2", disposition="dormant", **_kwargs(4))


def test_prune_duplicate_event_rejected():
    snap = _two_active_roots()
    snap = prune(snap, "THOUGHT-A", reason="r", disposition="rejected", **_kwargs(3))
    with pytest.raises(DuplicateEventError):
        prune(snap, "THOUGHT-B", reason="r", disposition="rejected", **_kwargs(3))


def test_prune_failure_prior_bytes_unchanged():
    snap = _two_active_roots()
    before = _bytes(snap)
    with pytest.raises(UnknownReferenceError):
        prune(snap, "THOUGHT-Z", reason="r", disposition="rejected", **_kwargs(3))
    assert _bytes(snap) == before
