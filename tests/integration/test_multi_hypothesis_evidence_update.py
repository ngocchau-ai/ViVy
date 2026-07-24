"""End-to-end deterministic multi-hypothesis evidence update integration test."""

from __future__ import annotations

import hashlib
import json

from nps_core.evidence_assimilator import (
    AssimilationPlan,
    EvidenceImpact,
    EvidencePacket,
    Reproducibility,
)
from nps_core.hypothesis_population import (
    PopulationSnapshot,
    ThoughtState,
    create,
)
from nps_core.state_update import EvidenceUpdateRecord, apply_evidence


# ---------------------------------------------------------------------------
# Local ThoughtState V1 factory (no imports from other tests)
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
# Canonical JSON / digest helpers
# ---------------------------------------------------------------------------

def _canonical_bytes(obj: object) -> bytes:
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snap_digest(snap: PopulationSnapshot) -> str:
    return _sha256(_canonical_bytes(snap.to_dict()))


# ---------------------------------------------------------------------------
# Build a deterministic snapshot with three active roots and history
# ---------------------------------------------------------------------------

def _build_snapshot() -> PopulationSnapshot:
    snap = PopulationSnapshot.empty()
    snap = create(
        snap,
        _state("THOUGHT-A", claim="alpha", confidence=0.4),
        event_id="EVT-100",
        timestamp="2025-06-01T00:00:00Z",
        actor="tester",
    )
    snap = create(
        snap,
        _state("THOUGHT-B", claim="beta", confidence=0.6),
        event_id="EVT-101",
        timestamp="2025-06-01T00:00:01Z",
        actor="tester",
    )
    snap = create(
        snap,
        _state("THOUGHT-C", claim="gamma", confidence=0.7),
        event_id="EVT-102",
        timestamp="2025-06-01T00:00:02Z",
        actor="tester",
    )
    return snap


# ---------------------------------------------------------------------------
# Build a packet targeting two roots
# ---------------------------------------------------------------------------

def _build_packet() -> EvidencePacket:
    return EvidencePacket(
        evidence_id="EV-2025.06.01-test",
        task_id="TASK-003",
        executor_id="executor-1",
        claim="evidence claim",
        result="evidence result",
        method="experiment",
        artifacts=("art-1",),
        confidence=0.8,
        limitations=("limit-1",),
        failure_modes=("fm-1",),
        reproducibility=Reproducibility(
            command="run-test", environment="ci", seed=42
        ),
        affected_hypotheses=("THOUGHT-A", "THOUGHT-B"),
        provenance=("prov-1",),
        content_hash="sha256-abcdef0123456789",
    )


# ---------------------------------------------------------------------------
# Build plan with different classifications per root
# ---------------------------------------------------------------------------

def _build_plan(packet: EvidencePacket, snap: PopulationSnapshot) -> AssimilationPlan:
    return AssimilationPlan.create(
        packet=packet,
        impacts=(
            EvidenceImpact(target_thought_id="THOUGHT-A", classification="supporting"),
            EvidenceImpact(target_thought_id="THOUGHT-B", classification="opposing"),
        ),
        snapshot=snap,
    )


# ---------------------------------------------------------------------------
# Build replacements: distinct confidence/status changes, correct bucket append
# ---------------------------------------------------------------------------

