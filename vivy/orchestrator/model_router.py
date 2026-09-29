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

from integration.activity_log import ActivityLog
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

import os  # noqa: E402


def _model_matches(requested: str, available: str) -> bool:
    """Match an API alias against a model id or GGUF path."""
    requested = requested.lower()
    available = available.lower().replace("\\", "/")
    name = available.rsplit("/", 1)[-1]
    base_requested = requested.split(":")[0]

    return (
        requested == available
        or requested in name
        or base_requested in name
        or (requested == "gemma4-e4b" and "gemma" in name and "e4b" in name)
        or ("qwen" in requested and "coder" in requested and "qwen" in name and "coder" in name)
    )

# Default model mapping — override via environment or config
# [REROUTED 26/09/2026] CODING/MATH từng default `"qwen2.5-coder:7b"` — gguf đó
# không bao giờ tồn tại trên đĩa (xem model_manifest.json
# task_archetype_mapping_note_2026-09-26). Chỉ có 2 model thật: gemma4-e4b
# (text/code) + qwen2-vl-72b (vision). Specialist riêng vẫn nhận qua
# `VIVY_CODER_URL` / `specialist_client` (xem _get_client_for_task).
_DEFAULT_MODEL_MAP: dict[TaskType, str] = {
    TaskType.CODING: os.environ.get("VIVY_CODER_MODEL", "gemma4-e4b"),
    TaskType.MATH: os.environ.get("VIVY_CODER_MODEL", "gemma4-e4b"),
    TaskType.REASONING: os.environ.get("VIVY_MODEL", "gemma4-e4b"),
    TaskType.GENERAL: os.environ.get("VIVY_MODEL", "gemma4-e4b"),
    TaskType.ANALYSIS: os.environ.get("VIVY_MODEL", "gemma4-e4b"),
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
        specialist_client: Any | None = None,
    ) -> None:
        """
        Parameters
        ----------
        llm_client:
            LLMClient instance (OpenAI-compatible) cho primary reasoner (Gemma).
        model_map:
            Mapping TaskType → model name. Defaults to _DEFAULT_MODEL_MAP.
        specialist_client:
            LLMClient instance riêng cho domain specialist (ví dụ Qwen Coder trên port 8081).
        """
        self._client = llm_client
        self._specialist_client = specialist_client
        if self._specialist_client is None:
            coder_url = os.environ.get("VIVY_CODER_URL")
            if coder_url:
                try:
                    from llm_bridge.client import LLMClient
                    self._specialist_client = LLMClient(base_url=coder_url)
                    logger.info("ModelRouter: Auto-wired specialist client from VIVY_CODER_URL=%s", coder_url)
                except Exception as e:
                    logger.debug("ModelRouter: Failed to auto-init specialist LLMClient: %s", e)

        self._model_map = model_map or dict(_DEFAULT_MODEL_MAP)
        self._activity = ActivityLog()

    def _get_client_for_task(self, task_type: TaskType) -> Any:
        """Lấy client tương ứng cho task (specialist nếu là CODING/MATH và có specialist_client)."""
        if task_type in (TaskType.CODING, TaskType.MATH) and self._specialist_client is not None:
            return self._specialist_client
        return self._client

    def select_model(self, task_type: TaskType, preferred_model: str | None = None) -> str:
        """Chọn model phù hợp nhất cho TaskType.

        preferred_model nếu được đặt sẽ được ưu tiên (sau khi validate).
        """
        if preferred_model:
            return preferred_model
        return self._model_map.get(task_type, os.environ.get("VIVY_MODEL", "gemma4-e4b"))

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
        consent = contract.metadata.get("vivy_consent_id", "")
        decision = contract.metadata.get("vivy_decision", "")
        expected_evidence = contract.metadata.get("expected_evidence", "")
        if not consent or decision != "DELEGATE_MODEL" or not expected_evidence:
            reason = "Missing ViVy consent, DELEGATE_MODEL decision, or expected evidence"
            self._activity.record("model_route_blocked", session_id=contract.task_id,
                                  task_type=contract.task_type.value,
                                  status="BLOCKED", reason=reason,
                                  has_consent=bool(consent), decision=decision,
                                  has_expected_evidence=bool(expected_evidence))
            return Evidence.escalated(reason)

        model = self.select_model(contract.task_type, contract.preferred_model)
        logger.info(
            "ModelRouter.dispatch: task=%s type=%s model=%s timeout=%ds",
            contract.task_id,
            contract.task_type,
            model,
            contract.timeout_s,
        )
        self._activity.record("model_route", session_id=contract.task_id,
                              task_type=contract.task_type.value, model=model,
                              preferred_model=contract.preferred_model or "")

        client = self._get_client_for_task(contract.task_type)
        list_models = getattr(client, "list_models", None)
        if callable(list_models):
            try:
                available = await list_models()
            except Exception as exc:  # noqa: BLE001
                self._activity.record("model_availability", session_id=contract.task_id,
                                      model=model, status="UNVERIFIED", error=str(exc))
            else:
                matched = next((item for item in available if _model_matches(model, item)), None)
                if matched is None:
                    reason = f"Model {model!r} is unavailable on the configured backend"
                    self._activity.record("model_availability", session_id=contract.task_id,
                                          model=model, status="UNAVAILABLE",
                                          available_models=available)
                    return Evidence.escalated(reason)
                self._activity.record("model_availability", session_id=contract.task_id,
                                      model=model, status="AVAILABLE", backend_model=matched)

        last_evidence: Evidence = Evidence.failure("", "No attempts made", model_used=model)

        for attempt in range(1, contract.max_retries + 1):
            logger.info("ModelRouter.dispatch: attempt %d/%d", attempt, contract.max_retries)
            evidence = await self._attempt(contract, model, attempt)
            self._activity.record("model_attempt", session_id=contract.task_id,
                                  task_type=contract.task_type.value, model=model,
                                  attempt=attempt, status=evidence.status.value,
                                  passes=evidence.passes)

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
            client = self._get_client_for_task(contract.task_type)
            output: str = await asyncio.wait_for(
                client.chat(prompt, model=model),
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
