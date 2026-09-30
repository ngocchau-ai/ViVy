"""Domain exceptions for distillation_dataset module.

Standard-library only.
"""

from __future__ import annotations

__all__ = [
    "DatasetError",
    "SplitError",
]


class DatasetError(ValueError):
    """Base domain exception for Distillation Dataset errors."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


class SplitError(DatasetError):
    """Raised when dataset split parameters or outputs are invalid."""