def _build_replacements(
    snap: PopulationSnapshot, evidence_id: str
) -> dict[str, ThoughtState]:
    """Return complete replacement ThoughtStates for A and B."""
    replacements: dict[str, ThoughtState] = {}
    for tid, new_conf, new_state in [
        ("THOUGHT-A", 0.55, "testing"),
        ("THOUGHT-B", 0.45, "partially_verified"),
    ]:
        prior = snap.get(tid)
        # Determine which bucket gets the evidence_id
        if tid == "THOUGHT-A":
            bucket = "supporting"
        else:
            bucket = "opposing"

        new_evidence = {
            "supporting": list(prior.evidence.supporting),
            "opposing": list(prior.evidence.opposing),
            "unresolved": list(prior.evidence.unresolved),
        }
        new_evidence[bucket].append(evidence_id)

        d = {
            "thought_id": prior.thought_id,
            "parent_ids": list(prior.parent_ids),
            "created_at": prior.created_at,
            "interpretation": {
                "summary": prior.interpretation.summary,
                "scope": prior.interpretation.scope,
                "excluded_scope": list(prior.interpretation.excluded_scope),
            },
            "hypothesis": {
                "claim": prior.hypothesis.claim,
                "predicted_observations": list(prior.hypothesis.predicted_observations),
                "falsification_conditions": list(prior.hypothesis.falsification_conditions),
            },
            "assumptions": [
                {"description": a.description, "criticality": a.criticality}
                for a in prior.assumptions
            ],
            "evidence": new_evidence,
            "metrics": {
                "confidence": new_conf,
                "novelty": prior.metrics.novelty,
                "diversity": prior.metrics.diversity,
                "expected_value": prior.metrics.expected_value,
                "information_need": prior.metrics.information_need,
                "risk_if_wrong": prior.metrics.risk_if_wrong,
                "execution_cost": prior.metrics.execution_cost,
            },
            "verification_plan": {
                "questions": list(prior.verification_plan.questions),
                "required_experiments": list(prior.verification_plan.required_experiments),
                "acceptable_evidence": list(prior.verification_plan.acceptable_evidence),
                "rejection_threshold": prior.verification_plan.rejection_threshold,
            },
            "executor_profile": {
                "skills": list(prior.executor_profile.skills),
                "tool_requirements": list(prior.executor_profile.tool_requirements),
                "preferred_model_class": prior.executor_profile.preferred_model_class,
                "independence_requirements": list(prior.executor_profile.independence_requirements),
            },
            "graph": {
                "dependencies": list(prior.graph.dependencies),
                "contradictions": list(prior.graph.contradictions),
                "overlaps": list(prior.graph.overlaps),
            },
            "status": {
                "state": new_state,
                "allowed_values": [
                    "active", "queued", "testing", "partially_verified",
                    "verified", "rejected", "merged", "dormant",
                ],
            },
        }
        replacements[tid] = ThoughtState.from_dict(d)
    return replacements


# ---------------------------------------------------------------------------
# Single replay: returns (result_snapshot, record, prior_snapshot, packet, plan)
# ---------------------------------------------------------------------------

def _replay() -> tuple[
    PopulationSnapshot,
    EvidenceUpdateRecord,
    PopulationSnapshot,
    EvidencePacket,
    AssimilationPlan,
]:
    snap = _build_snapshot()
    packet = _build_packet()
    plan = _build_plan(packet, snap)
    replacements = _build_replacements(snap, packet.evidence_id)

    result, record = apply_evidence(
        snap,
        plan,
        replacements,
        record_id="REC-001",
        timestamp="2025-06-01T01:00:00Z",
        actor="tester",
    )
    return result, record, snap, packet, plan


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_replay_byte_identical() -> None:
    """Two independent replays produce byte-identical packet, plan, record, and result."""
    r1_snap, r1_rec, r1_prior, r1_pkt, r1_plan = _replay()
    r2_snap, r2_rec, r2_prior, r2_pkt, r2_plan = _replay()

    assert r1_pkt.to_canonical_json() == r2_pkt.to_canonical_json()
    assert r1_plan.to_canonical_json() == r2_plan.to_canonical_json()
    assert r1_rec.to_canonical_json() == r2_rec.to_canonical_json()
    assert r1_snap.to_canonical_json() == r2_snap.to_canonical_json()


def test_prior_snapshot_unchanged() -> None:
    """Prior snapshot is byte-identical across replays and after update."""
    _, _, prior1, _, _ = _replay()
    _, _, prior2, _, _ = _replay()
    assert prior1.to_canonical_json() == prior2.to_canonical_json()


def test_record_target_ids_sorted() -> None:
    """Record sorted_target_ids is lexicographically sorted."""
    _, rec, _, _, _ = _replay()
    assert list(rec.sorted_target_ids) == sorted(rec.sorted_target_ids)
    assert rec.sorted_target_ids == ("THOUGHT-A", "THOUGHT-B")


