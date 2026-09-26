"""Tests for orchestrator module — engine, integration, feedback."""

from __future__ import annotations

import pytest

from llm_bridge.decoder import CoreResult
from llm_bridge.encoder import LogicForm
from orchestrator.engine import Orchestrator
from orchestrator.feedback import FeedbackLoop
from orchestrator.integration import solve_problem

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class _MockLLMClient:
    """A deterministic LLM client that returns canned responses."""

    def __init__(self) -> None:
        self.chat_calls: list[dict] = []

    async def chat(self, prompt, model=None, system_prompt=None, temperature=0.0):
        self.chat_calls.append(
            {
                "prompt": prompt,
                "model": model,
                "system_prompt": system_prompt,
                "temperature": temperature,
            }
        )
        # Return a valid JSON logic form.
        return (
            '{"propositions": ["All A are B", "All B are C"], '
            '"relations": [["A","B","subset"],["B","C","subset"]], '
            '"query": "All A are C?"}'
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_orchestrator_run_returns_core_result() -> None:
    client = _MockLLMClient()
    orch = Orchestrator(client)  # type: ignore[arg-type]
    result = await orch.run("All A are B. All B are C. Is A C?")
    assert isinstance(result, CoreResult)
    assert result.logic_form.propositions == ["All A are B", "All B are C"]
    assert result.logic_form.query == "All A are C?"
    assert result.control_signal in ("continue", "measure", "backtrack", "delegate")
    assert result.confidence >= 0.0


@pytest.mark.asyncio
async def test_orchestrator_uses_stub_fallback() -> None:
    """When core/memory/funnel are stubs, orchestrator still works."""
    client = _MockLLMClient()
    orch = Orchestrator(client)  # type: ignore[arg-type]
    result = await orch.run("Test question?")
    assert isinstance(result, CoreResult)
    assert "answer" in result.details


# ---------------------------------------------------------------------------
# FeedbackLoop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feedback_loop_skips_continue() -> None:
    client = _MockLLMClient()
    orch = Orchestrator(client)  # type: ignore[arg-type]
    lf = LogicForm(propositions=["P"], query="Q?")
    cr = CoreResult(logic_form=lf, conclusion="OK", confidence=0.9, control_signal="continue")
    loop = FeedbackLoop(orch)
    resolved = await loop.resolve(cr)
    assert resolved is cr  # no change


@pytest.mark.asyncio
async def test_feedback_loop_resolves_backtrack() -> None:
    client = _MockLLMClient()
    orch = Orchestrator(client)  # type: ignore[arg-type]
    lf = LogicForm(propositions=["P"], query="Q?")
    cr = CoreResult(logic_form=lf, conclusion="Maybe", confidence=0.3, control_signal="backtrack")
    loop = FeedbackLoop(orch)
    resolved = await loop.resolve(cr)
    assert isinstance(resolved, CoreResult)
    assert resolved.control_signal == "measure"  # real funnel returns measure for low confidence


# ---------------------------------------------------------------------------
# solve_problem
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_solve_problem_returns_string() -> None:
    client = _MockLLMClient()
    answer = await solve_problem(
        "All A are B. All B are C. Is A C?",
        llm_client=client,  # type: ignore[arg-type]
    )
    assert isinstance(answer, str)
    assert len(answer) > 0


@pytest.mark.asyncio
async def test_solve_problem_no_feedback() -> None:
    client = _MockLLMClient()
    answer = await solve_problem(
        "Test?",
        llm_client=client,  # type: ignore[arg-type]
        use_feedback=False,
    )
    assert isinstance(answer, str)
