"""Tầng 3 - Đánh giá & Lọc Logic (Logic Evaluator & Stream Filter).

Tính điểm tin cậy C_i cho từng luồng tư duy, áp dụng nguyên lý Occam's razor (brevity),
kiểm tra tính nhất quán logic và phát hiện mâu thuẫn giữa các luồng mạnh.
"""

from __future__ import annotations

import cmath

from dataclasses import dataclass, field
from typing import Any, Sequence

from nps_core.filter_funnel.svd_decomposer import ThoughtStream

__all__ = [
    "EvaluatedStream",
    "LogicFilterReport",
    "LogicFilter",
]


@dataclass(frozen=True, slots=True)
class EvaluatedStream:
    """Luồng tư duy đã qua đánh giá điểm tin cậy C_i."""

    stream: ThoughtStream
    consistency_score: float
    brevity_score: float
    confidence_score: float  # C_i = singular_value * consistency * brevity
    status: str  # "ACCEPTED", "MONITORED", "PRUNED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "stream_index": self.stream.stream_index,
            "singular_value": self.stream.singular_value,
            "amplitude_ratio": self.stream.amplitude_ratio,
            "consistency_score": self.consistency_score,
            "brevity_score": self.brevity_score,
            "confidence_score": self.confidence_score,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class LogicFilterReport:
    """Báo cáo đánh giá Tầng 3."""

    evaluated_streams: tuple[EvaluatedStream, ...]
    accepted_streams: tuple[EvaluatedStream, ...]
    monitored_streams: tuple[EvaluatedStream, ...]
    pruned_streams: tuple[EvaluatedStream, ...]
    conflict_detected: bool
    conflict_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_streams": [s.to_dict() for s in self.evaluated_streams],
            "accepted_count": len(self.accepted_streams),
            "monitored_count": len(self.monitored_streams),
            "pruned_count": len(self.pruned_streams),
            "conflict_detected": self.conflict_detected,
            "conflict_summary": self.conflict_summary,
        }


class LogicFilter:
    """Bộ lọc và đánh giá logic các luồng tư duy."""

    @staticmethod
    def calculate_brevity(step_count: int) -> float:
        """Tính điểm độ ngắn gọn b (Occam's razor)."""
        if step_count <= 0:
            return 1.0
        return 1.0 / (1.0 + 0.05 * step_count)

    @classmethod
    def evaluate_stream(
        cls,
        stream: ThoughtStream,
        step_count: int = 1,
        known_conflicts: Sequence[tuple[int, int]] = (),
        tau_accept: float = 0.5,
        tau_warn: float = 0.2,
    ) -> EvaluatedStream:
        """Đánh giá một luồng tư duy và phân loại trạng thái."""
        brevity = cls.calculate_brevity(step_count)

        # Tính consistency dựa trên việc có nằm trong cặp mâu thuẫn hay không
        is_conflicting = any(stream.stream_index in pair for pair in known_conflicts)
        consistency = 0.5 if is_conflicting else 1.0

        confidence = stream.amplitude_ratio * consistency * brevity

        if confidence >= tau_accept:
            status = "ACCEPTED"
        elif confidence >= tau_warn:
            status = "MONITORED"
        else:
            status = "PRUNED"

        return EvaluatedStream(
            stream=stream,
            consistency_score=consistency,
            brevity_score=brevity,
            confidence_score=confidence,
            status=status,
        )

    @classmethod
    def filter_streams(
        cls,
        streams: Sequence[ThoughtStream],
        step_count: int = 1,
        phase_conflict_detected: bool = False,
        tau_accept: float = 0.4,
        tau_warn: float = 0.15,
    ) -> LogicFilterReport:
        """Lọc và đánh giá danh sách các luồng tư duy."""
        evaluated: list[EvaluatedStream] = []
        accepted: list[EvaluatedStream] = []
        monitored: list[EvaluatedStream] = []
        pruned: list[EvaluatedStream] = []

        for s in streams:
            ev = cls.evaluate_stream(
                stream=s,
                step_count=step_count,
                tau_accept=tau_accept,
                tau_warn=tau_warn,
            )
            evaluated.append(ev)
            if ev.status == "ACCEPTED":
                accepted.append(ev)
            elif ev.status == "MONITORED":
                monitored.append(ev)
            else:
                pruned.append(ev)

        # Kiểm tra xung đột giữa các luồng ACCEPTED
        conflict_detected = phase_conflict_detected
        summary = ""

        if len(accepted) >= 2:
            # So sánh góc giữa vector kết luận (state_b) của 2 luồng mạnh nhất
            s1 = accepted[0].stream.state_b
            s2 = accepted[1].stream.state_b
            if len(s1) == len(s2) and len(s1) > 0:
                dot = sum(a.conjugate() * b for a, b in zip(s1, s2))
                norm1 = sum(abs(a) ** 2 for a in s1) ** 0.5
                norm2 = sum(abs(b) ** 2 for b in s2) ** 0.5
                if norm1 > 1e-12 and norm2 > 1e-12:
                    cos_sim = (dot / (norm1 * norm2)).real
                    if cos_sim < -0.5:  # Hướng ngược chiều / mâu thuẫn
                        conflict_detected = True
                        summary = f"Xung đột kết luận giữa Luồng {accepted[0].stream.stream_index} và Luồng {accepted[1].stream.stream_index} (cos_sim={cos_sim:.3f})"

        if phase_conflict_detected and not summary:
            summary = "Phát hiện hiện tượng lệch pha pi giữa các trạng thái cơ sở mạnh."

        return LogicFilterReport(
            evaluated_streams=tuple(evaluated),
            accepted_streams=tuple(accepted),
            monitored_streams=tuple(monitored),
            pruned_streams=tuple(pruned),
            conflict_detected=conflict_detected,
            conflict_summary=summary,
        )
