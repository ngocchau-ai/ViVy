"""Frozen configuration for 1B-parameter transformer training.

All config objects are immutable, validated dataclasses.
Standard-library only; no runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nps_core.model_training.errors import ConfigError

__all__ = [
    "ModelConfig",
    "TrainingConfig",
    "DataConfig",
    "PipelineConfig",
    "MODEL_1B",
    "MODEL_MOE_40B",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg_err(msg: str, *, path: str | None = None) -> ConfigError:
    return ConfigError(msg, path=path)


def _check_positive(value: int | float, name: str) -> None:
    if value <= 0:
        raise _cfg_err(f"{name} must be positive, got {value}", path=name)


def _check_non_negative(value: int | float, name: str) -> None:
    if value < 0:
        raise _cfg_err(f"{name} must be non-negative, got {value}", path=name)


def _check_power_of_2(value: int, name: str) -> None:
    if value & (value - 1) != 0:
        raise _cfg_err(f"{name} must be a power of 2, got {value}", path=name)


# ---------------------------------------------------------------------------
# ModelConfig — Transformer architecture (~1B parameters)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Transformer architecture configuration.

    Default values target approximately 1B total parameters with:
    - RMSNorm, SwiGLU activation, RoPE, GQA
    - 24 layers, hidden_size=2048, 16 attention heads
    """

    # --- Vocabulary ---
    vocab_size: int = 32000

    # --- Transformer geometry ---
    hidden_size: int = 2048
    num_layers: int = 24
    num_attention_heads: int = 16
    num_kv_heads: int = 4
    intermediate_size: int = 5632

    # --- Sequence ---
    max_position_embeddings: int = 4096
    max_seq_len: int = 4096

    # --- Normalization ---
    rms_norm_eps: float = 1e-5

    # --- RoPE ---
    rope_theta: float = 10000.0

    # --- Dropout ---
    attention_dropout: float = 0.0
    hidden_dropout: float = 0.0

    # --- Initialization ---
    initializer_range: float = 0.02

    # --- Tied embeddings ---
    tie_word_embeddings: bool = True

    def __post_init__(self) -> None:
        _check_positive(self.vocab_size, "vocab_size")
        _check_positive(self.hidden_size, "hidden_size")
        _check_positive(self.num_layers, "num_layers")
        _check_positive(self.num_attention_heads, "num_attention_heads")
        _check_positive(self.num_kv_heads, "num_kv_heads")
        _check_positive(self.intermediate_size, "intermediate_size")
        _check_positive(self.max_position_embeddings, "max_position_embeddings")
        _check_positive(self.max_seq_len, "max_seq_len")
        _check_positive(self.rms_norm_eps, "rms_norm_eps")
        _check_positive(self.rope_theta, "rope_theta")

        if self.hidden_size % self.num_attention_heads != 0:
            raise _cfg_err(
                f"hidden_size ({self.hidden_size}) must be divisible by "
                f"num_attention_heads ({self.num_attention_heads})",
                path="hidden_size",
            )
        if self.num_attention_heads % self.num_kv_heads != 0:
            raise _cfg_err(
                f"num_attention_heads ({self.num_attention_heads}) must be divisible by "
                f"num_kv_heads ({self.num_kv_heads})",
                path="num_attention_heads",
            )
        if not 0.0 <= self.attention_dropout <= 1.0:
            raise _cfg_err(
                f"attention_dropout must be in [0, 1], got {self.attention_dropout}",
                path="attention_dropout",
            )
        if not 0.0 <= self.hidden_dropout <= 1.0:
            raise _cfg_err(
                f"hidden_dropout must be in [0, 1], got {self.hidden_dropout}",
                path="hidden_dropout",
            )

    @property
    def head_dim(self) -> int:
        return self.hidden_size // self.num_attention_heads

    @property
    def num_kv_groups(self) -> int:
        return self.num_attention_heads // self.num_kv_heads

    def estimate_params(self) -> int:
        """Estimate total parameter count."""
        h = self.hidden_size
        v = self.vocab_size
        i = self.intermediate_size
        n = self.num_layers

        # Embedding
        embedding = v * h

        # Per-layer: attention (Q + K + V + O) + FFN (gate + up + down) + norms
        q_proj = h * h
        k_proj = h * (self.num_kv_heads * self.head_dim)
        v_proj = h * (self.num_kv_heads * self.head_dim)
        o_proj = h * h
        attention = q_proj + k_proj + v_proj + o_proj

        # SwiGLU: gate_proj + up_proj + down_proj
        ffn = h * i + h * i + i * h

        # RMSNorm: 2 * hidden_size (attention_norm + ffn_norm)
        norms = 2 * h

        per_layer = attention + ffn + norms
        total_layers = n * per_layer

        # Final RMSNorm
        final_norm = h

        # Output head (tied or separate)
        output_head = 0 if self.tie_word_embeddings else v * h

        return embedding + total_layers + final_norm + output_head

    def to_dict(self) -> dict[str, Any]:
        return {
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "num_attention_heads": self.num_attention_heads,
            "num_kv_heads": self.num_kv_heads,
            "intermediate_size": self.intermediate_size,
            "max_position_embeddings": self.max_position_embeddings,
            "max_seq_len": self.max_seq_len,
            "rms_norm_eps": self.rms_norm_eps,
            "rope_theta": self.rope_theta,
            "attention_dropout": self.attention_dropout,
            "hidden_dropout": self.hidden_dropout,
            "initializer_range": self.initializer_range,
            "tie_word_embeddings": self.tie_word_embeddings,
        }


