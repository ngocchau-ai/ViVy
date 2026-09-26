"""End-to-end test: syllogism reasoning through the full pipeline.

All A are B. All B are C. → Therefore All A are C.

Uses a fully mocked LLM client so the test runs offline and deterministically.
"""

from __future__ import annotations

import pytest

from llm_bridge.decoder import CoreResult
from orchestrator.integration import solve_problem, solve_problem_verbose


class _SyllogismClient:
    """Mock LLM that encodes syllogisms and decodes conclusions."""

    def __init__(self) -> None:
        self.encode_calls = 0
        self.decode_calls = 0

    async def chat(self, prompt, model=None, system_prompt=None, temperature=0.0):
        # Encoder path: system prompt asks for logic form JSON.
        if system_prompt and "logic-form" in system_prompt:
            self.encode_calls += 1
            return (
                '{"propositions": ["All A are B", "All B are C"], '
                '"relations": [["A","B","subset"],["B","C","subset"]], '
                '"query": "All A are C?"}'
            )
        # Decoder / feedback path.
        self.decode_calls += 1
        return "Yes, all A are C."


@pytest.mark.asyncio
async def test_syllogism_end_to_end() -> None:
    client = _SyllogismClient()
    question = "All A are B. All B are C. Therefore, are all A C?"
    answer = await solve_problem(question, llm_client=client)  # type: ignore[arg-type]
    assert isinstance(answer, str)
    assert answer.strip() != ""
    assert client.encode_calls >= 1


@pytest.mark.asyncio
async def test_syllogism_verbose_returns_result() -> None:
    client = _SyllogismClient()
    question = "All A are B. All B are C. Are all A C?"
    answer, result = await solve_problem_verbose(question, llm_client=client)  # type: ignore[arg-type]
    assert isinstance(answer, str)
    assert isinstance(result, CoreResult)
    # The logic form should capture the syllogism premises and conclusion query.
    assert "All A are B" in result.logic_form.propositions
    assert "All B are C" in result.logic_form.propositions
    assert "All A are C" in result.logic_form.query


@pytest.mark.asyncio
async def test_syllogism_relations_are_subset_chains() -> None:
    client = _SyllogismClient()
    question = "All A are B. All B are C. Are all A C?"
    _, result = await solve_problem_verbose(question, llm_client=client)  # type: ignore[arg-type]
    relations = result.logic_form.relations
    assert ("A", "B", "subset") in relations
    assert ("B", "C", "subset") in relations
