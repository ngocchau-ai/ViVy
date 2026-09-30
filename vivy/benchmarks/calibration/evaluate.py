"""T3 evaluation pipeline — does any confidence definition calibrate?

Fits isotonic calibration on dev, measures ECE/AUROC/Brier on held-out,
and selects the first definition meeting the T3 thresholds.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from benchmarks.calibration.isotonic import IsotonicModel, isotonic_regression
from benchmarks.calibration.metrics import (
    auroc,
    brier_score,
    expected_calibration_error,
)

__all__ = [
    "DefinitionMetrics",
    "T3Verdict",
    "run_t3_evaluation",
]

#: T3 acceptance thresholds (REVIEW_VIVY_2026-09-29.md §8).
ECE_THRESHOLD = 0.10
AUROC_THRESHOLD = 0.70


@dataclass(frozen=True)
class DefinitionMetrics:
    """Measured calibration quality for one confidence definition."""

    definition: str
    ece: float
    auroc: float
    brier: float
    n_items: int
    passes: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": self.definition,
            "ece": round(self.ece, 6),
            "auroc": round(self.auroc, 6),
            "brier": round(self.brier, 6),
            "n_items": self.n_items,
            "passes": self.passes,
        }


@dataclass
class T3Verdict:
    """The outcome of a T3 run: which definition (if any) passed."""

    selected: str
    status: str  # "PASS" | "FALLBACK"
    metrics: dict[str, DefinitionMetrics] = field(default_factory=dict)
    isotonic_model: dict[str, list[float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected,
            "status": self.status,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "isotonic_model": self.isotonic_model,
            "thresholds": {
                "ece": ECE_THRESHOLD,
                "auroc": AUROC_THRESHOLD,
            },
        }


def run_t3_evaluation(
    scores_by_def: dict[str, list[float]],
    labels: list[int],
    *,
    dev_indices: Sequence[int],
    heldout_indices: Sequence[int],
) -> T3Verdict:
    """Run T3: calibrate on dev, measure on held-out, select the winner.

    Parameters
    ----------
    scores_by_def:
        Definition name → score per item (must all have the same length).
    labels:
        Correctness labels (0 or 1), same length as each score list.
    dev_indices:
        Indices into ``labels`` for the calibration split.
    heldout_indices:
        Indices into ``labels`` for the evaluation split.
    """
    if not dev_indices:
        raise ValueError("dev_indices must be non-empty for calibration")
    if not heldout_indices:
        raise ValueError("heldout_indices must be non-empty for evaluation")

    metrics: dict[str, DefinitionMetrics] = {}
    models: dict[str, IsotonicModel] = {}

    for def_name in scores_by_def:
        raw_scores = scores_by_def[def_name]
        if len(raw_scores) != len(labels):
            raise ValueError(
                f"{def_name}: scores length {len(raw_scores)} != labels length {len(labels)}"
            )

        dev_scores = [raw_scores[i] for i in dev_indices]
        dev_labels = [labels[i] for i in dev_indices]
        heldout_scores = [raw_scores[i] for i in heldout_indices]
        heldout_labels = [labels[i] for i in heldout_indices]

        # Fit isotonic on dev
        model = isotonic_regression(dev_scores, dev_labels)
        models[def_name] = model

        # Apply calibration to heldout
        calibrated = [model.predict(s) for s in heldout_scores]

        # Measure on heldout
        ece = expected_calibration_error(calibrated, heldout_labels, n_bins=10)
        auc = auroc(calibrated, heldout_labels)
        brier = brier_score(calibrated, heldout_labels)
        passes = ece <= ECE_THRESHOLD and auc >= AUROC_THRESHOLD

        metrics[def_name] = DefinitionMetrics(
            definition=def_name,
            ece=ece,
            auroc=auc,
            brier=brier,
            n_items=len(heldout_labels),
            passes=passes,
        )

    # Select the first passing definition in registry order
    selected = "verifier"
    status = "FALLBACK"
    iso_dict: dict[str, list[float]] = {}

    for def_name in scores_by_def:
        if metrics[def_name].passes:
            selected = def_name
            status = "PASS"
            iso_dict = models[def_name].to_dict()
            break

    return T3Verdict(
        selected=selected,
        status=status,
        metrics=metrics,
        isotonic_model=iso_dict,
    )
