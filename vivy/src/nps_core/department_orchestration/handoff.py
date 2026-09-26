"""Automated Session Handoff Generator.

Standard-library only; generates clean markdown session handoff documents.
"""

from __future__ import annotations

from collections.abc import Sequence

from nps_core.department_orchestration.errors import HandoffValidationError

__all__ = [
    "HandoffGenerator",
]


class HandoffGenerator:
    """Generates standardized markdown handoff documentation for NPS Core sessions."""

    @staticmethod
    def generate(
        completed_tasks: Sequence[str],
        current_state: str,
        open_risks: Sequence[str],
        next_action: str,
        required_context: Sequence[str],
    ) -> str:
        """Generate markdown string conforming to handoff format."""
        if not completed_tasks:
            raise HandoffValidationError("completed_tasks cannot be empty", path="completed_tasks")
        if not current_state.strip():
            raise HandoffValidationError("current_state cannot be empty", path="current_state")
        if not next_action.strip():
            raise HandoffValidationError("next_action cannot be empty", path="next_action")

        lines: list[str] = ["# Session Handoff", "", "## Completed", ""]
        for task in completed_tasks:
            lines.append(f"- {task}")

        lines.extend(["", "## Current repository state", "", current_state.strip(), "", "## Open risks", ""])
        if open_risks:
            for risk in open_risks:
                lines.append(f"- {risk}")
        else:
            lines.append("- None reported.")

        lines.extend(["", "## Next exact action", "", next_action.strip(), "", "## Required context", ""])
        if required_context:
            for ctx in required_context:
                lines.append(f"- {ctx}")
        else:
            lines.append("- ARCHITECTURE.md")

        lines.append("")
        return "\n".join(lines)
