"""Domain exceptions for adaptive_n module.

Standard-library only.
"""

from __future__ import annotations

__all__ = [
    "AdaptiveNError",
    "BudgetExceededError",
]


class AdaptiveNError(ValueError):
    """Base domain exception for Adaptive N errors."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


class BudgetExceededError(AdaptiveNError):
    """Raised when target N_h exceeds maximum allowable budget."""
