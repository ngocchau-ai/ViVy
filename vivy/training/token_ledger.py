"""C08 token ledger — counts only with an explicit tokenizer.

Never a silent `len(text)//4`. An approximate tokenizer may be used only when
the caller opts in, and every summary is labeled `APPROXIMATE_NOT_VERIFIED`.

Changelog:
    24/09/2026 (Claude Code — P4 C08): Initial.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


class TokenizerRequired(RuntimeError):
    """Raised when no tokenizer is supplied, or only an approximate one is allowed."""


class Tokenizer(Protocol):
    is_approximate: bool
    kind: str

    def count(self, text: str) -> int: ...


@dataclass(frozen=True)
class ByteTokenizer:
    is_approximate: bool = False
    kind: str = "byte_exact"

    def count(self, text: str) -> int:
        return len((text or "").encode("utf-8"))


@dataclass(frozen=True)
class ApproximateTokenizer:
    is_approximate: bool = True
    kind: str = "approximate_whitespace"

    def count(self, text: str) -> int:
        return max(len((text or "").split()), 0)


byte_tokenizer = ByteTokenizer()
approximate_tokenizer = ApproximateTokenizer()


class TokenLedger:
    def __init__(
        self,
        *,
        tokenizer: Tokenizer | None,
        require_real_tokenizer: bool = True,
    ) -> None:
        if tokenizer is None:
            raise TokenizerRequired("a tokenizer is required — no silent char/4 heuristic")
        if require_real_tokenizer and getattr(tokenizer, "is_approximate", True):
            raise TokenizerRequired(
                "approximate tokenizer refused; pass a real model tokenizer or "
                "require_real_tokenizer=False and accept APPROXIMATE_NOT_VERIFIED"
            )
        self.tokenizer = tokenizer
        self.require_real_tokenizer = require_real_tokenizer
        self._counts: dict[str, int] = {}

    def count(self, text: str) -> int:
        return int(self.tokenizer.count(text or ""))

    def record(self, name: str, text: str) -> int:
        n = self.count(text)
        self._counts[name] = self._counts.get(name, 0) + n
        return n

    def summary(self) -> dict[str, Any]:
        before = self._counts.get("context_before")
        after = self._counts.get("context_after")
        delta = None
        reduction = None
        if before is not None and after is not None:
            delta = after - before
            if before > 0:
                reduction = 100.0 * (before - after) / before
        is_approx = bool(getattr(self.tokenizer, "is_approximate", True))
        return {
            "tokenizer_kind": getattr(self.tokenizer, "kind", "unknown"),
            "is_approximate": is_approx,
            "status_label": "APPROXIMATE_NOT_VERIFIED" if is_approx else "VERIFIED_COUNTS",
            "counts": dict(self._counts),
            "delta_before_to_after": delta,
            "reduction_percent": reduction,
            "note": "counts come from the injected tokenizer only; never len//4",
        }
