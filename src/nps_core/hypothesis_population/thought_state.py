"""Immutable ThoughtState V1 value model.

All value objects are frozen, slotted dataclasses validated on construction.
Serialization produces plain dict/list structures compatible with the V1
JSON schema.  No runtime dependencies beyond the Python standard library.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from nps_core.hypothesis_population.errors import ValidationError

__all__ = [
    "VALID_STATES",
    "VALID_STATE_SET",
    "TERMINAL_STATES",
    "PRUNE_DISPOSITIONS",
    "Interpretation",
    "Hypothesis",
    "Assumption",
    "Evidence",
    "Metrics",
    "VerificationPlan",
    "ExecutorProfile",
    "Graph",
    "Status",
    "ThoughtState",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STATES: tuple[str, ...] = (
    "active",
    "queued",
    "testing",
    "partially_verified",
    "verified",
    "rejected",
    "merged",
    "dormant",
)

VALID_STATE_SET: frozenset[str] = frozenset(VALID_STATES)

TERMINAL_STATES: frozenset[str] = frozenset({"rejected", "merged", "dormant"})

PRUNE_DISPOSITIONS: frozenset[str] = frozenset({"rejected", "dormant"})

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")

_ISO_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("must be a dict", path=path)
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError("must be a list", path=path)
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("must be a string", path=path)
    return value


def _string_list_to_tuple(items: list[Any], path: str) -> tuple[str, ...]:
    result: list[str] = []
    for i, item in enumerate(items):
        p = f"{path}[{i}]"
        if not isinstance(item, str):
            raise ValidationError("must be a string", path=p)
        result.append(item)
    return tuple(result)


def _check_non_empty(value: str, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("must be a non-empty string", path=path)


def _check_string_tuple(items: tuple[str, ...], path: str) -> None:
    seen: set[str] = set()
    for i, item in enumerate(items):
        p = f"{path}[{i}]"
        _check_non_empty(item, p)
        if item in seen:
            raise ValidationError(f"duplicate value: {item!r}", path=p)
        seen.add(item)


def _check_confidence(value: Any, path: str) -> float:
    if isinstance(value, bool):
        raise ValidationError("must be a number, not bool", path=path)
    if not isinstance(value, (int, float)):
        raise ValidationError("must be a number", path=path)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("must be finite", path=path)
    try:
        f = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError("must be a finite number", path=path) from exc
    if not math.isfinite(f):
        raise ValidationError("must be finite", path=path)
    if f < 0 or f > 1:
        raise ValidationError(
            "must be between 0 and 1 inclusive", path=path
        )
    return f


def _validate_dict_keys(
    data: dict[str, Any],
    required: frozenset[str],
    path: str,
) -> None:
    missing = required - data.keys()
    if missing:
        raise ValidationError(
            f"missing required keys: {sorted(missing)}",
            path=path,
        )
    extra = data.keys() - required
    if extra:
        raise ValidationError(
            f"unexpected keys: {sorted(extra)}",
            path=path,
        )


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Interpretation:
    """Interpretation sub-object of a ThoughtState."""

    summary: str
    scope: str
    excluded_scope: tuple[str, ...]

    def __post_init__(self) -> None:
        _check_non_empty(self.summary, "interpretation.summary")
        _check_non_empty(self.scope, "interpretation.scope")
        if not isinstance(self.excluded_scope, tuple):
            raise ValidationError(
                "excluded_scope must be a tuple",
                path="interpretation.excluded_scope",
            )
        _check_string_tuple(self.excluded_scope, "interpretation.excluded_scope")


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """Hypothesis sub-object of a ThoughtState."""

    claim: str
    predicted_observations: tuple[str, ...]
    falsification_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        _check_non_empty(self.claim, "hypothesis.claim")
        if not isinstance(self.predicted_observations, tuple):
            raise ValidationError(
                "predicted_observations must be a tuple",
                path="hypothesis.predicted_observations",
            )
        _check_string_tuple(
            self.predicted_observations, "hypothesis.predicted_observations"
        )
        if not isinstance(self.falsification_conditions, tuple):
            raise ValidationError(
                "falsification_conditions must be a tuple",
                path="hypothesis.falsification_conditions",
            )
        _check_string_tuple(
            self.falsification_conditions, "hypothesis.falsification_conditions"
        )


@dataclass(frozen=True, slots=True)
class Assumption:
    """Single assumption entry."""

    assumption_id: str
    statement: str
    confidence: float
    source: str

    def __post_init__(self) -> None:
        _check_non_empty(self.assumption_id, "assumptions[].assumption_id")
        _check_non_empty(self.statement, "assumptions[].statement")
        _check_non_empty(self.source, "assumptions[].source")
        checked = _check_confidence(self.confidence, "assumptions[].confidence")
        object.__setattr__(self, "confidence", checked)


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidence sub-object of a ThoughtState."""

    supporting: tuple[str, ...]
    opposing: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("supporting", "opposing", "unresolved"):
            val = getattr(self, name)
            if not isinstance(val, tuple):
                raise ValidationError(
                    f"{name} must be a tuple",
                    path=f"evidence.{name}",
                )
            _check_string_tuple(val, f"evidence.{name}")


