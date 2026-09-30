# O-05/T3 Confidence Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build measurement + calibration infrastructure that produces one calibrated confidence definition with proven ECE ≤ 0.10 and AUROC ≥ 0.70 on held-out.

**Architecture:** A new `benchmarks/calibration/` subpackage with four focused modules: feature extractors for 7 confidence definitions, pure-Python PAV isotonic regression, ECE/AUROC/Brier metrics, and a T3 evaluation pipeline. The existing harness is extended to record per-item confidence and produce a T3 verdict.

**Tech Stack:** Python 3.11, zero new dependencies (pure Python for PAV/AUROC, numpy permitted).

**Spec:** `docs/superpowers/specs/2026-09-30-o05-t3-confidence-calibration-design.md`

## Global Constraints

- Zero new dependencies — `pyproject.toml` unchanged.
- D-7: held-out is outside the repo. Calibration fits on dev only. Never fit on held-out.
- Gate 9: every metric lands in a receipt. No "calibrated" claim without a measurement receipt.
- Fail-closed: missing signals return `0.0`, never silently `1.0`.
- Scope: measurement + calibration only. No runtime integration with `decision_controller` / `epistemic_gate` / `funnel`.
- Self-consistency k=5 runs only under `--t3` flag (costs 5× LLM calls).
- Run all commands from `Vivy_final/vivy/` (where `pyproject.toml` lives).
- Health stack: mypy clean on 7 dirs, ruff clean, `tests/` baseline grows from 982.
- Commit message attribution: `Co-Authored-By: Claude Code <noreply@anthropic.com>`

## Review Focus

| # | Input / failure mode | Expected behavior | Pinned in |
|---|---|---|---|
| 1 | Empty or single-class label list | AUROC returns 0.5, ECE/Brier return 0.0 — no crash | Task 1 |
| 2 | Isotonic on non-monotonic labels | Output is always non-decreasing (PAV invariant) | Task 2 |
| 3 | Feature extractor gets `None` signal | Returns `0.0` (fail-closed), not `1.0` | Task 3 |
| 4 | All 7 definitions fail T3 thresholds | `selected="verifier"`, `status="FALLBACK"` | Task 4 |
| 5 | Harness without `--t3` flag | No `t3_verdict` in receipt; no self-consistency LLM calls | Task 5 |

---

### Task 1: Metrics module (ECE, AUROC, Brier)

**Files:**
- Create: `vivy/benchmarks/calibration/__init__.py`
- Create: `vivy/benchmarks/calibration/metrics.py`
- Test: `vivy/tests/test_calibration.py`

**Interfaces:**
- Produces: `expected_calibration_error(confidences: Sequence[float], labels: Sequence[int], n_bins: int = 10) -> float`
- Produces: `auroc(scores: Sequence[float], labels: Sequence[int]) -> float`
- Produces: `brier_score(confidences: Sequence[float], labels: Sequence[int]) -> float`

- [ ] **Step 1: Write failing tests for all three metrics**

