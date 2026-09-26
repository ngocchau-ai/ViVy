"""Department Workflow Engine and TaskContract Auditor for Stage 2.

Enforces Codex orchestration-only constraints and role-isolated task execution.
Standard-library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from nps_core.department_orchestration.errors import (
    DepartmentError,
    OrchestrationRuleViolationError,
)

__all__ = [
    "TaskContractSpec",
    "DepartmentWorkflowEngine",
]

_TASK_ID_RE = re.compile(r"^TASK-\d{3}$")


def _err(msg: str, *, path: str | None = None) -> DepartmentError:
    return DepartmentError(msg, path=path)


@dataclass(frozen=True, slots=True)
class TaskContractSpec:
    """Frozen value object holding parsed TaskContract requirements."""

    task_id: str
    title: str
    problem: str
    expected_outcome: str
    assigned_role: str
    allowed_files: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.task_id, bool) or not isinstance(self.task_id, str):
            raise _err("task_id must be a string", path="task_id")
        if not _TASK_ID_RE.match(self.task_id):
            raise _err("task_id must match ^TASK-\\d{3}$", path="task_id")
        if not self.title.strip():
            raise _err("title must be non-empty", path="title")
        if self.assigned_role not in ("local_coder", "local_tester", "local_reviewer"):
            raise OrchestrationRuleViolationError(
                f"Assigned role must be local model role, got {self.assigned_role!r}",
                path="assigned_role",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "problem": self.problem,
            "expected_outcome": self.expected_outcome,
            "assigned_role": self.assigned_role,
            "allowed_files": list(self.allowed_files),
            "acceptance_criteria": list(self.acceptance_criteria),
        }


class DepartmentWorkflowEngine:
    """Workflow engine enforcing local department contract rules."""

    @staticmethod
    def verify_contract(contract_dict: dict[str, Any]) -> TaskContractSpec:
        """Parse and verify TaskContract dictionary against Codex constraints."""
        if not isinstance(contract_dict, dict) or "task_contract" not in contract_dict:
            raise _err("Top-level dictionary must contain 'task_contract' key")

        tc = contract_dict["task_contract"]
        if not isinstance(tc, dict):
            raise _err("'task_contract' must be a dict")

        task_id = tc.get("task_id", "")
        title = tc.get("title", "")
        obj = tc.get("objective", {})
        impl = tc.get("implementation", {})
        val = tc.get("validation", {})

        problem = obj.get("problem", "") if isinstance(obj, dict) else ""
        expected_outcome = obj.get("expected_outcome", "") if isinstance(obj, dict) else ""
        assigned_role = impl.get("assigned_role", "") if isinstance(impl, dict) else ""
        allowed_files = tuple(impl.get("allowed_files", [])) if isinstance(impl, dict) else ()
        acceptance_criteria = tuple(val.get("acceptance_criteria", [])) if isinstance(val, dict) else ()

        spec = TaskContractSpec(
            task_id=task_id,
            title=title,
            problem=problem,
            expected_outcome=expected_outcome,
            assigned_role=assigned_role,
            allowed_files=allowed_files,
            acceptance_criteria=acceptance_criteria,
        )
        return spec

    @staticmethod
    def audit_evidence(spec: TaskContractSpec, evidence_dict: dict[str, Any]) -> bool:
        """Audit evidence packet against TaskContractSpec requirements."""
        if not isinstance(evidence_dict, dict):
            raise _err("evidence_dict must be a dict")
        if evidence_dict.get("task_id") != spec.task_id:
            raise OrchestrationRuleViolationError(
                f"Evidence task_id '{evidence_dict.get('task_id')}' does not match contract task_id '{spec.task_id}'",
                path="task_id",
            )
        if evidence_dict.get("result") not in ("PASSED", "APPROVED") and "passed" not in str(evidence_dict.get("result")).lower():
            raise OrchestrationRuleViolationError(
                f"Evidence result '{evidence_dict.get('result')}' indicates failure",
                path="result",
            )
        return True
