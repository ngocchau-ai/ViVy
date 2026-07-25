"""Integration test: multi-hypothesis atomic evidence update.

Validates the full pipeline from ThoughtState creation through
evidence packet, assimilation plan, and atomic state update.
"""

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


def _make_thought(
    thought_id: str,
    *,
    evidence: dict | None = None,
    confidence: float = 0.5,
) -> ThoughtState:
    """Create a minimal valid ThoughtState for testing."""
    ev = evidence or {"supporting": [], "opposing": [], "unresolved": []}
    return ThoughtState.from_dict({
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2025-01-01T00:00:00Z",
        "interpretation": {
            "summary": f"Summary for {thought_id}",
            "scope": "global",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": f"Claim for {thought_id}",
            "predicted_observations": ["obs1"],
            "falsification_conditions": ["fail1"],
        },
        "assumptions": [],
        "evidence": ev,
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
            "questions": ["q1"],
            "required_experiments": ["exp1"],
            "acceptable_evidence": ["ev1"],
            "rejection_threshold": 0.1,
        },
        "executor_profile": {
            "skills": ["analysis"],
            "tool_requirements": ["tool1"],
            "preferred_model_class": "reasoning",
            "independence_requirements": ["indep1"],
        },
        "graph": {
            "dependencies": [],
            "contradictions": [],
            "overlaps": [],
        },
        "status": {
            "state": "active",
            "allowed_values": [
                "active", "queued", "testing", "partially_verified",
                "verified", "rejected", "merged", "dormant",
            ],
        },
    })


def _make_packet(
    evidence_id: str,
    affected_hypotheses: list[str],
    content_hash: str = "a" * 64,
) -> EvidencePacket:
    """Create a minimal valid EvidencePacket for testing."""
    return EvidencePacket.from_dict({
        "evidence_id": evidence_id,
        "task_id": "TASK-001",
        "executor_id": "executor-1",
        "claim": "Test claim",
        "result": "Test result",
        "method": "Test method",
        "artifacts": ["artifact1"],
        "confidence": 0.8,
        "limitations": ["limit1"],
        "failure_modes": ["fail1"],
        "reproducibility": {
            "command": "run test",
            "environment": "test env",
            "seed": 42,
        },
        "affected_hypotheses": affected_hypotheses,
        "provenance": ["source1"],
        "content_hash": content_hash,
    })


def _build_replacement(
    thought: ThoughtState,
    classification: str,
    evidence_id: str,
    *,
    new_confidence: float | None = None,
    new_status: str | None = None,
) -> ThoughtState:
    """Build a replacement ThoughtState with evidence_id appended."""
    ev = thought.evidence
    new_ev = {
        "supporting": list(ev.supporting),
        "opposing": list(ev.opposing),
        "unresolved": list(ev.unresolved),
    }
    new_ev[classification].append(evidence_id)

    d = thought.to_dict()
    d["evidence"] = new_ev
    if new_confidence is not None:
        d["metrics"]["confidence"] = new_confidence
    if new_status is not None:
        d["status"]["state"] = new_status
    return ThoughtState.from_dict(d)


def test_multi_hypothesis_update() -> None:
    """Apply one evidence packet affecting two hypotheses atomically."""
    # 1. Create snapshot with two active thoughts
    t1 = _make_thought("THOUGHT-alpha")
    t2 = _make_thought("THOUGHT-beta")
    snapshot = PopulationSnapshot.empty()
    snapshot = create(
        snapshot, t1,
        event_id="EVT-001",
        timestamp="2025-01-01T00:00:00Z",
        actor="system",
    )
    snapshot = create(
        snapshot, t2,
        event_id="EVT-002",
        timestamp="2025-01-01T00:00:01Z",
        actor="system",
    )

    # 2. Build evidence packet
    packet = _make_packet(
        "EV-multi-001", ["THOUGHT-alpha", "THOUGHT-beta"],
    )

    # 3. Build assimilation plan
    impacts = (
        EvidenceImpact(
            target_thought_id="THOUGHT-alpha",
            classification="supporting",
        ),
        EvidenceImpact(
            target_thought_id="THOUGHT-beta",
            classification="opposing",
        ),
    )
    plan = AssimilationPlan.create(packet, impacts, snapshot)

    # 4. Build replacements
    replacements = {
        "THOUGHT-alpha": _build_replacement(
            t1, "supporting", "EV-multi-001",
            new_confidence=0.55, new_status="testing",
        ),
        "THOUGHT-beta": _build_replacement(
            t2, "opposing", "EV-multi-001",
            new_confidence=0.45, new_status="partially_verified",
        ),
    }

    # 5. Apply evidence atomically
    new_snapshot, record = apply_evidence(
        snapshot, plan, replacements,
        record_id="REC-001",
        timestamp="2025-01-01T00:00:02Z",
        actor="system",
    )

    # 6. Verify record
    assert isinstance(record, EvidenceUpdateRecord)
    assert record.record_id == "REC-001"
    assert record.evidence_id == "EV-multi-001"
    assert record.sorted_target_ids == ("THOUGHT-alpha", "THOUGHT-beta")

    # 7. Verify new snapshot
    updated_alpha = new_snapshot.get("THOUGHT-alpha")
    updated_beta = new_snapshot.get("THOUGHT-beta")
    assert updated_alpha is not None
    assert updated_beta is not None
    assert "EV-multi-001" in updated_alpha.evidence.supporting
    assert "EV-multi-001" in updated_beta.evidence.opposing

    # 8. Verify caller changes applied
    assert updated_alpha.metrics.confidence == 0.55
    assert updated_alpha.status.state == "testing"
    assert updated_beta.metrics.confidence == 0.45
    assert updated_beta.status.state == "partially_verified"

    # 9. Verify original snapshot unchanged (immutability)
    orig_alpha = snapshot.get("THOUGHT-alpha")
    orig_beta = snapshot.get("THOUGHT-beta")
    assert "EV-multi-001" not in orig_alpha.evidence.supporting
    assert "EV-multi-001" not in orig_beta.evidence.opposing

    # 10. Verify digest integrity
    assert record.prior_state_digest != record.result_state_digest
    assert len(record.prior_state_digest) == 64
    assert len(record.result_state_digest) == 64

    # 11. Third thought and history unchanged
    assert new_snapshot.history == snapshot.history
