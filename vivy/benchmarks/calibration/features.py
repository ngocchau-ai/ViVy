"""Confidence definition extractors for the T3 evaluation.

Each extractor reads a :class:`FeatureContext` and returns a float score
in [0, 1].  A missing signal (``None``) produces ``0.0`` — fail-closed,
never a silent ``1.0``.

Changelog:
    30/09/2026 (Claude Code — O-05/T3): Initial.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["EXTRACTORS", "FeatureContext", "extract_all"]


@dataclass(frozen=True)
class FeatureContext:
    """What an extractor needs to produce its score for one eval item."""

    item_id: str
    question: str
    model_reply: str
    tool_results: list[dict] | None
    parsed_answer: str | None
    # --- raw signals from the pipeline arm ---
    funnel_confidence: float | None
    state_norm: float | None
    llm_confidence: float | None
    ncore_min_score: float | None
    # --- for linear_tribunal ---
    prior_confidence: float | None
    supporting_count: int | None
    opposing_count: int | None
    # --- for self-consistency ---
    k_samples: list[str] | None


# --- individual extractors -------------------------------------------------


def _schmidt_spectrum(ctx: FeatureContext) -> float:
    if ctx.funnel_confidence is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.funnel_confidence)))


def _state_norm(ctx: FeatureContext) -> float:
    if ctx.state_norm is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.state_norm)))


def _llm_declared(ctx: FeatureContext) -> float:
    if ctx.llm_confidence is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.llm_confidence)))


def _ncore_min(ctx: FeatureContext) -> float:
    if ctx.ncore_min_score is None:
        return 0.0
    return float(max(0.0, min(1.0, ctx.ncore_min_score)))


def _linear_tribunal(ctx: FeatureContext) -> float:
    if (
        ctx.prior_confidence is None
        or ctx.supporting_count is None
        or ctx.opposing_count is None
    ):
        return 0.0
    prior = max(0.0, min(1.0, ctx.prior_confidence))
    delta = 0.1 * (ctx.supporting_count - ctx.opposing_count)
    return float(max(0.0, min(1.0, prior + delta)))


def _self_consistency(ctx: FeatureContext) -> float:
    if ctx.k_samples is None or len(ctx.k_samples) == 0:
        return 0.0
    counts: dict[str, int] = {}
    for reply in ctx.k_samples:
        counts[reply] = counts.get(reply, 0) + 1
    most_common = max(counts.values())
    return float(most_common / len(ctx.k_samples))


def _verifier(ctx: FeatureContext) -> float:
    if ctx.tool_results is None or len(ctx.tool_results) == 0:
        return 0.0
    any_ok = any(t.get("ok", False) for t in ctx.tool_results)
    any_fail = any(not t.get("ok", False) for t in ctx.tool_results)
    return 1.0 if (any_ok and not any_fail) else 0.0


# --- registry --------------------------------------------------------------

EXTRACTORS: dict[str, Callable[[FeatureContext], float]] = {
    "schmidt_spectrum": _schmidt_spectrum,
    "state_norm": _state_norm,
    "llm_declared": _llm_declared,
    "ncore_min": _ncore_min,
    "linear_tribunal": _linear_tribunal,
    "self_consistency": _self_consistency,
    "verifier": _verifier,
}


def extract_all(ctx: FeatureContext) -> dict[str, float]:
    """Run every extractor on one context, returning a score per definition."""
    return {name: fn(ctx) for name, fn in EXTRACTORS.items()}
