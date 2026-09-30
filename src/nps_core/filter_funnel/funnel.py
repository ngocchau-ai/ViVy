"""Tầng 4 & Orchestrator - Phễu lọc Tự kiểm chứng (Self-Verification Filter Funnel).

Điều phối 4 tầng phân tích biên độ/pha, SVD tách luồng, đánh giá logic và
phát tín hiệu điều khiển nhận thức (CONTINUE, HALT, BACKTRACK, DELEGATE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from nps_core.filter_funnel.amplitude_analyzer import AmplitudeAnalysisReport, AmplitudeAnalyzer
from nps_core.filter_funnel.logic_filter import LogicFilter, LogicFilterReport
from nps_core.filter_funnel.svd_decomposer import SVDDecomposer, ThoughtStream

__all__ = [
    "FunnelSignal",
    "ExtractedThoughtPattern",
    "FunnelResult",
    "FilterFunnel",
]


class FunnelSignal(str, Enum):
    """Tín hiệu điều khiển sinh ra từ Phễu lọc."""

    CONTINUE_EVOLUTION = "CONTINUE_EVOLUTION"  # Tiếp tục tiến hóa
    MEASURE_AND_HALT = "MEASURE_AND_HALT"      # Suy nghĩ đã hội tụ -> Trả kết quả
    BACKTRACK = "BACKTRACK"                      # Tất cả luồng đều yếu -> Quay lui
    DELEGATE_EXTERNAL = "DELEGATE_EXTERNAL"      # Phát hiện xung đột -> Ủy thác chuyên môn


@dataclass(frozen=True, slots=True)
class ExtractedThoughtPattern:
    """Mẫu suy luận thành công được trích xuất để nạp vào Memory Tương quan."""

    input_vector: tuple[complex, ...]
    output_vector: tuple[complex, ...]
    confidence: float
    entropy: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_vector": [str(c) for c in self.input_vector],
            "output_vector": [str(c) for c in self.output_vector],
            "confidence": self.confidence,
            "entropy": self.entropy,
        }


@dataclass(frozen=True, slots=True)
class FunnelResult:
    """Kết quả tổng hợp từ Phễu lọc Tự kiểm chứng."""

    signal: FunnelSignal
    overall_confidence: float
    entropy: float
    amplitude_report: AmplitudeAnalysisReport
    filter_report: LogicFilterReport
    extracted_pattern: ExtractedThoughtPattern | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal.value,
            "overall_confidence": self.overall_confidence,
            "entropy": self.entropy,
            "amplitude_report": self.amplitude_report.to_dict(),
            "filter_report": self.filter_report.to_dict(),
            "extracted_pattern": self.extracted_pattern.to_dict() if self.extracted_pattern else None,
        }


class FilterFunnel:
    """Bộ Phễu lọc Tự kiểm chứng (Self-Verification Filter Funnel)."""

    def __init__(
        self,
        entropy_halt_threshold: float = 0.5,
        confidence_halt_threshold: float = 0.7,
        svd_stream_threshold: float = 0.05,
    ) -> None:
        self.entropy_halt_threshold = entropy_halt_threshold
        self.confidence_halt_threshold = confidence_halt_threshold
        self.svd_stream_threshold = svd_stream_threshold

    def evaluate_state(
        self,
        state_vector: Sequence[complex | float],
        partition: tuple[int, int] = (2, 2),
        step_count: int = 1,
    ) -> FunnelResult:
        """Thực thi pipeline 4 tầng trên vector trạng thái."""
        if not state_vector:
            empty_amp = AmplitudeAnalyzer.analyze([])
            empty_logic = LogicFilter.filter_streams([])
            return FunnelResult(
                signal=FunnelSignal.BACKTRACK,
                overall_confidence=0.0,
                entropy=0.0,
                amplitude_report=empty_amp,
                filter_report=empty_logic,
            )

        # Tầng 1: Phân tích Biên độ & Pha
        amp_report = AmplitudeAnalyzer.analyze(state_vector)

        # Tầng 2: Tách luồng bằng SVD
        streams = SVDDecomposer.decompose(
            state_vector=state_vector,
            partition=partition,
            threshold=self.svd_stream_threshold,
        )

        # Tầng 3: Đánh giá & Lọc Logic
        filter_report = LogicFilter.filter_streams(
            streams=streams,
            step_count=step_count,
            phase_conflict_detected=amp_report.phase_conflict_detected,
        )

        # Tầng 4: Sinh tín hiệu điều khiển & Trích xuất pattern
        accepted = filter_report.accepted_streams
        overall_confidence = max((s.confidence_score for s in accepted), default=0.0)

        extracted_pattern: ExtractedThoughtPattern | None = None

        if filter_report.conflict_detected:
            signal = FunnelSignal.DELEGATE_EXTERNAL
        elif len(accepted) == 0 and len(filter_report.monitored_streams) == 0:
            signal = FunnelSignal.BACKTRACK
        elif (
            amp_report.entropy <= self.entropy_halt_threshold
            and overall_confidence >= self.confidence_halt_threshold
        ):
            signal = FunnelSignal.MEASURE_AND_HALT
            if accepted:
                best_stream = accepted[0].stream
                extracted_pattern = ExtractedThoughtPattern(
                    input_vector=best_stream.state_a,
                    output_vector=best_stream.state_b,
                    confidence=overall_confidence,
                    entropy=amp_report.entropy,
                )
        else:
            signal = FunnelSignal.CONTINUE_EVOLUTION

        return FunnelResult(
            signal=signal,
            overall_confidence=overall_confidence,
            entropy=amp_report.entropy,
            amplitude_report=amp_report,
            filter_report=filter_report,
            extracted_pattern=extracted_pattern,
        )
