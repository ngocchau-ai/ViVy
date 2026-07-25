"""Immutable deterministic lineage index for ThoughtState parent-child tracking.

Provides ``LineageIndex`` frozen dataclass for efficient lineage queries
on a population of ThoughtStates.  Standard-library only; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from nps_core.hypothesis_population.errors import (
    CycleDetectedError,
    DuplicateIdError,
    SelfReferenceError,
    UnknownReferenceError,
    ValidationError,
)
from nps_core.hypothesis_population.thought_state import ThoughtState

__all__ = [
    "LineageIndex",
]


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def _check_cycles(
    ids: tuple[str, ...],
    parent_pairs: tuple[tuple[str, str], ...],
) -> None:
    """Detect cycles using three-color DFS on child→parent edges.

    Raises :class:`CycleDetectedError` if a cycle is found.
    """
    if not parent_pairs:
        return

    adj: dict[str, list[str]] = {tid: [] for tid in ids}
    for child, parent in parent_pairs:
        adj[child].append(parent)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {tid: WHITE for tid in ids}
    back: dict[str, str | None] = {tid: None for tid in ids}

    def dfs(tid: str) -> tuple[str, ...] | None:
        color[tid] = GRAY
        for parent in adj.get(tid, []):
            if color.get(parent) == GRAY:
                # Back edge found — reconstruct cycle
                cycle: list[str] = [parent]
                cur = tid
                while cur != parent:
                    cycle.append(cur)
                    cur = back[cur]  # type: ignore[assignment]
                cycle.append(parent)
                cycle.reverse()
                return tuple(cycle)
            if color.get(parent) == WHITE:
                back[parent] = tid
                result = dfs(parent)
                if result is not None:
                    return result
        color[tid] = BLACK
        return None

    for tid in ids:
        if color[tid] == WHITE:
            cycle = dfs(tid)
            if cycle is not None:
                raise CycleDetectedError(
                    "cycle detected in lineage graph",
                )


# ---------------------------------------------------------------------------
# LineageIndex
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LineageIndex:
    """Immutable deterministic lineage index.

    Internally stores:
    - ``_ids``: sorted tuple of all thought IDs.
    - ``_parent_pairs``: sorted tuple of ``(child_id, parent_id)`` edges.

    All public query results are returned as lexicographically sorted tuples.
    """

    _ids: tuple[str, ...]
    _parent_pairs: tuple[tuple[str, str], ...]

    # -- Factory methods ----------------------------------------------------

    @classmethod
    def empty(cls) -> LineageIndex:
        """Create an empty lineage index."""
        return cls(_ids=(), _parent_pairs=())

    @classmethod
    def from_states(
        cls, states: Iterable[ThoughtState],
    ) -> LineageIndex:
        """Construct a LineageIndex from an iterable of ThoughtStates.

        Validates:
        - No duplicate thought_ids → DuplicateIdError
        - All parent_ids reference existing thought IDs → UnknownReferenceError
        - No self-references → SelfReferenceError
        - No cycles → CycleDetectedError
        """
        if isinstance(states, (list, tuple)):
            states_list = list(states)
        else:
            try:
                states_list = list(states)
            except TypeError as exc:
                raise ValidationError(
                    f"states must be an iterable, got {type(states).__name__}",
                    path="states",
                ) from exc

        for i, state in enumerate(states_list):
            if not isinstance(state, ThoughtState):
                raise ValidationError(
                    (
                        f"each state must be a ThoughtState, "
                        f"got {type(state).__name__}"
                    ),
                    path=f"states[{i}]",
                )

        # Collect thought IDs and check for duplicates
        all_ids: set[str] = set()
        for state in states_list:
            if state.thought_id in all_ids:
                raise DuplicateIdError(
                    f"duplicate thought_id: {state.thought_id!r}",
                    thought_id=state.thought_id,
                )
            all_ids.add(state.thought_id)

        # Build parent pairs and validate references
        parent_pairs: list[tuple[str, str]] = []
        for state in states_list:
            for parent_id in state.parent_ids:
                if parent_id == state.thought_id:
                    raise SelfReferenceError(
                        (
                            f"thought {state.thought_id!r} "
                            f"cannot be its own parent"
                        ),
                        thought_id=state.thought_id,
                        relation_type="lineage",
                    )
                if parent_id not in all_ids:
                    raise UnknownReferenceError(
                        (
                            f"parent {parent_id!r} of thought "
                            f"{state.thought_id!r} not found"
                        ),
                        thought_id=parent_id,
                    )
                parent_pairs.append((state.thought_id, parent_id))

        sorted_ids = tuple(sorted(all_ids))
        sorted_pairs = tuple(sorted(parent_pairs))

        _check_cycles(sorted_ids, sorted_pairs)

        return cls(_ids=sorted_ids, _parent_pairs=sorted_pairs)

    # -- Query methods ------------------------------------------------------

    def ids(self) -> tuple[str, ...]:
        """All thought IDs in lexicographic order."""
        return self._ids

    def parents_of(self, thought_id: str) -> tuple[str, ...]:
        """Return the parent IDs of the given thought, sorted."""
        ids_set = set(self._ids)
        if thought_id not in ids_set:
            raise UnknownReferenceError(
                f"unknown thought: {thought_id!r}",
                thought_id=thought_id,
            )
        return tuple(
            sorted(pid for cid, pid in self._parent_pairs if cid == thought_id)
        )

    def children_of(self, thought_id: str) -> tuple[str, ...]:
        """Return the children IDs of the given thought, sorted."""
        ids_set = set(self._ids)
        if thought_id not in ids_set:
            raise UnknownReferenceError(
                f"unknown thought: {thought_id!r}",
                thought_id=thought_id,
            )
        return tuple(
            sorted(cid for cid, pid in self._parent_pairs if pid == thought_id)
        )

    def contains(self, thought_id: str) -> bool:
        """Return True if the thought_id exists in the index."""
        return thought_id in set(self._ids)

    def add(self, state: ThoughtState) -> LineageIndex:
        """Return a new LineageIndex with the given thought added."""
        if not isinstance(state, ThoughtState):
            raise ValidationError(
                f"state must be a ThoughtState, "
                f"got {type(state).__name__}",
                path="state",
            )

        if state.thought_id in state.parent_ids:
            raise SelfReferenceError(
                (
                    f"thought {state.thought_id!r} "
                    f"cannot be its own parent"
                ),
                thought_id=state.thought_id,
                relation_type="lineage",
            )

        existing_ids = set(self._ids)
        if state.thought_id in existing_ids:
            raise DuplicateIdError(
                f"duplicate thought_id: {state.thought_id!r}",
                thought_id=state.thought_id,
            )

        for parent_id in state.parent_ids:
            if parent_id not in existing_ids:
                raise UnknownReferenceError(
                    (
                        f"parent {parent_id!r} of thought "
                        f"{state.thought_id!r} not found"
                    ),
                    thought_id=parent_id,
                )

        new_ids = tuple(sorted((*self._ids, state.thought_id)))
        new_pairs = list(self._parent_pairs)
        for parent_id in state.parent_ids:
            new_pairs.append((state.thought_id, parent_id))
        new_pairs.sort()

        result = LineageIndex(
            _ids=new_ids, _parent_pairs=tuple(new_pairs),
        )
        _check_cycles(result._ids, result._parent_pairs)
        return result

    # -- Serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, list[str]]:
        """Serialize to a dict mapping thought_id → sorted list of parent_ids."""
        result: dict[str, list[str]] = {}
        for tid in self._ids:
            parents = sorted(
                pid for cid, pid in self._parent_pairs if cid == tid,
            )
            result[tid] = parents
        return result
