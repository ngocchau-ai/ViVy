"""Deterministic serialization helpers for ThoughtState.

All functions are pure and produce byte-identical output for identical input.
No runtime dependencies beyond the Python standard library.
"""

from __future__ import annotations

import json
from typing import Any

from nps_core.hypothesis_population.errors import ValidationError
from nps_core.hypothesis_population.thought_state import ThoughtState

__all__ = [
    "CANONICAL_SEPARATORS",
    "thought_state_to_dict",
    "thought_state_from_dict",
    "canonical_json",
    "parse_json",
    "thought_state_from_json",
]

CANONICAL_SEPARATORS: tuple[str, str] = (",", ":")


def thought_state_to_dict(state: ThoughtState) -> dict[str, Any]:
    """Serialize a ThoughtState to a plain dict.

    Args:
        state: An actual ThoughtState instance.

    Returns:
        A plain dict/list structure compatible with the V1 schema.

    Raises:
        ValidationError: If *state* is not a ThoughtState.
    """
    if not isinstance(state, ThoughtState):
        raise ValidationError(
            f"expected ThoughtState, got {type(state).__name__}",
            path="state",
        )
    return state.to_dict()


def thought_state_from_dict(data: dict[str, Any]) -> ThoughtState:
    """Construct a ThoughtState from a plain dict.

    Delegates to ``ThoughtState.from_dict`` which validates all keys and
    values against the V1 schema shape.

    Args:
        data: A plain dict representing a ThoughtState.

    Returns:
        A validated, immutable ThoughtState.
    """
    return ThoughtState.from_dict(data)


def canonical_json(value: ThoughtState | dict[str, Any] | list[Any]) -> str:
    """Produce deterministic canonical JSON for *value*.

    ThoughtState instances are serialized through ``to_dict`` before
    encoding.  The output uses compact separators, sorted keys, and
    ``ensure_ascii=False``.  No platform-dependent newline characters
    are emitted.

    Args:
        value: A ThoughtState, dict, or list to serialize.

    Returns:
        A canonical JSON string.

    Raises:
        ValidationError: If *value* is not a supported type or contains
            non-finite floats.
    """
    if isinstance(value, ThoughtState):
        data: Any = value.to_dict()
    elif isinstance(value, dict):
        data = value
    elif isinstance(value, list):
        data = value
    else:
        raise ValidationError(
            f"canonical_json requires ThoughtState, dict, or list; "
            f"got {type(value).__name__}",
            path="root",
        )

    try:
        result = json.dumps(
            data,
            sort_keys=True,
            separators=CANONICAL_SEPARATORS,
            ensure_ascii=False,
            allow_nan=False,
        )
    except (ValueError, TypeError) as exc:
        raise ValidationError(
            f"JSON serialization failed: {exc}",
            path="root",
        ) from exc

    # json.dumps never produces platform-dependent newlines in Python, but
    # guard against any future change.
    return result.replace("\r\n", "\n").replace("\r", "\n")


def parse_json(text: str) -> Any:
    """Parse a JSON string into a Python object.

    Args:
        text: A JSON-encoded string.

    Returns:
        The decoded Python object.

    Raises:
        ValidationError: If *text* is not a string or contains invalid JSON.
    """
    if not isinstance(text, str):
        raise ValidationError(
            f"expected string, got {type(text).__name__}",
            path="json",
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {exc}",
            path="json",
        ) from exc


def thought_state_from_json(text: str) -> ThoughtState:
    """Parse a JSON string and construct a ThoughtState.

    The decoded value must be a JSON object (dict).  Delegates to
    ``ThoughtState.from_dict`` for full validation.

    Args:
        text: A JSON-encoded string representing a ThoughtState.

    Returns:
        A validated, immutable ThoughtState.

    Raises:
        ValidationError: If *text* is not a string, contains invalid JSON,
            or the decoded value is not a JSON object.
    """
    data = parse_json(text)
    if not isinstance(data, dict):
        raise ValidationError(
            f"expected JSON object, got {type(data).__name__}",
            path="json",
        )
    return ThoughtState.from_dict(data)
