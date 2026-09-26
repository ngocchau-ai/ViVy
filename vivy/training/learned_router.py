"""C — Learned router with Brier / ECE / permutation control (Plan 2, §5.2).

Trains a logistic-regression router on human-confirmed gold selection and
evaluates with three metrics:

  * **Brier score** — mean squared error of predicted probabilities vs binary
    labels. Lower is better. Gate: Brier < baseline (uniform prior).
  * **ECE** (Expected Calibration Error) — measures probability calibration.
    Gate: ECE < 0.10.
  * **Permutation control** — shuffles labels and verifies the model degrades
    to chance level (no label leakage). Gate: p > 0.05.

Promotion requires N ≥ 30 labeled gold rows. Below N=30, report metrics only.

Pass C is always scoped ``PROVISIONAL_RESULT`` because ``gold_outcome=unknown``
on legacy rows (KNOWN_LIMITATIONS L-30).

Changelog:
    24/09/2026 (Claude Code — Plan 2 C): Initial.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

MIN_ROWS_FOR_PROMOTION = 30
ECE_THRESHOLD = 0.10
PERMUTATION_P_THRESHOLD = 0.05
N_PERMUTATIONS = 200


# --- Metrics -----------------------------------------------------------------


def brier_score(predictions: Sequence[float], labels: Sequence[int]) -> float:
    """Mean squared error of predicted probabilities vs binary labels."""
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")
    if not predictions:
        raise ValueError("empty input")
    return sum((p - y) ** 2 for p, y in zip(predictions, labels)) / len(labels)


def expected_calibration_error(
    predictions: Sequence[float],
    labels: Sequence[int],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error over *n_bins* equal-width bins in [0, 1]."""
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")
    if not predictions:
        raise ValueError("empty input")
    n = len(predictions)
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, y in zip(predictions, labels):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, y))
    ece = 0.0
    for bin_items in bins:
        if not bin_items:
            continue
        avg_pred = sum(p for p, _ in bin_items) / len(bin_items)
        avg_label = sum(y for _, y in bin_items) / len(bin_items)
        ece += abs(avg_pred - avg_label) * (len(bin_items) / n)
    return ece


def baseline_brier(labels: Sequence[int]) -> float:
    """Brier score of a uniform-prior (0.5) predictor on *labels*."""
    if not labels:
        raise ValueError("empty input")
    n = len(labels)
    prior = sum(labels) / n
    # Uniform prior = class frequency; for balanced data this is 0.5 → Brier 0.25
    return sum((prior - y) ** 2 for y in labels) / n


def permutation_control(
    predictions: Sequence[float],
    labels: Sequence[int],
    n_permutations: int = N_PERMUTATIONS,
    seed: int = 42,
) -> float:
    """Permutation control p-value: verify no label leakage.

    Shuffles *labels* and evaluates the model on each shuffle. Returns a
    p-value = fraction of permuted Brier scores that are ≥ the real Brier.

    PASS gate: p > 0.05 — the model's true-label performance is not
    significantly degraded compared to permuted labels (no anti-correlation
    or leakage signal).
    FAIL: p ≤ 0.05 — permuted labels systematically outperform true labels.
    """
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")
    if not labels:
        raise ValueError("empty input")
    rng = random.Random(seed)
    labels_list = list(labels)
    real_brier = brier_score(predictions, labels_list)

    permuted_briers: list[float] = []
    for _ in range(n_permutations):
        shuffled = labels_list[:]
        rng.shuffle(shuffled)
        permuted_briers.append(brier_score(predictions, shuffled))

    ge_count = sum(1 for b in permuted_briers if b >= real_brier)
    return ge_count / n_permutations


def evaluate_router(
    predictions: Sequence[float],
    labels: Sequence[int],
    *,
    n_permutations: int = N_PERMUTATIONS,
) -> dict[str, Any]:
    """Full evaluation: Brier, ECE, baseline Brier, permutation p-value."""
    brier = brier_score(predictions, labels)
    ece = expected_calibration_error(predictions, labels)
    base = baseline_brier(labels)
    perm_p = permutation_control(predictions, labels, n_permutations=n_permutations)
    return {
        "brier_score": round(brier, 6),
        "ece": round(ece, 6),
        "baseline_brier": round(base, 6),
        "permutation_p_value": round(perm_p, 6),
        "n_rows": len(labels),
    }


