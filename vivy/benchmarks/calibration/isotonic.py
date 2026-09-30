"""Pool Adjacent Violators (PAV) isotonic regression.

Pure Python, zero dependencies.  Fits a monotone non-decreasing step
function mapping raw score → calibrated probability.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

__all__ = ["IsotonicModel", "isotonic_regression"]


@dataclass
class IsotonicModel:
    """Monotone step function: raw score → calibrated probability."""

    thresholds: list[float] = field(default_factory=list)
    values: list[float] = field(default_factory=list)

    def predict(self, score: float) -> float:
        """Return the calibrated probability for ``score``.

        Uses right-continuous step: the value of the first block whose
        threshold >= score; if score exceeds all thresholds, returns the
        last value.
        """
        if not self.values:
            return 0.0
        for t, v in zip(self.thresholds, self.values, strict=True):
            if score <= t:
                return v
        return self.values[-1]

    def to_dict(self) -> dict[str, list[float]]:
        """JSON-safe serialisation of the calibration curve."""
        return {"thresholds": list(self.thresholds), "values": list(self.values)}


def isotonic_regression(
    scores: Sequence[float],
    labels: Sequence[int],
) -> IsotonicModel:
    """Fit a monotone non-decreasing step function via PAV.

    Parameters
    ----------
    scores:
        Raw confidence scores (any order).
    labels:
        Binary correctness labels (0 or 1), same length as scores.
    """
    n = len(scores)
    if n == 0:
        return IsotonicModel(thresholds=[], values=[])
    if n != len(labels):
        raise ValueError(f"scores and labels length mismatch: {n} vs {len(labels)}")

    # Sort by score ascending
    paired = sorted(zip(scores, labels, strict=True), key=lambda t: t[0])
    sorted_scores = [p[0] for p in paired]
    sorted_labels = [p[1] for p in paired]

    # Each block: [start_idx, end_idx, sum_labels, count]
    blocks: list[list[int]] = []
    for i in range(n):
        blocks.append([i, i, sorted_labels[i], 1])

    # PAV: merge adjacent blocks while left mean > right mean
    i = 0
    while i < len(blocks) - 1:
        left = blocks[i]
        right = blocks[i + 1]
        mean_left = left[2] / left[3]
        mean_right = right[2] / right[3]
        if mean_left > mean_right:
            # Merge
            merged = [left[0], right[1], left[2] + right[2], left[3] + right[3]]
            blocks[i] = merged
            blocks.pop(i + 1)
            # Step back one to check if the new block violates with its left
            if i > 0:
                i -= 1
        else:
            i += 1

    # Build model: threshold = rightmost score in block, value = block mean
    model = IsotonicModel()
    for _start, end, sum_labels, count in blocks:
        model.thresholds.append(sorted_scores[end])
        model.values.append(round(sum_labels / count, 6))
    return model
