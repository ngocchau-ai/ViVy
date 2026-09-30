"""Unit tests for O-05/T3 confidence calibration infrastructure."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. ECE
# ---------------------------------------------------------------------------


class TestECE:
    def test_perfect_calibration_is_zero(self) -> None:
        from benchmarks.calibration.metrics import expected_calibration_error

        # Perfect calibration: predicted confidence matches empirical accuracy
        # bin 0 (conf=0.3): 10 samples, 3 correct → acc=0.3
        # bin 1 (conf=0.7): 10 samples, 7 correct → acc=0.7
        confidences = [0.3] * 10 + [0.7] * 10
        labels = [1] * 3 + [0] * 7 + [1] * 7 + [0] * 3
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

        # bin 0: conf=[0.1,0.2] -> mean_conf=0.15, labels=[0,0] -> acc=0, gap=0.15
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

        # 3 pos (0.8,0.6,0.4), 3 neg (0.7,0.5,0.3)
        # P(pos > neg): 0.8>0.7,0.5,0.3 (3); 0.6>0.5,0.3 (2); 0.4>0.3 (1) = 6/9
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

        # labels 1,0,1 -> PAV merges first two (1>0) to [0.5,0.5,1.0]
        # error: 0.25+0.25+0 = 0.5 (lower than all-pooled 2/3 = 0.667)
        model = isotonic_regression([0.1, 0.2, 0.3], [1, 0, 1])
        assert model.predict(0.0) == pytest.approx(0.5)
        assert model.predict(0.15) == pytest.approx(0.5)
        assert model.predict(0.25) == pytest.approx(1.0)
        assert model.predict(0.5) == pytest.approx(1.0)

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
