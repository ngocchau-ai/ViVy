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
    """State available when the control loop asks what to do next.

    ``budget_exhausted`` and ``single_round`` were added 29/09/2026 (WP-2 / O-03).
    Before that the caller never supplied ``evidence_verified`` / ``tool_failed``
    / ``repeated_failure`` (they stayed at their defaults), so HALT was
    unreachable and CHAT/BATCH reported DELEGATE for every answer (F-B01, F-B02).
    """

    requested: Decision
    has_expected_evidence: bool
    evidence_verified: bool = False
    tool_failed: bool = False
    repeated_failure: bool = False
    rounds: int = 0
    max_rounds: int = 10
    budget_exhausted: bool | None = None
    """Explicit budget verdict.  ``None`` derives it from ``rounds >= max_rounds``."""
    single_round: bool = False
    """True for CHAT/BATCH: one round only, so loop-governance rules do not apply."""


def resolve(ctx: DecisionContext) -> Decision:
    """Apply safety precedence before a model decision can stop the loop.

    Order (safety first):

    1. a failed tool call blocks everything — INCIDENT, or BACKTRACK when the
       same tool has already failed;
    2. verified evidence ends the loop with HALT (made reachable 29/09/2026;
       previously HALT required a request the parse map never produced) — but
       only when the model is not asking for more work.  Overriding an explicit
       FORAGE/DELEGATE into HALT is exactly the false-halt T4 forbids;
    3. an exhausted budget hands off to another model;
    4. a missing Expected_Evidence contract hands off rather than stopping;
    5. otherwise the model's own request stands, except an unverified HALT,
       which becomes CONTINUE.

    ``single_round`` short-circuits rules 3 and 4: those govern a multi-round
    loop, and applying them to a one-shot CHAT/BATCH run made every answer
    report DELEGATE.
    """
    if ctx.tool_failed:
        return Decision.BACKTRACK if ctx.repeated_failure else Decision.INCIDENT
    wants_more_work = ctx.requested in (Decision.FORAGE, Decision.DELEGATE, Decision.BACKTRACK)
    if ctx.evidence_verified and not wants_more_work:
        return Decision.HALT
    if not ctx.single_round:
        exhausted = (
            ctx.budget_exhausted
            if ctx.budget_exhausted is not None
            else ctx.rounds >= ctx.max_rounds
        )
        if exhausted:
            return Decision.DELEGATE
        if not ctx.has_expected_evidence:
            return Decision.DELEGATE
    if ctx.requested == Decision.HALT and not ctx.evidence_verified:
        return Decision.CONTINUE
    return ctx.requested
