"""Immutable deterministic lineage index for ThoughtState populations.

Provides a frozen, slotted dataclass that tracks parent-child relationships
between ThoughtState objects.  All internal state is stored as canonical
tuples to guarantee determinism and immutability.

No runtime dependencies beyond the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from nps_core.hypothesis_population.errors import (
    CycleDetectedError,
    DuplicateIdError,
    SelfReferenceError,
    UnknownReferenceError,
    ValidationError,
)
from nps_core.hypothesis_population.thought_state import ThoughtState

__all__ = ["LineageIndex"]


def _validate_state(state: ThoughtState) -> None:
    """Validate that *state* is a ``ThoughtState`` instance without coercion."""
    if not isinstance(state, ThoughtState):
        raise ValidationError(
            f"expected ThoughtState, got {type(state).__name__}",
            path="state",
        )


def _detect_cycle(
    adjacency: dict[str, tuple[str, ...]],
    new_id: str,
    new_parents: tuple[str, ...],
) -> None:
    """Raise ``CycleDetectedError`` if adding *new_id* with *new_parents* creates a cycle.

    Uses iterative DFS from *new_id* through its descendants (reverse edges
    are not needed because we only walk forward from the new node).
    """
    # Build a temporary forward adjacency that includes the new edge.
    full: dict[str, tuple[str, ...]] = dict(adjacency)
    full[new_id] = new_parents  # parents are "forward" from child perspective

    # We need to detect if any ancestor of new_id can reach new_id.
    # Walk backwards: for each parent of new_id, check if new_id is reachable.
    visited: set[str] = set()
    stack: list[str] = list(new_parents)
    while stack:
        node = stack.pop()
        if node == new_id:
            raise CycleDetectedError(
                f"adding {new_id} would create a cycle",
                thought_id=new_id,
            )
        if node in visited:
            continue
        visited.add(node)
        # node's parents are stored in full[node]
        for parent in full.get(node, ()):
            stack.append(parent)


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
    _parents: tuple[tuple[str, str], ...]  # (child, parent) edges
    _children: tuple[tuple[str, str], ...]  # (parent, child) edges

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def empty(cls) -> LineageIndex:
        """Return an empty ``LineageIndex``."""
        return cls(_ids=(), _parents=(), _children=())

    @classmethod
    def from_states(cls, states: Iterable[ThoughtState]) -> LineageIndex:
        """Build a ``LineageIndex`` from an iterable of ``ThoughtState`` objects.

        The result is independent of input order.  Duplicate IDs, unknown
        parent references, self-references, and cycles are rejected.
        """
        collected: list[ThoughtState] = []
        for state in states:
            _validate_state(state)
            collected.append(state)

        # Sort by thought_id for deterministic processing.
        collected.sort(key=lambda s: s.thought_id)

        # Check for duplicate IDs.
        seen_ids: set[str] = set()
        for state in collected:
            if state.thought_id in seen_ids:
                raise DuplicateIdError(
                    f"duplicate thought_id: {state.thought_id!r}",
                    thought_id=state.thought_id,
                )
            seen_ids.add(state.thought_id)

        # Validate self-references and unknown parents.
        for state in collected:
            for pid in state.parent_ids:
                if pid == state.thought_id:
                    raise SelfReferenceError(
                        f"thought {state.thought_id} references itself",
                        thought_id=state.thought_id,
                    )
                if pid not in seen_ids:
                    raise UnknownReferenceError(
                        f"parent {pid!r} not found in population",
                        thought_id=state.thought_id,
                    )

        # Build adjacency for cycle detection.
        # adjacency[thought_id] = tuple of parent_ids
        adjacency: dict[str, tuple[str, ...]] = {}
        for state in collected:
            adjacency[state.thought_id] = state.parent_ids

        # Detect cycles using topological sort (Kahn's algorithm).
        # Build in-degree map.
        in_degree: dict[str, int] = {tid: 0 for tid in adjacency}
        forward: dict[str, list[str]] = {tid: [] for tid in adjacency}
        for tid, parents in adjacency.items():
            in_degree[tid] = len(parents)
            for pid in parents:
                forward[pid].append(tid)

        queue: list[str] = sorted(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        processed = 0
        while queue:
            node = queue.pop(0)
            processed += 1
            for child in sorted(forward[node]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    # Insert in sorted position.
                    idx = 0
                    for idx, existing in enumerate(queue):
                        if child < existing:
                            break
                    else:
                        idx = len(queue)
                    queue.insert(idx, child)

        if processed != len(adjacency):
            raise CycleDetectedError(
                "population contains a cycle",
            )

        # Build canonical edge tuples.
        parent_edges: list[tuple[str, str]] = []
        child_edges: list[tuple[str, str]] = []
        for state in collected:
            for pid in state.parent_ids:
                parent_edges.append((state.thought_id, pid))
                child_edges.append((pid, state.thought_id))

        parent_edges.sort()
        child_edges.sort()

        return cls(
            _ids=tuple(sorted(seen_ids)),
            _parents=tuple(parent_edges),
            _children=tuple(child_edges),
        )

    # ------------------------------------------------------------------
    # Mutation (returns new instance)
    # ------------------------------------------------------------------

    def add(self, state: ThoughtState) -> LineageIndex:
        """Return a new ``LineageIndex`` with *state* added.

        Rejects duplicate IDs and requires every parent to already exist.
        The original index is never mutated.
        """
        _validate_state(state)

        if state.thought_id in set(self._ids):
            raise DuplicateIdError(
                f"duplicate thought_id: {state.thought_id!r}",
                thought_id=state.thought_id,
            )

        existing_ids = set(self._ids)
        for pid in state.parent_ids:
            if pid == state.thought_id:
                raise SelfReferenceError(
                    f"thought {state.thought_id} references itself",
                    thought_id=state.thought_id,
                )
            if pid not in existing_ids:
                raise UnknownReferenceError(
                    f"parent {pid!r} not found in index",
                    thought_id=state.thought_id,
                )

        # Build new adjacency and check for cycles.
        adjacency: dict[str, tuple[str, ...]] = {}
        # Reconstruct from existing edges.
        for child, parent in self._parents:
            adjacency.setdefault(child, [])
            adjacency[child] = (*adjacency.get(child, ()), parent)
        adjacency[state.thought_id] = state.parent_ids

        _detect_cycle(
            {k: tuple(v) if isinstance(v, list) else v for k, v in adjacency.items()},
            state.thought_id,
            state.parent_ids,
        )

        # Build new canonical tuples.
        new_ids = tuple(sorted((*self._ids, state.thought_id)))

        new_parent_edges: list[tuple[str, str]] = list(self._parents)
        new_child_edges: list[tuple[str, str]] = list(self._children)
        for pid in state.parent_ids:
            new_parent_edges.append((state.thought_id, pid))
            new_child_edges.append((pid, state.thought_id))
        new_parent_edges.sort()
        new_child_edges.sort()

        return LineageIndex(
            _ids=new_ids,
            _parents=tuple(new_parent_edges),
            _children=tuple(new_child_edges),
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def contains(self, thought_id: str) -> bool:
        """Return ``True`` if *thought_id* is in the index."""
        return thought_id in set(self._ids)

    def parents_of(self, thought_id: str) -> tuple[str, ...]:
        """Return the parent IDs of *thought_id*, sorted lexicographically.

        Raises ``UnknownReferenceError`` if *thought_id* is not in the index.
        """
        if thought_id not in set(self._ids):
            raise UnknownReferenceError(
                f"thought {thought_id!r} not found in index",
                thought_id=thought_id,
            )
        return tuple(
            sorted(pid for child, pid in self._parents if child == thought_id)
        )

    def children_of(self, thought_id: str) -> tuple[str, ...]:
        """Return the child IDs of *thought_id*, sorted lexicographically.

        Raises ``UnknownReferenceError`` if *thought_id* is not in the index.
        """
        if thought_id not in set(self._ids):
            raise UnknownReferenceError(
                f"thought {thought_id!r} not found in index",
                thought_id=thought_id,
            )
        return tuple(
            sorted(cid for parent, cid in self._children if parent == thought_id)
        )

    def ids(self) -> tuple[str, ...]:
        """Return all thought IDs, sorted lexicographically."""
        return self._ids

    def to_dict(self) -> dict[str, list[str]]:
        """Serialize the index to a plain dict mapping each ID to its parent IDs.

        Keys are sorted lexicographically; parent lists are sorted
        lexicographically.
        """
        result: dict[str, list[str]] = {}
        for tid in self._ids:
            result[tid] = list(self.parents_of(tid))
        return result
