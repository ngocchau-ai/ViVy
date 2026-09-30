"""Tests for llm_bridge.decoder.Decoder and CoreResult."""

from __future__ import annotations

import pytest

from llm_bridge.decoder import CoreResult, Decoder
from llm_bridge.encoder import LogicForm

# ---------------------------------------------------------------------------
# CoreResult
# ---------------------------------------------------------------------------


def test_core_result_defaults() -> None:
    lf = LogicForm(propositions=["P"], query="Q?")
    cr = CoreResult(logic_form=lf)
    assert cr.conclusion == ""
    assert cr.confidence == 0.0
    assert cr.control_signal == "continue"
    assert cr.details == {}


# ---------------------------------------------------------------------------
# Decoder.template_answer (deterministic, no API)
# ---------------------------------------------------------------------------


def test_template_answer_high_confidence() -> None:
    lf = LogicForm(propositions=["All A are B"], query="All A are C?")
    cr = CoreResult(logic_form=lf, conclusion="All A are C", confidence=0.95)
    assert Decoder.template_answer(cr) == "All A are C"


def test_template_answer_low_confidence() -> None:
    lf = LogicForm(propositions=["All A are B"], query="All A are C?")
    cr = CoreResult(logic_form=lf, conclusion="All A are C", confidence=0.3)
    answer = Decoder.template_answer(cr)
    assert "low confidence" in answer
    assert "All A are C" in answer


def test_template_answer_backtrack() -> None:
    lf = LogicForm(propositions=["P"], query="Q?")
    cr = CoreResult(
        logic_form=lf,
        conclusion="Maybe Q",
        confidence=0.7,
        control_signal="backtrack",
    )
    answer = Decoder.template_answer(cr)
    assert "needs further reasoning" in answer


def test_template_answer_empty_conclusion() -> None:
    lf = LogicForm(propositions=["P1", "P2"], query="Final?")
    cr = CoreResult(logic_form=lf, conclusion="", confidence=0.5)
    answer = Decoder.template_answer(cr)
    assert "Final?" in answer  # falls back to query


# ---------------------------------------------------------------------------
# Decoder.decode (with mocked client)
# ---------------------------------------------------------------------------


class _FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response

    async def chat(self, prompt, model=None, system_prompt=None, temperature=0.2):
        return self.response


@pytest.mark.asyncio
async def test_decode_uses_llm() -> None:
    fake = _FakeClient("Yes, all A are C.")
    dec = Decoder(fake)  # type: ignore[arg-type]
    lf = LogicForm(propositions=["All A are B", "All B are C"], query="All A are C?")
    cr = CoreResult(logic_form=lf, conclusion="All A are C", confidence=0.95)
    answer = await dec.decode(cr)
    assert answer == "Yes, all A are C."


@pytest.mark.asyncio
async def test_decode_fallback_on_llm_error() -> None:
    class _FailingClient:
        async def chat(self, prompt, model=None, system_prompt=None, temperature=0.2):
            from llm_bridge.client import LLMError

            raise LLMError("API down")

    dec = Decoder(_FailingClient())  # type: ignore[arg-type]
    lf = LogicForm(propositions=["P"], query="Q?")
    cr = CoreResult(logic_form=lf, conclusion="Yes Q", confidence=0.9)
    answer = await dec.decode(cr)
    assert answer == "Yes Q"  # template fallback
