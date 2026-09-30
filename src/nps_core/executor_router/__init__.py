"""Executor Router and N_e Accounting module for NPS Core.

Selects models, solvers, tools, or humans and accounts N_e.
Enforces N_h >= N_v >= N_e architecture invariant.
Standard-library only; no runtime dependencies beyond standard library.
"""

from __future__ import annotations

from nps_core.executor_router.errors import (
    ExecutorBudgetError,
    ExecutorRoutingError,
    UnmatchedRequirementError,
)
from nps_core.executor_router.router import (
    ExecutorAssignment,
    ExecutorDescriptor,
    ExecutorRouter,
    ExecutorRoutingPlan,
)

__all__ = [
    "ExecutorDescriptor",
    "ExecutorAssignment",
    "ExecutorRoutingPlan",
    "ExecutorRouter",
    "ExecutorRoutingError",
    "ExecutorBudgetError",
    "UnmatchedRequirementError",
]
