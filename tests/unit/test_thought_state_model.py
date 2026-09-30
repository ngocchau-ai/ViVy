"""Unit tests for ThoughtState model, serialization, and schema compliance."""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402

from nps_core.hypothesis_population import (  # noqa: E402
    Assumption,
    Evidence,
    ExecutorProfile,
    Graph,
    Hypothesis,
    Interpretation,
    Metrics,
    Status,
    ThoughtState,
    ValidationError,
    VerificationPlan,
    canonical_json,
    parse_json,
    thought_state_from_dict,
    thought_state_from_json,
    thought_state_to_dict,
    CANONICAL_SEPARATORS,
    VALID_STATES,
    VALID_STATE_SET,
    TERMINAL_STATES,
    PRUNE_DISPOSITIONS,
)

_SCHEMA_PATH = Path("schemas/thought_state.schema.json")


@pytest.fixture(scope="session")
def schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def validator(schema: dict[str, Any]) -> Draft202012Validator:
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _canonical_dict(
    *,
    thought_id: str = "THOUGHT-abc-001",
    parent_ids: list[str] | None = None,
    created_at: str = "2025-01-15T10:30:00+00:00",
    status_state: str = "active",
) -> dict[str, Any]:
    if parent_ids is None:
        parent_ids = []
    return {
        "thought_id": thought_id,
        "parent_ids": parent_ids,
        "created_at": created_at,
        "interpretation": {
            "summary": "Test summary",
            "scope": "global",
            "excluded_scope": [],
        },
        "hypothesis": {
            "claim": "The sky is blue",
            "predicted_observations": ["blue colour observed"],
            "falsification_conditions": ["sky is not blue"],
        },
        "assumptions": [
            {
                "assumption_id": "ASM-001",
                "statement": "Light scattering applies",
                "confidence": 0.9,
                "source": "physics",
            }
        ],
        "evidence": {
            "supporting": ["observation-1"],
            "opposing": [],
            "unresolved": [],
        },
        "metrics": {
            "confidence": 0.8,
            "novelty": 0.5,
            "diversity": 0.3,
            "expected_value": 0.7,
            "information_need": 0.2,
            "risk_if_wrong": 0.4,
            "execution_cost": 0.1,
        },
        "verification_plan": {
            "questions": ["Is the sky blue?"],
            "required_experiments": ["visual-inspection"],
            "acceptable_evidence": ["spectrometer-reading"],
            "rejection_threshold": 0.1,
        },
        "executor_profile": {
            "skills": ["observation"],
            "tool_requirements": ["spectrometer"],
            "preferred_model_class": "vision",
            "independence_requirements": ["no-bias"],
        },
        "graph": {
            "dependencies": [],
            "contradictions": [],
            "overlaps": [],
        },
        "status": {
            "state": status_state,
            "allowed_values": list(VALID_STATES),
        },
    }


def _mutate(d: dict, path: str, value: Any) -> dict:
    """Set a dotted-path key in a nested dict, returning the same dict.

    Supports decimal list indices (e.g. ``assumptions.0.confidence``).
    """
    keys = path.split(".")
    obj = d
    for k in keys[:-1]:
        if isinstance(obj, list) and k.isdigit():
            obj = obj[int(k)]
        else:
            obj = obj[k]
    last = keys[-1]
    if isinstance(obj, list) and last.isdigit():
        obj[int(last)] = value
    else:
        obj[last] = value
    return d


def _delete(d: dict, path: str) -> dict:
    """Delete a dotted-path key from a nested dict.

    Supports decimal list indices (e.g. ``assumptions.0.confidence``).
    """
    keys = path.split(".")
    obj = d
    for k in keys[:-1]:
        if isinstance(obj, list) and k.isdigit():
            obj = obj[int(k)]
        else:
            obj = obj[k]
    last = keys[-1]
    if isinstance(obj, list) and last.isdigit():
        del obj[int(last)]
    else:
        del obj[last]
    return d


