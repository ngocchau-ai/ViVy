"""Tests for llm_bridge.encoder.Encoder and LogicForm."""

from __future__ import annotations

import pytest

from llm_bridge.client import LLMError
from llm_bridge.encoder import Encoder, LogicForm

# ---------------------------------------------------------------------------
# LogicForm
# ---------------------------------------------------------------------------


def test_logic_form_defaults() -> None:
    lf = LogicForm()
    assert lf.propositions == []
    assert lf.relations == []
    assert lf.query == ""


def test_logic_form_roundtrip_dict() -> None:
    lf = LogicForm(
        propositions=["All A are B", "All B are C"],
        relations=[("A", "B", "subset"), ("B", "C", "subset")],
        query="All A are C?",
    )
    d = lf.to_dict()
    assert d["relations"] == [["A", "B", "subset"], ["B", "C", "subset"]]
    lf2 = LogicForm.from_dict(d)
    assert lf2 == lf


# ---------------------------------------------------------------------------
# Encoder.parse (deterministic, no API)
# ---------------------------------------------------------------------------


def test_parse_plain_json() -> None:
    raw = (
        '{"propositions": ["All A are B", "All B are C"], '
        '"relations": [["A","B","subset"],["B","C","subset"]], '
        '"query": "All A are C?"}'
    )
    lf = Encoder.parse(raw)
    assert lf.propositions == ["All A are B", "All B are C"]
    assert lf.relations == [("A", "B", "subset"), ("B", "C", "subset")]
    assert lf.query == "All A are C?"


def test_parse_markdown_fence() -> None:
    raw = '```json\n{"propositions": ["P1"], "relations": [], "query": "Q?"}\n```'
    lf = Encoder.parse(raw)
    assert lf.propositions == ["P1"]
    assert lf.query == "Q?"


def test_parse_with_stray_text() -> None:
    raw = (
        'Here is the result: {"propositions": ["P"], '
        '"relations": [["X","Y","implies"]], "query": "Is it?"} thanks!'
    )
    lf = Encoder.parse(raw)
    assert lf.propositions == ["P"]
    assert lf.relations == [("X", "Y", "implies")]


def test_parse_single_quotes() -> None:
    raw = "{'propositions': ['P'], 'relations': [], 'query': 'Q'}"
    lf = Encoder.parse(raw)
    assert lf.propositions == ["P"]
    assert lf.query == "Q"


def test_parse_invalid_raises() -> None:
    with pytest.raises(LLMError):
        Encoder.parse("this is not json at all")


def test_parse_relation_as_string() -> None:
    raw = '{"propositions": [], "relations": ["A,B,subset"], "query": ""}'
    lf = Encoder.parse(raw)
    assert lf.relations == [("A", "B", "subset")]


# ---------------------------------------------------------------------------
# Encoder.encode (with a mocked client)
# ---------------------------------------------------------------------------


class _FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_prompt: str | None = None

    async def chat(self, prompt, model=None, system_prompt=None, temperature=0.0):
        self.last_prompt = prompt
        return self.response


@pytest.mark.asyncio
async def test_encode_uses_client_and_parses() -> None:
    fake = _FakeClient(
        '{"propositions": ["All A are B"], "relations": [], "query": "Q?"}'
    )
    enc = Encoder(fake)  # type: ignore[arg-type]
    lf = await enc.encode("All A are B. Is Q?")
    assert lf.propositions == ["All A are B"]
    assert "All A are B" in fake.last_prompt
