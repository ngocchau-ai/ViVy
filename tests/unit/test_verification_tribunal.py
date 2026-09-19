"""Unit tests for Stage 5 Verification Tribunal."""

from __future__ import annotations

from nps_core.evidence_assimilator import EvidencePacket, Reproducibility
from nps_core.hypothesis_population import PopulationSnapshot
from nps_core.verification_tribunal import (
    ConfidenceCalibrator,
    ConflictDetector,
    VerificationTribunal,
)


def make_packet(eid: str, tid: str, result: str) -> EvidencePacket:
    return EvidencePacket(
        evidence_id=eid,
        task_id="TASK-001",
        executor_id="EXECUTOR-001",
        claim="Claim verified",
        result=result,
        method="test",
        artifacts=(),
        confidence=0.9,
        limitations=(),
        failure_modes=(),
        reproducibility=Reproducibility(command="pytest", environment="local", seed=None),
        affected_hypotheses=(tid,),
        provenance=("runner",),
        content_hash="a" * 64,
    )


def test_conflict_detector() -> None:
    p1 = make_packet("EV-001", "THOUGHT-001", "PASSED")
    p2 = make_packet("EV-002", "THOUGHT-001", "FAILED")

    conflicts = ConflictDetector.detect_conflicts((p1, p2))
    assert len(conflicts) == 1
    assert conflicts[0].thought_id == "THOUGHT-001"
    assert "EV-001" in conflicts[0].conflicting_evidence_ids


def test_confidence_calibrator() -> None:
    calibrated = ConfidenceCalibrator.calibrate(
        prior_confidence=0.5,
        supporting_count=3,
        opposing_count=1,
        weight=0.1,
    )
    assert calibrated == 0.7


def test_verification_tribunal_evaluate() -> None:
    p1 = make_packet("EV-001", "THOUGHT-001", "PASSED")
    snapshot = PopulationSnapshot.empty()

    conflicts, logs = VerificationTribunal.evaluate((p1,), snapshot)
    assert len(conflicts) == 0
    assert len(logs) == 1
    assert logs[0].evidence_id == "EV-001"
    assert logs[0].reproduced is True