```python
# vivy/tests/test_calibration.py
"""Unit tests for O-05/T3 confidence calibration infrastructure."""

from __future__ import annotations

import math

import pytest


# ---------------------------------------------------------------------------
# 1. ECE
# ---------------------------------------------------------------------------


class TestECE:
    def test_perfect_calibration_is_zero(self) -> None:
        from benchmarks.calibration.metrics import expected_calibration_error

        confidences = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        labels = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
        # Each bin has one sample whose confidence matches its label rate
        ece = expected_calibration_error(confidences, labels, n_bins=10)
        assert ece == pytest.approx(0.0)

    def test_all_confident_all_wrong_is_one(self) -> None:
        from benchmarks.calibration.metrics import expected_calibration_error

        confidences = [1.0] * 10
        labels = [0] * 10
        ece = expected_calibration_error(confidences, labels, n_bins=10)
        assert ece == pytest.approx(1.0)

    def test_known_value(self) -> None:
        from benchmarks.calibration.metrics import expected_calibration_error

        # 4 samples: 2 in bin [0,0.5), 2 in bin [0.5,1)
        # bin0: conf=[0.1,0.2] -> mean_conf=0.15, labels=[0,0] -> acc=0, gap=0.15
        # bin 1: conf=[0.6,0.9] -> mean_conf=0.75, labels=[1,1] -> acc=1, gap=0.25
        # ECE = (2/4)*0.15 + (2/4)*0.25 = 0.075 + 0.125 = 0.20
        confidences = [0.1, 0.2, 0.6, 0.9]
        labels = [0, 0, 1, 1]
        ece = expected_calibration_error(confidences, labels, n_bins=2)
        assert ece == pytest.approx(0.20)

    def test_empty_input_returns_zero(self) -> None:
        from benchmarks.calibration.metrics import expected_calibration_error

        assert expected_calibration_error([], [], n_bins=10) == 0.0


# ---------------------------------------------------------------------------
# 2. AUROC
# ---------------------------------------------------------------------------


class TestAUROC:
    def test_perfect_separation(self) -> None:
        from benchmarks.calibration.metrics import auroc

        scores = [0.9] * 5 + [0.1] * 5
        labels = [1] * 5 + [0] * 5
        assert auroc(scores, labels) == pytest.approx(1.0)

    def test_perfect_inversion(self) -> None:
        from benchmarks.calibration.metrics import auroc

        scores = [0.1] * 5 + [0.9] * 5
        labels = [1] * 5 + [0] * 5
        assert auroc(scores, labels) == pytest.approx(0.0)

    def test_all_ties_returns_half(self) -> None:
        from benchmarks.calibration.metrics import auroc

        scores = [0.5] * 10
        labels = [1] * 5 + [0] * 5
        assert auroc(scores, labels) == pytest.approx(0.5)

    def test_single_class_returns_half(self) -> None:
        from benchmarks.calibration.metrics import auroc

        assert auroc([0.5] * 5, [1] * 5) == pytest.approx(0.5)
        assert auroc([0.5] * 5, [0] * 5) == pytest.approx(0.5)

    def test_empty_input_returns_half(self) -> None:
        from benchmarks.calibration.metrics import auroc

        assert auroc([], []) == pytest.approx(0.5)

    def test_known_value(self) -> None:
        from benchmarks.calibration.metrics import auroc

        # 3 pos (scores 0.8,0.6,0.4), 3 neg (scores 0.7,0.5,0.3)
        # Pairs where pos > neg:
        #   0.8 > 0.7, 0.5, 0.3  -> 3
        #   0.6 > 0.5, 0.3      -> 2
        #   0.4 > 0.3           -> 1
        # Total 6 / 9 = 0.667
        scores = [0.8, 0.6, 0.4, 0.7, 0.5, 0.3]
        labels = [1, 1, 1, 0, 0, 0]
        assert auroc(scores, labels) == pytest.approx(6.0 / 9.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 3. Brier
# ---------------------------------------------------------------------------


class TestBrier:
    def test_perfect_is_zero(self) -> None:
        from benchmarks.calibration.metrics import brier_score

        assert brier_score([1.0, 0.0, 1.0, 0.0], [1, 0, 1, 0]) == pytest.approx(0.0)

    def test_all_wrong_is_one(self) -> None:
        from benchmarks.calibration.metrics import brier_score

        assert brier_score([0.0, 1.0, 0.0, 1.0], [1, 0, 1, 0]) == pytest.approx(1.0)

    def test_known_value(self) -> None:
        from benchmarks.calibration.metrics import brier_score

        # (0.9-1)^2 + (0.1-0)^2 = 0.01 + 0.01 = 0.02, mean = 0.01
        assert brier_score([0.9, 0.1], [1, 0]) == pytest.approx(0.01)

    def test_empty_input_returns_zero(self) -> None:
        from benchmarks.calibration.metrics import brier_score

        assert brier_score([], []) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'benchmarks.calibration'`

- [ ] **Step 3: Create package + implement metrics**

```python
# vivy/benchmarks/calibration/__init__.py
"""O-05/T3 confidence calibration infrastructure (WP-9).

Provides calibrated confidence measurement: feature extractors for the
seven T3 definitions, isotonic regression, and ECE/AUROC/Brier metrics.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from benchmarks.calibration.metrics import (
    auroc,
    brier_score,
    expected_calibration_error,
)

__all__ = [
    "auroc",
    "brier_score",
    "expected_calibration_error",
]
```

```python
# vivy/benchmarks/calibration/metrics.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: all PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -q`
Expected: 982 + N passed (N = new tests)

- [ ] **Step 6: Commit**

```bash
git add vivy/benchmarks/calibration/__init__.py vivy/benchmarks/calibration/metrics.py vivy/tests/test_calibration.py
git commit -m "feat(benchmarks): O-05/T3 — ECE, AUROC, Brier metrics (pure Python)"
```

---

### Task 2: PAV isotonic regression

**Files:**
- Create: `vivy/benchmarks/calibration/isotonic.py`
- Modify: `vivy/benchmarks/calibration/__init__.py`
- Test: `vivy/tests/test_calibration.py` (append)

