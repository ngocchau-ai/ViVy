"""Immutable ThoughtState lifecycle core."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from nps_core.hypothesis_population.errors import (
    DuplicateEventError,
    DuplicateIdError,
    InvalidDispositionError,
    InvalidTransitionError,
    MergeSourceError,
    TerminalStateError,
    UnknownReferenceError,
    ValidationError,
)
from nps_core.hypothesis_population.lineage import LineageIndex
from nps_core.hypothesis_population.thought_state import (
    TERMINAL_STATES,
    ThoughtState,
)

__all__ = [
    "TransitionEvent",
    "PopulationSnapshot",
    "create",
    "branch",
    "merge",
    "prune",
]

_VALID_OPERATIONS: frozenset[str] = frozenset({"create", "branch", "merge", "prune"})
_PRUNE_DISPOSITIONS: frozenset[str] = frozenset({"rejected", "dormant"})
_ISO_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")


def _validate_non_empty_str(value: Any, name: str) -> str:
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a string, not bool", path=name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string", path=name)
    return value


def _validate_thought_id(value: Any, name: str) -> str:
    _validate_non_empty_str(value, name)
    if not _THOUGHT_ID_RE.match(value):
        raise ValidationError(
            f"{name} must match ^THOUGHT-[A-Za-z0-9._-]+$", path=name
        )
    return value


def _validate_timestamp(value: Any, name: str) -> str:
    _validate_non_empty_str(value, name)
    if not _ISO_Z_RE.match(value):
        raise ValidationError(
            f"{name} must be RFC3339/ISO-8601 timezone-aware", path=name
        )
    raw = value
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise ValidationError(
            f"{name} is not a valid ISO-8601 datetime: {exc}", path=name
        ) from exc
    if dt.tzinfo is None:
        raise ValidationError(
            f"{name} must be timezone-aware", path=name
        )
    return value


def _validate_operation(value: Any) -> str:
    _validate_non_empty_str(value, "operation")
    if value not in _VALID_OPERATIONS:
        raise ValidationError(
            f"operation must be one of {sorted(_VALID_OPERATIONS)}, got {value!r}",
            path="operation",
        )
    return value


def _validate_id_tuple(items: tuple[str, ...], name: str) -> None:
    if not isinstance(items, tuple):
        raise ValidationError(f"{name} must be a tuple", path=name)
    seen: set[str] = set()
    for i, item in enumerate(items):
        p = f"{name}[{i}]"
        _validate_thought_id(item, p)
        if item in seen:
            raise ValidationError(f"duplicate ID in {name}: {item!r}", path=p)
        seen.add(item)


def _validate_event_id(value: Any) -> str:
    return _validate_non_empty_str(value, "event_id")


def _validate_actor(value: Any) -> str:
    return _validate_non_empty_str(value, "actor")


def _validate_reason(value: Any, operation: str) -> str | None:
    if operation == "prune":
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("prune requires a non-empty reason", path="reason")
        return value
    if value is not None:
        raise ValidationError(
            f"reason must be None for {operation} operation", path="reason"
        )
    return None


def _validate_disposition(value: Any, operation: str) -> str | None:
    if operation == "prune":
        if value not in _PRUNE_DISPOSITIONS:
            raise InvalidDispositionError(
                f"disposition must be one of {sorted(_PRUNE_DISPOSITIONS)}, got {value!r}",
                path="disposition",
            )
        return value
    if value is not None:
        raise ValidationError(
            f"disposition must be None for {operation} operation", path="disposition"
        )
    return None


def _is_terminal(state: ThoughtState) -> bool:
    return state.status.state in TERMINAL_STATES


def _is_active(state: ThoughtState) -> bool:
    return state.status.state == "active"


def _validate_operation_shape(
    operation: str,
    input_ids: tuple[str, ...],
    output_ids: tuple[str, ...],
) -> None:
    if operation == "create":
        if len(input_ids) != 0 or len(output_ids) != 1:
            raise InvalidTransitionError(
                "create requires 0 inputs and 1 output",
            )
    elif operation == "branch":
        if len(input_ids) != 1 or len(output_ids) != 1:
            raise InvalidTransitionError(
                "branch requires 1 input and 1 output",
            )
        if input_ids[0] == output_ids[0]:
            raise InvalidTransitionError(
                "branch requires distinct input and output IDs",
            )
    elif operation == "merge":
        if len(input_ids) < 2 or len(output_ids) != 1:
            raise InvalidTransitionError(
                "merge requires >=2 inputs and 1 output",
            )
        if output_ids[0] in input_ids:
            raise InvalidTransitionError(
                "merge output must not be in inputs",
            )
        if tuple(sorted(input_ids)) != input_ids:
            raise InvalidTransitionError(
                "merge inputs must be sorted",
            )
    elif operation == "prune":
        if len(input_ids) != 1 or len(output_ids) != 1:
            raise InvalidTransitionError(
                "prune requires 1 input and 1 output",
            )
        if input_ids[0] != output_ids[0]:
            raise InvalidTransitionError(
                "prune input and output must be the same ID",
            )


@dataclass(frozen=True, slots=True)
class TransitionEvent:
    event_id: str
    timestamp: str
    operation: str
    actor: str
    input_ids: tuple[str, ...]
    output_ids: tuple[str, ...]
    reason: str | None = None
    disposition: str | None = None

    def __post_init__(self) -> None:
        _validate_event_id(self.event_id)
        _validate_timestamp(self.timestamp, "timestamp")
        _validate_operation(self.operation)
        _validate_actor(self.actor)
        if not isinstance(self.input_ids, tuple):
            raise ValidationError("input_ids must be a tuple", path="input_ids")
        _validate_id_tuple(self.input_ids, "input_ids")
        if not isinstance(self.output_ids, tuple):
            raise ValidationError("output_ids must be a tuple", path="output_ids")
        _validate_id_tuple(self.output_ids, "output_ids")
        _validate_reason(self.reason, self.operation)
        _validate_disposition(self.disposition, self.operation)
        _validate_operation_shape(self.operation, self.input_ids, self.output_ids)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "actor": self.actor,
            "input_ids": list(self.input_ids),
            "output_ids": list(self.output_ids),
        }
        if self.reason is not None:
            result["reason"] = self.reason
        if self.disposition is not None:
            result["disposition"] = self.disposition
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransitionEvent:
        if not isinstance(data, dict):
            raise ValidationError("data must be a dict", path="root")
        required_keys = {
            "event_id", "timestamp", "operation", "actor", "input_ids", "output_ids",
        }
        optional_keys = {"reason", "disposition"}
        allowed_keys = required_keys | optional_keys
        missing = required_keys - data.keys()
        if missing:
            raise ValidationError(
                f"missing required keys: {sorted(missing)}", path="root"
            )
        extra = data.keys() - allowed_keys
        if extra:
            raise ValidationError(
                f"unexpected keys: {sorted(extra)}", path="root"
            )
        input_ids_raw = data["input_ids"]
        if not isinstance(input_ids_raw, list):
            raise ValidationError("input_ids must be a list", path="input_ids")
        input_ids = tuple(input_ids_raw)
        output_ids_raw = data["output_ids"]
        if not isinstance(output_ids_raw, list):
            raise ValidationError("output_ids must be a list", path="output_ids")
        output_ids = tuple(output_ids_raw)
        return cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            operation=data["operation"],
            actor=data["actor"],
            input_ids=input_ids,
            output_ids=output_ids,
            reason=data.get("reason"),
            disposition=data.get("disposition"),
        )


@dataclass(frozen=True, slots=True)
class PopulationSnapshot:
    thoughts: tuple[ThoughtState, ...] = ()
    history: tuple[TransitionEvent, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.thoughts, tuple):
            raise ValidationError("thoughts must be a tuple", path="thoughts")
        if not isinstance(self.history, tuple):
            raise ValidationError("history must be a tuple", path="history")
        for i, t in enumerate(self.thoughts):
            if not isinstance(t, ThoughtState):
                raise ValidationError(
                    f"thoughts[{i}] must be a ThoughtState", path=f"thoughts[{i}]"
                )
        for i, e in enumerate(self.history):
            if not isinstance(e, TransitionEvent):
                raise ValidationError(
                    f"history[{i}] must be a TransitionEvent", path=f"history[{i}]"
                )
        thought_ids: set[str] = set()
        for t in self.thoughts:
            if t.thought_id in thought_ids:
                raise DuplicateIdError(
                    f"duplicate thought_id: {t.thought_id!r}", thought_id=t.thought_id
                )
            thought_ids.add(t.thought_id)
        event_ids: set[str] = set()
        for e in self.history:
            if e.event_id in event_ids:
                raise DuplicateEventError(f"duplicate event_id: {e.event_id!r}")
            event_ids.add(e.event_id)
        if self.thoughts:
            LineageIndex.from_states(self.thoughts)
        for e in self.history:
            for ref_id in e.input_ids:
                if ref_id not in thought_ids:
                    raise UnknownReferenceError(
                        f"event {e.event_id} references unknown input thought {ref_id!r}",
                        thought_id=ref_id,
                    )
            for ref_id in e.output_ids:
                if ref_id not in thought_ids:
                    raise UnknownReferenceError(
                        f"event {e.event_id} references unknown output thought {ref_id!r}",
                        thought_id=ref_id,
                    )
        sorted_thoughts = tuple(sorted(self.thoughts, key=lambda t: t.thought_id))
        if sorted_thoughts is not self.thoughts:
            object.__setattr__(self, "thoughts", sorted_thoughts)

    @classmethod
    def empty(cls) -> PopulationSnapshot:
        return cls(thoughts=(), history=())

    def get(self, thought_id: str) -> ThoughtState | None:
        for t in self.thoughts:
            if t.thought_id == thought_id:
                return t
        return None

    def contains(self, thought_id: str) -> bool:
        return self.get(thought_id) is not None

    @property
    def lineage(self) -> LineageIndex:
        if not self.thoughts:
            return LineageIndex.empty()
        return LineageIndex.from_states(self.thoughts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "thoughts": [t.to_dict() for t in self.thoughts],
            "history": [e.to_dict() for e in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PopulationSnapshot:
        if not isinstance(data, dict):
            raise ValidationError("data must be a dict", path="root")
        required_keys = {"thoughts", "history"}
        missing = required_keys - data.keys()
        if missing:
            raise ValidationError(
                f"missing required keys: {sorted(missing)}", path="root"
            )
        extra = data.keys() - required_keys
        if extra:
            raise ValidationError(
                f"unexpected keys: {sorted(extra)}", path="root"
            )
        thoughts_raw = data["thoughts"]
        if not isinstance(thoughts_raw, list):
            raise ValidationError("thoughts must be a list", path="thoughts")
        thoughts = tuple(ThoughtState.from_dict(t) for t in thoughts_raw)
        history_raw = data["history"]
        if not isinstance(history_raw, list):
            raise ValidationError("history must be a list", path="history")
        history = tuple(TransitionEvent.from_dict(e) for e in history_raw)
        return cls(thoughts=thoughts, history=history)

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @classmethod
    def from_canonical_json(cls, text: str) -> PopulationSnapshot:
        if not isinstance(text, str):
            raise ValidationError(
                f"expected string, got {type(text).__name__}", path="json"
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid JSON: {exc}", path="json") from exc
        return cls.from_dict(data)


def create(
    snapshot: PopulationSnapshot,
    state: ThoughtState,
    *,
    event_id: str,
    timestamp: str,
    actor: str,
) -> PopulationSnapshot:
    if not isinstance(snapshot, PopulationSnapshot):
        raise ValidationError("snapshot must be a PopulationSnapshot", path="snapshot")
    if not isinstance(state, ThoughtState):
        raise ValidationError("state must be a ThoughtState", path="state")
    if snapshot.contains(state.thought_id):
        raise DuplicateIdError(
            f"thought_id already exists: {state.thought_id!r}",
            thought_id=state.thought_id,
        )
    if state.parent_ids:
        raise InvalidTransitionError(
            "create requires empty parent_ids", thought_id=state.thought_id
        )
    if not _is_active(state):
        raise InvalidTransitionError(
            f"create requires active status, got {state.status.state!r}",
            thought_id=state.thought_id,
        )
    event = TransitionEvent(
        event_id=event_id,
        timestamp=timestamp,
        operation="create",
        actor=actor,
        input_ids=(),
        output_ids=(state.thought_id,),
    )
    new_thoughts = tuple(
        sorted((*snapshot.thoughts, state), key=lambda t: t.thought_id)
    )
    new_history = (*snapshot.history, event)
    return PopulationSnapshot(thoughts=new_thoughts, history=new_history)


def branch(
    snapshot: PopulationSnapshot,
    child: ThoughtState,
    *,
    parent_id: str,
    event_id: str,
    timestamp: str,
    actor: str,
) -> PopulationSnapshot:
    if not isinstance(snapshot, PopulationSnapshot):
        raise ValidationError("snapshot must be a PopulationSnapshot", path="snapshot")
    if not isinstance(child, ThoughtState):
        raise ValidationError("child must be a ThoughtState", path="child")
    if snapshot.contains(child.thought_id):
        raise DuplicateIdError(
            f"thought_id already exists: {child.thought_id!r}",
            thought_id=child.thought_id,
        )
    parent = snapshot.get(parent_id)
    if parent is None:
        raise UnknownReferenceError(
            f"parent not found: {parent_id!r}", thought_id=parent_id
        )
    if _is_terminal(parent):
        raise TerminalStateError(
            f"parent is in terminal state: {parent.status.state!r}",
            thought_id=parent_id,
        )
    if not _is_active(child):
        raise InvalidTransitionError(
            f"branch requires active child status, got {child.status.state!r}",
            thought_id=child.thought_id,
        )
    if child.parent_ids != (parent_id,):
        raise InvalidTransitionError(
            f"child.parent_ids must be ({parent_id!r},), got {child.parent_ids!r}",
            thought_id=child.thought_id,
        )
    event = TransitionEvent(
        event_id=event_id,
        timestamp=timestamp,
        operation="branch",
        actor=actor,
        input_ids=(parent_id,),
        output_ids=(child.thought_id,),
    )
    new_thoughts = tuple(
        sorted((*snapshot.thoughts, child), key=lambda t: t.thought_id)
    )
    new_history = (*snapshot.history, event)
    return PopulationSnapshot(thoughts=new_thoughts, history=new_history)


def merge(
    snapshot: PopulationSnapshot,
    merged: ThoughtState,
    *,
    source_ids: Iterable[str],
    event_id: str,
    timestamp: str,
    actor: str,
) -> PopulationSnapshot:
    if not isinstance(snapshot, PopulationSnapshot):
        raise ValidationError("snapshot must be a PopulationSnapshot", path="snapshot")
    if not isinstance(merged, ThoughtState):
        raise ValidationError("merged must be a ThoughtState", path="merged")
    if isinstance(source_ids, (str, bytes)):
        raise MergeSourceError(
            "source_ids must not be a string or bytes", path="source_ids"
        )
    try:
        source_list = list(source_ids)
    except TypeError as exc:
        raise MergeSourceError(
            "source_ids must be iterable", path="source_ids"
        ) from exc
    seen: set[str] = set()
    for i, sid in enumerate(source_list):
        if not isinstance(sid, str):
            raise MergeSourceError(
                f"source_ids[{i}] must be a string", path=f"source_ids[{i}]"
            )
        if sid in seen:
            raise MergeSourceError(
                f"duplicate source ID: {sid!r}", path=f"source_ids[{i}]"
            )
        seen.add(sid)
    if len(seen) < 2:
        raise MergeSourceError(
            "merge requires at least two distinct source IDs", path="source_ids"
        )
    sorted_sources = tuple(sorted(seen))
    source_states: dict[str, ThoughtState] = {}
    for sid in sorted_sources:
        state = snapshot.get(sid)
        if state is None:
            raise UnknownReferenceError(
                f"source thought not found: {sid!r}", thought_id=sid
            )
        if _is_terminal(state):
            raise TerminalStateError(
                f"source thought is in terminal state: {state.status.state!r}",
                thought_id=sid,
            )
        source_states[sid] = state
    if snapshot.contains(merged.thought_id):
        raise DuplicateIdError(
            f"thought_id already exists: {merged.thought_id!r}",
            thought_id=merged.thought_id,
        )
    if not _is_active(merged):
        raise InvalidTransitionError(
            f"merge requires active result status, got {merged.status.state!r}",
            thought_id=merged.thought_id,
        )
    if merged.parent_ids != sorted_sources:
        raise MergeSourceError(
            f"merged.parent_ids must be {sorted_sources!r}, got {merged.parent_ids!r}",
            thought_id=merged.thought_id,
        )
    updated_thoughts: list[ThoughtState] = []
    for t in snapshot.thoughts:
        if t.thought_id in source_states:
            updated_thoughts.append(t.with_status("merged"))
        else:
            updated_thoughts.append(t)
    updated_thoughts.append(merged)
    new_thoughts = tuple(sorted(updated_thoughts, key=lambda t: t.thought_id))
    event = TransitionEvent(
        event_id=event_id,
        timestamp=timestamp,
        operation="merge",
        actor=actor,
        input_ids=sorted_sources,
        output_ids=(merged.thought_id,),
    )
    new_history = (*snapshot.history, event)
    return PopulationSnapshot(thoughts=new_thoughts, history=new_history)


def prune(
    snapshot: PopulationSnapshot,
    thought_id: str,
    *,
    reason: str,
    disposition: str,
    event_id: str,
    timestamp: str,
    actor: str,
) -> PopulationSnapshot:
    if not isinstance(snapshot, PopulationSnapshot):
        raise ValidationError("snapshot must be a PopulationSnapshot", path="snapshot")
    target = snapshot.get(thought_id)
    if target is None:
        raise UnknownReferenceError(
            f"thought not found: {thought_id!r}", thought_id=thought_id
        )
    if _is_terminal(target):
        raise TerminalStateError(
            f"thought is already in terminal state: {target.status.state!r}",
            thought_id=thought_id,
        )
    if disposition not in _PRUNE_DISPOSITIONS:
        raise InvalidDispositionError(
            f"disposition must be one of {sorted(_PRUNE_DISPOSITIONS)}, got {disposition!r}",
            path="disposition",
        )
    if not isinstance(reason, str) or not reason.strip():
        raise InvalidTransitionError(
            "prune requires a non-empty reason", thought_id=thought_id
        )
    updated_target = target.with_status(disposition)
    new_thoughts_list: list[ThoughtState] = []
    for t in snapshot.thoughts:
        if t.thought_id == thought_id:
            new_thoughts_list.append(updated_target)
        else:
            new_thoughts_list.append(t)
    new_thoughts = tuple(new_thoughts_list)
    event = TransitionEvent(
        event_id=event_id,
        timestamp=timestamp,
        operation="prune",
        actor=actor,
        input_ids=(thought_id,),
        output_ids=(thought_id,),
        reason=reason,
        disposition=disposition,
    )
    new_history = (*snapshot.history, event)
    return PopulationSnapshot(thoughts=new_thoughts, history=new_history)