@dataclass(frozen=True, slots=True)
class Metrics:
    """Metrics sub-object of a ThoughtState."""

    confidence: float
    novelty: float
    diversity: float
    expected_value: float
    information_need: float
    risk_if_wrong: float
    execution_cost: float

    def __post_init__(self) -> None:
        for name in (
            "confidence",
            "novelty",
            "diversity",
            "expected_value",
            "information_need",
            "risk_if_wrong",
            "execution_cost",
        ):
            val = getattr(self, name)
            checked = _check_confidence(val, f"metrics.{name}")
            object.__setattr__(self, name, checked)


@dataclass(frozen=True, slots=True)
class VerificationPlan:
    """Verification plan sub-object."""

    questions: tuple[str, ...]
    required_experiments: tuple[str, ...]
    acceptable_evidence: tuple[str, ...]
    rejection_threshold: float

    def __post_init__(self) -> None:
        for name in ("questions", "required_experiments", "acceptable_evidence"):
            val = getattr(self, name)
            if not isinstance(val, tuple):
                raise ValidationError(
                    f"{name} must be a tuple",
                    path=f"verification_plan.{name}",
                )
            _check_string_tuple(val, f"verification_plan.{name}")
        checked = _check_confidence(
            self.rejection_threshold, "verification_plan.rejection_threshold"
        )
        object.__setattr__(self, "rejection_threshold", checked)


@dataclass(frozen=True, slots=True)
class ExecutorProfile:
    """Executor profile sub-object."""

    skills: tuple[str, ...]
    tool_requirements: tuple[str, ...]
    preferred_model_class: str
    independence_requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("skills", "tool_requirements", "independence_requirements"):
            val = getattr(self, name)
            if not isinstance(val, tuple):
                raise ValidationError(
                    f"{name} must be a tuple",
                    path=f"executor_profile.{name}",
                )
            _check_string_tuple(val, f"executor_profile.{name}")
        _check_non_empty(
            self.preferred_model_class, "executor_profile.preferred_model_class"
        )


@dataclass(frozen=True, slots=True)
class Graph:
    """Graph sub-object of a ThoughtState."""

    dependencies: tuple[str, ...]
    contradictions: tuple[str, ...]
    overlaps: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("dependencies", "contradictions", "overlaps"):
            val = getattr(self, name)
            if not isinstance(val, tuple):
                raise ValidationError(
                    f"{name} must be a tuple",
                    path=f"graph.{name}",
                )
            _check_string_tuple(val, f"graph.{name}")


@dataclass(frozen=True, slots=True)
class Status:
    """Status sub-object of a ThoughtState."""

    state: str
    allowed_values: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.state not in VALID_STATE_SET:
            raise ValidationError(
                f"invalid state: {self.state!r}",
                path="status.state",
            )
        if self.allowed_values != VALID_STATES:
            raise ValidationError(
                "allowed_values must exactly equal VALID_STATES",
                path="status.allowed_values",
            )


