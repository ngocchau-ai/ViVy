"""Immutable ExperimentContract value model.

Conforms strictly to schemas/experiment.schema.json.
All value objects are frozen, slotted dataclasses validated on construction.
Serialization produces plain dict/list structures matching the JSON schema.
Standard-library only; no runtime dependencies beyond standard library.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from nps_core.experiment_designer.errors import ExperimentValidationError

__all__ = [
    "ExperimentContract",
]

_EXP_ID_RE = re.compile(r"^EXP-[A-Za-z0-9._-]+$")


def _err(msg: str, *, path: str | None = None) -> ExperimentValidationError:
    return ExperimentValidationError(msg, path=path)


def _check_non_empty_str(val: Any, path: str) -> str:
    if isinstance(val, bool) or not isinstance(val, str):
        raise _err(f"must be a string, got {type(val).__name__}", path=path)
    if not val.strip():
        raise _err("must be a non-empty string", path=path)
    return val


def _check_str_tuple(items: Any, path: str) -> tuple[str, ...]:
    if isinstance(items, (str, bytes)) or not isinstance(items, (list, tuple)):
        raise _err(f"must be a sequence of strings, got {type(items).__name__}", path=path)
    res: list[str] = []
    for i, item in enumerate(items):
        res.append(_check_non_empty_str(item, f"{path}[{i}]"))
    return tuple(res)


def _check_float_range(
    val: Any,
    path: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise _err(f"must be a number, got {type(val).__name__}", path=path)
    fval = float(val)
    if math.isnan(fval) or math.isinf(fval):
        raise _err("must be a finite number", path=path)
    if min_val is not None and fval < min_val:
        raise _err(f"must be >= {min_val}, got {fval}", path=path)
    if max_val is not None and fval > max_val:
        raise _err(f"must be <= {max_val}, got {fval}", path=path)
    return fval


@dataclass(frozen=True, slots=True)
class ExperimentContract:
    """Frozen, schema-compatible ExperimentContract."""

    experiment_id: str
    objective: str
    hypotheses_tested: tuple[str, ...]
    discriminating_outcomes: dict[str, str]
    method: str
    executor_requirements: tuple[str, ...]
    cost_budget: dict[str, float]
    stop_conditions: tuple[str, ...]
    expected_information_gain: float
    acceptance_schema: str

    def __post_init__(self) -> None:
        # experiment_id
        if isinstance(self.experiment_id, bool) or not isinstance(self.experiment_id, str):
            raise _err(f"experiment_id must be a string, got {type(self.experiment_id).__name__}", path="experiment.experiment_id")
        if not _EXP_ID_RE.match(self.experiment_id):
            raise _err("experiment_id must match ^EXP-[A-Za-z0-9._-]+$", path="experiment.experiment_id")

        # objective
        _check_non_empty_str(self.objective, "experiment.objective")

        # hypotheses_tested
        hyps = _check_str_tuple(self.hypotheses_tested, "experiment.hypotheses_tested")
        if not hyps:
            raise _err("hypotheses_tested must contain at least 1 item", path="experiment.hypotheses_tested")
        object.__setattr__(self, "hypotheses_tested", hyps)

        # discriminating_outcomes
        if not isinstance(self.discriminating_outcomes, dict):
            raise _err(f"discriminating_outcomes must be a dict, got {type(self.discriminating_outcomes).__name__}", path="experiment.discriminating_outcomes")
        if not self.discriminating_outcomes:
            raise _err("discriminating_outcomes must contain at least 1 property", path="experiment.discriminating_outcomes")
        clean_outcomes: dict[str, str] = {}
        for k, v in self.discriminating_outcomes.items():
            clean_k = _check_non_empty_str(k, f"experiment.discriminating_outcomes key '{k}'")
            clean_v = _check_non_empty_str(v, f"experiment.discriminating_outcomes['{k}']")
            clean_outcomes[clean_k] = clean_v
        object.__setattr__(self, "discriminating_outcomes", dict(clean_outcomes))

        # method
        _check_non_empty_str(self.method, "experiment.method")

        # executor_requirements
        exec_reqs = _check_str_tuple(self.executor_requirements, "experiment.executor_requirements")
        object.__setattr__(self, "executor_requirements", exec_reqs)

        # cost_budget
        if not isinstance(self.cost_budget, dict):
            raise _err(f"cost_budget must be a dict, got {type(self.cost_budget).__name__}", path="experiment.cost_budget")
        clean_budget: dict[str, float] = {}
        for k, v in self.cost_budget.items():
            clean_k = _check_non_empty_str(k, f"experiment.cost_budget key '{k}'")
            clean_v = _check_float_range(v, f"experiment.cost_budget['{k}']", min_val=0.0)
            clean_budget[clean_k] = clean_v
        object.__setattr__(self, "cost_budget", dict(clean_budget))

        # stop_conditions
        stops = _check_str_tuple(self.stop_conditions, "experiment.stop_conditions")
        object.__setattr__(self, "stop_conditions", stops)

        # expected_information_gain
        clean_eig = _check_float_range(self.expected_information_gain, "experiment.expected_information_gain", min_val=0.0, max_val=1.0)
        object.__setattr__(self, "expected_information_gain", clean_eig)

        # acceptance_schema
        _check_non_empty_str(self.acceptance_schema, "experiment.acceptance_schema")

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain dict conforming to schemas/experiment.schema.json."""
        return {
            "experiment": {
                "experiment_id": self.experiment_id,
                "objective": self.objective,
                "hypotheses_tested": list(self.hypotheses_tested),
                "discriminating_outcomes": dict(self.discriminating_outcomes),
                "method": self.method,
                "executor_requirements": list(self.executor_requirements),
                "cost_budget": dict(self.cost_budget),
                "stop_conditions": list(self.stop_conditions),
                "expected_information_gain": self.expected_information_gain,
                "acceptance_schema": self.acceptance_schema,
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentContract:
        """Construct from raw dict with strict validation."""
        if not isinstance(data, dict):
            raise _err(f"Input data must be a dict, got {type(data).__name__}", path="root")
        if set(data.keys()) != {"experiment"}:
            raise _err("Top-level dict must contain exactly one key: 'experiment'", path="root")

        exp_data = data["experiment"]
        if not isinstance(exp_data, dict):
            raise _err(f"'experiment' must be a dict, got {type(exp_data).__name__}", path="experiment")

        required_keys = {
            "experiment_id",
            "objective",
            "hypotheses_tested",
            "discriminating_outcomes",
            "method",
            "executor_requirements",
            "cost_budget",
            "stop_conditions",
            "expected_information_gain",
            "acceptance_schema",
        }

        actual_keys = set(exp_data.keys())
        missing = required_keys - actual_keys
        if missing:
            raise _err(f"Missing required fields: {sorted(missing)}", path="experiment")
        extra = actual_keys - required_keys
        if extra:
            raise _err(f"Unexpected extra fields: {sorted(extra)}", path="experiment")

        return cls(
            experiment_id=exp_data["experiment_id"],
            objective=exp_data["objective"],
            hypotheses_tested=exp_data["hypotheses_tested"],
            discriminating_outcomes=exp_data["discriminating_outcomes"],
            method=exp_data["method"],
            executor_requirements=exp_data["executor_requirements"],
            cost_budget=exp_data["cost_budget"],
            stop_conditions=exp_data["stop_conditions"],
            expected_information_gain=exp_data["expected_information_gain"],
            acceptance_schema=exp_data["acceptance_schema"],
        )

    def to_canonical_json(self) -> str:
        """Produce deterministic canonical JSON representation."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def digest(self) -> str:
        """SHA-256 hex digest of canonical JSON representation."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()
