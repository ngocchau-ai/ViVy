"""Domain errors for executor_router module.

All errors inherit from ExecutorRoutingError.
No runtime dependencies beyond standard library.
"""

from __future__ import annotations

__all__ = [
    "ExecutorRoutingError",
    "ExecutorBudgetError",
    "UnmatchedRequirementError",
]


class ExecutorRoutingError(ValueError):
    """Base domain exception for executor router errors."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


class ExecutorBudgetError(ExecutorRoutingError):
    """Raised when N_h >= N_v >= N_e invariant is violated or executor budget is exceeded."""


class UnmatchedRequirementError(ExecutorRoutingError):
    """Raised when an ExperimentContract requirement cannot be met by available executors."""
