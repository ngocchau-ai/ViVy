"""Funnel: quality filtering and curation for training data.

Provides deterministic scoring and filtering of TrainingExamples
based on confidence, evidence strength, verification status,
completeness, and deduplication.  Standard-library only; no I/O.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from nps_core.model_training.bridge import TrainingExample
from nps_core.model_training.errors import FunnelError

__all__ = [
    "FunnelConfig",
    "QualityScore",
    "FunnelResult",
    "score_example",
    "funnel",
    "deduplicate",
    "rank_by_quality",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _funnel_err(msg: str, **kwargs: Any) -> FunnelError:
    return FunnelError(msg, **kwargs)


# ---------------------------------------------------------------------------
# FunnelConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FunnelConfig:
    """Configuration for the quality funnel."""

    # --- Confidence thresholds ---
    min_confidence: float = 0.3
    max_confidence: float = 1.0

    # --- Evidence thresholds ---
    min_evidence_count: int = 1
    min_support_ratio: float = 0.0

    # --- Status preferences (ordered by priority) ---
    preferred_statuses: tuple[str, ...] = (
        "verified",
        "partially_verified",
        "testing",
        "active",
    )

    # --- Completeness ---
    require_hypothesis: bool = True
    require_evidence: bool = True
    require_verification_plan: bool = False

    # --- Diversity ---
    max_examples_per_thought: int = 5
    max_examples_per_task: int = 10000

    # --- Deduplication ---
    deduplicate: bool = True

    # --- Output ---
    max_total_examples: int = 100000

    def __post_init__(self) -> None:
        if not 0 <= self.min_confidence <= 1:
            raise _funnel_err(
                f"min_confidence must be in [0, 1], got {self.min_confidence}",
                path="min_confidence",
            )
        if not 0 <= self.max_confidence <= 1:
            raise _funnel_err(
                f"max_confidence must be in [0, 1], got {self.max_confidence}",
                path="max_confidence",
            )
        if self.min_confidence > self.max_confidence:
            raise _funnel_err(
                "min_confidence must be <= max_confidence",
                path="min_confidence",
            )
        if self.min_evidence_count < 0:
            raise _funnel_err(
                f"min_evidence_count must be >= 0, got {self.min_evidence_count}",
                path="min_evidence_count",
            )


# ---------------------------------------------------------------------------
# QualityScore
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QualityScore:
    """Immutable quality score for a training example."""

    confidence_score: float
    evidence_score: float
    status_score: float
    completeness_score: float
    overall_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence_score": round(self.confidence_score, 4),
            "evidence_score": round(self.evidence_score, 4),
            "status_score": round(self.status_score, 4),
            "completeness_score": round(self.completeness_score, 4),
            "overall_score": round(self.overall_score, 4),
        }


# ---------------------------------------------------------------------------
# FunnelResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FunnelResult:
    """Immutable result of the funnel pipeline."""

    accepted: tuple[TrainingExample, ...]
    rejected: tuple[TrainingExample, ...]
    scores: dict[str, QualityScore]
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_count": len(self.accepted),
            "rejected_count": len(self.rejected),
            "total_input": len(self.accepted) + len(self.rejected),
            "acceptance_rate": round(
                len(self.accepted)
                / max(len(self.accepted) + len(self.rejected), 1),
                4,
            ),
            "stats": self.stats,
        }


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

_STATUS_SCORES: dict[str, float] = {
    "verified": 1.0,
    "partially_verified": 0.8,
    "testing": 0.6,
    "active": 0.5,
    "queued": 0.4,
    "dormant": 0.2,
    "rejected": 0.1,
    "merged": 0.3,
}


def score_example(example: TrainingExample) -> QualityScore:
    """Compute a quality score for a training example."""
    meta = example.metadata

    # 1. Confidence score [0, 1]
    confidence = meta.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence_score = max(0.0, min(1.0, float(confidence)))

    # 2. Evidence score [0, 1]
    ev_count = meta.get("evidence_count", 0)
    if not isinstance(ev_count, (int, float)):
        ev_count = 0
    if ev_count <= 0:
        evidence_score = 0.0
    elif ev_count >= 10:
        evidence_score = 1.0
    else:
        evidence_score = min(1.0, 0.1 * ev_count + 0.2)

    # 3. Status score
    status = meta.get("status", "active")
    if not isinstance(status, str):
        status = "active"
    status_score = _STATUS_SCORES.get(status, 0.3)

    # 4. Completeness score
    completeness_items = 0
    completeness_total = 4

    if example.input and len(example.input) > 20:
        completeness_items += 1
    if example.output and len(example.output) > 10:
        completeness_items += 1
    if meta.get("thought_id"):
        completeness_items += 1
    if meta.get("parent_ids") is not None or meta.get("evidence_count", 0) > 0:
        completeness_items += 1

    completeness_score = completeness_items / completeness_total

    # Overall: weighted average
    overall = (
        0.35 * confidence_score
        + 0.25 * evidence_score
        + 0.20 * status_score
        + 0.20 * completeness_score
    )

    return QualityScore(
        confidence_score=confidence_score,
        evidence_score=evidence_score,
        status_score=status_score,
        completeness_score=completeness_score,
        overall_score=round(overall, 4),
    )


# ---------------------------------------------------------------------------
# Funnel pipeline
# ---------------------------------------------------------------------------


def funnel(
    examples: list[TrainingExample],
    *,
    config: FunnelConfig | None = None,
) -> FunnelResult:
    """Filter and curate training examples through the quality funnel."""
    if config is None:
        config = FunnelConfig()

    # Stage 1: Score all examples
    scores: dict[str, QualityScore] = {}
    for ex in examples:
        scores[ex.content_hash] = score_example(ex)

    # Stage 2-5: Filter
    accepted: list[TrainingExample] = []
    rejected: list[TrainingExample] = []

    for ex in examples:
        meta = ex.metadata

        # Confidence threshold
        confidence = meta.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        if confidence < config.min_confidence or confidence > config.max_confidence:
            rejected.append(ex)
            continue

        # Evidence threshold
        ev_count = meta.get("evidence_count", 0)
        if not isinstance(ev_count, (int, float)):
            ev_count = 0
        if ev_count < config.min_evidence_count:
            if config.require_evidence and ex.task in ("reasoning", "critique"):
                rejected.append(ex)
                continue

        # Status preference
        status = meta.get("status", "active")
        if not isinstance(status, str):
            status = "active"
        if status not in config.preferred_statuses and status not in _STATUS_SCORES:
            rejected.append(ex)
            continue

        # Completeness
        if config.require_hypothesis and ex.task == "reasoning":
            if "Hypothesis:" not in ex.output:
                rejected.append(ex)
                continue

        accepted.append(ex)

    # Stage 6: Deduplication
    if config.deduplicate:
        accepted = deduplicate(accepted)

    # Stage 7: Per-thought and per-task limits
    thought_counts: dict[str, int] = defaultdict(int)
    task_counts: dict[str, int] = defaultdict(int)
    limited: list[TrainingExample] = []

    for ex in accepted:
        tid = ex.metadata.get("thought_id", "unknown")
        if thought_counts[tid] >= config.max_examples_per_thought:
            continue
        if task_counts[ex.task] >= config.max_examples_per_task:
            continue
        thought_counts[tid] += 1
        task_counts[ex.task] += 1
        limited.append(ex)

    # Stage 8: Sort by quality and apply max_total
    limited.sort(
        key=lambda ex: scores[ex.content_hash].overall_score,
        reverse=True,
    )
    final = limited[: config.max_total_examples]

    # Rejected = those filtered + those cut by limits
    final_hashes = {ex.content_hash for ex in final}
    all_rejected = [ex for ex in examples if ex.content_hash not in final_hashes]

    stats: dict[str, Any] = {
        "scored": len(scores),
        "passed_thresholds": len(accepted),
        "after_dedup": len(accepted) if not config.deduplicate else "deduped",
        "after_limits": len(limited),
        "final": len(final),
        "per_task": dict(task_counts),
        "per_thought_top": dict(
            sorted(thought_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
    }

    return FunnelResult(
        accepted=tuple(final),
        rejected=tuple(all_rejected),
        scores=scores,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate(examples: list[TrainingExample]) -> list[TrainingExample]:
    """Remove duplicate examples by content_hash."""
    seen: set[str] = set()
    unique: list[TrainingExample] = []
    for ex in examples:
        if ex.content_hash not in seen:
            seen.add(ex.content_hash)
            unique.append(ex)
    return unique


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_by_quality(
    examples: list[TrainingExample],
) -> list[tuple[TrainingExample, QualityScore]]:
    """Rank examples by overall quality score (descending)."""
    scored = [(ex, score_example(ex)) for ex in examples]
    scored.sort(key=lambda pair: pair[1].overall_score, reverse=True)
    return scored