# --- Canonical construction and lossless round-trip ---

def test_from_dict_returns_thought_state() -> None:
    assert isinstance(ThoughtState.from_dict(_canonical_dict()), ThoughtState)


def test_to_dict_round_trip() -> None:
    d = _canonical_dict()
    assert ThoughtState.from_dict(d).to_dict() == d


def test_from_dict_to_dict_round_trip() -> None:
    d = _canonical_dict()
    assert thought_state_to_dict(thought_state_from_dict(d)) == d


def test_from_json_to_json_round_trip() -> None:
    d = _canonical_dict()
    j = json.dumps(d, sort_keys=True, separators=(",", ":"))
    assert thought_state_to_dict(thought_state_from_json(j)) == d


def test_parent_ids_preserved() -> None:
    d = _canonical_dict(parent_ids=["THOUGHT-parent-1", "THOUGHT-parent-2"])
    assert ThoughtState.from_dict(d).parent_ids == ("THOUGHT-parent-1", "THOUGHT-parent-2")


def test_assumptions_preserved() -> None:
    ts = ThoughtState.from_dict(_canonical_dict())
    assert len(ts.assumptions) == 1
    assert ts.assumptions[0].assumption_id == "ASM-001"


# --- Frozen / deep immutable nested values ---

@pytest.mark.parametrize(
    "mutator",
    [
        lambda ts: setattr(ts, "thought_id", "THOUGHT-xxx"),
        lambda ts: setattr(ts.interpretation, "summary", "mutated"),
        lambda ts: setattr(ts.metrics, "confidence", 0.0),
        lambda ts: setattr(ts.status, "state", "rejected"),
        lambda ts: setattr(ts.assumptions[0], "confidence", 0.0),
    ],
    ids=["top", "interpretation", "metrics", "status", "assumption"],
)
def test_frozen_rejects_mutation(mutator: Any) -> None:
    ts = ThoughtState.from_dict(_canonical_dict())
    with pytest.raises(AttributeError):
        mutator(ts)


def test_parent_ids_tuple_immutable() -> None:
    ts = ThoughtState.from_dict(_canonical_dict())
    assert isinstance(ts.parent_ids, tuple)
    with pytest.raises(AttributeError):
        ts.parent_ids.append("x")  # type: ignore[attr-defined]


def test_with_status_returns_new_instance() -> None:
    ts = ThoughtState.from_dict(_canonical_dict())
    ts2 = ts.with_status("testing")
    assert ts.status.state == "active"
    assert ts2.status.state == "testing"
    assert ts is not ts2


# --- Canonical JSON byte determinism and unicode preservation ---

def test_canonical_json_byte_identical() -> None:
    ts = ThoughtState.from_dict(_canonical_dict())
    j1, j2 = canonical_json(ts), canonical_json(ts)
    assert j1 == j2
    assert j1.encode("utf-8") == j2.encode("utf-8")


def test_canonical_json_sorted_keys() -> None:
    j = canonical_json(ThoughtState.from_dict(_canonical_dict()))
    assert j == json.dumps(json.loads(j), sort_keys=True, separators=(",", ":"))


def test_canonical_json_compact_separators() -> None:
    j = canonical_json(ThoughtState.from_dict(_canonical_dict()))
    assert ", " not in j and ": " not in j


def test_canonical_json_unicode_preserved() -> None:
    d = _canonical_dict()
    _mutate(d, "interpretation.summary", "ÃnÃ¯cÃ¶dÃ© æµè¯ ??")
    j = canonical_json(ThoughtState.from_dict(d))
    assert "ÃnÃ¯cÃ¶dÃ© æµè¯ ??" in j
    assert "\\u" not in j


def test_canonical_json_on_dict() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_canonical_json_on_list() -> None:
    assert canonical_json([3, 1, 2]) == "[3,1,2]"


def test_canonical_json_rejects_non_serializable() -> None:
    with pytest.raises(ValidationError, match="canonical_json requires"):
        canonical_json(42)  # type: ignore[arg-type]


