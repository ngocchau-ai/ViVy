"""
Decoder — Logic Result → Natural Language.

Takes the output of the unitary core (a :class:`LogicForm` plus the funnel's
verdict / confidence) and uses an LLM to synthesize a coherent natural-language
answer.  Also provides a deterministic fallback that builds a readable sentence
from the logic form when the API is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .client import LLMClient, LLMError
from .encoder import LogicForm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CoreResult:
    """Structured result produced by the unitary core + funnel.

    Attributes
    ----------
    logic_form:
        The logic form that was reasoned over.
    conclusion:
        The derived conclusion (a proposition string).
    confidence:
        Funnel confidence score in [0, 1].
    control_signal:
        Funnel control signal, e.g. ``"continue"``, ``"measure"``,
        ``"backtrack"``, ``"delegate"``.
    details:
        Extra context (thought streams, kept streams, etc.).
    """

    logic_form: LogicForm
    conclusion: str = ""
    confidence: float = 0.0
    control_signal: str = "continue"
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

DECODE_SYSTEM_PROMPT = """\
You are the natural-language answer synthesizer for a unitary reasoning engine.
Given the logic form of a question, the derived conclusion, and a confidence
score, produce a clear, concise answer in natural language.
If confidence is low, say so and qualify the answer.
Respond with ONLY the answer text — no JSON, no preamble.
"""


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------


class Decoder:
    """Synthesize a natural-language answer from a :class:`CoreResult`.

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

    async def decode(self, result: CoreResult) -> str:
        """Return a natural-language answer for a core result."""
        prompt = _build_decode_prompt(result)
        try:
            return await self.client.chat(
                prompt,
                model=self.model,
                system_prompt=DECODE_SYSTEM_PROMPT,
                temperature=0.2,
            )
        except LLMError as exc:
            logger.warning("LLM decode failed (%s); using template fallback", exc)
            return self.template_answer(result)

    # ------------------------------------------------------------------
    # Deterministic fallback (testable without a live API)
    # ------------------------------------------------------------------

    @staticmethod
    def template_answer(result: CoreResult) -> str:
        """Build a readable answer from a :class:`CoreResult` without an LLM."""
        conclusion = result.conclusion.strip() or _summarize_logic_form(result.logic_form)
        qualifier = ""
        if result.confidence < 0.5:
            qualifier = " (low confidence)"
        elif result.control_signal in ("backtrack", "delegate"):
            qualifier = " (needs further reasoning)"
        return f"{conclusion}{qualifier}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_decode_prompt(result: CoreResult) -> str:
    lf = result.logic_form
    return (
        "Synthesize an answer from this reasoning result.\n"
        f"PROPOSITIONS: {lf.propositions}\n"
        f"RELATIONS: {lf.relations}\n"
        f"QUERY: {lf.query}\n"
        f"CONCLUSION: {result.conclusion}\n"
        f"CONFIDENCE: {result.confidence:.2f}\n"
        f"CONTROL SIGNAL: {result.control_signal}\n"
        "ANSWER:"
    )


def _summarize_logic_form(lf: LogicForm) -> str:
    if lf.query:
        return lf.query
    if lf.propositions:
        return lf.propositions[-1]
    return "No conclusion was derived."
