"""Tests for ModelRouter — V5.0 Sprint 2B.

15 tests cho ModelRouter và verify_evidence function.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2B tests): Initial implementation.
"""

from __future__ import annotations

import asyncio
from typing import Any

from orchestrator.directive_contract import (
    DirectiveTaskContract,
    EvidenceCriteria,
    EvidenceStatus,
    TaskType,
)
from orchestrator.model_router import ModelRouter, verify_evidence

# ---------------------------------------------------------------------------
# Mock LLM client
# ---------------------------------------------------------------------------


class _MockLLMClient:
    """Mock LLM client with configurable response."""

    def __init__(self, response: str = "OK output", raise_exc: Exception | None = None) -> None:
        self._response = response
        self._raise = raise_exc
        self.call_count = 0

    async def chat(self, prompt: str, model: str | None = None, **kwargs: Any) -> str:
        self.call_count += 1
        if self._raise:
            raise self._raise
        return self._response


class _TimeoutLLMClient:
    """Mock LLM client that always times out."""

    async def chat(self, prompt: str, model: str | None = None, **kwargs: Any) -> str:
        await asyncio.sleep(9999)
        return ""


# ---------------------------------------------------------------------------
# Tests for verify_evidence
# ---------------------------------------------------------------------------


def test_verify_evidence_passes_clean_output() -> None:
    """Clean output with no errors passes default criteria."""
    criteria = EvidenceCriteria(description="Basic pass", require_no_error=True)
    passes, reason = verify_evidence("All good!", criteria)
    assert passes is True
    assert reason == ""


def test_verify_evidence_fails_on_traceback() -> None:
    """Output with 'Traceback' fails require_no_error check."""
    criteria = EvidenceCriteria(description="No error", require_no_error=True)
    passes, reason = verify_evidence("Traceback (most recent call last): ...", criteria)
    assert passes is False
    assert "Traceback" in reason


def test_verify_evidence_fails_on_missing_required_string() -> None:
    """Output missing required_contains string fails."""
    criteria = EvidenceCriteria(
        description="Must contain OK",
        require_output_contains=["PASS"],
    )
    passes, reason = verify_evidence("Test completed", criteria)
    assert passes is False
    assert "PASS" in reason


def test_verify_evidence_passes_with_required_string() -> None:
    """Output containing all required strings passes."""
    criteria = EvidenceCriteria(
        description="Must contain PASS",
        require_output_contains=["PASS"],
    )
    passes, reason = verify_evidence("Test result: PASS", criteria)
    assert passes is True


def test_verify_evidence_empty_output_fails_when_requires_contains() -> None:
    """Empty output fails when require_output_contains is set."""
    criteria = EvidenceCriteria(
        description="Needs content",
        require_output_contains=["something"],
    )
    passes, reason = verify_evidence("", criteria)
    assert passes is False


# ---------------------------------------------------------------------------
# Tests for ModelRouter
# ---------------------------------------------------------------------------


def test_model_router_select_model_default() -> None:
    """ModelRouter.select_model() returns default model for task type."""
    client = _MockLLMClient()
    router = ModelRouter(client)
    model = router.select_model(TaskType.REASONING)
    assert isinstance(model, str)
    assert len(model) > 0


def test_model_router_select_model_preferred_override() -> None:
    """preferred_model overrides automatic selection."""
    client = _MockLLMClient()
    router = ModelRouter(client)
    model = router.select_model(TaskType.CODING, preferred_model="my-custom-model")
    assert model == "my-custom-model"


def test_model_router_dispatch_success() -> None:
    """dispatch() returns PASS Evidence when model output passes criteria."""
    client = _MockLLMClient(response="The answer is 42")
    router = ModelRouter(client)
    contract = DirectiveTaskContract(
        task_id="t-001",
        task_description="What is the answer?",
        task_type=TaskType.REASONING,
        evidence_criteria=EvidenceCriteria(description="Non-empty output"),
        max_retries=1,
    )
    evidence = asyncio.run(router.dispatch(contract))
    assert evidence.passes is True
    assert evidence.status == EvidenceStatus.PASS
    assert evidence.output == "The answer is 42"