def test_evidence_content_hash_retained() -> None:
    """Record content_hash matches packet content_hash."""
    _, rec, _, pkt, _ = _replay()
    assert rec.content_hash == pkt.content_hash


def test_prior_result_digests_match_explicit_sha256() -> None:
    """Prior/result digests equal explicit SHA-256 of canonical snapshot bytes."""
    result, rec, prior, _, _ = _replay()
    assert rec.prior_state_digest == _sha256(_canonical_bytes(prior.to_dict()))
    assert rec.result_state_digest == _sha256(_canonical_bytes(result.to_dict()))


def test_third_thought_and_history_unchanged() -> None:
    """THOUGHT-C and snapshot history are preserved exactly."""
    result, _, prior, _, _ = _replay()
    assert result.get("THOUGHT-C").to_dict() == prior.get("THOUGHT-C").to_dict()
    assert result.history == prior.history


def test_evidence_bucket_append() -> None:
    """Selected buckets have evidence_id appended; others unchanged."""
    result, _, prior, pkt, _ = _replay()
    eid = pkt.evidence_id

    # THOUGHT-A: supporting bucket
    a_prior = prior.get("THOUGHT-A")
    a_result = result.get("THOUGHT-A")
    assert a_result.evidence.supporting == (*a_prior.evidence.supporting, eid)
    assert a_result.evidence.opposing == a_prior.evidence.opposing
    assert a_result.evidence.unresolved == a_prior.evidence.unresolved

    # THOUGHT-B: opposing bucket
    b_prior = prior.get("THOUGHT-B")
    b_result = result.get("THOUGHT-B")
    assert b_result.evidence.opposing == (*b_prior.evidence.opposing, eid)
    assert b_result.evidence.supporting == b_prior.evidence.supporting
    assert b_result.evidence.unresolved == b_prior.evidence.unresolved


def test_confidence_and_status_changes() -> None:
    """Caller-supplied confidence and status changes are applied."""
    result, _, _, _, _ = _replay()
    assert result.get("THOUGHT-A").metrics.confidence == 0.55
    assert result.get("THOUGHT-A").status.state == "testing"
    assert result.get("THOUGHT-B").metrics.confidence == 0.45
    assert result.get("THOUGHT-B").status.state == "partially_verified"


def test_immutable_fields_preserved() -> None:
    """Immutable fields are preserved on replacements."""
    result, _, prior, _, _ = _replay()
    for tid in ("THOUGHT-A", "THOUGHT-B"):
        p = prior.get(tid)
        r = result.get(tid)
        assert r.thought_id == p.thought_id
        assert r.parent_ids == p.parent_ids
        assert r.created_at == p.created_at
        assert r.interpretation == p.interpretation
        assert r.hypothesis == p.hypothesis
        assert r.assumptions == p.assumptions
        assert r.executor_profile == p.executor_profile
        assert r.graph == p.graph


def test_packet_round_trip() -> None:
    """EvidencePacket canonical JSON round-trip is exact."""
    _, _, _, pkt, _ = _replay()
    j = pkt.to_canonical_json()
    assert EvidencePacket.from_canonical_json(j).to_canonical_json() == j


def test_plan_round_trip_and_validate() -> None:
    """AssimilationPlan canonical JSON round-trip is exact; deserialized plan validates."""
    result, _, prior, _, plan = _replay()
    j = plan.to_canonical_json()
    restored = AssimilationPlan.from_canonical_json(j)
    assert restored.to_canonical_json() == j
    # Deserialized plan validates against the prior snapshot
    restored.validate_for(prior)


def test_record_round_trip() -> None:
    """EvidenceUpdateRecord canonical JSON round-trip is exact."""
    _, rec, _, _, _ = _replay()
    j = rec.to_canonical_json()
    assert EvidenceUpdateRecord.from_canonical_json(j).to_canonical_json() == j


def test_result_snapshot_round_trip() -> None:
    """Result PopulationSnapshot canonical JSON round-trip is exact."""
    result, _, _, _, _ = _replay()
    j = result.to_canonical_json()
    assert PopulationSnapshot.from_canonical_json(j).to_canonical_json() == j
