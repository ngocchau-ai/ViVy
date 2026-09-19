"""DirectiveTaskContract — Schema cho Model-to-Model Directive Protocol.

ViVy V5.0 Sprint 2: Khi EpistemicGate emit DELEGATE_MODEL, ViVy đóng gói
nhiệm vụ thành DirectiveTaskContract và gửi tới ModelRouter để dispatch.

Architecture:
    EpistemicGate(DELEGATE_MODEL)
        → DirectiveTaskContract(task, model, evidence_criteria)
        → ModelRouter.dispatch(contract)
        → Evidence(passes, metrics)

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2A): Initial implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskType(StrEnum):
    """Phân loại nhiệm vụ để ModelRouter chọn model phù hợp."""

    CODING = "CODING"
    MATH = "MATH"
    REASONING = "REASONING"
    GENERAL = "GENERAL"
    ANALYSIS = "ANALYSIS"


class EvidenceStatus(StrEnum):
    """Trạng thái kiểm chứng bằng chứng nghiệm thu."""

    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"
    ESCALATED = "ESCALATED"


@dataclass
class EvidenceCriteria:
    """Tiêu chuẩn bằng chứng nghiệm thu cho một DirectiveTaskContract.

    Parameters
    ----------
    description:
        Mô tả tiêu chuẩn kiểm chứng (e.g. "pytest returns 0 exit code").
    require_test_pass:
        Nếu True, kết quả phải đi kèm pytest pass report.
    require_output_contains:
        Danh sách chuỗi BẮT BUỘC phải xuất hiện trong output.
    require_no_error:
        Nếu True, output không được chứa ERROR/Traceback/exception.
    """

    description: str
    require_test_pass: bool = False
    require_output_contains: list[str] = field(default_factory=list)
    require_no_error: bool = True


@dataclass
class DirectiveTaskContract:
    """Hợp đồng nhiệm vụ ViVy gửi cho model chuyên trách.

    Parameters
    ----------
    task_id:
        ID duy nhất của nhiệm vụ (e.g. "vivy-task-001").
    task_description:
        Mô tả ngôn ngữ tự nhiên của nhiệm vụ.
    task_type:
        Phân loại nhiệm vụ (CODING | MATH | REASONING | GENERAL | ANALYSIS).
    context:
        Ngữ cảnh bổ sung cần thiết để thực thi (code snippet, data, etc.).
    evidence_criteria:
        Tiêu chuẩn bằng chứng nghiệm thu.
    preferred_model:
        Model ưu tiên (e.g. "gemma4eb", "deepseek-coder"). None = auto-select.
    timeout_s:
        Timeout tính bằng giây (mặc định 120s).
    max_retries:
        Số lần retry tối đa trước khi escalate (mặc định 3).
    metadata:
        Metadata tuỳ chọn.
    """

    task_id: str
    task_description: str
    task_type: TaskType
    context: str = ""
    evidence_criteria: EvidenceCriteria = field(
        default_factory=lambda: EvidenceCriteria(description="Output is non-empty")
    )
    preferred_model: str | None = None
    timeout_s: int = 120
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    """Bằng chứng nghiệm thu được trả về bởi ModelRouter sau khi dispatch.

    Parameters
    ----------
    status:
        PASS | FAIL | TIMEOUT | ESCALATED.
    output:
        Raw output từ model/execution.
    passes:
        True nếu status == PASS.
    metrics:
        Metrics bổ sung (time_s, tokens_used, retry_count, etc.).
    error_message:
        Mô tả lỗi nếu status != PASS.
    model_used:
        Tên model thực tế đã được dùng.
    attempt:
        Số lần thử đã thực hiện.
    """

    status: EvidenceStatus
    output: str
    passes: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    model_used: str = ""
    attempt: int = 1

    @classmethod
    def success(cls, output: str, model_used: str = "", attempt: int = 1, **metrics: Any) -> Evidence:
        """Factory: tạo Evidence PASS."""
        return cls(
            status=EvidenceStatus.PASS,
            output=output,
            passes=True,
            model_used=model_used,
            attempt=attempt,
            metrics=dict(metrics),
        )

    @classmethod
    def failure(cls, output: str, error: str, model_used: str = "", attempt: int = 1) -> Evidence:
        """Factory: tạo Evidence FAIL."""
        return cls(
            status=EvidenceStatus.FAIL,
            output=output,
            passes=False,
            error_message=error,
            model_used=model_used,
            attempt=attempt,
        )

    @classmethod
    def timeout(cls, model_used: str = "", attempt: int = 1) -> Evidence:
        """Factory: tạo Evidence TIMEOUT."""
        return cls(
            status=EvidenceStatus.TIMEOUT,
            output="",
            passes=False,
            error_message="Execution timed out",
            model_used=model_used,
            attempt=attempt,
        )

    @classmethod
    def escalated(cls, reason: str) -> Evidence:
        """Factory: tạo Evidence ESCALATED (cần con người can thiệp)."""
        return cls(
            status=EvidenceStatus.ESCALATED,
            output="",
            passes=False,
            error_message=f"Escalated to human: {reason}",
        )