def test_canonical_json_rejects_nan() -> None:
    with pytest.raises(ValidationError, match="JSON serialization failed"):
        canonical_json({"v": float("nan")})


def test_canonical_separators_constant() -> None:
    assert CANONICAL_SEPARATORS == (",", ":")


# --- Schema validation ---

def test_canonical_dict_validates(validator: Draft202012Validator) -> None:
    validator.validate(_canonical_dict())


def test_round_trip_validates(validator: Draft202012Validator) -> None:
    validator.validate(ThoughtState.from_dict(_canonical_dict()).to_dict())


def test_with_parent_validates(validator: Draft202012Validator) -> None:
    d = _canonical_dict(parent_ids=["THOUGHT-parent-1"])
    validator.validate(ThoughtState.from_dict(d).to_dict())


@pytest.mark.parametrize("state", list(TERMINAL_STATES))
def test_terminal_states_validate(state: str, validator: Draft202012Validator) -> None:
    d = _canonical_dict(status_state=state)
    validator.validate(ThoughtState.from_dict(d).to_dict())


def test_unicode_validates(validator: Draft202012Validator) -> None:
    d = _canonical_dict()
    _mutate(d, "interpretation.summary", "ÃnÃ¯cÃ¶dÃ© æµè¯")
    validator.validate(ThoughtState.from_dict(d).to_dict())


# --- Invalid ID / timestamp / status ---

