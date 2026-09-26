"""Tầng Memory Tương quan (Quantum-Inspired Associative Memory).

Lưu trữ và truy xuất các mẫu suy luận thành công theo nguyên lý Hopfield lượng tử
trên biên độ phức với ma trận trọng số Hebbian và phân cực SVD để unita hóa.
Standard-library design.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from nps_core.filter_funnel.svd_decomposer import SVDDecomposer

__all__ = [
    "PatternMatchResult",
    "QuantumAssociativeMemory",
]


@dataclass(frozen=True, slots=True)
class PatternMatchResult:
    """Kết quả truy vấn mẫu suy luận từ Associative Memory."""

    suggested_output: tuple[complex, ...]
    confidence: float  # Cosine similarity hoặc inner product norm
    matched_pattern_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggested_output": [str(c) for c in self.suggested_output],
            "confidence": self.confidence,
            "matched_pattern_index": self.matched_pattern_index,
        }


class QuantumAssociativeMemory:
    """Mạng Hopfield lượng trị / Bộ nhớ liên kết Unita (Quantum-Inspired Associative Memory)."""

    def __init__(self, dim_input: int, dim_output: int, use_unitary: bool = True) -> None:
        self.dim_input = dim_input
        self.dim_output = dim_output
        self.use_unitary = use_unitary

        # Ma trận trọng số W kích thước (dim_output x dim_input)
        self._w: list[list[complex]] = [
            [complex(0, 0) for _ in range(dim_input)] for _ in range(dim_output)
        ]
        self._pattern_count: int = 0
        self._stored_inputs: list[tuple[complex, ...]] = []
        self._stored_outputs: list[tuple[complex, ...]] = []

    @property
    def pattern_count(self) -> int:
        return self._pattern_count

    @staticmethod
    def _normalize(vec: Sequence[complex | float]) -> tuple[complex, ...]:
        norm_sq = sum(abs(c) ** 2 for c in vec)
        if norm_sq < 1e-15:
            return tuple(complex(0, 0) for _ in vec)
        norm = math.sqrt(norm_sq)
        return tuple(complex(c) / norm for c in vec)

    def store(
        self,
        input_vec: Sequence[complex | float],
        output_vec: Sequence[complex | float],
        learning_rate: float = 0.1,
    ) -> None:
        """Thêm cặp mẫu (|x_p>, |y_p>) vào bộ nhớ qua quy tắc Hebbian: W += eta * |y><x|."""
        x_norm = self._normalize(input_vec)
        y_norm = self._normalize(output_vec)

        if len(x_norm) != self.dim_input or len(y_norm) != self.dim_output:
            raise ValueError(
                f"Kích thước vector không khớp! Input: {len(x_norm)} (cần {self.dim_input}), "
                f"Output: {len(y_norm)} (cần {self.dim_output})"
            )

        # Cập nhật W += eta * y * x^H
        for i in range(self.dim_output):
            for j in range(self.dim_input):
                self._w[i][j] += learning_rate * y_norm[i] * x_norm[j].conjugate()

        self._pattern_count += 1
        self._stored_inputs.append(x_norm)
        self._stored_outputs.append(y_norm)

        if self.use_unitary and self.dim_input == self.dim_output:
            self._unitarize_weight_matrix()

    def _unitarize_weight_matrix(self) -> None:
        """Đưa ma trận trọng số W về unita thông qua phép phân cực SVD: U_unitary = U * V^H."""
        u, s, vh = SVDDecomposer.compute_svd_pure_python(self._w)
        if not u or not vh:
            return

        # U_unitary = U @ Vh
        rows = len(u)
        cols = len(vh[0]) if len(vh) > 0 else 0
        u_unitary = [[complex(0, 0) for _ in range(cols)] for _ in range(rows)]

        for i in range(rows):
            for k in range(len(s)):
                for j in range(cols):
                    u_unitary[i][j] += u[i][k] * vh[k][j]

        self._w = u_unitary

    def query(self, query_input: Sequence[complex | float]) -> PatternMatchResult:
        """Truy vấn bộ nhớ với vector đầu vào |x_query>. Trả về |y_suggest> và độ tin cậy."""
        x_norm = self._normalize(query_input)
        if len(x_norm) != self.dim_input:
            raise ValueError(f"Dim input {len(x_norm)} không khớp {self.dim_input}")

        if self._pattern_count == 0:
            default_y = tuple(complex(1.0 / math.sqrt(self.dim_output), 0) for _ in range(self.dim_output))
            return PatternMatchResult(suggested_output=default_y, confidence=0.0)

        # Tính y_tilde = W @ x_norm
        y_tilde = [complex(0, 0) for _ in range(self.dim_output)]
        for i in range(self.dim_output):
            for j in range(self.dim_input):
                y_tilde[i] += self._w[i][j] * x_norm[j]

        # Tìm mẫu khớp nhất theo Cosine Similarity với các input đã lưu
        best_match_idx: int | None = None
        max_cos_sim = -1.0

        for idx, stored_x in enumerate(self._stored_inputs):
            # Inner product <stored_x | x_norm>
            dot = sum(a.conjugate() * b for a, b in zip(stored_x, x_norm, strict=False))
            cos_sim = abs(dot)
            if cos_sim > max_cos_sim:
                max_cos_sim = cos_sim
                best_match_idx = idx

        norm_y = math.sqrt(sum(abs(c) ** 2 for c in y_tilde))
        if norm_y > 1e-12:
            suggested = tuple(c / norm_y for c in y_tilde)
        else:
            if best_match_idx is not None:
                suggested = self._stored_outputs[best_match_idx]
            else:
                suggested = tuple(complex(1.0 / math.sqrt(self.dim_output), 0) for _ in range(self.dim_output))

        confidence = max(0.0, min(1.0, max_cos_sim))

        return PatternMatchResult(
            suggested_output=suggested,
            confidence=confidence,
            matched_pattern_index=best_match_idx,
        )
