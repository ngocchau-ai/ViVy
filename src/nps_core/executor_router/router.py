"""Deterministic Executor Router and N_e Accounting module.

Standard-library only; no runtime dependencies beyond standard library.
Enforces the core architecture invariant: N_h >= N_v >= N_e.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from nps_core.experiment_designer import VerificationPortfolio
from nps_core.executor_router.errors import (
    ExecutorBudgetError,
    ExecutorRoutingError,
    UnmatchedRequirementError,
)

__all__ = [
    "ExecutorDescriptor",
    "ExecutorAssignment",
    "ExecutorRoutingPlan",
    "ExecutorRouter",
]

_EXECUTOR_ID_RE = re.compile(r"^EXECUTOR-[A-Za-z0-9._-]+$")


def _err(msg: str, *, path: str | None = None) -> ExecutorRoutingError:
    return ExecutorRoutingError(msg, path=path)


def _check_non_empty_str(val: Any, path: str) -> str:
    if isinstance(val, bool) or not isinstance(val, str):
        raise _err(f"must be a string, got {type(val).__name__}", path=path)
    if not val.strip():
        raise _err("must be a non-empty string", path=path)
    return val


@dataclass(frozen=True, slots=True)
class ExecutorDescriptor:
    """Frozen value object describing an available executor."""

    executor_id: str
    name: str
    skills: tuple[str, ...]
    supported_methods: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.executor_id, bool) or not isinstance(self.executor_id, str):
            raise _err(f"executor_id must be a string, got {type(self.executor_id).__name__}", path="executor_id")
        if not _EXECUTOR_ID_RE.match(self.executor_id):
            raise _err("executor_id must match ^EXECUTOR-[A-Za-z0-9._-]+$", path="executor_id")

        _check_non_empty_str(self.name, "name")

        if isinstance(self.skills, (str, bytes)) or not isinstance(self.skills, (list, tuple)):
            raise _err("skills must be a sequence of strings", path="skills")
        clean_skills = tuple(_check_non_empty_str(s, "skills") for s in self.skills)
        object.__setattr__(self, "skills", clean_skills)

        if isinstance(self.supported_methods, (str, bytes)) or not isinstance(self.supported_methods, (list, tuple)):
            raise _err("supported_methods must be a sequence of strings", path="supported_methods")
        clean_methods = tuple(_check_non_empty_str(m, "supported_methods") for m in self.supported_methods)
        object.__setattr__(self, "supported_methods", clean_methods)

    def satisfies(self, requirements: tuple[str, ...], method: str) -> bool:
        """Check whether executor meets requirement skills and method."""
        skill_set = set(self.skills)
        for req in requirements:
            if req not in skill_set:
                return False
        if self.supported_methods and method not in set(self.supported_methods):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "executor_id": self.executor_id,
            "name": self.name,
            "skills": list(self.skills),
            "supported_methods": list(self.supported_methods),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorDescriptor:
        if not isinstance(data, dict):
            raise _err(f"ExecutorDescriptor data must be a dict, got {type(data).__name__}")
        required = {"executor_id", "name", "skills", "supported_methods"}
        actual = set(data.keys())
        if required != actual:
            raise _err(f"ExecutorDescriptor key mismatch: missing {sorted(required - actual)}")
        return cls(
            executor_id=data["executor_id"],
            name=data["name"],
            skills=data["skills"],
            supported_methods=data["supported_methods"],
        )


@dataclass(frozen=True, slots=True)
class ExecutorAssignment:
    """Frozen value object assigning an experiment contract to an executor."""

    experiment_id: str
    executor_id: str
    allocated_budget: dict[str, float]

    def __post_init__(self) -> None:
        _check_non_empty_str(self.experiment_id, "experiment_id")
        if not _EXECUTOR_ID_RE.match(self.executor_id):
            raise _err("executor_id must match ^EXECUTOR-[A-Za-z0-9._-]+$", path="executor_id")
        if not isinstance(self.allocated_budget, dict):
            raise _err("allocated_budget must be a dict", path="allocated_budget")

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "executor_id": self.executor_id,
            "allocated_budget": dict(self.allocated_budget),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorAssignment:
        if not isinstance(data, dict):
            raise _err("ExecutorAssignment data must be a dict")
        return cls(
            experiment_id=data["experiment_id"],
            executor_id=data["executor_id"],
            allocated_budget=data["allocated_budget"],
        )


@dataclass(frozen=True, slots=True)
class ExecutorRoutingPlan:
    """Frozen value object holding the deterministic routing plan and N_e count."""

    portfolio_id: str
    assignments: tuple[ExecutorAssignment, ...]
    n_e: int

    def __post_init__(self) -> None:
        _check_non_empty_str(self.portfolio_id, "portfolio_id")
        if isinstance(self.assignments, (str, bytes)) or not isinstance(self.assignments, (list, tuple)):
            raise _err("assignments must be a sequence", path="assignments")
        clean_assignments = []
        for i, item in enumerate(self.assignments):
            if isinstance(item, dict):
                clean_assignments.append(ExecutorAssignment.from_dict(item))
            elif isinstance(item, ExecutorAssignment):
                clean_assignments.append(item)
            else:
                raise _err(f"assignments[{i}] invalid type", path=f"assignments[{i}]")
        object.__setattr__(self, "assignments", tuple(clean_assignments))

        unique_executors = {a.executor_id for a in self.assignments}
        expected_n_e = len(unique_executors)
        if isinstance(self.n_e, bool) or not isinstance(self.n_e, int):
            raise ExecutorBudgetError(f"n_e must be an integer, got {type(self.n_e).__name__}", path="n_e")
        if self.n_e != expected_n_e:
            raise ExecutorBudgetError(
                f"n_e ({self.n_e}) must equal the number of unique assigned executors ({expected_n_e})",
                path="n_e",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing_plan": {
                "portfolio_id": self.portfolio_id,
                "assignments": [a.to_dict() for a in self.assignments],
                "n_e": self.n_e,
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutorRoutingPlan:
        if not isinstance(data, dict) or set(data.keys()) != {"routing_plan"}:
            raise _err("Top-level dict must contain key 'routing_plan'")
        rdata = data["routing_plan"]
        return cls(
            portfolio_id=rdata["portfolio_id"],
            assignments=rdata["assignments"],
            n_e=rdata["n_e"],
        )

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


class ExecutorRouter:
    """Deterministic Executor Router for Stage 1."""

    @staticmethod
    def route(
        portfolio: VerificationPortfolio,
        executors: tuple[ExecutorDescriptor, ...],
        n_h: int,
    ) -> ExecutorRoutingPlan:
        """Route experiments in portfolio to available executors and account N_e.

        Enforces invariant: N_h >= N_v >= N_e.
        """
        n_v = portfolio.n_v
        if n_v > n_h:
            raise ExecutorBudgetError(f"Architecture invariant violated: N_v ({n_v}) > N_h ({n_h})", path="n_v")

        if not executors:
            raise UnmatchedRequirementError("No available executors provided for routing", path="executors")

        assignments: list[ExecutorAssignment] = []
        for exp in portfolio.experiments:
            matched_executor: ExecutorDescriptor | None = None
            for ex in executors:
                if ex.satisfies(exp.executor_requirements, exp.method):
                    matched_executor = ex
                    break
            if matched_executor is None:
                raise UnmatchedRequirementError(
                    f"Experiment '{exp.experiment_id}' requires {exp.executor_requirements} with method '{exp.method}', "
                    "no matching executor found",
                    path=f"experiments['{exp.experiment_id}']",
                )
            assignments.append(
                ExecutorAssignment(
                    experiment_id=exp.experiment_id,
                    executor_id=matched_executor.executor_id,
                    allocated_budget=exp.cost_budget,
                )
            )

        unique_executors = {a.executor_id for a in assignments}
        n_e = len(unique_executors)

        if n_e > n_v:
            raise ExecutorBudgetError(f"Architecture invariant violated: N_e ({n_e}) > N_v ({n_v})", path="n_e")

        return ExecutorRoutingPlan(
            portfolio_id=portfolio.portfolio_id,
            assignments=tuple(assignments),
            n_e=n_e,
        )