@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"thought_id": ""}, "thought_id"),
        ({"thought_id": "BAD-abc"}, "thought_id"),
        ({"thought_id": "THOUGHT-has space"}, "thought_id"),
        ({"created_at": "2025-01-15T10:30:00"}, "created_at"),
        ({"created_at": "not-a-date"}, "created_at"),
        ({"status_state": "invalid_state"}, "status"),
    ],
)
def test_invalid_identifiers(kwargs: dict, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        ThoughtState.from_dict(_canonical_dict(**kwargs))


@pytest.mark.parametrize(
    "path,value",
    [
        ("thought_id", 123),
        ("status.state", 42),
    ],
)
def test_non_string_identifiers(path: str, value: Any) -> None:
    d = _canonical_dict()
    _mutate(d, path, value)
    with pytest.raises(ValidationError):
        ThoughtState.from_dict(d)


# --- Missing / extra fields ---

@pytest.mark.parametrize(
    "field",
    [
        "thought_id", "parent_ids", "created_at", "interpretation",
        "hypothesis", "assumptions", "evidence", "metrics",
        "verification_plan", "executor_profile", "graph", "status",
    ],
)
def test_missing_root_field(field: str) -> None:
    d = _canonical_dict()
    del d[field]  # type: ignore[misc]
    with pytest.raises(ValidationError, match="missing required keys"):
        ThoughtState.from_dict(d)


def test_extra_root_field() -> None:
    d = _canonical_dict()
    d["extra_field"] = "surprise"
    with pytest.raises(ValidationError, match="unexpected keys"):
        ThoughtState.from_dict(d)


@pytest.mark.parametrize(
    "path",
    [
        "interpretation.summary",
        "metrics.confidence",
        "status.allowed_values",
    ],
)
def test_missing_nested_field(path: str) -> None:
    d = _canonical_dict()
    _delete(d, path)
    with pytest.raises(ValidationError, match="missing required keys"):
        ThoughtState.from_dict(d)


@pytest.mark.parametrize(
    "path",
    [
        "interpretation.extra",
        "metrics.extra_metric",
        "status.extra",
    ],
)
def test_extra_nested_field(path: str) -> None:
    d = _canonical_dict()
    _mutate(d, path, "nope")
    with pytest.raises(ValidationError, match="unexpected keys"):
        ThoughtState.from_dict(d)


# --- Strict primitive types ---

@pytest.mark.parametrize(
    "path,value,match",
    [
        ("metrics.confidence", True, "not bool"),
        ("metrics.novelty", False, "not bool"),
        ("assumptions.0.confidence", True, "not bool"),
        ("verification_plan.rejection_threshold", False, "not bool"),
        ("metrics.confidence", "high", "must be a number"),
        ("interpretation.summary", None, "must be a string"),
    ],
)
def test_wrong_primitive_type(path: str, value: Any, match: str) -> None:
    d = _canonical_dict()
    _mutate(d, path, value)
    with pytest.raises(ValidationError, match=match):
        ThoughtState.from_dict(d)


@pytest.mark.parametrize(
    "path,value,match",
    [
        ("parent_ids", "not-a-list", "must be a list"),
        ("assumptions", {"key": "value"}, "must be a list"),
    ],
)
def test_wrong_container_type(path: str, value: Any, match: str) -> None:
    d = _canonical_dict()
    _mutate(d, path, value)
    with pytest.raises(ValidationError, match=match):
        ThoughtState.from_dict(d)


def test_int_rejected_for_thought_id() -> None:
    d = _canonical_dict()
    _mutate(d, "thought_id", 42)
    with pytest.raises(ValidationError):
        ThoughtState.from_dict(d)


# --- Confidence range, NaN, infinities ---

@pytest.mark.parametrize(
    "path,value,match",
    [
        ("metrics.confidence", -0.1, "between 0 and 1"),
        ("metrics.confidence", 1.1, "between 0 and 1"),
        ("metrics.confidence", float("nan"), "finite"),
        ("metrics.confidence", float("inf"), "finite"),
        ("metrics.confidence", float("-inf"), "finite"),
        ("assumptions.0.confidence", float("nan"), "finite"),
        ("verification_plan.rejection_threshold", 2.0, "between 0 and 1"),
    ],
)
def test_invalid_confidence(path: str, value: Any, match: str) -> None:
    d = _canonical_dict()
    _mutate(d, path, value)
    with pytest.raises(ValidationError, match=match):
        ThoughtState.from_dict(d)


@pytest.mark.parametrize(
    "path",
    [
        "metrics.confidence",
        "assumptions.0.confidence",
    ],
    ids=["metric_confidence", "assumption_confidence"],
)
def test_huge_integer_confidence_rejected_as_validation_error(path: str) -> None:
    d = _canonical_dict()
    _mutate(d, path, 10**10000)
    with pytest.raises(ValidationError):
        ThoughtState.from_dict(d)


@pytest.mark.parametrize("value", [0, 1])
def test_confidence_boundary(value: int) -> None:
    d = _canonical_dict()
    _mutate(d, "metrics.confidence", value)
    assert ThoughtState.from_dict(d).metrics.confidence == float(value)


# --- Duplicate parent IDs ---

def test_duplicate_parent_ids() -> None:
    d = _canonical_dict(parent_ids=["THOUGHT-p1", "THOUGHT-p1"])
    with pytest.raises(ValidationError, match="duplicate"):
        ThoughtState.from_dict(d)


def test_self_reference_in_parent_ids() -> None:
    d = _canonical_dict(thought_id="THOUGHT-self", parent_ids=["THOUGHT-self"])
    with pytest.raises(ValidationError, match="own ID"):
        ThoughtState.from_dict(d)


def test_empty_parent_ids_allowed() -> None:
    assert ThoughtState.from_dict(_canonical_dict(parent_ids=[])).parent_ids == ()


def test_unique_parent_ids_allowed() -> None:
    d = _canonical_dict(parent_ids=["THOUGHT-p1", "THOUGHT-p2"])
    assert len(ThoughtState.from_dict(d).parent_ids) == 2


# --- JSON root/type failures ---

@pytest.mark.parametrize(
    "input_,match",
    [
        (123, "expected string"),
        ("{bad json", "invalid JSON"),
        ('"just a string"', "expected JSON object"),
        ("[]", "expected JSON object"),
        ("null", "expected JSON object"),
    ],
)
def test_from_json_failures(input_: Any, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        thought_state_from_json(input_)  # type: ignore[arg-type]


def test_parse_json_not_string() -> None:
    with pytest.raises(ValidationError, match="expected string"):
        parse_json(42)  # type: ignore[arg-type]


def test_parse_json_valid() -> None:
    assert parse_json('{"a": 1}') == {"a": 1}


def test_to_dict_rejects_non_thought_state() -> None:
    with pytest.raises(ValidationError, match="expected ThoughtState"):
        thought_state_to_dict("not a ThoughtState")  # type: ignore[arg-type]


def test_validation_error_is_value_error() -> None:
    with pytest.raises(ValueError):
        ThoughtState.from_dict({})


# --- Public imports and exact round trips ---

def test_all_constants_importable() -> None:
    assert isinstance(VALID_STATES, tuple)
    assert isinstance(VALID_STATE_SET, frozenset)
    assert isinstance(TERMINAL_STATES, frozenset)
    assert isinstance(PRUNE_DISPOSITIONS, frozenset)


def test_all_value_types_importable() -> None:
    for cls in (
        Assumption, Evidence, ExecutorProfile, Graph, Hypothesis,
        Interpretation, Metrics, Status, ThoughtState, VerificationPlan,
    ):
        assert isinstance(cls, type)


def test_all_serialization_functions_importable() -> None:
    for fn in (canonical_json, parse_json, thought_state_from_dict, thought_state_from_json, thought_state_to_dict):
        assert callable(fn)


def test_validation_error_importable() -> None:
    assert issubclass(ValidationError, ValueError)


def test_exact_round_trip_through_public_api() -> None:
    d = _canonical_dict()
    d2 = thought_state_to_dict(thought_state_from_dict(d))
    d3 = thought_state_to_dict(thought_state_from_dict(d2))
    assert d == d2 == d3


def test_json_round_trip_through_public_api() -> None:
    d = _canonical_dict()
    j = canonical_json(thought_state_from_dict(d))
    assert thought_state_to_dict(thought_state_from_json(j)) == d


def test_valid_states_match_schema_enum(schema: dict[str, Any]) -> None:
    state_enum = schema["properties"]["status"]["properties"]["state"]["enum"]
    assert set(state_enum) == set(VALID_STATES)


def test_deep_copy_round_trip() -> None:
    d = _canonical_dict()
    assert thought_state_to_dict(ThoughtState.from_dict(copy.deepcopy(d))) == d


# --- Duplicate assumption IDs ---

def test_duplicate_assumption_ids() -> None:
    d = _canonical_dict()
    d["assumptions"].append({
        "assumption_id": "ASM-001",
        "statement": "Another assumption",
        "confidence": 0.5,
        "source": "test",
    })
    with pytest.raises(ValidationError, match="duplicate assumption_id"):
        ThoughtState.from_dict(d)


# --- Empty strings in required non-empty fields ---

@pytest.mark.parametrize(
    "path",
    [
        "interpretation.summary",
        "hypothesis.claim",
        "assumptions.0.statement",
        "executor_profile.preferred_model_class",
    ],
)
def test_empty_string_rejected(path: str) -> None:
    d = _canonical_dict()
    _mutate(d, path, "")
    with pytest.raises(ValidationError, match="non-empty"):
        ThoughtState.from_dict(d)


# --- AST import allowlist ---

_ALLOWED_ROOTS = frozenset({"nps_core", "__future__", *sys.stdlib_module_names})


def test_production_module_imports_only_allowed() -> None:
    pkg = Path("src/nps_core/hypothesis_population")
    bad: list[str] = []
    for py in sorted(pkg.glob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in _ALLOWED_ROOTS:
                        bad.append(f"{py.name}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    if root not in _ALLOWED_ROOTS:
                        bad.append(f"{py.name}: {node.module}")
    assert not bad, f"Unexpected imports: {bad}"
