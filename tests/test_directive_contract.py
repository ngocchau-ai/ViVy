"""Tests for DirectiveTaskContract schema — V5.0 Sprint 2A.

10 tests cho các dataclasses và enums trong directive_contract.py.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2A tests): Initial implementation.
"""

from __future__ import annotations

from dataclasses import is_dataclass

from orchestrator.directive_contract import (
    DirectiveTaskContract,
    Evidence,
    EvidenceCriteria,
    EvidenceStatus,
    TaskType,
)


def test_directive_task_contract_is_dataclass() -> None:
    """DirectiveTaskContract must be a dataclass."""
    assert is_dataclass(DirectiveTaskContract)


def test_directive_task_contract_required_fields() -> None:
    """DirectiveTaskContract requires task_id, task_description, task_type."""
    c = DirectiveTaskContract(
        task_id="t001",
        task_description="Explain recursion",
        task_type=TaskType.REASONING,
    )
    assert c.task_id == "t001"
    assert c.task_description == "Explain recursion"
    assert c.task_type == TaskType.REASONING


def test_directive_task_contract_defaults() -> None:
    """Default values: timeout=120, max_retries=3, context=''."""
    c = DirectiveTaskContract(
        task_id="t002",
        task_description="Write sort function",
        task_type=TaskType.CODING,
    )
    assert c.timeout_s == 120
    assert c.max_retries == 3
    assert c.context == ""
    assert c.preferred_model is None


def test_task_type_values_are_strings() -> None:
    """TaskType must be StrEnum with expected values."""
    assert TaskType.CODING == "CODING"
    assert TaskType.MATH == "MATH"
    assert TaskType.REASONING == "REASONING"
    assert TaskType.GENERAL == "GENERAL"
    assert TaskType.ANALYSIS == "ANALYSIS"


def test_evidence_status_values() -> None:
    """EvidenceStatus must have PASS, FAIL, TIMEOUT, ESCALATED."""
    assert EvidenceStatus.PASS == "PASS"
    assert EvidenceStatus.FAIL == "FAIL"
    assert EvidenceStatus.TIMEOUT == "TIMEOUT"
    assert EvidenceStatus.ESCALATED == "ESCALATED"


def test_evidence_success_factory() -> None:
    """Evidence.success() creates a passing Evidence."""
    ev = Evidence.success(output="OK result", model_used="gemma4eb", attempt=1)
    assert ev.passes is True
    assert ev.status == EvidenceStatus.PASS
    assert ev.output == "OK result"
    assert ev.model_used == "gemma4eb"


def test_evidence_failure_factory() -> None:
    """Evidence.failure() creates a failing Evidence."""
    ev = Evidence.failure(output="bad output", error="missing keyword", model_used="gemma4eb")
    assert ev.passes is False
    assert ev.status == EvidenceStatus.FAIL
    assert ev.error_message == "missing keyword"


def test_evidence_timeout_factory() -> None:
    """Evidence.timeout() creates TIMEOUT Evidence."""
    ev = Evidence.timeout(model_used="gemma4eb", attempt=2)
    assert ev.status == EvidenceStatus.TIMEOUT
    assert ev.passes is False
    assert ev.attempt == 2


def test_evidence_escalated_factory() -> None:
    """Evidence.escalated() creates ESCALATED Evidence with reason in message."""
    ev = Evidence.escalated("All 3 attempts failed")
    assert ev.status == EvidenceStatus.ESCALATED
    assert ev.passes is False
    assert "All 3 attempts failed" in ev.error_message


def test_evidence_criteria_defaults() -> None:
    """EvidenceCriteria defaults: no test pass required, no_error=True."""
    c = EvidenceCriteria(description="Output is useful")
    assert c.require_test_pass is False
    assert c.require_no_error is True
    assert c.require_output_contains == []
