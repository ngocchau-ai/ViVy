"""Unit tests for department_orchestration module."""

from __future__ import annotations

import pytest

from nps_core.department_orchestration import (
    DepartmentWorkflowEngine,
    HandoffGenerator,
    HandoffValidationError,
    OrchestrationRuleViolationError,
)


def test_verify_contract_valid() -> None:
    contract_dict = {
        "task_contract": {
            "task_id": "TASK-007",
            "title": "Stage 2 Workflow Automation",
            "objective": {
                "problem": "Stage 2 automation needed",
                "expected_outcome": "Clean workflow engine",
            },
            "implementation": {
                "assigned_role": "local_coder",
                "allowed_files": ["src/nps_core/department_orchestration/**"],
            },
            "validation": {
                "acceptance_criteria": ["All tests pass"],
            },
        }
    }

    spec = DepartmentWorkflowEngine.verify_contract(contract_dict)
    assert spec.task_id == "TASK-007"
    assert spec.assigned_role == "local_coder"

    evidence = {
        "task_id": "TASK-007",
        "result": "PASSED",
    }
    assert DepartmentWorkflowEngine.audit_evidence(spec, evidence) is True


def test_verify_contract_invalid_role() -> None:
    contract_dict = {
        "task_contract": {
            "task_id": "TASK-007",
            "title": "Stage 2 Workflow Automation",
            "implementation": {
                "assigned_role": "codex_direct_writer",
            },
        }
    }
    with pytest.raises(OrchestrationRuleViolationError, match="Assigned role must be local model role"):
        DepartmentWorkflowEngine.verify_contract(contract_dict)


def test_handoff_generator() -> None:
    content = HandoffGenerator.generate(
        completed_tasks=("TASK-001", "TASK-002", "TASK-007"),
        current_state="Stage 2 workflow complete",
        open_risks=("None",),
        next_action="Execute TASK-008",
        required_context=("ARCHITECTURE.md",),
    )

    assert "# Session Handoff" in content
    assert "TASK-007" in content
    assert "Stage 2 workflow complete" in content


def test_handoff_generator_validation() -> None:
    with pytest.raises(HandoffValidationError, match="completed_tasks cannot be empty"):
        HandoffGenerator.generate([], "state", [], "next", [])
