"""
Orchestrator Integration — end-to-end entry point.

Provides :func:`solve_problem`, which takes a natural-language question and
returns a natural-language answer by wiring together the LLM bridge, the
unitary core, the filter funnel, and the decoder.
"""

from __future__ import annotations

import logging
from typing import Any

from llm_bridge.client import LLMClient
from llm_bridge.decoder import CoreResult, Decoder

from .engine import Orchestrator
from .feedback import FeedbackLoop

logger = logging.getLogger(__name__)


async def solve_problem(
    question: str,
    *,
    llm_client: LLMClient | None = None,
    orchestrator: Orchestrator | None = None,
    use_feedback: bool = True,
    **orchestrator_kwargs: Any,
) -> str:
    """End-to-end reasoning: natural-language question → natural-language answer.

    Parameters
    ----------
    question:
        The user's natural-language question.
    llm_client:
        Optional :class:`LLMClient`.  Created with defaults if not provided.
    orchestrator:
        Optional pre-built :class:`Orchestrator`.  Built from *llm_client*
        and *orchestrator_kwargs* if not provided.
    use_feedback:
        Whether to run the feedback loop for ``backtrack`` / ``delegate``
        control signals.
    orchestrator_kwargs:
        Extra keyword arguments forwarded to :class:`Orchestrator`.

    Returns
    -------
    str
        The natural-language answer.
    """
    if orchestrator is None:
        llm_client = llm_client or LLMClient()
        orchestrator = Orchestrator(llm_client, **orchestrator_kwargs)

    result = await orchestrator.run(question)

    if use_feedback and result.control_signal in ("backtrack", "delegate"):
        logger.info("solve_problem: feedback loop triggered (%s)", result.control_signal)
        loop = FeedbackLoop(orchestrator)
        result = await loop.resolve(result)

    answer = result.details.get("answer")
    if not answer:
        decoder = orchestrator.decoder or Decoder(orchestrator.llm_client)
        answer = await decoder.decode(result)
        result.details["answer"] = answer

    return answer


async def solve_problem_verbose(
    question: str,
    *,
    llm_client: LLMClient | None = None,
    orchestrator: Orchestrator | None = None,
    **kwargs: Any,
) -> tuple[str, CoreResult]:
    """Like :func:`solve_problem` but also returns the full :class:`CoreResult`."""
    if orchestrator is None:
        llm_client = llm_client or LLMClient()
        orchestrator = Orchestrator(llm_client, **kwargs)

    result = await orchestrator.run(question)
    answer = result.details.get("answer") or await (
        orchestrator.decoder or Decoder(orchestrator.llm_client)
    ).decode(result)
    result.details["answer"] = answer
    return answer, result
