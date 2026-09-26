"""Local Software Department Orchestration for Stage 2.

Provides TaskContract verification, evidence auditing, and automated session handoff generation.
Standard-library only.
"""

from __future__ import annotations

from nps_core.department_orchestration.errors import (
    DepartmentError,
    HandoffValidationError,
    OrchestrationRuleViolationError,
)
from nps_core.department_orchestration.handoff import HandoffGenerator
from nps_core.department_orchestration.workflow import (
    DepartmentWorkflowEngine,
    TaskContractSpec,
)

__all__ = [
    "TaskContractSpec",
    "DepartmentWorkflowEngine",
    "HandoffGenerator",
    "DepartmentError",
    "OrchestrationRuleViolationError",
    "HandoffValidationError",
]
