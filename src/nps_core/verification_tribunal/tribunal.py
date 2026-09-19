"""Verification Tribunal Engine for Stage 5.

Evaluates evidence packets, generates ReproductionLogs, detects correlated errors,
and integrates Self-Verification Filter Funnel for metacognitive verification.
Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from nps_core.evidence_assimilator import EvidencePacket
from nps_core.filter_funnel import FilterFunnel, FunnelResult
from nps_core.hypothesis_population import PopulationSnapshot
from nps_core.verification_tribunal.conflict import ConflictDetector, ConflictReport

__all__ = [
    "ReproductionLog",
    "VerificationTribunal",
]


@dataclass(frozen=True, slots=True)
class ReproductionLog:
    """Frozen value object capturing evidence reproduction log metadata."""

    evidence_id: str
    executor_id: str
    command: str
    environment: str
    reproduced: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "executor_id": self.executor_id,
            "command": self.command,
            "environment": self.environment,
            "reproduced": self.reproduced,
        }


class VerificationTribunal:
    """Evaluates evidence packets, detects conflicts, and generates reproduction logs."""

    @staticmethod
    def evaluate(
        packets: Sequence[EvidencePacket],
        snapshot: PopulationSnapshot,
    ) -> tuple[tuple[ConflictReport, ...], tuple[ReproductionLog, ...]]:
        """Evaluate evidence packets against snapshot, returning conflicts and reproduction logs."""
        conflicts = ConflictDetector.detect_conflicts(packets)

        reproduction_logs: list[ReproductionLog] = []
        for pkt in packets:
            cmd = pkt.reproducibility.command if pkt.reproducibility else "n/a"
            env = pkt.reproducibility.environment if pkt.reproducibility else "n/a"
            reproduced = pkt.result.upper() == "PASSED"
            reproduction_logs.append(
                ReproductionLog(
                    evidence_id=pkt.evidence_id,
                    executor_id=pkt.executor_id,
                    command=cmd,
                    environment=env,
                    reproduced=reproduced,
                )
            )

        return conflicts, tuple(reproduction_logs)

    @classmethod
    def evaluate_with_filter_funnel(
        cls,
        packets: Sequence[EvidencePacket],
        snapshot: PopulationSnapshot,
        state_vector: Sequence[complex | float],
        partition: tuple[int, int] = (2, 2),
        funnel: FilterFunnel | None = None,
    ) -> tuple[tuple[ConflictReport, ...], tuple[ReproductionLog, ...], FunnelResult]:
        """Evaluate evidence packets and execute Self-Verification Filter Funnel on state vector."""
        conflicts, reproduction_logs = cls.evaluate(packets, snapshot)

        active_funnel = funnel or FilterFunnel()
        funnel_result = active_funnel.evaluate_state(state_vector=state_vector, partition=partition)

        return conflicts, reproduction_logs, funnel_result
