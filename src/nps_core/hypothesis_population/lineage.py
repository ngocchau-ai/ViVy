"""Immutable deterministic lineage index for ThoughtState parent-child tracking.

Provides ``LineageIndex`` frozen dataclass for efficient lineage queries
on a population of ThoughtStates.  Standard-library only; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nps_core.hypothesis_population.errors import (
    SelfReferenceError,
    ValidationError,
)
from nps_core.hypothesis_population.thought_state import ThoughtState

__all__ = [
    "LineageIndex",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_thought_id(value: str, *, field: str) -> None:
    """Validate a thought ID is a non-empty string."""
    if not isinstance(value, str):
        raise ValidationError(
            f"{field} must be a string, got {type(value).__name__}",
            path=field,
        )
    if not value.strip():
        raise ValidationError(
            f"{field} must be non-empty",
            path=field,
        )


# ---------------------------------------------------------------------------
# LineageIndex
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LineageIndex:
    """Immutable deterministic lineage index.

    Internally stores:
    - ``_ids``: sorted tuple of all thought IDs.
    - ``_parents``: tuple of ``(child_id, parent_id)`` edges sorted
      lexicographically.
    - ``_children``: tuple of ``(parent_id, child_id)`` edges sorted
      lexicographically.

    All public query results are returned as lexicographically sorted tuples.
    """

    _ids: tuple[str, ...]
    _parents: tuple[tuple[str, str], ...]
    _children: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        # Validate types
        if not isinstance(self._ids, tuple):
            raise ValidationError(
                f"_ids must be a tuple, got {type(self._ids).__name__}",
                path="_ids",
            )
        if not isinstance(self._parents, tuple):
            raise ValidationError(
                f"_parents must be a tuple, got {type(self._parents).__name__}",
                path="_parents",
            )
        if not isinstance(self._children, tuple):
            raise ValidationError(
                f"_children must be a tuple, got {type(self._children).__name__}",
                path="_children",
            )

    # -- Factory methods ----------------------------------------------------

    @classmethod
    def empty(cls) -> LineageIndex:
        """Create an empty lineage index."""
        return cls(_ids=(), _parents=(), _children=())

    @classmethod
    def from_states(cls, states: tuple[ThoughtState, ...]) -> LineageIndex:
        """Construct a LineageIndex from a tuple of ThoughtStates.

        Validates:
        - No self-references (thought_id in its own parent_ids)
        - All parent_ids reference existing thought IDs

        Parameters
        ----------
        states:
            Tuple of ThoughtState instances.

        Returns
        -------
        LineageIndex
            A validated, immutable lineage index.
        """
        if not isinstance(states, tuple):
            raise ValidationError(
                f"states must be a tuple, got {type(states).__name__}",
                path="states",
            )

        # Collect all thought IDs
        all_ids: set[str] = set()
        for state in states:
            if not isinstance(state, ThoughtState):
                raise ValidationError(
                    f"each state must be a ThoughtState, got {type(state).__name__}",
                    path="states",
                )
            all_ids.add(state.thought_id)

        # Build edge lists
        parent_edges: list[tuple[str, str]] = []
        child_edges: list[tuple[str, str]] = []

        for state in states:
            # Check for self-references
            if state.thought_id in state.parent_ids:
                raise SelfReferenceError(
                    f"thought {state.thought_id!r} cannot be its own parent",
                    thought_id=state.thought_id,
                    relation_type="lineage",
                )

            for parent_id in state.parent_ids:
                # Validate parent exists
                if parent_id not in all_ids:
                    raise ValidationError(
                        (
                            f"parent {parent_id!r} of thought "
                            f"{state.thought_id!r} not found in states"
                        ),
                        path="parent_ids",
                    )

                # child depends on parent
                parent_edges.append((state.thought_id, parent_id))
                # parent has child
                child_edges.append((parent_id, state.thought_id))

        # Sort for determinism
        sorted_ids = tuple(sorted(all_ids))
        sorted_parents = tuple(sorted(parent_edges))
        sorted_children = tuple(sorted(child_edges))

        return cls(
            _ids=sorted_ids,
            _parents=sorted_parents,
            _children=sorted_children,
        )

    # -- Query methods ------------------------------------------------------

    @property
    def ids(self) -> tuple[str, ...]:
        """All thought IDs in lexicographic order."""
        return self._ids

    def parent_ids(self, thought_id: str) -> tuple[str, ...]:
        """Return the parent IDs of the given thought, sorted lexicographically.

        Parameters
        ----------
        thought_id:
            The thought ID to query.

        Returns
        -------
        tuple[str, ...]
            Sorted tuple of parent IDs.

        Raises
        ------
        ValidationError
            If thought_id is not a string.
        """
        _validate_thought_id(thought_id, field="thought_id")
        return tuple(
            sorted(pid for cid, pid in self._parents if cid == thought_id)
        )

    def children_ids(self, thought_id: str) -> tuple[str, ...]:
        """Return the children IDs of the given thought, sorted lexicographically.

        Parameters
        ----------
        thought_id:
            The thought ID to query.

        Returns
        -------
        tuple[str, ...]
            Sorted tuple of children IDs.

        Raises
        ------
        ValidationError
            If thought_id is not a string.
        """
        _validate_thought_id(thought_id, field="thought_id")
        return tuple(
            sorted(cid for pid, cid in self._children if pid == thought_id)
        )

    def ancestors(self, thought_id: str) -> tuple[str, ...]:
        """Return all ancestor IDs of the given thought, sorted lexicographically.

        Uses BFS to traverse parent edges.

        Parameters
        ----------
        thought_id:
            The thought ID to query.

        Returns
        -------
        tuple[str, ...]
            Sorted tuple of all ancestor IDs (excluding the thought itself).

        Raises
        ------
        ValidationError
            If thought_id is not a string.
        """
        _validate_thought_id(thought_id, field="thought_id")

        # Build adjacency list for parent lookups
        parent_map: dict[str, list[str]] = {}
        for cid, pid in self._parents:
            parent_map.setdefault(cid, []).append(pid)

        # BFS from thought_id upward
        visited: set[str] = set()
        queue: list[str] = [thought_id]

        while queue:
            current = queue.pop(0)
            for parent in parent_map.get(current, []):
                if parent not in visited:
                    visited.add(parent)
                    queue.append(parent)

        # Exclude the thought itself
        visited.discard(thought_id)
        return tuple(sorted(visited))

    def descendants(self, thought_id: str) -> tuple[str, ...]:
        """Return all descendant IDs of the given thought, sorted lexicographically.

        Uses BFS to traverse child edges.

        Parameters
        ----------
        thought_id:
            The thought ID to query.

        Returns
        -------
        tuple[str, ...]
            Sorted tuple of all descendant IDs (excluding the thought itself).

        Raises
        ------
        ValidationError
            If thought_id is not a string.
        """
        _validate_thought_id(thought_id, field="thought_id")

        # Build adjacency list for child lookups
        child_map: dict[str, list[str]] = {}
        for pid, cid in self._children:
            child_map.setdefault(pid, []).append(cid)

        # BFS from thought_id downward
        visited: set[str] = set()
        queue: list[str] = [thought_id]

        while queue:
            current = queue.pop(0)
            for child in child_map.get(current, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)

        # Exclude the thought itself
        visited.discard(thought_id)
        return tuple(sorted(visited))

    def add(self, state: ThoughtState) -> LineageIndex:
        """Return a new LineageIndex with the given thought added.

        Parameters
        ----------
        state:
            The ThoughtState to add.

        Returns
        -------
        LineageIndex
            A new immutable lineage index with the thought added.

        Raises
        ------
        ValidationError
            If state is not a ThoughtState or has invalid parent references.
        """
        if not isinstance(state, ThoughtState):
            raise ValidationError(
                f"state must be a ThoughtState, got {type(state).__name__}",
                path="state",
            )

        # Check for self-reference
        if state.thought_id in state.parent_ids:
            raise SelfReferenceError(
                f"thought {state.thought_id!r} cannot be its own parent",
                thought_id=state.thought_id,
                relation_type="lineage",
            )

        # Build new ID set
        new_ids_set = set(self._ids)
        new_ids_set.add(state.thought_id)

        # Validate parent references
        for parent_id in state.parent_ids:
            if parent_id not in new_ids_set:
                raise ValidationError(
                    (
                        f"parent {parent_id!r} of thought "
                        f"{state.thought_id!r} not found in index"
                    ),
                    path="parent_ids",
                )

        # Build new edge lists
        new_parents = list(self._parents)
        new_children = list(self._children)

        for parent_id in state.parent_ids:
            new_parents.append((state.thought_id, parent_id))
            new_children.append((parent_id, state.thought_id))

        return LineageIndex(
            _ids=tuple(sorted(new_ids_set)),
            _parents=tuple(sorted(new_parents)),
            _children=tuple(sorted(new_children)),
        )

    # -- Serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "ids": list(self._ids),
            "parents": [list(edge) for edge in self._parents],
            "children": [list(edge) for edge in self._children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LineageIndex:
        """Strict construction from a plain dict."""
        if not isinstance(data, dict):
            raise ValidationError(
                f"expected dict, got {type(data).__name__}",
                path="root",
            )

        required = {"ids", "parents", "children"}
        missing = required - data.keys()
        if missing:
            raise ValidationError(
                f"missing keys: {sorted(missing)}",
                path="root",
            )
        extra = data.keys() - required
        if extra:
            raise ValidationError(
                f"unexpected keys: {sorted(extra)}",
                path="root",
            )

        # Parse ids
        raw_ids = data["ids"]
        if not isinstance(raw_ids, list):
            raise ValidationError(
                f"ids must be a JSON list, got {type(raw_ids).__name__}",
                path="ids",
            )
        ids = tuple(sorted(raw_ids))

        # Parse parents
        raw_parents = data["parents"]
        if not isinstance(raw_parents, list):
            raise ValidationError(
                f"parents must be a JSON list, got {type(raw_parents).__name__}",
                path="parents",
            )
        parents: list[tuple[str, str]] = []
        for i, edge in enumerate(raw_parents):
            if not isinstance(edge, list) or len(edge) != 2:
                raise ValidationError(
                    f"parents[{i}] must be a 2-element list",
                    path=f"parents[{i}]",
                )
            parents.append((edge[0], edge[1]))

        # Parse children
        raw_children = data["children"]
        if not isinstance(raw_children, list):
            raise ValidationError(
                f"children must be a JSON list, got {type(raw_children).__name__}",
                path="children",
            )
        children: list[tuple[str, str]] = []
        for i, edge in enumerate(raw_children):
            if not isinstance(edge, list) or len(edge) != 2:
                raise ValidationError(
                    f"children[{i}] must be a 2-element list",
                    path=f"children[{i}]",
                )
            children.append((edge[0], edge[1]))

        return cls(
            _ids=ids,
            _parents=tuple(sorted(parents)),
            _children=tuple(sorted(children)),
        )