@dataclass(frozen=True, slots=True)
class ThoughtState:
    """Immutable ThoughtState V1 value model."""

    thought_id: str
    parent_ids: tuple[str, ...]
    created_at: str
    interpretation: Interpretation
    hypothesis: Hypothesis
    assumptions: tuple[Assumption, ...]
    evidence: Evidence
    metrics: Metrics
    verification_plan: VerificationPlan
    executor_profile: ExecutorProfile
    graph: Graph
    status: Status

    def __post_init__(self) -> None:
        # thought_id
        if not isinstance(self.thought_id, str) or not _THOUGHT_ID_RE.match(
            self.thought_id
        ):
            raise ValidationError(
                "thought_id must match ^THOUGHT-[A-Za-z0-9._-]+$",
                path="thought_id",
            )

        # parent_ids
        if not isinstance(self.parent_ids, tuple):
            raise ValidationError("parent_ids must be a tuple", path="parent_ids")
        _check_string_tuple(self.parent_ids, "parent_ids")
        if self.thought_id in self.parent_ids:
            raise ValidationError(
                "parent_ids cannot contain the thought's own ID",
                path="parent_ids",
            )

        # created_at
        if not isinstance(self.created_at, str):
            raise ValidationError("created_at must be a string", path="created_at")
        if not _ISO_Z_RE.match(self.created_at):
            raise ValidationError(
                "created_at must be RFC3339/ISO-8601 timezone-aware",
                path="created_at",
            )
        raw = self.created_at
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                f"created_at is not a valid ISO-8601 datetime: {exc}",
                path="created_at",
            ) from exc
        if dt.tzinfo is None:
            raise ValidationError(
                "created_at must be timezone-aware",
                path="created_at",
            )

        # assumptions
        if not isinstance(self.assumptions, tuple):
            raise ValidationError(
                "assumptions must be a tuple", path="assumptions"
            )
        seen_ids: set[str] = set()
        for i, a in enumerate(self.assumptions):
            if not isinstance(a, Assumption):
                raise ValidationError(
                    "each assumption must be an Assumption",
                    path=f"assumptions[{i}]",
                )
            if a.assumption_id in seen_ids:
                raise ValidationError(
                    f"duplicate assumption_id: {a.assumption_id!r}",
                    path=f"assumptions[{i}].assumption_id",
                )
            seen_ids.add(a.assumption_id)

        # nested types
        if not isinstance(self.interpretation, Interpretation):
            raise ValidationError(
                "interpretation must be an Interpretation",
                path="interpretation",
            )
        if not isinstance(self.hypothesis, Hypothesis):
            raise ValidationError(
                "hypothesis must be a Hypothesis",
                path="hypothesis",
            )
        if not isinstance(self.evidence, Evidence):
            raise ValidationError("evidence must be an Evidence", path="evidence")
        if not isinstance(self.metrics, Metrics):
            raise ValidationError("metrics must be a Metrics", path="metrics")
        if not isinstance(self.verification_plan, VerificationPlan):
            raise ValidationError(
                "verification_plan must be a VerificationPlan",
                path="verification_plan",
            )
        if not isinstance(self.executor_profile, ExecutorProfile):
            raise ValidationError(
                "executor_profile must be an ExecutorProfile",
                path="executor_profile",
            )
        if not isinstance(self.graph, Graph):
            raise ValidationError("graph must be a Graph", path="graph")
        if not isinstance(self.status, Status):
            raise ValidationError("status must be a Status", path="status")

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThoughtState:
        """Construct a ThoughtState from a plain dict.

        Validates all keys and values; rejects missing or extra keys at
        every level.
        """
        _require_dict(data, "")

        required = frozenset({
            "thought_id",
            "parent_ids",
            "created_at",
            "interpretation",
            "hypothesis",
            "assumptions",
            "evidence",
            "metrics",
            "verification_plan",
            "executor_profile",
            "graph",
            "status",
        })
        _validate_dict_keys(data, required, "")

        # --- thought_id ---
        thought_id = _require_string(data["thought_id"], "thought_id")

        # --- parent_ids ---
        parent_ids_raw = _require_list(data["parent_ids"], "parent_ids")
        parent_ids = _string_list_to_tuple(parent_ids_raw, "parent_ids")

        # --- created_at ---
        created_at = _require_string(data["created_at"], "created_at")

        # --- interpretation ---
        interp_raw = _require_dict(data["interpretation"], "interpretation")
        _validate_dict_keys(
            interp_raw,
            frozenset({"summary", "scope", "excluded_scope"}),
            "interpretation",
        )
        summary = _require_string(interp_raw["summary"], "interpretation.summary")
        scope = _require_string(interp_raw["scope"], "interpretation.scope")
        excl_raw = _require_list(
            interp_raw["excluded_scope"], "interpretation.excluded_scope"
        )
        excluded_scope = _string_list_to_tuple(
            excl_raw, "interpretation.excluded_scope"
        )
        interpretation = Interpretation(
            summary=summary,
            scope=scope,
            excluded_scope=excluded_scope,
        )

        # --- hypothesis ---
        hyp_raw = _require_dict(data["hypothesis"], "hypothesis")
        _validate_dict_keys(
            hyp_raw,
            frozenset({"claim", "predicted_observations", "falsification_conditions"}),
            "hypothesis",
        )
        claim = _require_string(hyp_raw["claim"], "hypothesis.claim")
        pred_raw = _require_list(
            hyp_raw["predicted_observations"], "hypothesis.predicted_observations"
        )
        predicted_observations = _string_list_to_tuple(
            pred_raw, "hypothesis.predicted_observations"
        )
        fals_raw = _require_list(
            hyp_raw["falsification_conditions"],
            "hypothesis.falsification_conditions",
        )
        falsification_conditions = _string_list_to_tuple(
            fals_raw, "hypothesis.falsification_conditions"
        )
        hypothesis = Hypothesis(
            claim=claim,
            predicted_observations=predicted_observations,
            falsification_conditions=falsification_conditions,
        )

        # --- assumptions ---
        assumptions_raw = _require_list(data["assumptions"], "assumptions")
        assumptions_list: list[Assumption] = []
        for i, a_raw in enumerate(assumptions_raw):
            a_path = f"assumptions[{i}]"
            a_dict = _require_dict(a_raw, a_path)
            _validate_dict_keys(
                a_dict,
                frozenset({"assumption_id", "statement", "confidence", "source"}),
                a_path,
            )
            assumptions_list.append(
                Assumption(
                    assumption_id=_require_string(
                        a_dict["assumption_id"], f"{a_path}.assumption_id"
                    ),
                    statement=_require_string(
                        a_dict["statement"], f"{a_path}.statement"
                    ),
                    confidence=_check_confidence(
                        a_dict["confidence"], f"{a_path}.confidence"
                    ),
                    source=_require_string(
                        a_dict["source"], f"{a_path}.source"
                    ),
                )
            )
        assumptions = tuple(assumptions_list)

        # --- evidence ---
        ev_raw = _require_dict(data["evidence"], "evidence")
        _validate_dict_keys(
            ev_raw,
            frozenset({"supporting", "opposing", "unresolved"}),
            "evidence",
        )
        supporting_raw = _require_list(ev_raw["supporting"], "evidence.supporting")
        opposing_raw = _require_list(ev_raw["opposing"], "evidence.opposing")
        unresolved_raw = _require_list(ev_raw["unresolved"], "evidence.unresolved")
        evidence = Evidence(
            supporting=_string_list_to_tuple(supporting_raw, "evidence.supporting"),
            opposing=_string_list_to_tuple(opposing_raw, "evidence.opposing"),
            unresolved=_string_list_to_tuple(unresolved_raw, "evidence.unresolved"),
        )

        # --- metrics ---
        met_raw = _require_dict(data["metrics"], "metrics")
        _validate_dict_keys(
            met_raw,
            frozenset({
                "confidence",
                "novelty",
                "diversity",
                "expected_value",
                "information_need",
                "risk_if_wrong",
                "execution_cost",
            }),
            "metrics",
        )
        metrics = Metrics(
            confidence=_check_confidence(met_raw["confidence"], "metrics.confidence"),
            novelty=_check_confidence(met_raw["novelty"], "metrics.novelty"),
            diversity=_check_confidence(met_raw["diversity"], "metrics.diversity"),
            expected_value=_check_confidence(
                met_raw["expected_value"], "metrics.expected_value"
            ),
            information_need=_check_confidence(
                met_raw["information_need"], "metrics.information_need"
            ),
            risk_if_wrong=_check_confidence(
                met_raw["risk_if_wrong"], "metrics.risk_if_wrong"
            ),
            execution_cost=_check_confidence(
                met_raw["execution_cost"], "metrics.execution_cost"
            ),
        )

        # --- verification_plan ---
        vp_raw = _require_dict(data["verification_plan"], "verification_plan")
        _validate_dict_keys(
            vp_raw,
            frozenset({
                "questions",
                "required_experiments",
                "acceptable_evidence",
                "rejection_threshold",
            }),
            "verification_plan",
        )
        questions_raw = _require_list(
            vp_raw["questions"], "verification_plan.questions"
        )
        req_exp_raw = _require_list(
            vp_raw["required_experiments"], "verification_plan.required_experiments"
        )
        acc_ev_raw = _require_list(
            vp_raw["acceptable_evidence"], "verification_plan.acceptable_evidence"
        )
        verification_plan = VerificationPlan(
            questions=_string_list_to_tuple(
                questions_raw, "verification_plan.questions"
            ),
            required_experiments=_string_list_to_tuple(
                req_exp_raw, "verification_plan.required_experiments"
            ),
            acceptable_evidence=_string_list_to_tuple(
                acc_ev_raw, "verification_plan.acceptable_evidence"
            ),
            rejection_threshold=_check_confidence(
                vp_raw["rejection_threshold"],
                "verification_plan.rejection_threshold",
            ),
        )

        # --- executor_profile ---
        ep_raw = _require_dict(data["executor_profile"], "executor_profile")
        _validate_dict_keys(
            ep_raw,
            frozenset({
                "skills",
                "tool_requirements",
                "preferred_model_class",
                "independence_requirements",
            }),
            "executor_profile",
        )
        skills_raw = _require_list(ep_raw["skills"], "executor_profile.skills")
        tool_req_raw = _require_list(
            ep_raw["tool_requirements"], "executor_profile.tool_requirements"
        )
        preferred_model_class = _require_string(
            ep_raw["preferred_model_class"],
            "executor_profile.preferred_model_class",
        )
        indep_raw = _require_list(
            ep_raw["independence_requirements"],
            "executor_profile.independence_requirements",
        )
        executor_profile = ExecutorProfile(
            skills=_string_list_to_tuple(skills_raw, "executor_profile.skills"),
            tool_requirements=_string_list_to_tuple(
                tool_req_raw, "executor_profile.tool_requirements"
            ),
            preferred_model_class=preferred_model_class,
            independence_requirements=_string_list_to_tuple(
                indep_raw, "executor_profile.independence_requirements"
            ),
        )

        # --- graph ---
        g_raw = _require_dict(data["graph"], "graph")
        _validate_dict_keys(
            g_raw,
            frozenset({"dependencies", "contradictions", "overlaps"}),
            "graph",
        )
        deps_raw = _require_list(g_raw["dependencies"], "graph.dependencies")
        contra_raw = _require_list(g_raw["contradictions"], "graph.contradictions")
        overlaps_raw = _require_list(g_raw["overlaps"], "graph.overlaps")
        graph = Graph(
            dependencies=_string_list_to_tuple(deps_raw, "graph.dependencies"),
            contradictions=_string_list_to_tuple(
                contra_raw, "graph.contradictions"
            ),
            overlaps=_string_list_to_tuple(overlaps_raw, "graph.overlaps"),
        )

        # --- status ---
        st_raw = _require_dict(data["status"], "status")
        _validate_dict_keys(
            st_raw, frozenset({"state", "allowed_values"}), "status"
        )
        state = _require_string(st_raw["state"], "status.state")
        allowed_raw = _require_list(
            st_raw["allowed_values"], "status.allowed_values"
        )
        allowed_values = _string_list_to_tuple(
            allowed_raw, "status.allowed_values"
        )
        status = Status(
            state=state,
            allowed_values=allowed_values,
        )

        return cls(
            thought_id=thought_id,
            parent_ids=parent_ids,
            created_at=created_at,
            interpretation=interpretation,
            hypothesis=hypothesis,
            assumptions=assumptions,
            evidence=evidence,
            metrics=metrics,
            verification_plan=verification_plan,
            executor_profile=executor_profile,
            graph=graph,
            status=status,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict/list structure compatible with V1 schema.

        Preserves tuple order.  Does not use ``dataclasses.asdict``.
        """

        def _interp(v: Interpretation) -> dict[str, Any]:
            return {
                "summary": v.summary,
                "scope": v.scope,
                "excluded_scope": list(v.excluded_scope),
            }

        def _hyp(v: Hypothesis) -> dict[str, Any]:
            return {
                "claim": v.claim,
                "predicted_observations": list(v.predicted_observations),
                "falsification_conditions": list(v.falsification_conditions),
            }

        def _assump(v: Assumption) -> dict[str, Any]:
            return {
                "assumption_id": v.assumption_id,
                "statement": v.statement,
                "confidence": float(v.confidence),
                "source": v.source,
            }

        def _evid(v: Evidence) -> dict[str, Any]:
            return {
                "supporting": list(v.supporting),
                "opposing": list(v.opposing),
                "unresolved": list(v.unresolved),
            }

        def _met(v: Metrics) -> dict[str, Any]:
            return {
                "confidence": float(v.confidence),
                "novelty": float(v.novelty),
                "diversity": float(v.diversity),
                "expected_value": float(v.expected_value),
                "information_need": float(v.information_need),
                "risk_if_wrong": float(v.risk_if_wrong),
                "execution_cost": float(v.execution_cost),
            }

        def _vp(v: VerificationPlan) -> dict[str, Any]:
            return {
                "questions": list(v.questions),
                "required_experiments": list(v.required_experiments),
                "acceptable_evidence": list(v.acceptable_evidence),
                "rejection_threshold": float(v.rejection_threshold),
            }

        def _ep(v: ExecutorProfile) -> dict[str, Any]:
            return {
                "skills": list(v.skills),
                "tool_requirements": list(v.tool_requirements),
                "preferred_model_class": v.preferred_model_class,
                "independence_requirements": list(v.independence_requirements),
            }

        def _graph(v: Graph) -> dict[str, Any]:
            return {
                "dependencies": list(v.dependencies),
                "contradictions": list(v.contradictions),
                "overlaps": list(v.overlaps),
            }

        def _status(v: Status) -> dict[str, Any]:
            return {
                "state": v.state,
                "allowed_values": list(v.allowed_values),
            }

        return {
            "thought_id": self.thought_id,
            "parent_ids": list(self.parent_ids),
            "created_at": self.created_at,
            "interpretation": _interp(self.interpretation),
            "hypothesis": _hyp(self.hypothesis),
            "assumptions": [_assump(a) for a in self.assumptions],
            "evidence": _evid(self.evidence),
            "metrics": _met(self.metrics),
            "verification_plan": _vp(self.verification_plan),
            "executor_profile": _ep(self.executor_profile),
            "graph": _graph(self.graph),
            "status": _status(self.status),
        }

    def with_status(self, state: str) -> ThoughtState:
        """Return a new ThoughtState with the given status state.

        Uses ``dataclasses.replace``; the original is never mutated.
        The canonical ``allowed_values`` tuple is preserved.
        """
        if state not in VALID_STATE_SET:
            raise ValidationError(
                f"invalid state: {state!r}",
                path="status.state",
            )
        new_status = Status(state=state, allowed_values=VALID_STATES)
        return replace(self, status=new_status)
