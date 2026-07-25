"""Training orchestration for 1B-parameter transformer model.

Provides ``TrainingState`` and ``train_step`` for deterministic
training loop construction.  Requires PyTorch for actual training;
standard-library-only helpers are available for state management.

This module is the ONLY file in model_training that optionally
imports PyTorch.  All other modules remain stdlib-only.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any

from nps_core.model_training.config import (
    DataConfig,
    ModelConfig,
    PipelineConfig,
    TrainingConfig,
)
from nps_core.model_training.errors import TrainerError

__all__ = [
    "TrainingState",
    "TrainMetrics",
    "create_optimizer",
    "create_scheduler",
    "train_step",
    "save_checkpoint",
    "load_checkpoint",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trainer_err(msg: str, **kwargs: Any) -> TrainerError:
    return TrainerError(msg, **kwargs)


# ---------------------------------------------------------------------------
# TrainMetrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrainMetrics:
    """Immutable snapshot of training metrics at a given step."""

    step: int
    epoch: int
    loss: float
    learning_rate: float
    grad_norm: float
    tokens_per_second: float
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "epoch": self.epoch,
            "loss": round(self.loss, 6),
            "learning_rate": self.learning_rate,
            "grad_norm": round(self.grad_norm, 4),
            "tokens_per_second": round(self.tokens_per_second, 2),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


# ---------------------------------------------------------------------------
# TrainingState — mutable checkpoint state
# ---------------------------------------------------------------------------


@dataclass
class TrainingState:
    """Mutable training state for checkpointing and resumption."""

    global_step: int = 0
    epoch: int = 0
    total_tokens: int = 0
    best_loss: float = float("inf")
    best_step: int = 0
    metrics_history: list[dict[str, Any]] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def update_step(
        self,
        *,
        loss: float,
        learning_rate: float,
        grad_norm: float,
        num_tokens: int,
        elapsed: float,
    ) -> TrainMetrics:
        """Record a training step and return metrics."""
        self.global_step += 1
        self.total_tokens += num_tokens

        tps = num_tokens / max(elapsed, 1e-6)

        metrics = TrainMetrics(
            step=self.global_step,
            epoch=self.epoch,
            loss=loss,
            learning_rate=learning_rate,
            grad_norm=grad_norm,
            tokens_per_second=tps,
            elapsed_seconds=elapsed,
        )

        self.metrics_history.append(metrics.to_dict())

        if loss < self.best_loss:
            self.best_loss = loss
            self.best_step = self.global_step

        return metrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_step": self.global_step,
            "epoch": self.epoch,
            "total_tokens": self.total_tokens,
            "best_loss": self.best_loss,
            "best_step": self.best_step,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainingState:
        return cls(
            global_step=data.get("global_step", 0),
            epoch=data.get("epoch", 0),
            total_tokens=data.get("total_tokens", 0),
            best_loss=data.get("best_loss", float("inf")),
            best_step=data.get("best_step", 0),
            config=data.get("config", {}),
        )

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )


# ---------------------------------------------------------------------------
# Learning rate scheduler
# ---------------------------------------------------------------------------


def _cosine_schedule(
    step: int,
    *,
    warmup_steps: int,
    total_steps: int,
    max_lr: float,
    min_lr: float,
) -> float:
    """Cosine annealing with linear warmup."""
    if step < warmup_steps:
        return max_lr * step / max(warmup_steps, 1)
    if step >= total_steps:
        return min_lr
    progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))


def _linear_schedule(
    step: int,
    *,
    warmup_steps: int,
    total_steps: int,
    max_lr: float,
    min_lr: float,
) -> float:
    """Linear decay with linear warmup."""
    if step < warmup_steps:
        return max_lr * step / max(warmup_steps, 1)
    if step >= total_steps:
        return min_lr
    progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
    return max_lr - progress * (max_lr - min_lr)


def _constant_schedule(
    step: int,
    *,
    warmup_steps: int,
    max_lr: float,
    **_kwargs: Any,
) -> float:
    """Constant LR with linear warmup."""
    if step < warmup_steps:
        return max_lr * step / max(warmup_steps, 1)
    return max_lr


def get_learning_rate(
    step: int,
    config: TrainingConfig,
) -> float:
    """Compute learning rate for the given step."""
    if config.lr_schedule == "cosine":
        return _cosine_schedule(
            step,
            warmup_steps=config.warmup_steps,
            total_steps=config.total_steps,
            max_lr=config.learning_rate,
            min_lr=config.min_learning_rate,
        )
    elif config.lr_schedule == "linear":
        return _linear_schedule(
            step,
            warmup_steps=config.warmup_steps,
            total_steps=config.total_steps,
            max_lr=config.learning_rate,
            min_lr=config.min_learning_rate,
        )
    elif config.lr_schedule == "constant":
        return _constant_schedule(
            step,
            warmup_steps=config.warmup_steps,
            max_lr=config.learning_rate,
        )
    else:
        raise _trainer_err(f"unknown lr_schedule: {config.lr_schedule!r}")


# ---------------------------------------------------------------------------
# PyTorch-dependent functions (optional import)
# ---------------------------------------------------------------------------


def _require_torch() -> Any:
    """Import and return torch; raise TrainerError if unavailable."""
    try:
        import torch
        return torch
    except ImportError as exc:
        raise TrainerError(
            "PyTorch is required for training. Install with: pip install torch",
        ) from exc


def create_optimizer(
    model: Any,
    config: TrainingConfig,
) -> Any:
    """Create AdamW optimizer with weight decay. Requires PyTorch."""
    torch = _require_torch()

    decay_params: list[Any] = []
    no_decay_params: list[Any] = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if any(
            nd in name
            for nd in ("bias", "norm.weight", "embedding", "layernorm")
        ):
            no_decay_params.append(param)
        else:
            decay_params.append(param)

    optimizer_groups = [
        {"params": decay_params, "weight_decay": config.weight_decay},
        {"params": no_decay_params, "weight_decay": 0.0},
    ]

    return torch.optim.AdamW(
        optimizer_groups,
        lr=config.learning_rate,
        betas=(config.adam_beta1, config.adam_beta2),
        eps=config.adam_eps,
    )


def create_scheduler(
    optimizer: Any,
    config: TrainingConfig,
) -> Any:
    """Create learning rate scheduler. Requires PyTorch."""
    torch = _require_torch()

    def lr_lambda(step: int) -> float:
        return get_learning_rate(step, config) / config.learning_rate

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def train_step(
    model: Any,
    batch: dict[str, Any],
    optimizer: Any,
    scheduler: Any,
    scaler: Any,
    config: TrainingConfig,
    state: TrainingState,
) -> TrainMetrics:
    """Execute a single training step. Requires PyTorch."""
    torch = _require_torch()

    start_time = time.monotonic()

    device = next(model.parameters()).device
    input_ids = batch["input_ids"].to(device)
    labels = batch["labels"].to(device)
    attention_mask = batch.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    if config.use_amp and scaler is not None:
        with torch.cuda.amp.autocast(
            dtype=torch.bfloat16 if config.amp_dtype == "bfloat16" else torch.float16
        ):
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / config.gradient_accumulation_steps
        scaler.scale(loss).backward()
    else:
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )
        loss = outputs.loss / config.gradient_accumulation_steps
        loss.backward()

    actual_step = state.global_step + 1
    if actual_step % config.gradient_accumulation_steps == 0:
        if config.use_amp and scaler is not None:
            scaler.unscale_(optimizer)

        grad_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            config.max_grad_norm,
        )

        if config.use_amp and scaler is not None:
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()

        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
    else:
        grad_norm = torch.tensor(0.0)

    elapsed = time.monotonic() - start_time
    num_tokens = input_ids.numel()

    metrics = state.update_step(
        loss=loss.item() * config.gradient_accumulation_steps,
        learning_rate=scheduler.get_last_lr()[0],
        grad_norm=grad_norm.item() if hasattr(grad_norm, "item") else float(grad_norm),
        num_tokens=num_tokens,
        elapsed=elapsed,
    )

    return metrics


def save_checkpoint(
    model: Any,
    optimizer: Any,
    scheduler: Any,
    state: TrainingState,
    path: str,
) -> None:
    """Save training checkpoint. Requires PyTorch."""
    torch = _require_torch()

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "training_state": state.to_dict(),
    }
    torch.save(checkpoint, path)


def load_checkpoint(
    model: Any,
    optimizer: Any,
    scheduler: Any,
    path: str,
) -> TrainingState:
    """Load training checkpoint. Requires PyTorch."""
    torch = _require_torch()

    checkpoint = torch.load(path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    state = TrainingState.from_dict(checkpoint["training_state"])

    return state
