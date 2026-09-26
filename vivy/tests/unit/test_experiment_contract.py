"""Unit tests for ExperimentContract, VerificationNeed, and VerificationPortfolio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator  # noqa: E402

from nps_core.experiment_designer import (  # noqa: E402
    ExperimentContract,
    ExperimentValidationError,
    PortfolioValidationError,
    VerificationNeed,
    VerificationPortfolio,
    VerifierBudgetError,
)

_SCHEMA_PATH = Path("schemas/experiment.schema.json")


@pytest.fixture(scope="session")
def experiment_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def validator(experiment_schema: dict[str, Any]) -> Draft202012Validator:
    return Draft202012Validator(experiment_schema)


def make_valid_contract() -> ExperimentContract:
    return ExperimentContract(
        experiment_id="EXP-001",
        objective="Verify causality of hypothesis A vs B",
        hypotheses_tested=("THOUGHT-001", "THOUGHT-002"),
        discriminating_outcomes={"outcome_a": "THOUGHT-001 holds", "outcome_b": "THOUGHT-002 holds"},
        method="A/B execution in sandbox",
        executor_requirements=("python3", "sandbox"),
        cost_budget={"compute_seconds": 12.5, "memory_mb": 512.0},
        stop_conditions=("timeout_30s", "error_threshold_reached"),
        expected_information_gain=0.85,
        acceptance_schema="schemas/evidence_packet.schema.json",
    )


def test_valid_experiment_contract_schema_compliance(validator: Draft202012Validator) -> None:
    contract = make_valid_contract()
    data = contract.to_dict()
    errors = list(validator.iter_errors(data))
    assert not errors, f"Schema validation failed: {errors}"


def test_experiment_contract_roundtrip() -> None:
    contract = make_valid_contract()
    d = contract.to_dict()
    reconstructed = ExperimentContract.from_dict(d)
    assert reconstructed == contract
    assert reconstructed.to_canonical_json() == contract.to_canonical_json()
    assert reconstructed.digest == contract.digest


def test_experiment_contract_invalid_id() -> None:
    with pytest.raises(ExperimentValidationError, match="experiment_id must match"):
        ExperimentContract(
            experiment_id="INVALID_ID",
            objective="Obj",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": 1.0},
            stop_conditions=("stop",),
            expected_information_gain=0.5,
            acceptance_schema="schema",
        )


def test_experiment_contract_empty_fields() -> None:
    with pytest.raises(ExperimentValidationError, match="must be a non-empty string"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="   ",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": 1.0},
            stop_conditions=("stop",),
            expected_information_gain=0.5,
            acceptance_schema="schema",
        )

    with pytest.raises(ExperimentValidationError, match="must contain at least 1 item"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="obj",
            hypotheses_tested=(),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": 1.0},
            stop_conditions=("stop",),
            expected_information_gain=0.5,
            acceptance_schema="schema",
        )


def test_experiment_contract_budget_numeric_edge_cases() -> None:
    # Reject bool in float
    with pytest.raises(ExperimentValidationError, match="must be a number"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="obj",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": True},
            stop_conditions=("stop",),
            expected_information_gain=0.5,
            acceptance_schema="schema",
        )

    # Reject NaN / infinity in float
    with pytest.raises(ExperimentValidationError, match="must be a finite number"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="obj",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": float("nan")},
            stop_conditions=("stop",),
            expected_information_gain=0.5,
            acceptance_schema="schema",
        )

    # Reject negative float
    with pytest.raises(ExperimentValidationError, match="must be >= 0"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="obj",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": -1.5},
            stop_conditions=("stop",),
            expected_information_gain=0.5,
            acceptance_schema="schema",
        )


def test_experiment_contract_information_gain_bounds() -> None:
    # Reject > 1.0
    with pytest.raises(ExperimentValidationError, match="must be <= 1.0"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="obj",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": 1.0},
            stop_conditions=("stop",),
            expected_information_gain=1.05,
            acceptance_schema="schema",
        )

    # Reject bool for expected_information_gain
    with pytest.raises(ExperimentValidationError, match="must be a number"):
        ExperimentContract(
            experiment_id="EXP-001",
            objective="obj",
            hypotheses_tested=("THOUGHT-001",),
            discriminating_outcomes={"k": "v"},
            method="method",
            executor_requirements=("req",),
            cost_budget={"cost": 1.0},
            stop_conditions=("stop",),
            expected_information_gain=False,
            acceptance_schema="schema",
        )


def test_verification_need_valid_and_errors() -> None:
    need = VerificationNeed(
        need_id="NEED-001",
        target_hypothesis_id="THOUGHT-001",
        uncertainty_description="High variance in response latency",
        acceptable_evidence_types=("benchmark_log", "metric_packet"),
    )
    assert need.need_id == "NEED-001"
    assert need.target_hypothesis_id == "THOUGHT-001"
    assert need.to_dict() == VerificationNeed.from_dict(need.to_dict()).to_dict()

    with pytest.raises(PortfolioValidationError, match="need_id must match"):
        VerificationNeed(
            need_id="BAD_NEED",
            target_hypothesis_id="THOUGHT-001",
            uncertainty_description="desc",
            acceptable_evidence_types=("type",),
        )


def test_verification_portfolio_creation_and_n_v_budget() -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "desc1", ("type1",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-002", "desc2", ("type2",))
    exp = make_valid_contract()

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest="a" * 64,
        verification_needs=(need1, need2),
        experiments=(exp,),
        n_v=2,
    )
    assert portfolio.n_v == 2

    # Reject n_v mismatch
    with pytest.raises(VerifierBudgetError, match="n_v \\(3\\) must equal"):
        VerificationPortfolio(
            portfolio_id="PORTFOLIO-001",
            snapshot_digest="a" * 64,
            verification_needs=(need1, need2),
            experiments=(exp,),
            n_v=3,
        )

    # Reject bool / non-int n_v
    with pytest.raises(VerifierBudgetError, match="n_v must be an integer"):
        VerificationPortfolio(
            portfolio_id="PORTFOLIO-001",
            snapshot_digest="a" * 64,
            verification_needs=(need1, need2),
            experiments=(exp,),
            n_v=True,
        )


def test_verification_portfolio_duplicate_ids() -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "desc1", ("type1",))
    need1_dup = VerificationNeed("NEED-001", "THOUGHT-002", "desc2", ("type2",))
    exp = make_valid_contract()

    with pytest.raises(PortfolioValidationError, match="Duplicate need_id 'NEED-001'"):
        VerificationPortfolio(
            portfolio_id="PORTFOLIO-001",
            snapshot_digest="a" * 64,
            verification_needs=(need1, need1_dup),
            experiments=(exp,),
            n_v=2,
        )