# ---------------------------------------------------------------------------
# TrainingConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Training hyperparameters for 1B model."""

    # --- Optimization ---
    learning_rate: float = 3e-4
    min_learning_rate: float = 3e-5
    weight_decay: float = 0.1
    adam_beta1: float = 0.9
    adam_beta2: float = 0.95
    adam_eps: float = 1e-8
    max_grad_norm: float = 1.0

    # --- Schedule ---
    warmup_steps: int = 2000
    total_steps: int = 100000
    lr_schedule: str = "cosine"

    # --- Batch ---
    batch_size: int = 8
    gradient_accumulation_steps: int = 8
    effective_batch_size: int = 64

    # --- Precision ---
    use_amp: bool = True
    amp_dtype: str = "bfloat16"

    # --- Checkpointing ---
    save_every_steps: int = 1000
    eval_every_steps: int = 500
    keep_last_n_checkpoints: int = 3

    # --- Reproducibility ---
    seed: int = 42

    def __post_init__(self) -> None:
        if not 0 < self.learning_rate < 1:
            raise _cfg_err(
                f"learning_rate must be in (0, 1), got {self.learning_rate}",
                path="learning_rate",
            )
        if not 0 < self.min_learning_rate <= self.learning_rate:
            raise _cfg_err(
                "min_learning_rate must be in (0, learning_rate]",
                path="min_learning_rate",
            )
        _check_positive(self.warmup_steps, "warmup_steps")
        _check_positive(self.total_steps, "total_steps")
        if self.warmup_steps >= self.total_steps:
            raise _cfg_err(
                "warmup_steps must be less than total_steps",
                path="warmup_steps",
            )
        _check_positive(self.batch_size, "batch_size")
        _check_positive(self.gradient_accumulation_steps, "gradient_accumulation_steps")

        computed_ebs = self.batch_size * self.gradient_accumulation_steps
        if self.effective_batch_size != computed_ebs:
            raise _cfg_err(
                f"effective_batch_size ({self.effective_batch_size}) must equal "
                f"batch_size * gradient_accumulation_steps ({computed_ebs})",
                path="effective_batch_size",
            )

        if self.lr_schedule not in ("cosine", "linear", "constant"):
            raise _cfg_err(
                f"lr_schedule must be 'cosine', 'linear', or 'constant', got {self.lr_schedule!r}",
                path="lr_schedule",
            )
        if self.amp_dtype not in ("bfloat16", "float16"):
            raise _cfg_err(
                f"amp_dtype must be 'bfloat16' or 'float16', got {self.amp_dtype!r}",
                path="amp_dtype",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_rate": self.learning_rate,
            "min_learning_rate": self.min_learning_rate,
            "weight_decay": self.weight_decay,
            "adam_beta1": self.adam_beta1,
            "adam_beta2": self.adam_beta2,
            "adam_eps": self.adam_eps,
            "max_grad_norm": self.max_grad_norm,
            "warmup_steps": self.warmup_steps,
            "total_steps": self.total_steps,
            "lr_schedule": self.lr_schedule,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "effective_batch_size": self.effective_batch_size,
            "use_amp": self.use_amp,
            "amp_dtype": self.amp_dtype,
            "save_every_steps": self.save_every_steps,
            "eval_every_steps": self.eval_every_steps,
            "keep_last_n_checkpoints": self.keep_last_n_checkpoints,
            "seed": self.seed,
        }


