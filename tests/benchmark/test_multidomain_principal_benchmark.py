"""Scientific Principal Model Multi-Domain Benchmark (Stage 8).

Validates end-to-end multi-domain operational readiness across:
1. Software Engineering domain.
2. Medical Diagnosis domain.
3. Financial Strategy domain.

Exercising Stages 0 through 7 cleanly in a single integrated test suite.
"""

from __future__ import annotations

import time

from nps_core.adaptive_n import (
    AdaptiveNController,
    ExperimentBundler,
    InformationGainRanker,
)
from nps_core.distillation_dataset import DatasetBuilder
from nps_core.evidence_assimilator import (
    AssimilationPlan,
    EvidenceImpact,
    EvidencePacket,
    Reproducibility,
)
from nps_core.executor_router import ExecutorDescriptor, ExecutorRouter
from nps_core.experiment_designer import VerificationNeed, VerificationPortfolio
from nps_core.hypothesis_population import (
    PopulationSnapshot,
    thought_state_from_dict,
)
from nps_core.model_training import StudentProposalEngine
from nps_core.state_update import apply_evidence
from nps_core.thought_ecology import build as build_ecology
from nps_core.verification_tribunal import VerificationTribunal


def run_domain_pipeline(domain_name: str, claims: tuple[str, ...]) -> dict[str, float | int | str]:
    start = time.perf_counter()

    # Stage 7: Generate student proposals
    thoughts = tuple(
        StudentProposalEngine.generate_proposal(f"THOUGHT-{domain_name[:3].upper()}-{i+1:03d}", claim)
        for i, claim in enumerate(claims)
    )

    # Stage 1: Build snapshot and ecology
    snapshot = PopulationSnapshot(thoughts=thoughts)
    n_h = len(snapshot.thoughts)
    ecology = build_ecology(snapshot)

    # Stage 4: Adaptive N & Ranking
    target_n = AdaptiveNController.compute_target_n(snapshot, ecology, max_budget=20)
    ranked = InformationGainRanker.rank_hypotheses(snapshot)
    assert len(ranked) > 0

    # Stage 4 & 1: Define needs, bundle experiments, create portfolio
    needs = tuple(
        VerificationNeed(f"NEED-{t.thought_id}", t.thought_id, f"Uncertainty in {domain_name}", ("log",))
        for t in snapshot.thoughts
    )
    experiments = ExperimentBundler.bundle_needs(needs, max_hypotheses_per_exp=2)

    portfolio = VerificationPortfolio(
        portfolio_id=f"PORTFOLIO-{domain_name[:3].upper()}",
        snapshot_digest=ecology.snapshot_digest,
        verification_needs=needs,
        experiments=experiments,
        n_v=len(needs),
    )
    portfolio.validate_for(snapshot)
    n_v = portfolio.n_v

    # Stage 1 & 2: Executor routing and invariant verification
    ex = ExecutorDescriptor(f"EXECUTOR-{domain_name[:3].upper()}", f"{domain_name} Worker", ("python",), ("automated_test",))
    plan = ExecutorRouter.route(portfolio, (ex,), n_h=n_h)
    n_e = plan.n_e
    assert n_h >= n_v >= n_e, f"Invariant violated in {domain_name}: N_h ({n_h}) >= N_v ({n_v}) >= N_e ({n_e})"

    # Stage 5: Tribunal evaluation
    pkt = EvidencePacket(
        evidence_id=f"EV-{domain_name[:3].upper()}-001",
        task_id=f"TASK-{experiments[0].experiment_id}",
        executor_id=ex.executor_id,
        claim=f"{domain_name} claim verified",
        result="PASSED",
        method="automated_test",
        artifacts=(),
        confidence=0.95,
        limitations=(),
        failure_modes=(),
        reproducibility=Reproducibility(command="pytest", environment="local", seed=None),
        affected_hypotheses=(snapshot.thoughts[0].thought_id,),
        provenance=(f"{domain_name} pipeline",),
        content_hash="a" * 64,
    )
    conflicts, repro_logs = VerificationTribunal.evaluate((pkt,), snapshot)

    # Stage 1: Evidence assimilation & state update
    target_tid = snapshot.thoughts[0].thought_id
    impact = EvidenceImpact(target_tid, "supporting")
    assim_plan = AssimilationPlan(pkt, (impact,))

    updated_dict = snapshot.thoughts[0].to_dict()
    updated_dict["evidence"]["supporting"].append(pkt.evidence_id)
    t0_updated = thought_state_from_dict(updated_dict)
    replacements = {target_tid: t0_updated}

    updated_snapshot, record = apply_evidence(
        snapshot,
        assim_plan,
        replacements,
        record_id=f"REC-{domain_name[:3].upper()}",
        timestamp="2026-07-25T10:10:00Z",
        actor=f"{domain_name}_pipeline",
    )

    # Stage 6: Distillation dataset extraction
    manifest = DatasetBuilder.build_manifest(f"v1-{domain_name[:3].lower()}", updated_snapshot)

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "domain": domain_name,
        "n_h": n_h,
        "n_v": n_v,
        "n_e": n_e,
        "target_n": target_n,
        "conflicts": len(conflicts),
        "repro_logs": len(repro_logs),
        "manifest_records": len(manifest.records),
        "elapsed_ms": round(elapsed_ms, 2),
    }


def test_multidomain_principal_benchmark() -> None:
    domains = [
        ("Software_Engineering", ("AST parser maintains idempotency", "Pytest suite has zero regression")),
        ("Medical_Diagnosis", ("Patient biomarker indicates Type A response", "Drug interaction is non-inhibitory")),
        ("Financial_Strategy", ("Portfolio Sharpe ratio exceeds benchmark", "Tail risk is bounded under 5%")),
    ]

    results = []
    for name, claims in domains:
        res = run_domain_pipeline(name, claims)
        results.append(res)
        assert res["elapsed_ms"] < 150.0, f"Domain {name} took {res['elapsed_ms']}ms (>150ms threshold)"

    assert len(results) == 3
