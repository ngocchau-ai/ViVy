"""Experiment Bundler for Stage 4.

Bundles verification needs into compact ExperimentContract contracts testing multiple hypotheses.
Standard-library only.
"""

from __future__ import annotations

from typing import Sequence

from nps_core.experiment_designer import ExperimentContract, VerificationNeed

__all__ = [
    "ExperimentBundler",
]


class ExperimentBundler:
    """Bundles verification needs into discriminative ExperimentContracts."""

    @staticmethod
    def bundle_needs(
        needs: Sequence[VerificationNeed],
        max_hypotheses_per_exp: int = 3,
    ) -> tuple[ExperimentContract, ...]:
        """Group verification needs into discriminative experiment contracts."""
        if not needs:
            return ()

        contracts: list[ExperimentContract] = []
        chunk: list[VerificationNeed] = []
        exp_idx = 1

        for need in needs:
            chunk.append(need)
            if len(chunk) >= max_hypotheses_per_exp:
                contracts.append(ExperimentBundler._make_contract(exp_idx, chunk))
                exp_idx += 1
                chunk = []

        if chunk:
            contracts.append(ExperimentBundler._make_contract(exp_idx, chunk))

        return tuple(contracts)

    @staticmethod
    def _make_contract(idx: int, needs_chunk: list[VerificationNeed]) -> ExperimentContract:
        hyps = tuple(sorted({n.target_hypothesis_id for n in needs_chunk}))
        exp_id = f"EXP-{idx:03d}"
        return ExperimentContract(
            experiment_id=exp_id,
            objective=f"Bundled test for hypotheses {hyps}",
            hypotheses_tested=hyps,
            discriminating_outcomes={"pass": "all_pass", "fail": "any_fail"},
            method="automated_test",
            executor_requirements=("python",),
            cost_budget={"time_s": 10.0},
            stop_conditions=("complete",),
            expected_information_gain=0.85,
            acceptance_schema="schemas/evidence_packet.schema.json",
        )
