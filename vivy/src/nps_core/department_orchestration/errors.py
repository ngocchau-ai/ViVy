"""Domain exceptions for department_orchestration module.

Standard-library only; no runtime dependencies beyond standard library.
"""

from __future__ import annotations

__all__ = [
    "DepartmentError",
    "OrchestrationRuleViolationError",
    "HandoffValidationError",
]


class DepartmentError(ValueError):
    """Base domain exception for local software department errors."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


class OrchestrationRuleViolationError(DepartmentError):
    """Raised when Codex orchestration-only or local model role isolation rule is violated."""


class HandoffValidationError(DepartmentError):
    """Raised when session handoff document structure is invalid."""
