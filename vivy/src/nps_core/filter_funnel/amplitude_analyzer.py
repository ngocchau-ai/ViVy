"""Tầng 1 - Phân tích Biên độ & Pha (Amplitude & Phase Analyzer).

Phân tích không gian trạng thái phức, tính phân bố xác suất, entropy suy nghĩ,
và phát hiện hiện tượng giao thoa triệt tiêu / lệch pha pi.
Standard-library design (with complex math support).
"""

from __future__ import annotations

import cmath
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "BasisStateAnalysis",
    "AmplitudeAnalysisReport",
    "AmplitudeAnalyzer",
]


@dataclass(frozen=True, slots=True)
class BasisStateAnalysis:
    """Thông tin phân tích của một trạng thái cơ sở."""

    index: int
    complex_amplitude: complex
    probability: float
    magnitude: float
    phase: float  # Radians [-pi, pi]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "complex_amplitude": str(self.complex_amplitude),
            "probability": self.probability,
            "magnitude": self.magnitude,
            "phase": self.phase,
        }


@dataclass(frozen=True, slots=True)
class AmplitudeAnalysisReport:
    """Báo cáo phân tích Tầng 1 thu được từ vector trạng thái."""

    probabilities: tuple[float, ...]
    entropy: float
    top_k_states: tuple[BasisStateAnalysis, ...]
    phase_conflict_detected: bool
    destructive_pairs: tuple[tuple[int, int], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "probabilities": list(self.probabilities),
            "entropy": self.entropy,
            "top_k_states": [s.to_dict() for s in self.top_k_states],
            "phase_conflict_detected": self.phase_conflict_detected,
            "destructive_pairs": list(self.destructive_pairs),
        }


class AmplitudeAnalyzer:
    """Bộ phân tích biên độ và pha trạng thái lượng trị/phức."""

    @staticmethod
    def normalize_vector(state: Sequence[complex | float]) -> tuple[complex, ...]:
        """Chuẩn hóa vector trạng thái về norm = 1."""
        norm_sq = sum(abs(c) ** 2 for c in state)
        if norm_sq < 1e-15:
            n = len(state)
            if n == 0:
                return ()
            val = complex(1.0 / math.sqrt(n), 0.0)
            return tuple(val for _ in state)

        norm = math.sqrt(norm_sq)
        return tuple(complex(c) / norm for c in state)

    @staticmethod
    def calculate_entropy(probabilities: Sequence[float]) -> float:
        """Tính entropy Shannon của phân bố xác suất."""
        entropy = 0.0
        for p in probabilities:
            if p > 1e-12:
                entropy -= p * math.log2(p)
        return max(0.0, entropy)

    @classmethod
    def analyze(
        cls,
        state_vector: Sequence[complex | float],
        top_k: int = 5,
        phase_conflict_threshold: float = 0.85 * math.pi,
    ) -> AmplitudeAnalysisReport:
        """Phân tích vector trạng thái, tính entropy và phát hiện giao thoa lệch pha pi."""
        if not state_vector:
            return AmplitudeAnalysisReport(
                probabilities=(),
                entropy=0.0,
                top_k_states=(),
                phase_conflict_detected=False,
                destructive_pairs=(),
            )

        norm_state = cls.normalize_vector(state_vector)
        probs = tuple(abs(c) ** 2 for c in norm_state)
        entropy = cls.calculate_entropy(probs)

        analyzed_states: list[BasisStateAnalysis] = []
        for idx, c in enumerate(norm_state):
            mag = abs(c)
            prob = mag**2
            phase = cmath.phase(c)
            analyzed_states.append(
                BasisStateAnalysis(
                    index=idx,
                    complex_amplitude=c,
                    probability=prob,
                    magnitude=mag,
                    phase=phase,
                )
            )

        # Sắp xếp theo xác suất giảm dần
        sorted_states = sorted(analyzed_states, key=lambda s: s.probability, reverse=True)
        k_val = min(top_k, len(sorted_states))
        top_k_list = tuple(sorted_states[:k_val])

        # Kiểm tra pha triệt tiêu (lệch pha xấp xỉ pi) giữa các trạng thái mạnh nhất
        destructive_pairs: list[tuple[int, int]] = []
        phase_conflict = False

        strong_states = [s for s in top_k_list if s.probability > 0.05]
        for i in range(len(strong_states)):
            for j in range(i + 1, len(strong_states)):
                s1 = strong_states[i]
                s2 = strong_states[j]
                diff = abs(s1.phase - s2.phase)
                # Đưa diff về dải [0, pi]
                if diff > math.pi:
                    diff = 2 * math.pi - diff

                if diff >= phase_conflict_threshold:
                    phase_conflict = True
                    destructive_pairs.append((s1.index, s2.index))

        return AmplitudeAnalysisReport(
            probabilities=probs,
            entropy=entropy,
            top_k_states=top_k_list,
            phase_conflict_detected=phase_conflict,
            destructive_pairs=tuple(destructive_pairs),
        )
