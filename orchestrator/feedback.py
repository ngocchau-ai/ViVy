"""
Orchestrator Feedback Loop — handles 'backtrack' and 'delegate' control signals.

When the filter funnel signals that the current reasoning path is weak
(``backtrack``) or outside the core's competence (``delegate``), the feedback
loop asks the LLM for supplementary information and re-runs the pipeline with
that additional context.
"""

from __future__ import annotations

import logging

from llm_bridge.decoder import CoreResult

from .engine import Orchestrator

logger = logging.getLogger(__name__)

# Control signals that trigger the feedback loop.
FEEDBACK_SIGNALS = frozenset({"backtrack", "delegate"})

# Prompt used to request supplementary information from the LLM.
FEEDBACK_SYSTEM_PROMPT = """\
You are a reasoning assistant. The unitary core could not confidently resolve a
question. Provide supplementary information or a clarifying reformulation that
would help the reasoning engine reach a conclusion. Be concise.
"""


class FeedbackLoop:
    """Iteratively resolve weak reasoning via supplementary LLM calls.

    Parameters
    ----------
    orchestrator:
        The :class:`Orchestrator` whose pipeline will be re-run.
    max_rounds:
        Maximum number of feedback rounds before giving up.
    """

    def __init__(self, orchestrator: Orchestrator, max_rounds: int = 3) -> None:
        self.orchestrator = orchestrator
        self.max_rounds = max_rounds

    async def resolve(self, initial: CoreResult) -> CoreResult:
        """Resolve a weak result by requesting supplementary LLM information.

        Returns the best :class:`CoreResult` obtained, or the last result if
        the loop exhausts its rounds.
        """
        result = initial
        for round_no in range(1, self.max_rounds + 1):
            if result.control_signal not in FEEDBACK_SIGNALS:
                break

            logger.info(
                "FeedbackLoop round %d: signal=%s — requesting supplementary info",
                round_no,
                result.control_signal,
            )
            supplement = await self._request_supplement(result)
            if not supplement:
                logger.warning("FeedbackLoop: LLM returned no supplement; stopping")
                break

            # Re-run the pipeline with the supplement folded into the question.
            question = self._compose_question(result, supplement)
            result = await self.orchestrator.run(question)
            result.details["feedback_rounds"] = round_no
            result.details["supplement"] = supplement

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request_supplement(self, result: CoreResult) -> str:
        client = self.orchestrator.llm_client
        prompt = (
            "The reasoning engine produced this weak result:\n"
            f"QUERY: {result.logic_form.query}\n"
            f"CONCLUSION: {result.conclusion}\n"
            f"CONFIDENCE: {result.confidence:.2f}\n"
            f"SIGNAL: {result.control_signal}\n"
            "Please provide supplementary information to help resolve it."
        )
        try:
            return await client.chat(
                prompt,
                system_prompt=FEEDBACK_SYSTEM_PROMPT,
                temperature=0.3,
            )
        except Exception as exc:  # noqa: BLE001 — feedback must not crash pipeline
            logger.warning("FeedbackLoop: LLM supplement failed: %s", exc)
            return ""

    @staticmethod
    def _compose_question(result: CoreResult, supplement: str) -> str:
        base = result.logic_form.query or " ".join(result.logic_form.propositions)
        return f"{base}\n[Supplementary context: {supplement}]"
