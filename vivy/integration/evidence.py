"""Validation boundary for promotion to durable knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidencePacket:
    claim: str
    evidence_ids: tuple[str, ...]
    source: str
    expected_evidence: str
    actual_observation: str
    acceptance: str
    confidence: float
    limits: str
    task_id: str
    session_id: str
    state_hash: str
    input_hash: str = ""
    output_hash: str = ""

    def valid_for_promotion(self) -> bool:
        return bool(self.claim.strip() and self.evidence_ids and self.source.strip()
                    and self.expected_evidence.strip() and self.actual_observation.strip()
                    and self.acceptance.strip() and self.limits.strip()
                    and self.task_id.strip() and self.session_id.strip()
                    and self.state_hash.strip() and 0.0 <= self.confidence <= 1.0)


def evidence_from_mapping(value: dict[str, Any]) -> EvidencePacket:
    return EvidencePacket(
        claim=str(value.get("claim", "")),
        evidence_ids=tuple(value.get("evidence_ids", ())),
        source=str(value.get("source", "")),
        expected_evidence=str(value.get("expected_evidence", "")),
        actual_observation=str(value.get("actual_observation", "")),
        acceptance=str(value.get("acceptance", "")),
        confidence=float(value.get("confidence", -1)),
        limits=str(value.get("limits", "")),
        task_id=str(value.get("task_id", "")),
        session_id=str(value.get("session_id", "")),
        state_hash=str(value.get("state_hash", "")),
        input_hash=str(value.get("input_hash", "")),
        output_hash=str(value.get("output_hash", "")),
    )
