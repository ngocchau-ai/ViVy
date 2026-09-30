"""Adaptive N Controller for Stage 4.

Dynamically controls hypothesis population size N_h and detects merge/dedup candidates.
Standard-library only.
"""

from __future__ import annotations

from nps_core.adaptive_n.errors import BudgetExceededError
from nps_core.hypothesis_population.lifecycle import PopulationSnapshot
from nps_core.thought_ecology import ThoughtEcology

__all__ = [
    "AdaptiveNController",
]


class AdaptiveNController:
    """Controller for dynamic N_h allocation and hypothesis deduplication."""

    @staticmethod
    def compute_target_n(
        snapshot: PopulationSnapshot,
        ecology: ThoughtEcology,
        max_budget: int = 20,
    ) -> int:
        """Compute recommended target N_h based on population size, ecology, and budget limit."""
        n_h = len(snapshot.thoughts)
        contradiction_count = len(ecology.contradictions)

        # Base allocation scaling: scale up if high contradictions, cap at max_budget
        suggested_n = n_h + (contradiction_count // 2)
        if suggested_n > max_budget:
            raise BudgetExceededError(
                f"Target N_h ({suggested_n}) exceeds maximum budget ({max_budget})",
                path="max_budget",
            )
        return max(1, suggested_n)

    @staticmethod
    def detect_duplicates(
        snapshot: PopulationSnapshot,
    ) -> tuple[tuple[str, str], ...]:
        """Detect potential duplicate hypothesis pairs based on exact or overlapping claims."""
        duplicates: list[tuple[str, str]] = []
        thoughts = snapshot.thoughts

        for i in range(len(thoughts)):
            for j in range(i + 1, len(thoughts)):
                t1, t2 = thoughts[i], thoughts[j]
                c1 = t1.hypothesis.claim.strip().lower()
                c2 = t2.hypothesis.claim.strip().lower()
                if c1 == c2:
                    duplicates.append((min(t1.thought_id, t2.thought_id), max(t1.thought_id, t2.thought_id)))

        return tuple(sorted(duplicates))
