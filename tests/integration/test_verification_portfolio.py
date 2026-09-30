"""Integration tests for VerificationPortfolio validation against PopulationSnapshot."""

from __future__ import annotations

import hashlib

import pytest

from nps_core.experiment_designer import (
    ExperimentContract,
    SnapshotMismatchError,
    UncoveredNeedError,
    UnknownThoughtError,
    UnlinkedContractError,
    VerificationNeed,
    VerificationPortfolio,
    VerifierBudgetError,
)
from nps_core.hypothesis_population import (
    VALID_STATES,
    PopulationSnapshot,
    ThoughtState,
    thought_state_from_dict,
)


def _canonical_dict(thought_id: str) -> dict:
    return {
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2026-07-25T10:00:00Z",
        "interpretation": {
            "summary": "Test summary",
            "scope": "global",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": "Claim for " + thought_id,
            "predicted_observations": ["blue colour observed"],
            "falsification_conditions": ["sky is not blue"],
        },
        "assumptions": [
            {
                "assumption_id": "ASM-001",
                "statement": "Light scattering applies",
                "confidence": 0.95,
                "source": "test",
            }
        ],
        "evidence": {
            "supporting": [],
            "opposing": [],
            "unresolved": [],
        },
        "metrics": {
            "confidence": 0.8,
            "novelty": 0.5,
            "diversity": 0.5,
            "expected_value": 0.5,
            "information_need": 0.5,
            "risk_if_wrong": 0.5,
            "execution_cost": 0.5,
        },
        "verification_plan": {
            "questions": [],
            "required_experiments": [],
            "acceptable_evidence": [],
            "rejection_threshold": 0.2,
        },
        "executor_profile": {
            "skills": ["python"],
            "tool_requirements": [],
            "preferred_model_class": "coder",
            "independence_requirements": [],
        },
        "graph": {
            "dependencies": [],
            "contradictions": [],
            "overlaps": [],
        },
        "status": {
            "state": "active",
            "allowed_values": list(VALID_STATES),
        },
    }


def create_thought(thought_id: str) -> ThoughtState:
    return thought_state_from_dict(_canonical_dict(thought_id))


def make_snapshot(thoughts: tuple[ThoughtState, ...]) -> PopulationSnapshot:
    return PopulationSnapshot(thoughts=tuple(thoughts))


def get_snapshot_digest(snapshot: PopulationSnapshot) -> str:
    return hashlib.sha256(snapshot.to_canonical_json().encode("utf-8")).hexdigest()


@pytest.fixture
def population_snapshot() -> PopulationSnapshot:
    t1 = create_thought("THOUGHT-001")
    t2 = create_thought("THOUGHT-002")
    t3 = create_thought("THOUGHT-003")
    return make_snapshot((t1, t2, t3))


def make_experiment(exp_id: str, hyps: tuple[str, ...]) -> ExperimentContract:
    return ExperimentContract(
        experiment_id=exp_id,
        objective="Integration test experiment",
        hypotheses_tested=hyps,
        discriminating_outcomes={"pass": "pass", "fail": "fail"},
        method="automated test",
        executor_requirements=("pytest",),
        cost_budget={"time_s": 5.0},
        stop_conditions=("complete",),
        expected_information_gain=0.9,
        acceptance_schema="schemas/evidence_packet.schema.json",
    )


def test_verification_portfolio_valid_integration(population_snapshot: PopulationSnapshot) -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("log",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-002", "Uncertainty 2", ("metric",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001", "THOUGHT-002"))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=get_snapshot_digest(population_snapshot),
        verification_needs=(need1, need2),
        experiments=(exp1,),
        n_v=2,
    )

    # Must validate cleanly without exception
    portfolio.validate_for(population_snapshot)


def test_verification_portfolio_snapshot_mismatch(population_snapshot: PopulationSnapshot) -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("log",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",))

    bogus_digest = "f" * 64
    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=bogus_digest,
        verification_needs=(need1,),
        experiments=(exp1,),
        n_v=1,
    )

    with pytest.raises(SnapshotMismatchError, match="does not match PopulationSnapshot digest"):
        portfolio.validate_for(population_snapshot)


def test_verification_portfolio_unknown_target_thought(population_snapshot: PopulationSnapshot) -> None:
    need_bad = VerificationNeed("NEED-001", "THOUGHT-UNKNOWN", "Uncertainty", ("log",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=get_snapshot_digest(population_snapshot),
        verification_needs=(need_bad,),
        experiments=(exp1,),
        n_v=1,
    )

    with pytest.raises(UnknownThoughtError, match="references unknown target_hypothesis_id 'THOUGHT-UNKNOWN'"):
        portfolio.validate_for(population_snapshot)


def test_verification_portfolio_unknown_experiment_thought(population_snapshot: PopulationSnapshot) -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty", ("log",))
    exp_bad = make_experiment("EXP-001", ("THOUGHT-UNKNOWN",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=get_snapshot_digest(population_snapshot),
        verification_needs=(need1,),
        experiments=(exp_bad,),
        n_v=1,
    )

    with pytest.raises(UnknownThoughtError, match="references unknown hypothesis_id 'THOUGHT-UNKNOWN'"):
        portfolio.validate_for(population_snapshot)


def test_verification_portfolio_n_v_exceeds_n_h() -> None:
    # Population with 1 thought (N_h = 1)
    t1 = create_thought("THOUGHT-001")
    small_snapshot = make_snapshot((t1,))

    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("log",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-001", "Uncertainty 2", ("log",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=get_snapshot_digest(small_snapshot),
        verification_needs=(need1, need2),
        experiments=(exp1,),
        n_v=2,
    )

    with pytest.raises(VerifierBudgetError, match="N_v \\(2\\) exceeds N_h \\(1\\)"):
        portfolio.validate_for(small_snapshot)


def test_verification_portfolio_uncovered_need(population_snapshot: PopulationSnapshot) -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("log",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-002", "Uncertainty 2", ("log",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=get_snapshot_digest(population_snapshot),
        verification_needs=(need1, need2),
        experiments=(exp1,),
        n_v=2,
    )

    with pytest.raises(UncoveredNeedError, match="are not covered by any ExperimentContract"):
        portfolio.validate_for(population_snapshot)


def test_verification_portfolio_unlinked_contract(population_snapshot: PopulationSnapshot) -> None:
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("log",))
    exp1 = make_experiment("EXP-001", ("THOUGHT-001",))
    exp_unlinked = make_experiment("EXP-002", ("THOUGHT-003",))

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=get_snapshot_digest(population_snapshot),
        verification_needs=(need1,),
        experiments=(exp1, exp_unlinked),
        n_v=1,
    )

    with pytest.raises(UnlinkedContractError, match="do not cover any verification need in portfolio"):
        portfolio.validate_for(population_snapshot)
