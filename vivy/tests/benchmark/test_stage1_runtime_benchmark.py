"""Integrated Stage 1 Runtime Benchmark.

Tests the full end-to-end pipeline of Stage 1:
ThoughtState creation -> PopulationSnapshot -> ThoughtEcology ->
VerificationPortfolio (N_v) -> ExecutorRouter (N_e) -> Invariant N_h >= N_v >= N_e ->
EvidencePacket -> AssimilationPlan -> StateUpdate (apply_evidence) -> Updated Snapshot & Ecology.
"""

from __future__ import annotations

import time

from nps_core.evidence_assimilator import (
    AssimilationPlan,
    EvidenceImpact,
    EvidencePacket,
    Reproducibility,
)
from nps_core.executor_router import ExecutorDescriptor, ExecutorRouter
from nps_core.experiment_designer import (
    ExperimentContract,
    VerificationNeed,
    VerificationPortfolio,
)
from nps_core.hypothesis_population import (
    VALID_STATES,
    PopulationSnapshot,
    thought_state_from_dict,
)
from nps_core.state_update import apply_evidence
from nps_core.thought_ecology import build as build_ecology


def _make_thought_dict(thought_id: str, claim: str) -> dict:
    return {
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2026-07-25T10:00:00Z",
        "interpretation": {
            "summary": f"Summary for {thought_id}",
            "scope": "global",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": claim,
            "predicted_observations": ["Observation 1"],
            "falsification_conditions": ["Falsification 1"],
        },
        "assumptions": [
            {
                "assumption_id": "ASM-001",
                "statement": "Shared assumption",
                "confidence": 0.9,
                "source": "test",
            }
        ],
        "evidence": {
            "supporting": [],
            "opposing": [],
            "unresolved": [],
        },
        "metrics": {
            "confidence": 0.5,
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


def test_stage1_runtime_end_to_end_benchmark() -> None:
    start_time = time.perf_counter()

    # Step 1: Initialize population (N_h = 3)
    t1 = thought_state_from_dict(_make_thought_dict("THOUGHT-001", "Claim A"))
    t2 = thought_state_from_dict(_make_thought_dict("THOUGHT-002", "Claim B"))
    t3 = thought_state_from_dict(_make_thought_dict("THOUGHT-003", "Claim C"))
    snapshot = PopulationSnapshot(thoughts=(t1, t2, t3))
    n_h = len(snapshot.thoughts)
    assert n_h == 3

    # Step 2: Build initial Thought Ecology
    ecology = build_ecology(snapshot)
    assert len(ecology.thought_ids) == 3

    # Step 3: Define verification needs & contracts (N_v = 2)
    need1 = VerificationNeed("NEED-001", "THOUGHT-001", "Uncertainty A", ("log",))
    need2 = VerificationNeed("NEED-002", "THOUGHT-002", "Uncertainty B", ("log",))
    exp1 = ExperimentContract(
        experiment_id="EXP-001",
        objective="Verify THOUGHT-001 and THOUGHT-002",
        hypotheses_tested=("THOUGHT-001", "THOUGHT-002"),
        discriminating_outcomes={"pass": "pass", "fail": "fail"},
        method="automated_test",
        executor_requirements=("python",),
        cost_budget={"cpu": 1.0},
        stop_conditions=("done",),
        expected_information_gain=0.9,
        acceptance_schema="schemas/evidence_packet.schema.json",
    )

    portfolio = VerificationPortfolio(
        portfolio_id="PORTFOLIO-001",
        snapshot_digest=ecology.snapshot_digest,
        verification_needs=(need1, need2),
        experiments=(exp1,),
        n_v=2,
    )
    portfolio.validate_for(snapshot)
    n_v = portfolio.n_v
    assert n_v == 2

    # Step 4: Route experiments to executors (N_e = 1)
    executor = ExecutorDescriptor("EXECUTOR-001", "Python Worker", ("python",), ("automated_test",))
    routing_plan = ExecutorRouter.route(portfolio, (executor,), n_h=n_h)
    n_e = routing_plan.n_e
    assert n_e == 1

    # Step 5: Verify core architecture invariant N_h >= N_v >= N_e
    assert n_h >= n_v >= n_e, f"Invariant violated: N_h ({n_h}) >= N_v ({n_v}) >= N_e ({n_e})"

    # Step 6: Create EvidencePacket from executor execution
    packet = EvidencePacket(
        evidence_id="EV-001",
        task_id="TASK-EXP-001",
        executor_id="EXECUTOR-001",
        claim="Claim A verified by automated test",
        result="PASSED",
        method="automated_test",
        artifacts=(),
        confidence=0.95,
        limitations=(),
        failure_modes=(),
        reproducibility=Reproducibility(command="pytest", environment="local", seed=None),
        affected_hypotheses=("THOUGHT-001",),
        provenance=("automated test runner",),
        content_hash="a" * 64,
    )

    # Step 7: Formulate AssimilationPlan with EvidenceImpact
    impact = EvidenceImpact("THOUGHT-001", "supporting")
    plan = AssimilationPlan(packet, (impact,))

    # Step 8: Apply state update to population snapshot
    t1_updated_dict = _make_thought_dict("THOUGHT-001", "Claim A")
    t1_updated_dict["evidence"]["supporting"] = ["EV-001"]
    t1_updated = thought_state_from_dict(t1_updated_dict)
    replacements = {"THOUGHT-001": t1_updated}

    updated_snapshot, record = apply_evidence(
        snapshot,
        plan,
        replacements,
        record_id="REC-001",
        timestamp="2026-07-25T10:05:00Z",
        actor="executor_router",
    )

    # Step 9: Re-build Thought Ecology on updated snapshot
    updated_ecology = build_ecology(updated_snapshot)
    assert "EV-001" in updated_snapshot.get("THOUGHT-001").evidence.supporting
    assert updated_ecology.snapshot_digest != ecology.snapshot_digest

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    assert elapsed_ms < 100.0, f"Stage 1 benchmark cycle took {elapsed_ms:.2f}ms (>100ms threshold)"
