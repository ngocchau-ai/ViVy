"""Token-Efficient Context Cache for Stage 3.

Standard-library only; caches ContextCapsule objects with commit-bound freshness checks.
"""

from __future__ import annotations

import hashlib

from nps_core.codegraph.retrieval import ContextCapsule

__all__ = [
    "ContextCache",
]


class ContextCache:
    """In-memory commit-bound cache for ContextCapsules."""

    def __init__(self) -> None:
        self._store: dict[str, ContextCapsule] = {}

    @staticmethod
    def _make_key(query: str, max_token_budget: int, git_commit: str) -> str:
        raw = f"{query}:{max_token_budget}:{git_commit}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, query: str, max_token_budget: int, git_commit: str) -> ContextCapsule | None:
        key = self._make_key(query, max_token_budget, git_commit)
        return self._store.get(key)

    def put(self, query: str, max_token_budget: int, git_commit: str, capsule: ContextCapsule) -> None:
        key = self._make_key(query, max_token_budget, git_commit)
        self._store[key] = capsule

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
