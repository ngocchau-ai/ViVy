"""Unit tests for Stage 4 Adaptive N Controller, Information Gain Ranker, and Experiment Bundler."""

from __future__ import annotations

import pytest

from nps_core.adaptive_n import (
    AdaptiveNController,
    BudgetExceededError,
    ExperimentBundler,
    InformationGainRanker,
)
from nps_core.experiment_designer import VerificationNeed
from nps_core.hypothesis_population import (
    VALID_STATES,
    PopulationSnapshot,
    thought_state_from_dict,
)
from nps_core.thought_ecology import build as build_ecology


def _make_thought_dict(thought_id: str, claim: str, confidence: float = 0.5) -> dict:
    return {
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2026-07-25T10:00:00Z",
        "interpretation": {
            "summary": f"Summary {thought_id}",
            "scope": "global",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": claim,
            "predicted_observations": ["obs"],
            "falsification_conditions": ["cond"],
        },
        "assumptions": [],
        "evidence": {"supporting": [], "opposing": [], "unresolved": []},
        "metrics": {
            "confidence": confidence,
            "novelty": 0.5,
            "diversity": 0.5,
            "expected_value": 0.5,
            "information_need": 0.8,
            "risk_if_wrong": 0.7,
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
        "graph": {"dependencies": [], "contradictions": [], "overlaps": []},
        "status": {"state": "active", "allowed_values": list(VALID_STATES)},
    }


def test_adaptive_n_controller() -> None:
    t1 = thought_state_from_dict(_make_thought_dict("THOUGHT-001", "Same Claim"))
    t2 = thought_state_from_dict(_make_thought_dict("THOUGHT-002", "Same Claim"))
    snapshot = PopulationSnapshot(thoughts=(t1, t2))
    ecology = build_ecology(snapshot)

    # Compute target N
    target_n = AdaptiveNController.compute_target_n(snapshot, ecology, max_budget=10)
    assert target_n == 2

    # Exceed budget raises BudgetExceededError
    with pytest.raises(BudgetExceededError, match="exceeds maximum budget"):
        AdaptiveNController.compute_target_n(snapshot, ecology, max_budget=1)

    # Duplicate detection
    dups = AdaptiveNController.detect_duplicates(snapshot)
    assert len(dups) == 1
    assert dups[0] == ("THOUGHT-001", "THOUGHT-002")


def test_information_gain_ranker() -> None:
    t1 = thought_state_from_dict(_make_thought_dict("THOUGHT-001", "Claim A", confidence=0.2))
    t2 = thought_state_from_dict(_make_thought_dict("THOUGHT-002", "Claim B", confidence=0.9))
    snapshot = PopulationSnapshot(thoughts=(t1, t2))

    ranked = InformationGainRanker.rank_hypotheses(snapshot)
    assert len(ranked) == 2
    assert ranked[0][0] == "THOUGHT-001"  # Higher E[IG] due to lower confidence


def test_experiment_bundler() -> None:
    n1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty 1", ("type1",))
    n2 = VerificationNeed("NEED-002", "THOUGHT-002", "Uncertainty 2", ("type2",))
    n3 = VerificationNeed("NEED-003", "THOUGHT-003", "Uncertainty 3", ("type3",))

    contracts = ExperimentBundler.bundle_needs((n1, n2, n3), max_hypotheses_per_exp=2)
    assert len(contracts) == 2
    assert len(contracts[0].hypotheses_tested) == 2
    assert len(contracts[1].hypotheses_tested) == 1