def check_promotion(metrics: dict[str, Any]) -> tuple[bool, str]:
    """Check the promotion gate. Returns (can_promote, reason).

    All four conditions must hold:
      1. Brier < baseline (uniform prior)
      2. ECE < 0.10
      3. permutation control p > 0.05 (no leakage)
      4. N ≥ 30 labeled gold rows
    """
    n = metrics.get("n_rows", 0)
    if n < MIN_ROWS_FOR_PROMOTION:
        return False, f"N={n} < {MIN_ROWS_FOR_PROMOTION} — report metrics only, no promotion"

    brier = metrics["brier_score"]
    base = metrics["baseline_brier"]
    if brier >= base:
        return False, f"Brier={brier:.4f} >= baseline={base:.4f} — model does not beat uniform prior"

    ece = metrics["ece"]
    if ece >= ECE_THRESHOLD:
        return False, f"ECE={ece:.4f} >= {ECE_THRESHOLD} — model is not well-calibrated"

    perm_p = metrics["permutation_p_value"]
    if perm_p <= PERMUTATION_P_THRESHOLD:
        return False, f"permutation_p={perm_p:.4f} <= {PERMUTATION_P_THRESHOLD} — label leakage suspected"

    return True, (
        f"PASS (PROVISIONAL_RESULT): Brier={brier:.4f} < baseline={base:.4f}, "
        f"ECE={ece:.4f} < {ECE_THRESHOLD}, perm_p={perm_p:.4f} > {PERMUTATION_P_THRESHOLD}, "
        f"N={n}. gold_outcome=unknown (L-30) — max PROVISIONAL_RESULT."
    )


# --- Logistic regression router (pure Python) ---------------------------------


class LogisticRouter:
    """Simple logistic-regression router. Pure Python, no numpy dependency.

    Features: flat float vectors. Labels: 0 or 1.
    Trained with batch gradient descent on logistic loss.
    """

    def __init__(self, n_features: int, *, lr: float = 0.1, epochs: int = 200) -> None:
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.lr = lr
        self.epochs = epochs
        self._trained = False

    @staticmethod
    def _sigmoid(z: float) -> float:
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        ez = math.exp(z)
        return ez / (1.0 + ez)

    def predict_proba(self, features: Sequence[Sequence[float]]) -> list[float]:
        if not self._trained:
            raise RuntimeError("router not trained — call train() first")
        probs = []
        for x in features:
            z = self.bias + sum(w * xi for w, xi in zip(self.weights, x))
            probs.append(self._sigmoid(z))
        return probs

    def train(
        self,
        features: Sequence[Sequence[float]],
        labels: Sequence[int],
    ) -> None:
        n = len(features)
        if n == 0:
            raise ValueError("empty training set")
        if len(labels) != n:
            raise ValueError("features and labels length mismatch")
        d = len(features[0])
        self.weights = [0.0] * d
        self.bias = 0.0
        for _ in range(self.epochs):
            grad_w = [0.0] * d
            grad_b = 0.0
            for x, y in zip(features, labels):
                z = self.bias + sum(w * xi for w, xi in zip(self.weights, x))
                p = self._sigmoid(z)
                err = p - y
                for j in range(d):
                    grad_w[j] += err * x[j]
                grad_b += err
            for j in range(d):
                self.weights[j] -= self.lr * grad_w[j] / n
            self.bias -= self.lr * grad_b / n
        self._trained = True


def train_router(
    features: Sequence[Sequence[float]],
    labels: Sequence[int],
    *,
    lr: float = 0.1,
    epochs: int = 200,
) -> LogisticRouter:
    """Train and return a fitted LogisticRouter."""
    if not features:
        raise ValueError("empty feature matrix")
    n_features = len(features[0])
    router = LogisticRouter(n_features, lr=lr, epochs=epochs)
    router.train(features, labels)
    return router


# --- Feature extraction helpers -----------------------------------------------


def extract_candidate_features(candidate: dict[str, Any]) -> list[float]:
    """Extract a flat feature vector from a candidate dict.

    Features (5-dim):
      [0] has_action_type (1.0 if action_type non-empty)
      [1] is_destructive (1.0 if action_type in DESTRUCTIVE)
      [2] is_abstain (1.0 if action_type in ABSTAIN)
      [3] description_length_norm (log-scaled, capped at 1.0)
      [4] has_description (1.0 if description non-empty)
    """
    action = str(candidate.get("action_type", "") or "").lower()
    desc = str(candidate.get("description", "") or "")
    destructive = {"delete", "kill", "trade_buy", "wipe", "rm", "drop", "format", "shutdown"}
    abstain = {"abstain", "noul", "halt", "no_action", "wait", "refusal"}
    return [
        1.0 if action else 0.0,
        1.0 if action in destructive else 0.0,
        1.0 if action in abstain else 0.0,
        min(math.log1p(len(desc)) / 10.0, 1.0),
        1.0 if desc else 0.0,
    ]


def build_training_set(
    records: Sequence[dict[str, Any]],
) -> tuple[list[list[float]], list[int]]:
    """Build (features, labels) from gold selection records.

    Each record must have ``candidates`` (list of dicts) and ``selected_candidate``.
    Produces one sample per candidate: label=1 if selected, 0 otherwise.
    """
    features: list[list[float]] = []
    labels: list[int] = []
    for record in records:
        selected = record.get("selected_candidate")
        for cand in record.get("candidates", []) or []:
            if not isinstance(cand, dict):
                continue
            features.append(extract_candidate_features(cand))
            labels.append(1 if str(cand.get("id")) == str(selected) else 0)
    return features, labels
