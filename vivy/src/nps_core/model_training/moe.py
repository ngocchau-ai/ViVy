"""Mixture-of-Experts (MoE) Architecture Configuration & Router for ViVy 40B/7B.

Provides MoEConfig and MoERouter calculating sparse expert activation routing and compute cost savings.
Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nps_core.model_training.errors import ConfigError

__all__ = [
    "MoEConfig",
    "MoERouter",
]

_EXPERT_NAMES = (
    "Multimodal_Vision",
    "Bilingual_NLP_EN_VI",
    "Chain_of_Thought_Logic",
    "Code_AST_Analysis",
    "Quantitative_Timeseries",
    "Distillation_Memory",
    "Verification_Tribunal",
    "General_Synthesis",
)


@dataclass(frozen=True, slots=True)
class MoEConfig:
    """Frozen configuration for ViVy Sparse Mixture-of-Experts (40B total / 7B active)."""

    model_name: str = "vivy-moe-40b-7b"
    num_total_experts: int = 8
    num_active_experts: int = 2
    total_parameters: int = 40_000_000_000
    active_parameters: int = 7_000_000_000
    router_type: str = "top_k_softmax"

    def __post_init__(self) -> None:
        if self.num_total_experts <= 0:
            raise ConfigError("num_total_experts must be positive", path="num_total_experts")
        if self.num_active_experts <= 0 or self.num_active_experts > self.num_total_experts:
            raise ConfigError("num_active_experts invalid", path="num_active_experts")

    @property
    def compute_reduction_ratio(self) -> float:
        """Compute percentage of FLOPs saved compared to dense 40B evaluation."""
        return 1.0 - (self.active_parameters / self.total_parameters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "num_total_experts": self.num_total_experts,
            "num_active_experts": self.num_active_experts,
            "total_parameters": self.total_parameters,
            "active_parameters": self.active_parameters,
            "compute_reduction_ratio": round(self.compute_reduction_ratio, 4),
            "router_type": self.router_type,
        }


class MoERouter:
    """Router routing tasks and tokens to top-k active experts."""

    @staticmethod
    def route_task(task_type: str, config: MoEConfig | None = None) -> tuple[str, ...]:
        """Select top-k active experts for a given task type."""
        config or MoEConfig()
        task_lower = task_type.lower()

        if "vision" in task_lower or "image" in task_lower:
            return (_EXPERT_NAMES[0], _EXPERT_NAMES[2])
        elif "code" in task_lower or "ast" in task_lower:
            return (_EXPERT_NAMES[3], _EXPERT_NAMES[2])
        elif "lang" in task_lower or "nlp" in task_lower or "bilingual" in task_lower or "vietnamese" in task_lower or "english" in task_lower:
            return (_EXPERT_NAMES[1], _EXPERT_NAMES[7])
        else:
            return (_EXPERT_NAMES[2], _EXPERT_NAMES[7])
