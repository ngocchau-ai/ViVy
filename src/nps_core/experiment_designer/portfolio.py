"""Immutable VerificationNeed and VerificationPortfolio value models.

Standard-library only; no runtime dependencies beyond standard library.
All value objects are frozen, slotted dataclasses validated on construction.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from nps_core.experiment_designer.contract import ExperimentContract
from nps_core.experiment_designer.errors import (
    PortfolioValidationError,
    SnapshotMismatchError,
    UncoveredNeedError,
    UnknownThoughtError,
    UnlinkedContractError,
    VerifierBudgetError,
)
from nps_core.hypothesis_population.lifecycle import PopulationSnapshot

__all__ = [
    "VerificationNeed",
    "VerificationPortfolio",
]

_NEED_ID_RE = re.compile(r"^NEED-[A-Za-z0-9._-]+$")
_PORTFOLIO_ID_RE = re.compile(r"^PORTFOLIO-[A-Za-z0-9._-]+$")
_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")
_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _err(msg: str, *, path: str | None = None) -> PortfolioValidationError:
    return PortfolioValidationError(msg, path=path)


def _check_non_empty_str(val: Any, path: str) -> str:
    if isinstance(val, bool) or not isinstance(val, str):
        raise _err(f"must be a string, got {type(val).__name__}", path=path)
    if not val.strip():
        raise _err("must be a non-empty string", path=path)
    return val


@dataclass(frozen=True, slots=True)
class VerificationNeed:
    """Frozen value object for caller-supplied verification need."""

    need_id: str
    target_hypothesis_id: str
    uncertainty_description: str
    acceptable_evidence_types: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.need_id, bool) or not isinstance(self.need_id, str):
            raise _err(f"need_id must be a string, got {type(self.need_id).__name__}", path="need_id")
        if not _NEED_ID_RE.match(self.need_id):
            raise _err("need_id must match ^NEED-[A-Za-z0-9._-]+$", path="need_id")

        if isinstance(self.target_hypothesis_id, bool) or not isinstance(self.target_hypothesis_id, str):
            raise _err(f"target_hypothesis_id must be a string, got {type(self.target_hypothesis_id).__name__}", path="target_hypothesis_id")
        if not _THOUGHT_ID_RE.match(self.target_hypothesis_id):
            raise _err("target_hypothesis_id must match ^THOUGHT-[A-Za-z0-9._-]+$", path="target_hypothesis_id")

        _check_non_empty_str(self.uncertainty_description, "uncertainty_description")

        if isinstance(self.acceptable_evidence_types, (str, bytes)) or not isinstance(self.acceptable_evidence_types, (list, tuple)):
            raise _err("acceptable_evidence_types must be a sequence of strings", path="acceptable_evidence_types")
        types_res: list[str] = []
        for i, item in enumerate(self.acceptable_evidence_types):
            types_res.append(_check_non_empty_str(item, f"acceptable_evidence_types[{i}]"))
        if not types_res:
            raise _err("acceptable_evidence_types must contain at least 1 item", path="acceptable_evidence_types")
        object.__setattr__(self, "acceptable_evidence_types", tuple(types_res))

    def to_dict(self) -> dict[str, Any]:
        return {
            "need_id": self.need_id,
            "target_hypothesis_id": self.target_hypothesis_id,
            "uncertainty_description": self.uncertainty_description,
            "acceptable_evidence_types": list(self.acceptable_evidence_types),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationNeed:
        if not isinstance(data, dict):
            raise _err(f"VerificationNeed data must be a dict, got {type(data).__name__}")
        required = {"need_id", "target_hypothesis_id", "uncertainty_description", "acceptable_evidence_types"}
        actual = set(data.keys())
        if required != actual:
            missing = required - actual
            extra = actual - required
            err_msg = []
            if missing:
                err_msg.append(f"missing {sorted(missing)}")
            if extra:
                err_msg.append(f"unexpected {sorted(extra)}")
            raise _err(f"VerificationNeed keys mismatch: {'; '.join(err_msg)}")
        return cls(
            need_id=data["need_id"],
            target_hypothesis_id=data["target_hypothesis_id"],
            uncertainty_description=data["uncertainty_description"],
            acceptable_evidence_types=data["acceptable_evidence_types"],
        )


@dataclass(frozen=True, slots=True)
class VerificationPortfolio:
    """Frozen value object for exact-snapshot VerificationPortfolio."""

    portfolio_id: str
    snapshot_digest: str
    verification_needs: tuple[VerificationNeed, ...]
    experiments: tuple[ExperimentContract, ...]
    n_v: int

    def __post_init__(self) -> None:
        if isinstance(self.portfolio_id, bool) or not isinstance(self.portfolio_id, str):
            raise _err(f"portfolio_id must be a string, got {type(self.portfolio_id).__name__}", path="portfolio_id")
        if not _PORTFOLIO_ID_RE.match(self.portfolio_id):
            raise _err("portfolio_id must match ^PORTFOLIO-[A-Za-z0-9._-]+$", path="portfolio_id")

        if isinstance(self.snapshot_digest, bool) or not isinstance(self.snapshot_digest, str):
            raise _err(f"snapshot_digest must be a string, got {type(self.snapshot_digest).__name__}", path="snapshot_digest")
        if not _HEX64_RE.match(self.snapshot_digest):
            raise _err("snapshot_digest must be a 64-character hex string", path="snapshot_digest")

        # verification_needs
        if isinstance(self.verification_needs, (str, bytes)) or not isinstance(self.verification_needs, (list, tuple)):
            raise _err("verification_needs must be a sequence", path="verification_needs")
        needs_res: list[VerificationNeed] = []
        seen_need_ids: set[str] = set()
        for i, item in enumerate(self.verification_needs):
            if isinstance(item, dict):
                vn = VerificationNeed.from_dict(item)
            elif isinstance(item, VerificationNeed):
                vn = item
            else:
                raise _err(f"verification_needs[{i}] must be VerificationNeed or dict", path=f"verification_needs[{i}]")
            if vn.need_id in seen_need_ids:
                raise _err(f"Duplicate need_id '{vn.need_id}' in verification_needs", path=f"verification_needs[{i}]")
            seen_need_ids.add(vn.need_id)
            needs_res.append(vn)
        object.__setattr__(self, "verification_needs", tuple(needs_res))

        # experiments
        if isinstance(self.experiments, (str, bytes)) or not isinstance(self.experiments, (list, tuple)):
            raise _err("experiments must be a sequence", path="experiments")
        exp_res: list[ExperimentContract] = []
        seen_exp_ids: set[str] = set()
        for i, item in enumerate(self.experiments):
            if isinstance(item, dict):
                ec = ExperimentContract.from_dict(item)
            elif isinstance(item, ExperimentContract):
                ec = item
            else:
                raise _err(f"experiments[{i}] must be ExperimentContract or dict", path=f"experiments[{i}]")
            if ec.experiment_id in seen_exp_ids:
                raise _err(f"Duplicate experiment_id '{ec.experiment_id}' in experiments", path=f"experiments[{i}]")
            seen_exp_ids.add(ec.experiment_id)
            exp_res.append(ec)
        object.__setattr__(self, "experiments", tuple(exp_res))

        # n_v accounting
        if isinstance(self.n_v, bool) or not isinstance(self.n_v, int):
            raise VerifierBudgetError(f"n_v must be an integer, got {type(self.n_v).__name__}", path="n_v")
        if self.n_v < 0:
            raise VerifierBudgetError(f"n_v cannot be negative, got {self.n_v}", path="n_v")
        expected_n_v = len(self.verification_needs)
        if self.n_v != expected_n_v:
            raise VerifierBudgetError(
                f"n_v ({self.n_v}) must equal the number of verification_needs ({expected_n_v})",
                path="n_v",
            )

    def validate_for(self, snapshot: PopulationSnapshot) -> None:
        """Validate portfolio against exact PopulationSnapshot and architecture invariants."""
        actual_digest = hashlib.sha256(snapshot.to_canonical_json().encode("utf-8")).hexdigest()
        if self.snapshot_digest != actual_digest:
            raise SnapshotMismatchError(
                f"Portfolio snapshot_digest '{self.snapshot_digest}' does not match "
                f"PopulationSnapshot digest '{actual_digest}'",
                path="snapshot_digest",
            )

        known_thought_ids = {t.thought_id for t in snapshot.thoughts}
        n_h = len(known_thought_ids)
        if self.n_v > n_h:
            raise VerifierBudgetError(
                f"Verifier budget rule violated: N_v ({self.n_v}) exceeds N_h ({n_h})",
                path="n_v",
            )

        # Check all target_hypothesis_ids in verification_needs exist in snapshot
        needed_target_ids: set[str] = set()
        for need in self.verification_needs:
            if need.target_hypothesis_id not in known_thought_ids:
                raise UnknownThoughtError(
                    f"VerificationNeed '{need.need_id}' references unknown target_hypothesis_id '{need.target_hypothesis_id}'",
                    path=f"verification_needs['{need.need_id}']",
                )
            needed_target_ids.add(need.target_hypothesis_id)

        # Check all tested hypotheses in experiments exist in snapshot
        covered_target_ids: set[str] = set()
        for exp in self.experiments:
            exp_covers_any_need = False
            for hyp_id in exp.hypotheses_tested:
                if hyp_id not in known_thought_ids:
                    raise UnknownThoughtError(
                        f"ExperimentContract '{exp.experiment_id}' references unknown hypothesis_id '{hyp_id}'",
                        path=f"experiments['{exp.experiment_id}']",
                    )
                if hyp_id in needed_target_ids:
                    exp_covers_any_need = True
                    covered_target_ids.add(hyp_id)
            if not exp_covers_any_need:
                raise UnlinkedContractError(
                    f"ExperimentContract '{exp.experiment_id}' tests hypotheses {exp.hypotheses_tested} "
                    f"which do not cover any verification need in portfolio",
                    path=f"experiments['{exp.experiment_id}']",
                )

        # Check every verification need is covered by at least one experiment
        uncovered = needed_target_ids - covered_target_ids
        if uncovered:
            uncovered_needs = [
                n.need_id for n in self.verification_needs if n.target_hypothesis_id in uncovered
            ]
            raise UncoveredNeedError(
                f"Verification needs {sorted(uncovered_needs)} targeting hypotheses {sorted(uncovered)} "
                "are not covered by any ExperimentContract in the portfolio",
                path="verification_needs",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio": {
                "portfolio_id": self.portfolio_id,
                "snapshot_digest": self.snapshot_digest,
                "verification_needs": [vn.to_dict() for vn in self.verification_needs],
                "experiments": [exp.to_dict() for exp in self.experiments],
                "n_v": self.n_v,
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationPortfolio:
        if not isinstance(data, dict):
            raise _err(f"Input data must be a dict, got {type(data).__name__}")
        if set(data.keys()) != {"portfolio"}:
            raise _err("Top-level dict must contain exactly one key: 'portfolio'")
        pdata = data["portfolio"]
        if not isinstance(pdata, dict):
            raise _err(f"'portfolio' must be a dict, got {type(pdata).__name__}")

        required = {"portfolio_id", "snapshot_digest", "verification_needs", "experiments", "n_v"}
        actual = set(pdata.keys())
        if required != actual:
            missing = required - actual
            extra = actual - required
            err_msg = []
            if missing:
                err_msg.append(f"missing {sorted(missing)}")
            if extra:
                err_msg.append(f"unexpected {sorted(extra)}")
            raise _err(f"Portfolio keys mismatch: {'; '.join(err_msg)}")

        return cls(
            portfolio_id=pdata["portfolio_id"],
            snapshot_digest=pdata["snapshot_digest"],
            verification_needs=pdata["verification_needs"],
            experiments=pdata["experiments"],
            n_v=pdata["n_v"],
        )

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()
