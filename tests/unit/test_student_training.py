"""Unit tests for Stage 7 Student Model proposal engine and latency evaluator."""

from __future__ import annotations

import pytest

from nps_core.model_training import (
    LatencyEvaluator,
    ModelTrainingError,
    StudentProposalEngine,
    StudentTrainingConfig,
)


def test_student_training_config() -> None:
    cfg = StudentTrainingConfig("student-1b", 32, 1e-4, 512)
    assert cfg.model_name == "student-1b"

    with pytest.raises(ModelTrainingError, match="batch_size must be positive"):
        StudentTrainingConfig("student-1b", -1, 1e-4, 512)


def test_student_proposal_engine() -> None:
    t = StudentProposalEngine.generate_proposal("THOUGHT-001", "Student claim")
    assert t.thought_id == "THOUGHT-001"
    assert t.hypothesis.claim == "Student claim"
    assert t.executor_profile.preferred_model_class == "student"


def test_latency_evaluator() -> None:
    res = LatencyEvaluator.evaluate_latency(
        StudentProposalEngine.generate_proposal,
        iterations=5,
        max_latency_ms=200.0,
    )
    assert "mean_latency_ms" in res
    assert "max_latency_ms" in res
    assert res["max_latency_ms"] < 200.0