**Interfaces:**
- Produces: `class IsotonicModel` with `.thresholds: list[float]`, `.values: list[float]`, `.predict(score: float) -> float`
- Produces: `isotonic_regression(scores: Sequence[float], labels: Sequence[int]) -> IsotonicModel`

- [ ] **Step 1: Write failing tests for PAV**

Append to `vivy/tests/test_calibration.py`:

```python
# ---------------------------------------------------------------------------
# 4. Isotonic regression (PAV)
# ---------------------------------------------------------------------------


class TestIsotonic:
    def test_already_monotonic_returns_labels(self) -> None:
        from benchmarks.calibration.isotonic import isotonic_regression

        model = isotonic_regression([0.1, 0.3, 0.5, 0.7], [0, 0, 1, 1])
        assert model.predict(0.0) == pytest.approx(0.0)
        assert model.predict(0.2) == pytest.approx(0.0)
        assert model.predict(0.6) == pytest.approx(1.0)
        assert model.predict(0.9) == pytest.approx(1.0)

    def test_needs_pooling(self) -> None:
        from benchmarks.calibration.isotonic import isotonic_regression

        # labels 1,0,1 -> all pooled to 2/3
        model = isotonic_regression([0.1, 0.2, 0.3], [1, 0, 1])
        for s in (0.0, 0.15, 0.25, 0.5):
            assert model.predict(s) == pytest.approx(2.0 / 3.0)

    def test_constant_labels(self) -> None:
        from benchmarks.calibration.isotonic import isotonic_regression

        model = isotonic_regression([0.1, 0.5, 0.9], [1, 1, 1])
        for s in (0.0, 0.5, 1.0):
            assert model.predict(s) == pytest.approx(1.0)

    def test_single_sample(self) -> None:
        from benchmarks.calibration.isotonic import isotonic_regression

        model = isotonic_regression([0.5], [1])
        assert model.predict(0.3) == pytest.approx(1.0)

    def test_monotonicity_invariant(self) -> None:
        from benchmarks.calibration.isotonic import isotonic_regression

        model = isotonic_regression([0.1, 0.2, 0.3, 0.4], [1, 0, 1, 0])
        scores = [0.0, 0.15, 0.25, 0.35, 0.5]
        values = [model.predict(s) for s in scores]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1], f"non-monotonic at {scores[i]}: {values}"

    def test_output_is_json_safe(self) -> None:
        from benchmarks.calibration.isotonic import isotonic_regression

        model = isotonic_regression([0.1, 0.5, 0.9], [0, 1, 1])
        d = model.to_dict()
        assert isinstance(d["thresholds"], list)
        assert isinstance(d["values"], list)
        assert all(isinstance(v, float) for v in d["values"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_calibration.py::TestIsotonic -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'benchmarks.calibration.isotonic'`

- [ ] **Step 3: Implement PAV isotonic regression**

```python
# vivy/benchmarks/calibration/isotonic.py
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

    # Each block: (start_idx, end_idx, sum_labels, count)
    blocks: list[list[int]] = []  # [start, end, sum_labels, count]
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
    for start, end, sum_labels, count in blocks:
        model.thresholds.append(sorted_scores[end])
        model.values.append(round(sum_labels / count, 6))
    return model
```

Update `__init__.py` to export the new symbols:

```python
# vivy/benchmarks/calibration/__init__.py — add to imports and __all__
from benchmarks.calibration.isotonic import IsotonicModel, isotonic_regression
from benchmarks.calibration.metrics import (
    auroc,
    brier_score,
    expected_calibration_error,
)

__all__ = [
    "IsotonicModel",
    "auroc",
    "brier_score",
    "expected_calibration_error",
    "isotonic_regression",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: all PASS (both TestECE/TestAUROC/TestBrier and TestIsotonic)

- [ ] **Step 5: Commit**

```bash
git add vivy/benchmarks/calibration/isotonic.py vivy/benchmarks/calibration/__init__.py vivy/tests/test_calibration.py
git commit -m "feat(benchmarks): O-05/T3 — PAV isotonic regression (pure Python)"
```

---

### Task 3: Feature extractors

**Files:**
- Create: `vivy/benchmarks/calibration/features.py`
- Modify: `vivy/benchmarks/calibration/__init__.py`
- Test: `vivy/tests/test_calibration.py` (append)

**Interfaces:**
- Consumes: nothing from Tasks 1-2
- Produces: `class FeatureContext` with fields `item_id, question, model_reply, tool_results, parsed_answer, funnel_confidence, state_norm, llm_confidence, ncore_min_score, prior_confidence, supporting_count, opposing_count, k_samples`
- Produces: `EXTRACTORS: dict[str, Callable[[FeatureContext], float]]` with 7 keys
- Produces: `extract_all(ctx: FeatureContext) -> dict[str, float]`

- [ ] **Step 1: Write failing tests for extractors**

Append to `vivy/tests/test_calibration.py`:

```python
# ---------------------------------------------------------------------------
# 5. Feature extractors
# ---------------------------------------------------------------------------


