"""Bounded, deterministic control transitions for the ViVy cognitive loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    FORAGE = "FORAGE"
    DELEGATE = "DELEGATE"
    BACKTRACK = "BACKTRACK"
    CONTINUE = "CONTINUE"
    HALT = "HALT"
    INCIDENT = "INCIDENT"


@dataclass(frozen=True)
class DecisionContext:
    requested: Decision
    has_expected_evidence: bool
    evidence_verified: bool = False
    tool_failed: bool = False
    repeated_failure: bool = False
    rounds: int = 0
    max_rounds: int = 10


def resolve(ctx: DecisionContext) -> Decision:
    """Apply safety precedence before a model decision can stop the loop."""
    if ctx.tool_failed:
        return Decision.BACKTRACK if ctx.repeated_failure else Decision.INCIDENT
    if ctx.rounds >= ctx.max_rounds:
        return Decision.DELEGATE
    if not ctx.has_expected_evidence:
        return Decision.DELEGATE
    if ctx.requested == Decision.HALT and not ctx.evidence_verified:
        return Decision.CONTINUE
    return ctx.requested
