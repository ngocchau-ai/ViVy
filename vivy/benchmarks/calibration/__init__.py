"""O-05/T3 confidence calibration infrastructure (WP-9).

Provides calibrated confidence measurement: feature extractors for the
seven T3 definitions, isotonic regression, and ECE/AUROC/Brier metrics.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from benchmarks.calibration.features import EXTRACTORS, FeatureContext, extract_all
from benchmarks.calibration.isotonic import IsotonicModel, isotonic_regression
from benchmarks.calibration.metrics import (
    auroc,
    brier_score,
    expected_calibration_error,
)

__all__ = [
    "EXTRACTORS",
    "FeatureContext",
    "IsotonicModel",
    "auroc",
    "brier_score",
    "expected_calibration_error",
    "extract_all",
    "isotonic_regression",
]
