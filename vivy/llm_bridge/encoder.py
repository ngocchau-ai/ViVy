"""
Encoder — Natural Language → Logic Form.

Uses an LLM (via :class:`LLMClient`) plus a deterministic JSON parser to
convert a natural-language question into a structured :class:`LogicForm`
containing propositions, relations, and a query.  The LLM is prompted to
emit strict JSON; a regex-based parser extracts the fields so that even
slightly malformed model output can be recovered.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .client import LLMClient, LLMError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class LogicForm:
    """Structured logic representation of a natural-language question.

    Attributes
    ----------
    propositions:
        Atomic statements extracted from the input, e.g.
        ``["All A are B", "All B are C"]``.
    relations:
        Ordered pairs / tuples capturing the logical relationships, e.g.
        ``[("A", "B", "subset"), ("B", "C", "subset")]``.
    query:
        The question being asked, e.g. ``"All A are C?"``.
    """

    propositions: list[str] = field(default_factory=list)
    relations: list[tuple[str, ...]] = field(default_factory=list)
    query: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {
            "propositions": list(self.propositions),
            "relations": [list(r) for r in self.relations],
            "query": self.query,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogicForm:
        """Deserialize from a dict produced by :meth:`to_dict`."""
        return cls(
            propositions=list(data.get("propositions", [])),
            relations=[tuple(r) for r in data.get("relations", [])],
            query=str(data.get("query", "")),
        )


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

ENCODE_SYSTEM_PROMPT = """\
You are a logic-form extractor for a unitary reasoning engine.
Given a natural-language question, extract:
  - propositions: the atomic factual statements (strings).
  - relations: tuples (subject, object, relation) capturing the logical
    links between the entities in the propositions.
  - query: the question being asked, as a single string.
Respond with ONLY a JSON object of the form:
{"propositions": ["..."], "relations": [["A","B","subset"], ...], "query": "..."}
Do not include any text outside the JSON object.
"""


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------


class Encoder:
    """Convert natural-language text into a :class:`LogicForm`.

    Parameters
    ----------
    client:
        The :class:`LLMClient` used to call the model.
    model:
        Optional model override.  Defaults to the client's default model.
    """

    def __init__(self, client: LLMClient, model: str | None = None) -> None:
        self.client = client
        self.model = model

    async def encode(self, nl_text: str) -> LogicForm:
        """Encode a natural-language question into a :class:`LogicForm`."""
        prompt = _build_encode_prompt(nl_text)
        raw = await self.client.chat(
            prompt,
            model=self.model,
            system_prompt=ENCODE_SYSTEM_PROMPT,
            temperature=0.0,
        )
        return self.parse(raw)

    # ------------------------------------------------------------------
    # Deterministic parsing (testable without a live API)
    # ------------------------------------------------------------------

    @staticmethod
    def parse(raw: str) -> LogicForm:
        """Parse an LLM JSON response into a :class:`LogicForm`.

        Tolerates markdown fences, stray text, and single-quoted keys.
        Raises :class:`LLMError` if no usable JSON can be found.
        """
        data = _extract_json(raw)
        if data is None:
            raise LLMError(f"Could not parse encoder output: {raw!r}")

        propositions = _as_str_list(data.get("propositions", []))
        relations = _as_relation_list(data.get("relations", []))
        query = str(data.get("query", "")).strip()

        return LogicForm(
            propositions=propositions,
            relations=relations,
            query=query,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_encode_prompt(nl_text: str) -> str:
    return (
        "Extract the logic form of the following question.\n"
        f"QUESTION: {nl_text}\n"
        "OUTPUT (JSON only):"
    )


def _extract_json(raw: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from an LLM response."""
    text = raw.strip()
    # Strip markdown code fences.
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    # Try strict JSON parse first.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Fall back to locating the first { ... } block.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # Last resort: tolerate single quotes.
    try:
        import ast

        obj = ast.literal_eval(text if text.startswith("{") else candidate)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return []


def _as_relation_list(value: Any) -> list[tuple[str, ...]]:
    if not isinstance(value, list):
        return []
    relations: list[tuple[str, ...]] = []
    for item in value:
        if isinstance(item, (list, tuple)):
            rel = tuple(str(x).strip() for x in item if str(x).strip())
        elif isinstance(item, str):
            rel = tuple(x.strip() for x in item.split(",") if x.strip())
        else:
            continue
        if rel:
            relations.append(rel)
    return relations