def test_model_router_dispatch_fail_then_escalate() -> None:
    """dispatch() escalates after max_retries failed attempts."""
    client = _MockLLMClient(response="Error: something went wrong")
    router = ModelRouter(client)
    contract = DirectiveTaskContract(
        task_id="t-002",
        task_description="This will fail",
        task_type=TaskType.GENERAL,
        evidence_criteria=EvidenceCriteria(
            description="Must not have errors",
            require_no_error=True,
        ),
        max_retries=2,
        timeout_s=30,
    )
    evidence = asyncio.run(router.dispatch(contract))
    # Error: marker triggers fail → escalation after 2 retries
    assert evidence.status == EvidenceStatus.ESCALATED
    assert evidence.passes is False


def test_model_router_dispatch_timeout() -> None:
    """dispatch() returns TIMEOUT Evidence when model call exceeds timeout."""
    client = _TimeoutLLMClient()
    router = ModelRouter(client)
    contract = DirectiveTaskContract(
        task_id="t-003",
        task_description="This will timeout",
        task_type=TaskType.GENERAL,
        timeout_s=1,
        max_retries=1,
    )
    evidence = asyncio.run(router.dispatch(contract))
    assert evidence.status in (EvidenceStatus.TIMEOUT, EvidenceStatus.ESCALATED)
    assert evidence.passes is False


def test_model_router_dispatch_exception_becomes_failure() -> None:
    """Exception from LLM client is captured and returned as FAIL/ESCALATED."""
    client = _MockLLMClient(raise_exc=ConnectionError("Connection refused"))
    router = ModelRouter(client)
    contract = DirectiveTaskContract(
        task_id="t-004",
        task_description="Will raise exception",
        task_type=TaskType.GENERAL,
        max_retries=1,
    )
    evidence = asyncio.run(router.dispatch(contract))
    assert evidence.passes is False


def test_model_router_retries_before_escalate() -> None:
    """dispatch() retries max_retries times before escalating."""
    client = _MockLLMClient(response="Error: bad output")
    router = ModelRouter(client)
    contract = DirectiveTaskContract(
        task_id="t-005",
        task_description="Will fail on every attempt",
        task_type=TaskType.GENERAL,
        evidence_criteria=EvidenceCriteria(description="No errors", require_no_error=True),
        max_retries=3,
        timeout_s=10,
    )
    evidence = asyncio.run(router.dispatch(contract))
    # Should attempt 3 times
    assert client.call_count == 3
    assert evidence.status == EvidenceStatus.ESCALATED


def test_model_router_build_prompt_includes_task() -> None:
    """_build_prompt() includes task_description and task_type."""
    client = _MockLLMClient()
    router = ModelRouter(client)
    contract = DirectiveTaskContract(
        task_id="t-006",
        task_description="Sort this list",
        task_type=TaskType.CODING,
        context="mylist = [3, 1, 2]",
    )
    prompt = router._build_prompt(contract)
    assert "Sort this list" in prompt
    assert "CODING" in prompt
    assert "mylist" in prompt


def test_model_router_custom_model_map() -> None:
    """ModelRouter accepts custom model_map overrides."""
    custom_map = {
        TaskType.CODING: "deepseek-coder",
        TaskType.MATH: "qwen-math",
        TaskType.REASONING: "gemma4eb",
        TaskType.GENERAL: "gemma4eb",
        TaskType.ANALYSIS: "gemma4eb",
    }
    client = _MockLLMClient()
    router = ModelRouter(client, model_map=custom_map)
    assert router.select_model(TaskType.CODING) == "deepseek-coder"
    assert router.select_model(TaskType.MATH) == "qwen-math"
