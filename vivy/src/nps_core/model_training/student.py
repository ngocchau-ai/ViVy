"""NPS Student Model Proposal Engine and Latency Evaluator for Stage 7.

Standard-library only.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nps_core.hypothesis_population import (
    VALID_STATES,
    ThoughtState,
    thought_state_from_dict,
)
from nps_core.model_training.errors import ModelTrainingError

__all__ = [
    "StudentTrainingConfig",
    "StudentProposalEngine",
    "LatencyEvaluator",
]


@dataclass(frozen=True, slots=True)
class StudentTrainingConfig:
    """Frozen value object holding student model training hyperparameters."""

    model_name: str
    batch_size: int
    learning_rate: float
    max_sequence_length: int

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ModelTrainingError("batch_size must be positive", path="batch_size")
        if self.learning_rate <= 0:
            raise ModelTrainingError("learning_rate must be positive", path="learning_rate")


class StudentProposalEngine:
    """Student model engine generating fast hypothesis proposals."""

    @staticmethod
    def generate_proposal(thought_id: str, claim: str, parent_ids: tuple[str, ...] = ()) -> ThoughtState:
        """Generate a valid schema-compliant ThoughtState proposal."""
        d = {
            "thought_id": thought_id,
            "parent_ids": list(parent_ids),
            "created_at": "2026-07-25T10:00:00Z",
            "interpretation": {
                "summary": f"Student proposal for {thought_id}",
                "scope": "global",
                "excluded_scope": [],
            },
            "hypothesis": {
                "claim": claim,
                "predicted_observations": ["student observation"],
                "falsification_conditions": ["student falsification"],
            },
            "assumptions": [
                {
                    "assumption_id": "ASM-STU-001",
                    "statement": "Student baseline axiom",
                    "confidence": 0.85,
                    "source": "student_proposal",
                }
            ],
            "evidence": {"supporting": [], "opposing": [], "unresolved": []},
            "metrics": {
                "confidence": 0.6,
                "novelty": 0.7,
                "diversity": 0.5,
                "expected_value": 0.6,
                "information_need": 0.5,
                "risk_if_wrong": 0.4,
                "execution_cost": 0.2,
            },
            "verification_plan": {
                "questions": [],
                "required_experiments": [],
                "acceptable_evidence": [],
                "rejection_threshold": 0.2,
            },
            "executor_profile": {
                "skills": ["python"],
                "tool_requirements": [],
                "preferred_model_class": "student",
                "independence_requirements": [],
            },
            "graph": {"dependencies": [], "contradictions": [], "overlaps": []},
            "status": {"state": "active", "allowed_values": list(VALID_STATES)},
        }
        return thought_state_from_dict(d)


class LatencyEvaluator:
    """Evaluates student model proposal latency against SLAs."""

    @staticmethod
    def evaluate_latency(
        proposal_fn: Callable[..., Any],
        iterations: int = 10,
        max_latency_ms: float = 200.0,
    ) -> dict[str, float]:
        """Measure mean and max latency over iterations, asserting < max_latency_ms."""
        times: list[float] = []

        for i in range(iterations):
            start = time.perf_counter()
            proposal_fn(f"THOUGHT-STU-{i:03d}", f"Claim {i}")
            elapsed = (time.perf_counter() - start) * 1000.0
            times.append(elapsed)

        mean_lat = sum(times) / len(times)
        max_lat = max(times)

        if max_lat > max_latency_ms:
            raise ModelTrainingError(
                f"Latency SLA violated: max latency {max_lat:.2f}ms exceeds threshold {max_latency_ms:.2f}ms",
                path="latency",
            )

        return {
            "mean_latency_ms": round(mean_lat, 3),
            "max_latency_ms": round(max_lat, 3),
        }
