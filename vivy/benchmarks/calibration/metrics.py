"""Calibration quality metrics: ECE, AUROC, Brier.

Pure Python, zero dependencies.  ECE and Brier formulas match the existing
implementations in ``training/learned_router.py`` and
``training/independent_baselines.py``; AUROC is written here because no
implementation existed in the repo.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = [
    "auroc",
    "brier_score",
    "expected_calibration_error",
]


def expected_calibration_error(
    confidences: Sequence[float],
    labels: Sequence[int],
    n_bins: int = 10,
) -> float:
    """Equal-width-bin ECE: Σ (n_m/n) · |acc_m − conf_m|.

    Matches ``training/learned_router.py:46-68``.
    Returns 0.0 for empty input.
    """
    n = len(confidences)
    if n == 0:
        return 0.0
    bins: list[list[float]] = [[] for _ in range(n_bins)]
    bin_labels: list[list[int]] = [[] for _ in range(n_bins)]
    for c, y in zip(confidences, labels, strict=True):
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append(c)
        bin_labels[idx].append(y)
    ece = 0.0
    for i in range(n_bins):
        if not bins[i]:
            continue
        n_m = len(bins[i])
        mean_conf = sum(bins[i]) / n_m
        mean_acc = sum(bin_labels[i]) / n_m
        ece += (n_m / n) * abs(mean_acc - mean_conf)
    return ece


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Area under the ROC curve via rank-based Mann-Whitney U.

    AUC = P(score_positive > score_negative).
    Ties contribute 0.5.  Returns 0.5 when either class is empty.
    """
    n_pos = sum(1 for y in labels if y == 1)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    # Sort by score ascending, assign average ranks (1-based)
    paired = sorted(zip(scores, labels, strict=True), key=lambda t: t[0])
    ranks = [0.0] * len(paired)
    i = 0
    while i < len(paired):
        j = i
        while j + 1 < len(paired) and paired[j + 1][0] == paired[i][0]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    sum_ranks_pos = sum(r for r, (_, y) in zip(ranks, paired, strict=True) if y == 1)
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def brier_score(
    confidences: Sequence[float],
    labels: Sequence[int],
) -> float:
    """Mean squared error between confidence and binary label.

    Matches ``training/learned_router.py:37-43``.  Returns 0.0 for empty input.
    """
    n = len(confidences)
    if n == 0:
        return 0.0
    return sum((c - y) ** 2 for c, y in zip(confidences, labels, strict=True)) / n
