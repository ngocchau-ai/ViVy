"""Unit tests for EvidenceImpact, AssimilationPlan, and snapshot validation.

Covers the public API from nps_core.evidence_assimilator and
nps_core.hypothesis_population without importing helpers from other test files.
"""

from __future__ import annotations

import json

import pytest

from nps_core.evidence_assimilator import (
    AssimilationPlan,
    EvidenceImpact,
    EvidencePacket,
    IMPACT_CLASSIFICATIONS,
    ImpactValidationError,
    PlanValidationError,
    Reproducibility,
)
from nps_core.hypothesis_population import (
    PopulationSnapshot,
    ThoughtState,
    TransitionEvent,
)


# ---------------------------------------------------------------------------
# Local ThoughtState V1 factory
# ---------------------------------------------------------------------------

def _thought(
    thought_id: str,
    *,
    status: str = "active",
    supporting: tuple[str, ...] = (),
    opposing: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> ThoughtState:
    """Return a minimal valid ThoughtState via from_dict."""
    return ThoughtState.from_dict({
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2025-01-01T00:00:00Z",
        "interpretation": {
            "summary": "s",
            "scope": "sc",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": "c",
            "predicted_observations": [],
            "falsification_conditions": [],
        },
        "assumptions": [],
        "evidence": {
            "supporting": list(supporting),
            "opposing": list(opposing),
            "unresolved": list(unresolved),
        },
        "metrics": {
            "confidence": 0.5,
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


def _packet(
    evidence_id: str = "EV-001",
    affected: tuple[str, ...] = ("THOUGHT-A",),
) -> EvidencePacket:
    """Return a minimal valid EvidencePacket."""
    return EvidencePacket(
        evidence_id=evidence_id,
        task_id="TASK-001",
        executor_id="exec-1",
        claim="the claim",
        result="the result",
        method="experiment",
        artifacts=("art-1",),
        confidence=0.8,
        limitations=("lim-1",),
        failure_modes=("fm-1",),
        reproducibility=Reproducibility(
            command="run.sh",
            environment="test",
            seed=42,
        ),
        affected_hypotheses=affected,
        provenance=("prov-1",),
        content_hash="abc123",
    )


def _snapshot(*thoughts: ThoughtState) -> PopulationSnapshot:
    """Build a PopulationSnapshot with one create event per thought."""
    events = []
    for i, t in enumerate(thoughts):
        events.append(
            _event(f"evt-{i:04d}", "create", output_ids=(t.thought_id,))
        )
    return PopulationSnapshot(thoughts=thoughts, history=tuple(events))


def _event(
    event_id: str,
    operation: str,
    *,
    input_ids: tuple[str, ...] = (),
    output_ids: tuple[str, ...] = (),
) -> TransitionEvent:
    return TransitionEvent(
        event_id=event_id,
        timestamp="2025-01-01T00:00:00Z",
        operation=operation,
        actor="tester",
        input_ids=input_ids,
        output_ids=output_ids,
    )


def _kwargs(n: int) -> dict:
    return {
        "event_id": f"evt-{n:04d}",
        "timestamp": f"2025-01-{n + 1:02d}T00:00:00Z",
        "actor": f"actor-{n}",
    }


# ===========================================================================
# EvidenceImpact tests
# ===========================================================================

class TestEvidenceImpactFrozen:
    def test_fields_are_frozen(self):
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        with pytest.raises(AttributeError):
            imp.target_thought_id = "THOUGHT-B"  # type: ignore[misc]


class TestEvidenceImpactValidation:
    def test_valid_classifications(self):
        for cls in IMPACT_CLASSIFICATIONS:
            imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification=cls)
            assert imp.classification == cls

    def test_invalid_classification_rejected(self):
        with pytest.raises(ImpactValidationError, match="classification"):
            EvidenceImpact(target_thought_id="THOUGHT-A", classification="maybe")

    def test_invalid_thought_id_pattern_rejected(self):
        with pytest.raises(ImpactValidationError, match="THOUGHT-"):
            EvidenceImpact(target_thought_id="INVALID", classification="supporting")

    def test_non_string_classification_rejected(self):
        with pytest.raises(ImpactValidationError, match="str"):
            EvidenceImpact(target_thought_id="THOUGHT-A", classification=1)  # type: ignore[arg-type]

    def test_non_string_target_rejected(self):
        with pytest.raises(ImpactValidationError, match="str"):
            EvidenceImpact(target_thought_id=123, classification="supporting")  # type: ignore[arg-type]


class TestEvidenceImpactIdPattern:
    @pytest.mark.parametrize(
        "tid",
        ["THOUGHT-A", "THOUGHT-0001", "THOUGHT-abc.def_123"],
    )
    def test_valid_thought_id_patterns(self, tid: str):
        imp = EvidenceImpact(target_thought_id=tid, classification="supporting")
        assert imp.target_thought_id == tid

    @pytest.mark.parametrize(
        "tid",
        ["THOUGHT-", "thought-A", "THOUGHT A", ""],
    )
    def test_invalid_thought_id_patterns(self, tid: str):
        with pytest.raises(ImpactValidationError):
            EvidenceImpact(target_thought_id=tid, classification="supporting")


class TestEvidenceImpactDictRoundTrip:
    def test_to_dict_from_dict(self):
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        d = imp.to_dict()
        assert d == {"target_thought_id": "THOUGHT-A", "classification": "supporting"}
        imp2 = EvidenceImpact.from_dict(d)
        assert imp2 == imp

    def test_from_dict_strict_keys(self):
        d = {"target_thought_id": "THOUGHT-A", "classification": "supporting"}
        imp = EvidenceImpact.from_dict(d)
        assert imp.target_thought_id == "THOUGHT-A"

    def test_from_dict_missing_key_rejected(self):
        d = {"target_thought_id": "THOUGHT-A"}
        with pytest.raises(ImpactValidationError, match="missing"):
            EvidenceImpact.from_dict(d)

    def test_from_dict_extra_key_rejected(self):
        d = {"target_thought_id": "THOUGHT-A", "classification": "supporting", "extra": 1}
        with pytest.raises(ImpactValidationError, match="unexpected"):
            EvidenceImpact.from_dict(d)

    def test_from_dict_non_dict_rejected(self):
        with pytest.raises(ImpactValidationError, match="dict"):
            EvidenceImpact.from_dict("not a dict")  # type: ignore[arg-type]


# ===========================================================================
# AssimilationPlan structural tests
# ===========================================================================

class TestAssimilationPlanDirectConstruction:
    def test_valid_construction(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        assert plan.packet is pkt
        assert len(plan.impacts) == 1

    def test_impacts_must_be_tuple(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        with pytest.raises(PlanValidationError, match="tuple"):
            AssimilationPlan(packet=pkt, impacts=[imp])  # type: ignore[arg-type]

    def test_impacts_must_be_non_empty(self):
        pkt = _packet(affected=("THOUGHT-A",))
        with pytest.raises(PlanValidationError, match="non-empty"):
            AssimilationPlan(packet=pkt, impacts=())

    def test_impacts_must_be_evidence_impact_instances(self):
        pkt = _packet(affected=("THOUGHT-A",))
        with pytest.raises(PlanValidationError, match="EvidenceImpact"):
            AssimilationPlan(packet=pkt, impacts=({"target_thought_id": "THOUGHT-A", "classification": "supporting"},))  # type: ignore[arg-type]

    def test_duplicate_target_rejected(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp1 = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        imp2 = EvidenceImpact(target_thought_id="THOUGHT-A", classification="opposing")
        with pytest.raises(PlanValidationError, match="duplicate"):
            AssimilationPlan(packet=pkt, impacts=(imp1, imp2))

    def test_target_set_mismatch_missing_in_impacts(self):
        pkt = _packet(affected=("THOUGHT-A", "THOUGHT-B"))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        with pytest.raises(PlanValidationError, match="packet but not in impacts"):
            AssimilationPlan(packet=pkt, impacts=(imp,))

    def test_target_set_mismatch_extra_in_impacts(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp_a = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        imp_b = EvidenceImpact(target_thought_id="THOUGHT-B", classification="supporting")
        with pytest.raises(PlanValidationError, match="impacts but not in packet"):
            AssimilationPlan(packet=pkt, impacts=(imp_a, imp_b))

    def test_packet_must_be_evidence_packet(self):
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        with pytest.raises(PlanValidationError, match="EvidencePacket"):
            AssimilationPlan(packet="not a packet", impacts=(imp,))  # type: ignore[arg-type]


class TestAssimilationPlanNormalization:
    def test_impacts_sorted_by_target_id(self):
        pkt = _packet(affected=("THOUGHT-B", "THOUGHT-A"))
        imp_b = EvidenceImpact(target_thought_id="THOUGHT-B", classification="supporting")
        imp_a = EvidenceImpact(target_thought_id="THOUGHT-A", classification="opposing")
        plan = AssimilationPlan(packet=pkt, impacts=(imp_b, imp_a))
        assert plan.impacts[0].target_thought_id == "THOUGHT-A"
        assert plan.impacts[1].target_thought_id == "THOUGHT-B"

    def test_structural_set_equality_with_packet_targets(self):
        pkt = _packet(affected=("THOUGHT-X", "THOUGHT-Y", "THOUGHT-Z"))
        impacts = tuple(
            EvidenceImpact(target_thought_id=tid, classification="supporting")
            for tid in ("THOUGHT-Z", "THOUGHT-X", "THOUGHT-Y")
        )
        plan = AssimilationPlan(packet=pkt, impacts=impacts)
        plan_targets = {i.target_thought_id for i in plan.impacts}
        assert plan_targets == set(pkt.affected_hypotheses)


# ===========================================================================
# AssimilationPlan serialization tests
# ===========================================================================

class TestAssimilationPlanSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        d = plan.to_dict()
        assert "packet" in d
        assert "impacts" in d
        plan2 = AssimilationPlan.from_dict(d)
        assert plan2.to_dict() == d

    def test_canonical_json_roundtrip(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        j1 = plan.to_canonical_json()
        j2 = plan.to_canonical_json()
        assert j1 == j2
        plan2 = AssimilationPlan.from_canonical_json(j1)
        assert plan2.to_dict() == plan.to_dict()

    def test_canonical_json_is_sorted_compact(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        j = plan.to_canonical_json()
        parsed = json.loads(j)
        assert json.dumps(parsed, sort_keys=True, separators=(",", ":")) == j

    def test_from_dict_strict_keys(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        d = plan.to_dict()
        plan2 = AssimilationPlan.from_dict(d)
        assert plan2.to_dict() == d

    def test_from_dict_missing_key_rejected(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        d = plan.to_dict()
        del d["impacts"]
        with pytest.raises(PlanValidationError, match="missing"):
            AssimilationPlan.from_dict(d)

    def test_from_dict_extra_key_rejected(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        d = plan.to_dict()
        d["extra"] = 1
        with pytest.raises(PlanValidationError, match="unexpected"):
            AssimilationPlan.from_dict(d)

    def test_from_dict_impacts_must_be_list(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        d = plan.to_dict()
        d["impacts"] = ("not", "a", "list")
        with pytest.raises(PlanValidationError, match="list"):
            AssimilationPlan.from_dict(d)


class TestAssimilationPlanCanonicalJsonErrors:
    def test_malformed_json_rejected(self):
        with pytest.raises(PlanValidationError, match="invalid JSON"):
            AssimilationPlan.from_canonical_json("{bad json")

    def test_non_string_rejected(self):
        with pytest.raises(PlanValidationError, match="str"):
            AssimilationPlan.from_canonical_json(123)  # type: ignore[arg-type]

    def test_non_object_root_rejected(self):
        with pytest.raises(PlanValidationError, match="object"):
            AssimilationPlan.from_canonical_json("[]")


# ===========================================================================
# create / validate_for tests
# ===========================================================================

class TestAssimilationPlanCreate:
    def test_create_succeeds_on_active_targets(self):
        snap = _snapshot(_thought("THOUGHT-A"))
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan.create(pkt, (imp,), snap)
        assert plan.packet is pkt

    def test_create_succeeds_multiple_targets(self):
        snap = _snapshot(_thought("THOUGHT-A"), _thought("THOUGHT-B"))
        pkt = _packet(affected=("THOUGHT-A", "THOUGHT-B"))
        impacts = (
            EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting"),
            EvidenceImpact(target_thought_id="THOUGHT-B", classification="opposing"),
        )
        plan = AssimilationPlan.create(pkt, impacts, snap)
        assert len(plan.impacts) == 2


class TestAssimilationPlanValidateForMissingTarget:
    def test_missing_target_raises(self):
        snap = _snapshot(_thought("THOUGHT-A"))
        pkt = _packet(affected=("THOUGHT-A", "THOUGHT-B"))
        impacts = (
            EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting"),
            EvidenceImpact(target_thought_id="THOUGHT-B", classification="supporting"),
        )
        plan = AssimilationPlan(packet=pkt, impacts=impacts)
        with pytest.raises(PlanValidationError, match="not found") as exc_info:
            plan.validate_for(snap)
        assert exc_info.value.thought_id == "THOUGHT-B"
        assert exc_info.value.evidence_id == "EV-001"


class TestAssimilationPlanValidateForTerminalTarget:
    @pytest.mark.parametrize("terminal", ["rejected", "merged", "dormant"])
    def test_terminal_target_raises(self, terminal: str):
        snap = _snapshot(_thought("THOUGHT-A", status=terminal))
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        with pytest.raises(PlanValidationError, match="terminal") as exc_info:
            plan.validate_for(snap)
        assert exc_info.value.thought_id == "THOUGHT-A"


class TestAssimilationPlanValidateForEvidenceAlreadyPresent:
    @pytest.mark.parametrize("bucket", ["supporting", "opposing", "unresolved"])
    def test_evidence_id_in_bucket_raises(self, bucket: str):
        kwargs: dict = {bucket: ("EV-001",)}
        snap = _snapshot(_thought("THOUGHT-A", **kwargs))
        pkt = _packet(evidence_id="EV-001", affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        with pytest.raises(PlanValidationError, match="already present") as exc_info:
            plan.validate_for(snap)
        assert exc_info.value.thought_id == "THOUGHT-A"
        assert exc_info.value.evidence_id == "EV-001"


# ===========================================================================
# Stale-plan revalidation tests
# ===========================================================================

class TestStalePlanRevalidation:
    def test_deserialized_plan_fails_on_invalid_snapshot(self):
        """A plan deserialized from JSON must still fail validate_for on a
        snapshot where the target is now terminal."""
        snap_active = _snapshot(_thought("THOUGHT-A"))
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan.create(pkt, (imp,), snap_active)

        # Serialize and deserialize
        j = plan.to_canonical_json()
        plan2 = AssimilationPlan.from_canonical_json(j)

        # Now the snapshot has THOUGHT-A pruned
        snap_terminal = _snapshot(_thought("THOUGHT-A", status="rejected"))
        with pytest.raises(PlanValidationError, match="terminal"):
            plan2.validate_for(snap_terminal)

    def test_deserialized_plan_fails_when_evidence_added(self):
        """A deserialized plan must fail if the evidence ID was already added
        to the snapshot between serialization and validation."""
        snap_clean = _snapshot(_thought("THOUGHT-A"))
        pkt = _packet(evidence_id="EV-001", affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan.create(pkt, (imp,), snap_clean)

        j = plan.to_canonical_json()
        plan2 = AssimilationPlan.from_canonical_json(j)

        # Evidence now present in snapshot
        snap_with_ev = _snapshot(_thought("THOUGHT-A", supporting=("EV-001",)))
        with pytest.raises(PlanValidationError, match="already present"):
            plan2.validate_for(snap_with_ev)


# ===========================================================================
# Failure immutability tests
# ===========================================================================

class TestFailureImmutability:
    def test_validate_for_failure_leaves_snapshot_unchanged(self):
        snap = _snapshot(_thought("THOUGHT-A"))
        before = snap.to_canonical_json()
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))

        # Make target terminal
        snap_term = _snapshot(_thought("THOUGHT-A", status="rejected"))
        snap_term_before = snap_term.to_canonical_json()

        with pytest.raises(PlanValidationError):
            plan.validate_for(snap_term)
        assert snap_term.to_canonical_json() == snap_term_before
        assert before == snap.to_canonical_json()

    def test_create_failure_leaves_snapshot_unchanged(self):
        snap = _snapshot(_thought("THOUGHT-A"))
        before = snap.to_canonical_json()
        pkt = _packet(affected=("THOUGHT-B",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-B", classification="supporting")
        with pytest.raises(PlanValidationError):
            AssimilationPlan.create(pkt, (imp,), snap)
        assert snap.to_canonical_json() == before


# ===========================================================================
# Error metadata stability tests
# ===========================================================================

class TestErrorMetadata:
    def test_plan_validation_error_domain_class(self):
        snap = _snapshot(_thought("THOUGHT-A"))
        pkt = _packet(affected=("THOUGHT-B",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-B", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        with pytest.raises(PlanValidationError) as exc_info:
            plan.validate_for(snap)
        assert isinstance(exc_info.value, PlanValidationError)
        assert exc_info.value.thought_id == "THOUGHT-B"
        assert exc_info.value.evidence_id == "EV-001"

    def test_impact_validation_error_domain_class(self):
        with pytest.raises(ImpactValidationError) as exc_info:
            EvidenceImpact(target_thought_id="THOUGHT-A", classification="bad")
        assert isinstance(exc_info.value, ImpactValidationError)
        assert exc_info.value.path == "classification"

    def test_plan_error_carries_thought_id_on_duplicate(self):
        pkt = _packet(affected=("THOUGHT-A",))
        imp1 = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        imp2 = EvidenceImpact(target_thought_id="THOUGHT-A", classification="opposing")
        with pytest.raises(PlanValidationError) as exc_info:
            AssimilationPlan(packet=pkt, impacts=(imp1, imp2))
        assert exc_info.value.thought_id == "THOUGHT-A"

    def test_terminal_error_carries_state_in_message(self):
        snap = _snapshot(_thought("THOUGHT-A", status="rejected"))
        pkt = _packet(affected=("THOUGHT-A",))
        imp = EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting")
        plan = AssimilationPlan(packet=pkt, impacts=(imp,))
        with pytest.raises(PlanValidationError, match="rejected"):
            plan.validate_for(snap)


# ===========================================================================
# IMPACT_CLASSIFICATIONS constant
# ===========================================================================

class TestImpactClassificationsConstant:
    def test_exact_classifications(self):
        assert IMPACT_CLASSIFICATIONS == ("opposing", "supporting", "unresolved")

    def test_is_tuple(self):
        assert isinstance(IMPACT_CLASSIFICATIONS, tuple)
        assert len(IMPACT_CLASSIFICATIONS) == 3
