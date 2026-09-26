"""Domain errors for experiment_designer module.

All errors inherit from ExperimentValidationError.
No runtime dependencies beyond standard library.
"""

from __future__ import annotations

__all__ = [
    "ExperimentValidationError",
    "PortfolioValidationError",
    "VerifierBudgetError",
    "SnapshotMismatchError",
    "UnknownThoughtError",
    "UncoveredNeedError",
    "UnlinkedContractError",
]


class ExperimentValidationError(ValueError):
    """Base validation error for experiment designer runtime."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


class PortfolioValidationError(ExperimentValidationError):
    """Error raised when VerificationPortfolio structural or snapshot validation fails."""


class VerifierBudgetError(PortfolioValidationError):
    """Error raised when verifier budget (N_v) constraints or bounds are violated."""


class SnapshotMismatchError(PortfolioValidationError):
    """Error raised when portfolio snapshot digest does not match supplied PopulationSnapshot."""


class UnknownThoughtError(PortfolioValidationError):
    """Error raised when referenced hypothesis ID is not present in the PopulationSnapshot."""


class UncoveredNeedError(PortfolioValidationError):
    """Error raised when a VerificationNeed is not covered by any ExperimentContract."""


class UnlinkedContractError(PortfolioValidationError):
    """Error raised when an ExperimentContract does not cover any VerificationNeed."""
