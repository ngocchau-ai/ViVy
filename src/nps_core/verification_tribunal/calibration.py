"""Confidence Calibrator for Stage 5.

Computes calibrated confidence scores based on Bayesian evidence updates.
Standard-library only.
"""

from __future__ import annotations

__all__ = [
    "ConfidenceCalibrator",
]


class ConfidenceCalibrator:
    """Computes calibrated hypothesis confidence scores."""

    @staticmethod
    def calibrate(
        prior_confidence: float,
        supporting_count: int,
        opposing_count: int,
        weight: float = 0.1,
    ) -> float:
        """Calculate Bayesian updated confidence score bounded in [0.0, 1.0]."""
        prior = max(0.0, min(1.0, prior_confidence))
        delta = (supporting_count * weight) - (opposing_count * weight)
        posterior = prior + delta
        return round(max(0.0, min(1.0, posterior)), 4)
