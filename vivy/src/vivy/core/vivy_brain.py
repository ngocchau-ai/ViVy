"""
ViVy Quantum Core Brain.

This module implements the core neural reasoning engine of ViVy, completely from scratch.
It strictly adheres to the NPS Core Architecture and 4-Level Self-Verification Filter Funnel.
"""

from typing import Any

import numpy as np
from scipy.linalg import svd

from .associative_memory import QuantumAssociativeMemory


class FilterFunnelSignal:
    CONTINUE = "CONTINUE_EVOLUTION"
    HALT = "MEASURE_AND_HALT"
    BACKTRACK = "BACKTRACK"
    DELEGATE = "DELEGATE_EXTERNAL"

class ViVyQuantumCore:
    """
    N-Thought Population Reasoning Engine with 4-Level Self-Verification Filter Funnel.
    Replaces Llama-based external reasoning with a fully autonomous Quantum-inspired state-space core.
    """

    def __init__(self, state_dim: int = 1024, memory_use_unitary: bool = True):
        self.state_dim = state_dim
        self.memory = QuantumAssociativeMemory(dim=state_dim, use_unitary=memory_use_unitary)
        self.active_state_vector: np.ndarray | None = None
        self.thought_history: list[np.ndarray] = []

    def _level_1_amplitude_phase_analyzer(self, state_vector: np.ndarray) -> dict[str, Any]:
        """
        Level 1: Kính hiển vi trạng thái.
        - Tính phân bố xác suất |c_k|^2
        - Đo entropy S = -sum p_k * log(p_k)
        - Đánh giá giao thoa triệt tiêu (lệch pha pi)
        """
        # Calculate probabilities
        probs = np.abs(state_vector)**2
        # Normalize just in case
        norm_sum = np.sum(probs)
        if norm_sum > 0:
            probs = probs / norm_sum

        # Shannon Entropy
        entropy = -np.sum(probs * np.log2(probs + 1e-12))

        # Phase interference check (detecting opposing phases on high amplitudes)
        # We look at top K amplitudes
        top_k_indices = np.argsort(probs)[-5:]
        phases = np.angle(state_vector[top_k_indices])

        destructive_interference = False
        for i in range(len(phases)):
            for j in range(i + 1, len(phases)):
                phase_diff = np.abs(phases[i] - phases[j])
                # If phase difference is close to pi (~3.14)
                if np.isclose(phase_diff, np.pi, atol=0.2):
                    destructive_interference = True
                    break

        return {
            "entropy": entropy,
            "destructive_interference": destructive_interference,
            "top_probs": probs[top_k_indices].tolist()
        }

    def _level_2_svd_stream_decomposer(self, state_vector: np.ndarray) -> list[dict[str, Any]]:
        """
        Level 2: Phổ kế suy nghĩ (SVD on Matricization).
        Tách không gian thành Tiền đề (Premise) và Kết luận (Conclusion).
        """
        # Reshape into a 2D matrix (assume equal split for simplicity)
        side_len = int(np.sqrt(self.state_dim))
        if side_len * side_len != self.state_dim:
            # Fallback reshape if not perfect square
            M = state_vector.reshape(2, self.state_dim // 2)
        else:
            M = state_vector.reshape(side_len, side_len)

        U, S, Vh = svd(M, full_matrices=False)
        total_norm = np.linalg.norm(S)

        streams = []
        threshold = 0.05
        for i, val in enumerate(S):
            ratio = val / (total_norm + 1e-12)
            if ratio > threshold:
                streams.append({
                    "singular_value": val,
                    "amplitude_ratio": ratio,
                    "premise_vector": U[:, i],
                    "conclusion_vector": Vh[i, :]
                })
        return streams

    def _level_3_evaluator_logic_filter(self, streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Level 3: Logic lọc.
        C_i = sigma_i * consistency * brevity
        """
        evaluated_streams = []
        for _i, stream in enumerate(streams):
            # Mock consistency (e.g. check against DB) and brevity for now
            consistency = 0.9
            brevity = 0.95

            c_score = stream["singular_value"] * consistency * brevity
            stream["confidence_score"] = c_score
            stream["status"] = "ACCEPTED" if c_score > 0.1 else "MONITORED"
            evaluated_streams.append(stream)

        return evaluated_streams

    def _level_4_metacognitive_trigger(self, l1_res: dict[str, Any], l3_streams: list[dict[str, Any]]) -> str:
        """
        Level 4: Sinh tín hiệu điều khiển & ghi nhớ.
        """
        if l1_res["destructive_interference"]:
            return FilterFunnelSignal.DELEGATE

        if l1_res["entropy"] < 1.0 and len(l3_streams) == 1:
            return FilterFunnelSignal.HALT

        if l1_res["entropy"] > 3.0 or len(l3_streams) == 0:
            return FilterFunnelSignal.BACKTRACK

        return FilterFunnelSignal.CONTINUE

    def process_state(self, state_vector: np.ndarray) -> dict[str, Any]:
        """
        Chạy toàn bộ Phễu lọc tự kiểm chứng trên một vector trạng thái.
        """
        assert len(state_vector) == self.state_dim, "Kích thước vector không khớp"
        self.active_state_vector = state_vector
        self.thought_history.append(state_vector)

        # Pass through the 4-level funnel
        l1 = self._level_1_amplitude_phase_analyzer(state_vector)
        l2 = self._level_2_svd_stream_decomposer(state_vector)
        l3 = self._level_3_evaluator_logic_filter(l2)
        signal = self._level_4_metacognitive_trigger(l1, l3)

        # If successfully halted with a clear conclusion, store in memory
        if signal == FilterFunnelSignal.HALT and len(self.thought_history) > 1:
            # Store transition from initial state to final state as a success pattern
            self.memory.store(self.thought_history[0], self.thought_history[-1])

        return {
            "signal": signal,
            "entropy": float(l1["entropy"]),
            "destructive_interference": l1["destructive_interference"],
            "streams_count": len(l3),
            "highest_confidence": max([s["confidence_score"] for s in l3]) if l3 else 0.0
        }
