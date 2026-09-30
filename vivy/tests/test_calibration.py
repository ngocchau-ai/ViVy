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


# ---------------------------------------------------------------------------
# 6. T3 evaluation pipeline
# ---------------------------------------------------------------------------


class TestT3Evaluation:
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
        # Interleave: dev gets 10 pos + 10 neg, heldout gets 10 pos + 10 neg
        dev = list(range(10)) + list(range(20, 30))
        heldout = list(range(10, 20)) + list(range(30, 40))

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


# ---------------------------------------------------------------------------
# 7. Harness integration
# ---------------------------------------------------------------------------


class TestHarnessIntegration:
    def test_item_score_has_confidence_field(self) -> None:
        from benchmarks.harness import ItemScore

        score = ItemScore(
            id="test-1",
            domain="arith",
            kind="exact",
            expected="4",
            expected_kind="string",
            confidence_by_definition={"schmidt_spectrum": 0.7, "verifier": 1.0},
        )
        assert score.confidence_by_definition["schmidt_spectrum"] == 0.7
        assert score.confidence_by_definition["verifier"] == 1.0

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


class TestHarnessT3Labels:
    def test_label_uses_named_arm_not_any_arm(self) -> None:
        """T3 label must reflect the named arm's correctness, not 'any arm'.

        If baseline is correct but pipeline is wrong, label must be 0 —
        T3 calibrates the pipeline's confidence against the pipeline's outcome.
        """
        from benchmarks.harness import ItemScore, t3_correctness_labels

        s = ItemScore(
            id="x", domain="d", kind="k", expected="1", expected_kind="number",
            arms={
                "baseline": {"correct": True},
                "pipeline": {"correct": False},
            },
        )
        labels = t3_correctness_labels([s], arm="pipeline")
        assert labels == [0], (
            "label must be pipeline correctness (0), not any-arm (would be 1)"
        )

    def test_label_uses_named_arm_when_correct(self) -> None:
        from benchmarks.harness import ItemScore, t3_correctness_labels

        s = ItemScore(
            id="x", domain="d", kind="k", expected="1", expected_kind="number",
            arms={
                "baseline": {"correct": False},
                "pipeline": {"correct": True},
            },
        )
        labels = t3_correctness_labels([s], arm="pipeline")
        assert labels == [1]

    def test_label_missing_arm_defaults_zero(self) -> None:
        from benchmarks.harness import ItemScore, t3_correctness_labels

        s = ItemScore(
            id="x", domain="d", kind="k", expected="1", expected_kind="number",
            arms={"baseline": {"correct": True}},
        )
        labels = t3_correctness_labels([s], arm="pipeline")
        assert labels == [0], "missing arm must be 0 (fail-closed)"
