"""Multi-Model Router — V5.0 Sprint 2B.

ModelRouter dispatches DirectiveTaskContracts tới các Pretrained Domain Models
(Gemma 4EB, DeepSeek Coder, v.v.) thông qua Ollama API.

Architecture (V5.0):
    EpistemicGate(DELEGATE_MODEL)
        → DirectiveTaskContract
        → ModelRouter.dispatch()   ← THIS MODULE
            → select_model()
            → _call_model() via LLMClient
            → verify_evidence()
            → retry/escalate if needed
        → Evidence

Sprint 2 Constraint: Chỉ dùng Gemma 4EB (đã chạy được).
Thêm model thứ 2 sau khi Router ổn định.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2B): Initial implementation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from orchestrator.directive_contract import (
    DirectiveTaskContract,
    Evidence,
    EvidenceCriteria,
    EvidenceStatus,
    TaskType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model Registry (Sprint 2: single model, expand in Sprint 3+)
# ---------------------------------------------------------------------------

# Default model mapping — override via environment or config
_DEFAULT_MODEL_MAP: dict[TaskType, str] = {
    TaskType.CODING: "gemma4eb",       # Sprint 2: Gemma 4EB for all types
    TaskType.MATH: "gemma4eb",
    TaskType.REASONING: "gemma4eb",
    TaskType.GENERAL: "gemma4eb",
    TaskType.ANALYSIS: "gemma4eb",
}


# ---------------------------------------------------------------------------
# Evidence Verifier
# ---------------------------------------------------------------------------


def verify_evidence(output: str, criteria: EvidenceCriteria) -> tuple[bool, str]:
    """Kiểm tra output có đáp ứng EvidenceCriteria không.

    Returns
    -------
    (passes, reason)
        passes: True nếu tất cả criteria đều PASS.
        reason: mô tả lỗi nếu passes=False.
    """
    if not output and criteria.require_output_contains:
        return False, "Output is empty but required_contains is set"

    if criteria.require_no_error:
        error_markers = ["Traceback", "Error:", "ERROR:", "Exception:", "FAILED"]
        for marker in error_markers:
            if marker in output:
                return False, f"Output contains error marker: {marker!r}"

    for required in criteria.require_output_contains:
        if required not in output:
            return False, f"Output does not contain required string: {required!r}"

    return True, ""


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------


class ModelRouter:
    """Dispatches DirectiveTaskContracts to pretrained specialist models.

    Usage::

        from llm_bridge.client import LLMClient
        router = ModelRouter(llm_client)
        contract = DirectiveTaskContract(
            task_id="t001",
            task_description="Explain gradient descent",
            task_type=TaskType.REASONING,
        )
        evidence = asyncio.run(router.dispatch(contract))
        assert evidence.passes
    """

    def __init__(
        self,
        llm_client: Any,
        model_map: dict[TaskType, str] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        llm_client:
            LLMClient instance (OpenAI-compatible).
        model_map:
            Mapping TaskType → model name. Defaults to _DEFAULT_MODEL_MAP.
        """
        self._client = llm_client
        self._model_map = model_map or dict(_DEFAULT_MODEL_MAP)

    def select_model(self, task_type: TaskType, preferred_model: str | None = None) -> str:
        """Chọn model phù hợp nhất cho TaskType.

        preferred_model nếu được đặt sẽ được ưu tiên (sau khi validate).
        """
        if preferred_model:
            return preferred_model
        return self._model_map.get(task_type, "gemma4eb")

    async def dispatch(self, contract: DirectiveTaskContract) -> Evidence:
        """Dispatch contract tới model, retry nếu fail, escalate nếu hết retry.

        Parameters
        ----------
        contract:
            DirectiveTaskContract chứa task + evidence criteria.

        Returns
        -------
        Evidence
            PASS | FAIL | TIMEOUT | ESCALATED
        """
        model = self.select_model(contract.task_type, contract.preferred_model)
        logger.info(
            "ModelRouter.dispatch: task=%s type=%s model=%s timeout=%ds",
            contract.task_id,
            contract.task_type,
            model,
            contract.timeout_s,
        )

        last_evidence: Evidence = Evidence.failure("", "No attempts made", model_used=model)

        for attempt in range(1, contract.max_retries + 1):
            logger.info("ModelRouter.dispatch: attempt %d/%d", attempt, contract.max_retries)
            evidence = await self._attempt(contract, model, attempt)

            if evidence.status == EvidenceStatus.TIMEOUT:
                logger.warning("ModelRouter: timeout on attempt %d", attempt)
                last_evidence = evidence
                # Timeout is likely permanent — escalate immediately
                break

            if evidence.passes:
                logger.info("ModelRouter: PASS on attempt %d", attempt)
                return evidence

            logger.warning(
                "ModelRouter: FAIL on attempt %d — %s",
                attempt,
                evidence.error_message,
            )
            last_evidence = evidence

            if attempt < contract.max_retries:
                # Brief backoff between retries
                await asyncio.sleep(1.0)

        # All retries exhausted or timeout
        logger.error(
            "ModelRouter: all %d attempts failed — escalating task=%s",
            contract.max_retries,
            contract.task_id,
        )
        return Evidence.escalated(
            f"All {contract.max_retries} attempts failed. Last error: {last_evidence.error_message}"
        )

    async def _attempt(
        self,
        contract: DirectiveTaskContract,
        model: str,
        attempt: int,
    ) -> Evidence:
        """Single attempt to call model and verify evidence."""
        prompt = self._build_prompt(contract)

        try:
            start = time.monotonic()
            output: str = await asyncio.wait_for(
                self._client.chat(prompt, model=model),
                timeout=float(contract.timeout_s),
            )
            elapsed = time.monotonic() - start

            passes, reason = verify_evidence(output, contract.evidence_criteria)

            if passes:
                return Evidence.success(
                    output=output,
                    model_used=model,
                    attempt=attempt,
                    time_s=round(elapsed, 2),
                )
            else:
                return Evidence.failure(
                    output=output,
                    error=reason,
                    model_used=model,
                    attempt=attempt,
                )

        except TimeoutError:
            return Evidence.timeout(model_used=model, attempt=attempt)
        except Exception as exc:  # noqa: BLE001
            return Evidence.failure(
                output="",
                error=f"Exception: {exc}",
                model_used=model,
                attempt=attempt,
            )

    def _build_prompt(self, contract: DirectiveTaskContract) -> str:
        """Build prompt từ DirectiveTaskContract."""
        parts = [
            f"[DIRECTIVE CONTRACT — {contract.task_type}]",
            f"Task ID: {contract.task_id}",
            f"Task: {contract.task_description}",
        ]
        if contract.context:
            parts.append(f"\nContext:\n{contract.context}")
        if contract.evidence_criteria.description:
            parts.append(f"\nSuccess Criteria: {contract.evidence_criteria.description}")
        return "\n".join(parts)
