"""Domain exceptions for verification_tribunal module.

Standard-library only.
"""

from __future__ import annotations

__all__ = [
    "TribunalError",
    "TribunalConflictError",
]


class TribunalError(ValueError):
    """Base domain exception for Verification Tribunal errors."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


class TribunalConflictError(TribunalError):
    """Raised when unresolvable evidence conflict occurs during tribunal evaluation."""
