"""Domain exceptions for the model training pipeline.

All exceptions are deterministic and carry no nondeterministic data.
"""

from __future__ import annotations

__all__ = [
    "ModelTrainingError",
    "BridgeError",
    "FunnelError",
    "ConfigError",
    "TrainerError",
]


class ModelTrainingError(ValueError):
    """Stable base domain exception for model training errors."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
    ) -> None:
        self.message = message
        self.path = path
        rendered = message
        if path is not None:
            rendered = f"path={path}: {rendered}"
        super().__init__(rendered)


class BridgeError(ModelTrainingError):
    """ThoughtState-to-TrainingExample conversion failed."""


class FunnelError(ModelTrainingError):
    """Quality filtering or curation failed."""


class ConfigError(ModelTrainingError):
    """Model or training configuration is invalid."""


class TrainerError(ModelTrainingError):
    """Training orchestration failed."""
