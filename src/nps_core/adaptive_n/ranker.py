"""Information-Gain Ranker for Stage 4.

Ranks hypotheses deterministically by expected information gain.
Standard-library only.
"""

from __future__ import annotations

from nps_core.hypothesis_population.lifecycle import PopulationSnapshot

__all__ = [
    "InformationGainRanker",
]


class InformationGainRanker:
    """Ranks hypotheses in PopulationSnapshot by expected information gain E[IG]."""

    @staticmethod
    def rank_hypotheses(snapshot: PopulationSnapshot) -> tuple[tuple[str, float], ...]:
        """Compute expected information gain for each hypothesis and return sorted tuple (thought_id, E[IG])."""
        scored: list[tuple[str, float]] = []

        for t in snapshot.thoughts:
            # E[IG] = (1 - confidence) * risk_if_wrong * information_need
            conf = t.metrics.confidence
            risk = t.metrics.risk_if_wrong
            need = t.metrics.information_need
            ig = round((1.0 - conf) * risk * need, 6)
            scored.append((t.thought_id, ig))

        # Sort by E[IG] descending, then thought_id ascending
        scored.sort(key=lambda item: (-item[1], item[0]))
        return tuple(scored)
