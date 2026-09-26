"""Unit tests for ExecutorRouter and N_e accounting."""

from __future__ import annotations

import pytest

from nps_core.executor_router import (
    ExecutorBudgetError,
    ExecutorDescriptor,
    ExecutorRouter,
    ExecutorRoutingPlan,
    UnmatchedRequirementError,
)
from nps_core.experiment_designer import (
    ExperimentContract,
    VerificationNeed,
    VerificationPortfolio,
)


def make_experiment(exp_id: str, hyps: tuple[str, ...], reqs: tuple[str, ...] = ("python",)) -> ExperimentContract:
    return ExperimentContract(
        experiment_id=exp_id,
        objective="Test experiment",
        hypotheses_tested=hyps,
        discriminating_outcomes={"pass": "pass"},
        method="automated_test",
        executor_requirements=reqs,
        cost_budget={"cpu": 1.0},
        stop_conditions=("done",),
        expected_information_gain=0.8,
        acceptance_schema="schema",
    )


def test_executor_descriptor_validation() -> None:
    ex = ExecutorDescriptor("EXECUTOR-001", "Python Sandbox", ("python", "sandbox"), ("automated_test",))
    assert ex.executor_id == "EXECUTOR-001"
    assert ex.satisfies(("python",), "automated_test")
    assert not ex.satisfies(("gpu",), "automated_test")
    assert ex.to_dict() == ExecutorDescriptor.from_dict(ex.to_dict()).to_dict()


def test_executor_router_valid_routing() -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("type1",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-002", "Uncertainty 2", ("type2",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001", "THOUGHT-002"))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest="a" * 64,
        verification_needs=(need1, need2),
        experiments=(exp1,),
        n_v=2,
    )

    ex1 = ExecutorDescriptor("EXECUTOR-001", "Exec 1", ("python",), ("automated_test",))
    plan = ExecutorRouter.route(portfolio, (ex1,), n_h=3)

    assert plan.n_e == 1
    assert plan.assignments[0].executor_id == "EXECUTOR-001"
    assert plan.assignments[0].experiment_id == "EXP-001"

    # Test round-trip
    assert ExecutorRoutingPlan.from_dict(plan.to_dict()) == plan


def test_executor_router_unmatched_requirement() -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("type1",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",), reqs=("quantum_hardware",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest="a" * 64,
        verification_needs=(need1,),
        experiments=(exp1,),
        n_v=1,
    )

    ex1 = ExecutorDescriptor("EXECUTOR-001", "Exec 1", ("python",), ("automated_test",))
    with pytest.raises(UnmatchedRequirementError, match="no matching executor found"):
        ExecutorRouter.route(portfolio, (ex1,), n_h=3)


def test_executor_router_invariant_n_h_ge_n_v_ge_n_e() -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("type1",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-002", "Uncertainty 2", ("type2",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",))
    exp2 = make_experiment("EXP-002", ("THOUGHT-002",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest="a" * 64,
        verification_needs=(need1, need2),
        experiments=(exp1, exp2),
        n_v=2,
    )

    ex1 = ExecutorDescriptor("EXECUTOR-001", "Exec 1", ("python",), ("automated_test",))
    ex2 = ExecutorDescriptor("EXECUTOR-002", "Exec 2", ("python",), ("automated_test",))

    # N_h = 1, N_v = 2 -> N_v > N_h violation
    with pytest.raises(ExecutorBudgetError, match="N_v \\(2\\) > N_h \\(1\\)"):
        ExecutorRouter.route(portfolio, (ex1, ex2), n_h=1)