# ---------------------------------------------------------------------------
# DataConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DataConfig:
    """Data pipeline configuration."""

    max_seq_len: int = 4096
    tokenizer_name: str = "sentencepiece"
    tokenizer_path: str = ""
    num_workers: int = 4
    prefetch_factor: int = 2
    pin_memory: bool = True

    # --- Bridge ---
    task_types: tuple[str, ...] = (
        "reasoning",
        "verification",
        "critique",
        "synthesis",
    )

    # --- Funnel ---
    min_confidence: float = 0.3
    min_evidence_count: int = 1
    preferred_statuses: tuple[str, ...] = (
        "verified",
        "partially_verified",
        "testing",
        "active",
    )

    def __post_init__(self) -> None:
        _check_positive(self.max_seq_len, "max_seq_len")
        _check_non_negative(self.num_workers, "num_workers")
        _check_positive(self.prefetch_factor, "prefetch_factor")
        if not 0 <= self.min_confidence <= 1:
            raise _cfg_err(
                f"min_confidence must be in [0, 1], got {self.min_confidence}",
                path="min_confidence",
            )
        _check_non_negative(self.min_evidence_count, "min_evidence_count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_seq_len": self.max_seq_len,
            "tokenizer_name": self.tokenizer_name,
            "tokenizer_path": self.tokenizer_path,
            "num_workers": self.num_workers,
            "prefetch_factor": self.prefetch_factor,
            "pin_memory": self.pin_memory,
            "task_types": list(self.task_types),
            "min_confidence": self.min_confidence,
            "min_evidence_count": self.min_evidence_count,
            "preferred_statuses": list(self.preferred_statuses),
        }


# ---------------------------------------------------------------------------
# PipelineConfig — aggregates all sub-configs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Top-level pipeline configuration aggregating model, training, and data."""

    model: ModelConfig
    training: TrainingConfig
    data: DataConfig

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model.to_dict(),
            "training": self.training.to_dict(),
            "data": self.data.to_dict(),
        }


# ---------------------------------------------------------------------------
# Pre-built 1B configuration
# ---------------------------------------------------------------------------

MODEL_1B = PipelineConfig(
    model=ModelConfig(
        vocab_size=32000,
        hidden_size=2048,
        num_layers=24,
        num_attention_heads=16,
        num_kv_heads=4,
        intermediate_size=5632,
        max_position_embeddings=4096,
        max_seq_len=4096,
        rms_norm_eps=1e-5,
        rope_theta=10000.0,
        attention_dropout=0.0,
        hidden_dropout=0.0,
        initializer_range=0.02,
        tie_word_embeddings=True,
    ),
    training=TrainingConfig(
        learning_rate=3e-4,
        min_learning_rate=3e-5,
        weight_decay=0.1,
        adam_beta1=0.9,
        adam_beta2=0.95,
        adam_eps=1e-8,
        max_grad_norm=1.0,
        warmup_steps=2000,
        total_steps=100000,
        lr_schedule="cosine",
        batch_size=8,
        gradient_accumulation_steps=8,
        effective_batch_size=64,
        use_amp=True,
        amp_dtype="bfloat16",
        save_every_steps=1000,
        eval_every_steps=500,
        keep_last_n_checkpoints=3,
        seed=42,
    ),
    data=DataConfig(
        max_seq_len=4096,
        tokenizer_name="sentencepiece",
        tokenizer_path="",
        num_workers=4,
        prefetch_factor=2,
        pin_memory=True,
        task_types=(
            "reasoning",
            "verification",
            "critique",
            "synthesis",
            "ecology_analysis",
        ),
        min_confidence=0.3,
        min_evidence_count=1,
        preferred_statuses=(
            "verified",
            "partially_verified",
            "testing",
            "active",
        ),
    ),
)


# ---------------------------------------------------------------------------
# MODEL_MOE_40B — PipelineConfig targeting ~40B parameters (7B active)
# ---------------------------------------------------------------------------


MODEL_MOE_40B: PipelineConfig = PipelineConfig(
    model=ModelConfig(
        vocab_size=32000,
        hidden_size=4096,
        num_layers=32,
        num_attention_heads=32,
        num_kv_heads=8,
        intermediate_size=11008,
        max_position_embeddings=8192,
        max_seq_len=8192,
        rms_norm_eps=1e-5,
        rope_theta=10000.0,
        attention_dropout=0.0,
        hidden_dropout=0.0,
        initializer_range=0.02,
        tie_word_embeddings=True,
    ),
    training=TrainingConfig(
        learning_rate=3e-4,
        min_learning_rate=3e-5,
        weight_decay=0.1,
        adam_beta1=0.9,
        adam_beta2=0.95,
        adam_eps=1e-8,
        max_grad_norm=1.0,
        warmup_steps=2000,
        total_steps=100000,
        lr_schedule="cosine",
        batch_size=8,
        gradient_accumulation_steps=8,
        effective_batch_size=64,
        use_amp=True,
        amp_dtype="bfloat16",
        save_every_steps=1000,
        eval_every_steps=500,
        keep_last_n_checkpoints=3,
        seed=42,
    ),
    data=DataConfig(
        max_seq_len=8192,
        tokenizer_name="sentencepiece",
        tokenizer_path="",
        num_workers=4,
        prefetch_factor=2,
        pin_memory=True,
        task_types=(
            "reasoning",
            "verification",
            "critique",
            "synthesis",
            "ecology_analysis",
            "multimodal_vision",
            "bilingual_nlp",
        ),
        min_confidence=0.3,
        min_evidence_count=1,
        preferred_statuses=(
            "verified",
            "partially_verified",
            "testing",
            "active",
        ),
    ),
)
