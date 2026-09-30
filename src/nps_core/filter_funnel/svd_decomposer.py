"""Tầng 2 - Tách luồng tư duy bằng SVD (SVD Stream Decomposer).

Thực hiện ma trận hóa (matricization) tensor trạng thái theo phân hoạch (nA, nB)
và thực hiện SVD để tách các luồng tư duy độc lập.
Standard-library implementation with pure Python SVD algorithm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

__all__ = [
    "ThoughtStream",
    "SVDDecomposer",
]


@dataclass(frozen=True, slots=True)
class ThoughtStream:
    """Đại diện cho một luồng tư duy độc lập trích xuất từ SVD."""

    stream_index: int
    singular_value: float
    amplitude_ratio: float
    state_a: tuple[complex, ...]  # Vector trạng thái con đại diện cho Tiền đề (nA)
    state_b: tuple[complex, ...]  # Vector trạng thái con đại diện cho Kết luận (nB)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stream_index": self.stream_index,
            "singular_value": self.singular_value,
            "amplitude_ratio": self.amplitude_ratio,
            "state_a": [str(c) for c in self.state_a],
            "state_b": [str(c) for c in self.state_b],
        }


class SVDDecomposer:
    """Bộ thực thi SVD và tách luồng tư duy từ ma trận trạng thái."""

    @staticmethod
    def _matrix_multiply_complex(
        a: list[list[complex]], b: list[list[complex]]
    ) -> list[list[complex]]:
        rows_a = len(a)
        cols_a = len(a[0]) if rows_a > 0 else 0
        cols_b = len(b[0]) if len(b) > 0 else 0

        res = [[complex(0, 0) for _ in range(cols_b)] for _ in range(rows_a)]
        for i in range(rows_a):
            for k in range(cols_a):
                if abs(a[i][k]) < 1e-15:
                    continue
                for j in range(cols_b):
                    res[i][j] += a[i][k] * b[k][j]
        return res

    @staticmethod
    def compute_svd_pure_python(
        matrix: list[list[complex]], max_iters: int = 50
    ) -> tuple[list[list[complex]], list[float], list[list[complex]]]:
        """Tính SVD của ma trận M = U S V^H bằng thuật toán Jacobi một phía (One-sided Jacobi).

        Trả về (U, S, Vh).
        """
        rows = len(matrix)
        cols = len(matrix[0]) if rows > 0 else 0

        if rows == 0 or cols == 0:
            return [], [], []

        # Khởi tạo V = Identity(cols x cols)
        v = [[complex(1 if i == j else 0, 0) for j in range(cols)] for i in range(cols)]
        # Tạo bản sao của M (rows x cols) làm ma trận A
        a = [[matrix[i][j] for j in range(cols)] for i in range(rows)]

        # Triển khai Hestenes/Jacobi one-sided
        for _ in range(max_iters):
            converged = True
            for i in range(cols):
                for j in range(i + 1, cols):
                    # Tính tích trong cột i và cột j
                    alpha = sum(a[k][i].conjugate() * a[k][i] for k in range(rows)).real
                    beta = sum(a[k][j].conjugate() * a[k][j] for k in range(rows)).real
                    gamma = sum(a[k][i].conjugate() * a[k][j] for k in range(rows))

                    if abs(gamma) > 1e-12:
                        converged = False
                        # Jacobi rotation angle
                        tau = (beta - alpha) / (2 * abs(gamma))
                        if tau >= 0:
                            t = 1.0 / (tau + math.sqrt(1.0 + tau * tau))
                        else:
                            t = -1.0 / (-tau + math.sqrt(1.0 + tau * tau))

                        c = 1.0 / math.sqrt(1.0 + t * t)
                        s = t * c
                        phase = gamma / abs(gamma) if abs(gamma) > 1e-15 else 1.0
                        s_phase = s * phase

                        # Xoay cột i và j trong A
                        for k in range(rows):
                            a_ik = a[k][i]
                            a_jk = a[k][j]
                            a[k][i] = c * a_ik - s_phase.conjugate() * a_jk
                            a[k][j] = s_phase * a_ik + c * a_jk

                        # Xoay cột i và j trong V
                        for k in range(cols):
                            v_ik = v[k][i]
                            v_jk = v[k][j]
                            v[k][i] = c * v_ik - s_phase.conjugate() * v_jk
                            v[k][j] = s_phase * v_ik + c * v_jk

            if converged:
                break

        # S là norm của các cột trong A
        singular_values: list[float] = []
        u: list[list[complex]] = [[complex(0, 0) for _ in range(cols)] for _ in range(rows)]

        for j in range(cols):
            col_norm = math.sqrt(sum(abs(a[k][j]) ** 2 for k in range(rows)))
            singular_values.append(col_norm)
            if col_norm > 1e-12:
                for k in range(rows):
                    u[k][j] = a[k][j] / col_norm
            else:
                for k in range(rows):
                    u[k][j] = complex(0, 0)

        # Chuyển V thành V^H (Hermitian transpose)
        vh = [[v[j][i].conjugate() for j in range(cols)] for i in range(cols)]

        # Sắp xếp singular values giảm dần
        indexed = sorted(enumerate(singular_values), key=lambda x: x[1], reverse=True)
        sorted_s = [x[1] for x in indexed]
        sorted_u = [[u[r][idx] for idx, _ in indexed] for r in range(rows)]
        sorted_vh = [[vh[idx][c] for c in range(cols)] for idx, _ in indexed]

        return sorted_u, sorted_s, sorted_vh

    @classmethod
    def decompose(
        cls,
        state_vector: Sequence[complex | float],
        partition: tuple[int, int],
        threshold: float = 0.05,
    ) -> tuple[ThoughtStream, ...]:
        """Ma trận hóa state_vector thành 2^(nA) x 2^(nB) và tách luồng tư duy theo SVD."""
        n_a, n_b = partition
        rows = 1 << n_a  # 2^nA
        cols = 1 << n_b  # 2^nB

        expected_dim = rows * cols
        if len(state_vector) != expected_dim:
            # Nếu kích thước không khớp chính xác, tự điều chỉnh gần đúng
            if len(state_vector) == 0:
                return ()
            total = len(state_vector)
            rows = max(1, int(math.isqrt(total)))
            cols = max(1, total // rows)
            expected_dim = rows * cols

        matrix = [[complex(0, 0) for _ in range(cols)] for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx < len(state_vector):
                    matrix[r][c] = complex(state_vector[idx])

        u, s, vh = cls.compute_svd_pure_python(matrix)

        total_norm = math.sqrt(sum(val**2 for val in s))
        if total_norm < 1e-15:
            total_norm = 1.0

        streams: list[ThoughtStream] = []
        for i, val in enumerate(s):
            ratio = val / total_norm
            if ratio >= threshold or (i == 0 and len(s) > 0):
                # Vector U[:, i] (trạng thái con A)
                u_col = tuple(u[r][i] for r in range(len(u)))
                # Vector Vh[i, :] (trạng thái con B)
                v_row = tuple(vh[i][c] for c in range(len(vh[0])))

                streams.append(
                    ThoughtStream(
                        stream_index=i,
                        singular_value=val,
                        amplitude_ratio=ratio,
                        state_a=u_col,
                        state_b=v_row,
                    )
                )

        return tuple(streams)
