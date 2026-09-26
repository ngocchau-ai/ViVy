"""Token-Efficient Context Retrieval Capsule for Stage 3.

Standard-library only; provides rank-ordered symbol retrieval within strict token budgets.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ContextCapsule",
    "ContextRetriever",
]


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token)."""
    return max(1, len(text) // 4)


@dataclass(frozen=True, slots=True)
class ContextCapsule:
    """Frozen value object representing a token-budgeted context capsule."""

    query: str
    symbols: tuple[dict[str, Any], ...]
    estimated_tokens: int
    max_token_budget: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "symbols": list(self.symbols),
            "estimated_tokens": self.estimated_tokens,
            "max_token_budget": self.max_token_budget,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextCapsule:
        return cls(
            query=data["query"],
            symbols=tuple(data["symbols"]),
            estimated_tokens=data["estimated_tokens"],
            max_token_budget=data["max_token_budget"],
        )

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


class ContextRetriever:
    """Retrieves symbol context capsules within specified token budgets."""

    @staticmethod
    def build_capsule(
        codegraph_nodes: Sequence[dict[str, Any]],
        query: str,
        max_token_budget: int = 1000,
    ) -> ContextCapsule:
        """Filter and rank codegraph symbol nodes matching query within token budget."""
        query_terms = [q.lower() for q in query.split() if q.strip()]
        matched_symbols: list[tuple[int, dict[str, Any]]] = []

        for node in codegraph_nodes:
            name = str(node.get("name", "")).lower()
            qname = str(node.get("qualified_name", "")).lower()
            score = 0
            for term in query_terms:
                if term in qname:
                    score += 2
                elif term in name:
                    score += 1
            if score > 0 or not query_terms:
                matched_symbols.append((score, node))

        # Sort by relevance score descending
        matched_symbols.sort(key=lambda item: item[0], reverse=True)

        selected: list[dict[str, Any]] = []
        current_tokens = 0

        for _, symbol in matched_symbols:
            symbol_tokens = _estimate_tokens(json.dumps(symbol))
            if current_tokens + symbol_tokens <= max_token_budget:
                selected.append(symbol)
                current_tokens += symbol_tokens
            if current_tokens >= max_token_budget:
                break

        return ContextCapsule(
            query=query,
            symbols=tuple(selected),
            estimated_tokens=current_tokens,
            max_token_budget=max_token_budget,
        )