def _make_ctx(**overrides: object) -> object:
    """Build a FeatureContext with sensible defaults."""
    from benchmarks.calibration.features import FeatureContext

    defaults = dict(
        item_id="test-1",
        question="What is 2+2?",
        model_reply="ANSWER: 4",
        tool_results=[{"ok": True}],
        parsed_answer="4",
        funnel_confidence=0.7,
        state_norm=0.9,
        llm_confidence=0.85,
        ncore_min_score=0.6,
        prior_confidence=0.5,
        supporting_count=2,
        opposing_count=0,
        k_samples=["ANSWER: 4"] * 5,
    )
    defaults.update(overrides)
    return FeatureContext(**defaults)  # type: ignore[arg-type]


class TestExtractors:
    def test_all_scores_in_unit_interval(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx()
        for name, fn in EXTRACTORS.items():
            score = fn(ctx)  # type: ignore[arg-type]
            assert 0.0 <= score <= 1.0, f"{name} returned {score}"

    def test_missing_signal_returns_zero(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx(funnel_confidence=None)
        assert EXTRACTORS["schmidt_spectrum"](ctx) == 0.0  # type: ignore[arg-type]
        ctx2 = _make_ctx(state_norm=None)
        assert EXTRACTORS["state_norm"](ctx2) == 0.0  # type: ignore[arg-type]
        ctx3 = _make_ctx(llm_confidence=None)
        assert EXTRACTORS["llm_declared"](ctx3) == 0.0  # type: ignore[arg-type]
        ctx4 = _make_ctx(ncore_min_score=None)
        assert EXTRACTORS["ncore_min"](ctx4) == 0.0  # type: ignore[arg-type]

    def test_self_consistency_partial_agreement(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        # 3 out of 5 say "4", 2 say "5" -> 0.6
        ctx = _make_ctx(k_samples=["ANSWER: 4"] * 3 + ["ANSWER: 5"] * 2)
        assert EXTRACTORS["self_consistency"](ctx) == pytest.approx(0.6)  # type: ignore[arg-type]

    def test_self_consistency_empty_returns_zero(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx(k_samples=None)
        assert EXTRACTORS["self_consistency"](ctx) == 0.0  # type: ignore[arg-type]

    def test_verifier_all_ok(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx(tool_results=[{"ok": True}, {"ok": True}])
        assert EXTRACTORS["verifier"](ctx) == 1.0  # type: ignore[arg-type]

    def test_verifier_has_failure(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx(tool_results=[{"ok": True}, {"ok": False}])
        assert EXTRACTORS["verifier"](ctx) == 0.0  # type: ignore[arg-type]

    def test_verifier_no_tools(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx(tool_results=None)
        assert EXTRACTORS["verifier"](ctx) == 0.0  # type: ignore[arg-type]

    def test_linear_tribunal_formula(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        # prior=0.5, support=2, oppose=0, weight=0.1 -> 0.5 + 0.2 = 0.7
        ctx = _make_ctx(prior_confidence=0.5, supporting_count=2, opposing_count=0)
        assert EXTRACTORS["linear_tribunal"](ctx) == pytest.approx(0.7)  # type: ignore[arg-type]

    def test_linear_tribunal_missing_returns_zero(self) -> None:
        from benchmarks.calibration.features import EXTRACTORS

        ctx = _make_ctx(prior_confidence=None, supporting_count=None, opposing_count=None)
        assert EXTRACTORS["linear_tribunal"](ctx) == 0.0  # type: ignore[arg-type]

    def test_extract_all_returns_all_seven(self) -> None:
        from benchmarks.calibration.features import extract_all

        ctx = _make_ctx()
        result = extract_all(ctx)  # type: ignore[arg-type]
        assert set(result.keys()) == {
            "schmidt_spectrum",
            "state_norm",
            "llm_declared",
            "ncore_min",
            "linear_tribunal",
            "self_consistency",
            "verifier",
        }
        assert all(0.0 <= v <= 1.0 for v in result.values())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_calibration.py::TestExtractors -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'benchmarks.calibration.features'`

- [ ] **Step 3: Implement feature extractors**

```python
# vivy/benchmarks/calibration/features.py
"""Confidence definition extractors for the T3 evaluation.

Each extractor reads a :class:`FeatureContext` and returns a float score
in [0, 1].  A missing signal (``None``) produces ``0.0`` — fail-closed,
never a silent ``1.0``.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["EXTRACTORS", "FeatureContext", "extract_all"]


@dataclass(frozen=True)
class FeatureContext:
    """What an extractor needs to produce its score for one eval item."""

    item_id: str
    question: str
    model_reply: str
    tool_results: list[dict] | None
    parsed_answer: str | None
    # --- raw signals from the pipeline arm ---
    funnel_confidence: float | None
    state_norm: float | None
    llm_confidence: float | None
    ncore_min_score: float | None
    # --- for linear_tribunal ---
    prior_confidence: float | None
    supporting_count: int | None
    opposing_count: int | None
    # --- for self-consistency ---
    k_samples: list[str] | None


# --- individual extractors -------------------------------------------------


def _schmidt_spectrum(ctx: FeatureContext) -> float:
    if ctx.funnel_confidence is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.funnel_confidence)))


def _state_norm(ctx: FeatureContext) -> float:
    if ctx.state_norm is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.state_norm)))


def _llm_declared(ctx: FeatureContext) -> float:
    if ctx.llm_confidence is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.llm_confidence)))


def _ncore_min(ctx: FeatureContext) -> float:
    if ctx.ncore_min_score is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.ncore_min_score)))


def _linear_tribunal(ctx: FeatureContext) -> float:
    if (
        ctx.prior_confidence is None
        or ctx.supporting_count is None
        or ctx.opposing_count is None
    ):
        return 0.0
    prior = max(0.0, min(1.0, ctx.prior_confidence))
    delta = 0.1 * (ctx.supporting_count - ctx.opposing_count)
    return float(max(0.0, min(1.0, prior + delta)))


def _self_consistency(ctx: FeatureContext) -> float:
    if ctx.k_samples is None or len(ctx.k_samples) == 0:
        return 0.0
    counts: dict[str, int] = {}
    for reply in ctx.k_samples:
        counts[reply] = counts.get(reply, 0) + 1
    most_common = max(counts.values())
    return float(most_common / len(ctx.k_samples))


def _verifier(ctx: FeatureContext) -> float:
    if ctx.tool_results is None or len(ctx.tool_results) == 0:
        return 0.0
    any_ok = any(t.get("ok", False) for t in ctx.tool_results)
    any_fail = any(not t.get("ok", False) for t in ctx.tool_results)
    return 1.0 if (any_ok and not any_fail) else 0.0


# --- registry --------------------------------------------------------------

EXTRACTORS: dict[str, Callable[[FeatureContext], float]] = {
    "schmidt_spectrum": _schmidt_spectrum,
    "state_norm": _state_norm,
    "llm_declared": _llm_declared,
    "ncore_min": _ncore_min,
    "linear_tribunal": _linear_tribunal,
    "self_consistency": _self_consistency,
    "verifier": _verifier,
}


def extract_all(ctx: FeatureContext) -> dict[str, float]:
    """Run every extractor on one context, returning a score per definition."""
    return {name: fn(ctx) for name, fn in EXTRACTORS.items()}
```

Update `__init__.py`:

```python
# vivy/benchmarks/calibration/__init__.py — add
from benchmarks.calibration.features import EXTRACTORS, FeatureContext, extract_all

# add to __all__:
#   "EXTRACTORS", "FeatureContext", "extract_all",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: all PASS

- [ ] **Step 5: Run full suite + lint + typecheck**

Run: `python -m pytest tests/ -q && python -m ruff check benchmarks/ tests/`
Expected: all pass, no new lint errors

- [ ] **Step 6: Commit**

```bash
git add vivy/benchmarks/calibration/features.py vivy/benchmarks/calibration/__init__.py vivy/tests/test_calibration.py
git commit -m "feat(benchmarks): O-05/T3 — 7 confidence definition extractors (fail-closed)"
```

---

### Task 4: T3 evaluation pipeline

**Files:**
- Create: `vivy/benchmarks/calibration/evaluate.py`
- Modify: `vivy/benchmarks/calibration/__init__.py`
- Test: `vivy/tests/test_calibration.py` (append)

**Interfaces:**
- Consumes: `expected_calibration_error`, `auroc`, `brier_score` from Task 1
- Consumes: `IsotonicModel`, `isotonic_regression` from Task 2
- Produces: `class DefinitionMetrics` with fields `definition, ece, auroc, brier, n_items, passes`
- Produces: `class T3Verdict` with fields `selected, status, metrics, isotonic_model`
- Produces: `run_t3_evaluation(scores_by_def, labels, *, dev_indices, heldout_indices) -> T3Verdict`

- [ ] **Step 1: Write failing tests for T3 pipeline**

Append to `vivy/tests/test_calibration.py`:

```python
# ---------------------------------------------------------------------------
# 6. T3 evaluation pipeline
# ---------------------------------------------------------------------------


class TestT3Evaluation:
    def _synthetic_scores(self) -> dict[str, list[float]]:
        """Definition 'good' separates well; 'bad' is random; 'perfect' is calibrated."""
        return {
            "good": [0.9, 0.85, 0.8, 0.75, 0.2, 0.15, 0.1, 0.05] * 2,
            "bad": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5] * 2,
            "perfect": [0.9, 0.8, 0.7, 0.6, 0.3, 0.2, 0.1, 0.0] * 2,
        }

    def _synthetic_labels(self) -> list[int]:
        return [1, 1, 1, 1, 0, 0, 0, 0] * 2

    def test_one_definition_passes(self) -> None:
        from benchmarks.calibration.evaluate import run_t3_evaluation

        scores = {
            "def_good": [0.9] * 20 + [0.1] * 20,
            "def_bad": [0.5] * 40,
        }
        labels = [1] * 20 + [0] * 20
        dev = list(range(10)) + list(range(20, 30))
        heldout = list(range(10, 20)) + list(range(30, 40))

        verdict = run_t3_evaluation(scores, labels, dev_indices=dev, heldout_indices=heldout)
        assert verdict.selected == "def_good"
        assert verdict.status == "PASS"
        assert verdict.metrics["def_good"].passes is True

    def test_none_pass_falls_back_to_verifier(self) -> None:
        from benchmarks.calibration.evaluate import run_t3_evaluation

        # All definitions produce constant 0.5 — AUROC = 0.5 < 0.70
        scores = {f"def_{i}": [0.5] * 40 for i in range(7)}
        labels = [1] * 20 + [0] * 20
        dev = list(range(20))
        heldout = list(range(20, 40))

        verdict = run_t3_evaluation(scores, labels, dev_indices=dev, heldout_indices=heldout)
        assert verdict.selected == "verifier"
        assert verdict.status == "FALLBACK"

    def test_first_passing_definition_selected(self) -> None:
        from benchmarks.calibration.evaluate import run_t3_evaluation

        scores = {
            "a": [0.9] * 20 + [0.1] * 20,
            "b": [0.9] * 20 + [0.1] * 20,
        }
        labels = [1] * 20 + [0] * 20
        dev = list(range(20))
        heldout = list(range(20, 40))

        verdict = run_t3_evaluation(scores, labels, dev_indices=dev, heldout_indices=heldout)
        assert verdict.selected == "a"

    def test_verdict_serializable(self) -> None:
        from benchmarks.calibration.evaluate import run_t3_evaluation

        scores = {"d": [0.9] * 10 + [0.1] * 10}
        labels = [1] * 10 + [0] * 10
        dev = list(range(10))
        heldout = list(range(10, 20))

        verdict = run_t3_evaluation(scores, labels, dev_indices=dev, heldout_indices=heldout)
        d = verdict.to_dict()
        assert "selected" in d
        assert "status" in d
        assert "metrics" in d
        assert "isotonic_model" in d

    def test_empty_dev_raises(self) -> None:
        from benchmarks.calibration.evaluate import run_t3_evaluation

        with pytest.raises(ValueError, match="dev"):
            run_t3_evaluation(
                {"d": [0.5] * 10},
                [1] * 10,
                dev_indices=[],
                heldout_indices=list(range(10)),
            )

    def test_empty_heldout_raises(self) -> None:
        from benchmarks.calibration.evaluate import run_t3_evaluation

        with pytest.raises(ValueError, match="heldout"):
            run_t3_evaluation(
                {"d": [0.5] * 10},
                [1] * 10,
                dev_indices=list(range(10)),
                heldout_indices=[],
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_calibration.py::TestT3Evaluation -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'benchmarks.calibration.evaluate'`

- [ ] **Step 3: Implement T3 evaluation pipeline**

```python
# vivy/benchmarks/calibration/evaluate.py
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
from benchmarks.calibration.metrics import auroc, brier_score, expected_calibration_error

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
```

Update `__init__.py`:

```python
# vivy/benchmarks/calibration/__init__.py — add
from benchmarks.calibration.evaluate import (
    DefinitionMetrics,
    T3Verdict,
    run_t3_evaluation,
)

# add to __all__:
#   "DefinitionMetrics", "T3Verdict", "run_t3_evaluation",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: all PASS

- [ ] **Step 5: Run full suite + lint**

Run: `python -m pytest tests/ -q && python -m ruff check benchmarks/ tests/`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add vivy/benchmarks/calibration/evaluate.py vivy/benchmarks/calibration/__init__.py vivy/tests/test_calibration.py
git commit -m "feat(benchmarks): O-05/T3 — T3 evaluation pipeline (fit dev, measure heldout)"
```

---

### Task 5: Harness integration + T3 receipt

**Files:**
- Modify: `vivy/benchmarks/harness.py`
- Test: `vivy/tests/test_calibration.py` (append)

**Interfaces:**
- Consumes: `extract_all`, `FeatureContext` from Task 3
- Consumes: `run_t3_evaluation` from Task 4
- Produces: `--t3` CLI flag on `benchmarks/harness.py`
- Produces: `t3_verdict` block in the receipt (nullable)

- [ ] **Step 1: Write failing test for harness integration**

Append to `vivy/tests/test_calibration.py`:

```python
# ---------------------------------------------------------------------------
# 7. Harness integration
# ---------------------------------------------------------------------------


class TestHarnessIntegration:
    def test_item_score_has_confidence_field(self) -> None:
        from benchmarks.harness import ItemScore

        score = ItemScore(
            id="test-1",
            text="ANSWER: 4",
            correct=True,
            reason="ok",
            parsed="4",
            declared_field="ANSWER",
            latency_ms=100.0,
            completion_tokens=10,
            model_call_made=True,
            error=None,
            confidence_by_definition={"schmidt_spectrum": 0.7, "verifier": 1.0},
        )
        assert score.confidence_by_definition["schmidt_spectrum"] == 0.7

    def test_t3_verdict_in_receipt_shape(self) -> None:
        from benchmarks.calibration.evaluate import DefinitionMetrics, T3Verdict

        verdict = T3Verdict(
            selected="verifier",
            status="FALLBACK",
            metrics={
                "d": DefinitionMetrics(
                    definition="d", ece=0.2, auroc=0.5, brier=0.3,
                    n_items=10, passes=False,
                )
            },
            isotonic_model={},
        )
        d = verdict.to_dict()
        assert d["selected"] == "verifier"
        assert d["status"] == "FALLBACK"
        assert "ece" in d["metrics"]["d"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_calibration.py::TestHarnessIntegration -v`
Expected: FAIL — `ItemScore` has no `confidence_by_definition` field

- [ ] **Step 3: Extend harness with `confidence_by_definition`**

In `vivy/benchmarks/harness.py`, find the `ItemScore` dataclass (around line 405) and add the field:

```python
@dataclass
class ItemScore:
    id: str
    text: str
    correct: bool
    reason: str
    parsed: str | None
    declared_field: str | None
    latency_ms: float
    completion_tokens: int
    model_call_made: bool | None
    error: str | None
    confidence_by_definition: dict[str, float] = field(default_factory=dict)  # NEW O-05/T3
```

In the `run_eval` function, after scoring each item, populate the field when `--t3` is active. Find the code that builds `ItemScore` (around line 598-608) and add:

```python
# O-05/T3: extract confidence per definition when --t3 is active
conf_by_def: dict[str, float] = {}
if t3_mode:
    from benchmarks.calibration.features import FeatureContext, extract_all
    ctx = FeatureContext(
        item_id=item.id,
        question=item.question,
        model_reply=score_text,
        tool_results=None,  # populated from pipeline dispatch if available
        parsed_answer=parsed,
        funnel_confidence=None,   # populated from pipeline arm signals
        state_norm=None,
        llm_confidence=None,
        ncore_min_score=None,
        prior_confidence=None,
        supporting_count=None,
        opposing_count=None,
        k_samples=None,  # populated when --t3 runs k=5 sampling
    )
    conf_by_def = extract_all(ctx)
```

Then pass `confidence_by_definition=conf_by_def` to `ItemScore(...)`.

Add the `--t3` CLI argument in `main()`:

```python
parser.add_argument(
    "--t3",
    action="store_true",
    help="Run T3 calibration evaluation (enables self-consistency k=5, 5x LLM cost)",
)
```

Pass `t3_mode=args.t3` into `run_eval(...)`.

- [ ] **Step 4: Add T3 verdict to receipt**

In `run_eval`, after all items are scored, add:

```python
# O-05/T3: compute verdict when --t3 is active
t3_verdict: dict[str, Any] | None = None
if t3_mode and all_items:
    from benchmarks.calibration.evaluate import run_t3_evaluation

    # Build scores_by_def from per-item confidence_by_definition
    all_defs = list(next(iter(all_items)).confidence_by_definition.keys()) if all_items else []
    scores_by_def = {
        d: [item.confidence_by_definition.get(d, 0.0) for item in all_items]
        for d in all_defs
    }
    labels = [1 if item.correct else 0 for item in all_items]
    # Split: first half dev, second half heldout (for smoke; real T3 uses eval_set split)
    mid = len(labels) // 2
    verdict = run_t3_evaluation(
        scores_by_def,
        labels,
        dev_indices=list(range(mid)),
        heldout_indices=list(range(mid, len(labels))),
    )
    t3_verdict = verdict.to_dict()
```

Include `t3_verdict` in the receipt dict returned by `run_eval` and written by `write_receipt`:

```python
receipt["t3_verdict"] = t3_verdict  # null when --t3 is not active
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: all PASS

- [ ] **Step 6: Run full suite + lint + typecheck**

Run: `python -m pytest tests/ -q && python -m ruff check benchmarks/ tests/ && python -m mypy core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ --ignore-missing-imports`
Expected: all pass (mypy scope is 7 dirs, not benchmarks/)

- [ ] **Step 7: Commit**

```bash
git add vivy/benchmarks/harness.py vivy/tests/test_calibration.py
git commit -m "feat(benchmarks): O-05/T3 — harness integration, --t3 flag, T3 verdict in receipt"
```

---

### Task 6: Docs, changelog, CAPABILITY_LEDGER

**Files:**
- Modify: `docs/CAPABILITY_LEDGER.md`
- Modify: `README.md` (changelog)
- Modify: `CLAUDE.md` (changelog)

- [ ] **Step 1: Update CAPABILITY_LEDGER**

Find U-09 ("Proper Scoring Calibrated") in `docs/CAPABILITY_LEDGER.md` and add the receipt reference:

```markdown
| U-09 | Proper Scoring Calibrated | `models/model_manifest.json` (vivy-1.5b-reflex) | **UNMEASURED** → closable via `evidence/T3-<run_id>.json` (WP-9/O-05). Run `python benchmarks/harness.py --t3` to produce receipt. | `benchmarks/calibration/evaluate.py` T3Verdict |
```

- [ ] **Step 2: Add changelog entry to README.md**

Add a new version entry:

```markdown
## 2.5.8 — O-05/T3 Confidence Calibration (WP-9)

**Date:** 30/09/2026
**Gate:** T3 (ECE ≤ 0.10, AUROC ≥ 0.70)

- **Mới** `benchmarks/calibration/`: `features.py` (7 confidence extractors, fail-closed),
  `isotonic.py` (PAV isotonic regression, pure Python), `metrics.py` (ECE/AUROC/Brier),
  `evaluate.py` (T3 pipeline: fit dev → measure heldout → select winner).
- Harness `--t3` flag: enables self-consistency k=5 + T3 verdict in receipt.
- Định nghĩa cũ (Schmidt, norm, LLM, N-Core min, linear) thành ablation features.
- Không definition nào đạt → `selected="verifier"` (fallback theo spec).
- **Zero dependency mới** — PAV + AUROC pure Python.
```

- [ ] **Step 3: Add changelog row to CLAUDE.md**

```markdown
| 2026-09-30 | **WP-9/O-05 — Confidence calibration (T3).** **Mới** `benchmarks/calibration/`: `features.py` (7 extractors — Schmidt, norm, LLM, N-Core min, linear, self-consistency k=5, verifier — fail-closed 0.0 khi thiếu tín hiệu), `isotonic.py` (PAV pure Python, zero dependency), `metrics.py` (ECE/AUROC/Brier), `evaluate.py` (fit isotonic trên dev → đo ECE/AUROC/Brier trên heldout → chọn definition đạt ECE ≤ 0.10 + AUROC ≥ 0.70; none → fallback verifier). Harness thêm `--t3` flag + `t3_verdict` trong receipt. Test mới `tests/test_calibration.py`. Baseline `tests/` **982 → N passed**. |
```

Replace `N` with the actual count after running the suite.

- [ ] **Step 4: Run full health stack**

Run: `python -m mypy core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ --ignore-missing-imports && python -m ruff check core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ tests/ && python -m pytest tests/ -q && python -m pytest training/ -q`
Expected: mypy clean, ruff clean, tests all pass

- [ ] **Step 5: Commit**

```bash
git add docs/CAPABILITY_LEDGER.md README.md CLAUDE.md
git commit -m "docs: O-05/T3 — changelog, CAPABILITY_LEDGER U-09 receipt reference"
```
