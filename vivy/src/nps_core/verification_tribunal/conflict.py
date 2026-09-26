"""Conflict Detector and ConflictReport for Stage 5.

Identifies conflicting evidence packets targeting the same hypothesis.
Standard-library only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from nps_core.evidence_assimilator import EvidencePacket

__all__ = [
    "ConflictReport",
    "ConflictDetector",
]


@dataclass(frozen=True, slots=True)
class ConflictReport:
    """Frozen value object holding conflict details between evidence packets."""

    thought_id: str
    conflicting_evidence_ids: tuple[str, ...]
    contradiction_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "thought_id": self.thought_id,
            "conflicting_evidence_ids": list(self.conflicting_evidence_ids),
            "contradiction_reason": self.contradiction_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConflictReport:
        return cls(
            thought_id=data["thought_id"],
            conflicting_evidence_ids=tuple(data["conflicting_evidence_ids"]),
            contradiction_reason=data["contradiction_reason"],
        )

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


class ConflictDetector:
    """Detects conflicting evidence packets for hypotheses."""

    @staticmethod
    def detect_conflicts(packets: Sequence[EvidencePacket]) -> tuple[ConflictReport, ...]:
        """Group evidence packets by affected hypothesis and detect conflicting results."""
        by_thought: dict[str, list[EvidencePacket]] = {}
        for pkt in packets:
            for tid in pkt.affected_hypotheses:
                by_thought.setdefault(tid, []).append(pkt)

        reports: list[ConflictReport] = []
        for tid, pkt_list in sorted(by_thought.items()):
            results = {p.result.upper() for p in pkt_list}
            if len(results) > 1 or ("PASSED" in results and "FAILED" in results):
                eids = tuple(sorted(p.evidence_id for p in pkt_list))
                reports.append(
                    ConflictReport(
                        thought_id=tid,
                        conflicting_evidence_ids=eids,
                        contradiction_reason=f"Conflicting results {sorted(results)} across packets {eids}",
                    )
                )

        return tuple(reports)
