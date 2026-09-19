"""Experiment Designer module for NPS Core.

Selects experiments, manages ExperimentContracts, VerificationNeeds,
and VerificationPortfolio for verifier-demand (N_v) accounting.
Standard-library only; no runtime dependencies beyond standard library.
"""

from __future__ import annotations

from nps_core.experiment_designer.contract import ExperimentContract
from nps_core.experiment_designer.errors import (
    ExperimentValidationError,
    PortfolioValidationError,
    SnapshotMismatchError,
    UncoveredNeedError,
    UnknownThoughtError,
    UnlinkedContractError,
    VerifierBudgetError,
)
from nps_core.experiment_designer.portfolio import (
    VerificationNeed,
    VerificationPortfolio,
)

__all__ = [
    "ExperimentContract",
    "VerificationNeed",
    "VerificationPortfolio",
    "ExperimentValidationError",
    "PortfolioValidationError",
    "VerifierBudgetError",
    "SnapshotMismatchError",
    "UnknownThoughtError",
    "UncoveredNeedError",
    "UnlinkedContractError",
]
