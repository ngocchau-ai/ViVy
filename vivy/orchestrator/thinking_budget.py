"""Dynamic Thinking Budget — per-request budget from epistemic decision.

Maps EpistemicGate / directive decisions to a per-request thinking budget
(0 / 384 / 1024) instead of force-disabling thinking on every call or relying
on a single static server-level hard cap.

Budget ladder (Claude 3.7-style hybrid reasoning):
    OFF      (0)    — EXECUTE_DIRECTLY / HALT: high confidence, no extra reasoning
    STANDARD (384)  — NEED_KNOWLEDGE_FORAGING / CONTINUE / unknown: moderate reasoning
    DEEP     (1024) — DELEGATE_* / BACKTRACK / INCIDENT: specialist-grade reasoning

`reasoning_format` stays "none" so HoH contract text remains in message.content.
When thinking is enabled, callers MUST keep the content/reasoning_content fallback
(Gemma4 can route the answer into reasoning_content and hide the directive).

Gate 9: this module selects a budget. It does NOT claim latency, quality, or
accuracy gains from enabling thinking — those need their own receipts.

Changelog:
    23/09/2026 (Claude Code — P1 Dynamic Thinking Budget): Initial.
"""

from __future__ import annotations

from typing import Any

# Budget ladder (thinking tokens per request)
THINKING_BUDGET_OFF = 0
THINKING_BUDGET_STANDARD = 384
THINKING_BUDGET_DEEP = 1024

# Must stay in sync with start_vivy_gemma4.ps1 `--reasoning-budget`.
# The server flag is the hard ceiling; client-side we clamp to it.
THINKING_BUDGET_CEILING = 1024

# Decision → budget. Includes EpistemicDecision, parse_directive aliases,
# and DecisionController values so one resolver serves every call path.
_DECISION_BUDGET: dict[str, int] = {
    # EpistemicGate / parse_directive
    "EXECUTE_DIRECTLY": THINKING_BUDGET_OFF,
    "EXECUTE": THINKING_BUDGET_OFF,
    "HALT": THINKING_BUDGET_OFF,
    "NEED_KNOWLEDGE_FORAGING": THINKING_BUDGET_STANDARD,
    "NEED_INFO": THINKING_BUDGET_STANDARD,
    "CONTINUE": THINKING_BUDGET_STANDARD,
    "FORAGE": THINKING_BUDGET_STANDARD,
    "UNKNOWN": THINKING_BUDGET_STANDARD,
    "DELEGATE_MODEL": THINKING_BUDGET_DEEP,
    "DELEGATE_CODEX": THINKING_BUDGET_DEEP,
    "DELEGATE_CLAUDE": THINKING_BUDGET_DEEP,
    "DELEGATE": THINKING_BUDGET_DEEP,
    "BACKTRACK": THINKING_BUDGET_DEEP,
    "INCIDENT": THINKING_BUDGET_DEEP,
}


def _decision_key(decision: Any) -> str:
    """Normalize EpistemicDecision / Decision / str to an uppercase map key.

    str(Decision.DELEGATE) is "Decision.DELEGATE" (Enum.__str__), so prefer
    .value whenever present.
    """
    value = getattr(decision, "value", decision)
    return str(value).strip().upper()


def resolve_thinking_budget(decision: str | Any | None) -> int:
    """Map an epistemic/directive decision to a thinking budget.

    Accepts EpistemicDecision, DecisionController Decision, or any string.
    None / unknown → THINKING_BUDGET_STANDARD (moderate reasoning for an
    uncharacterized request — not force-off).
    """
    if decision is None:
        return THINKING_BUDGET_STANDARD
    return _DECISION_BUDGET.get(_decision_key(decision), THINKING_BUDGET_STANDARD)


def clamp_thinking_budget(budget: int) -> int:
    """Clamp budget into [0, THINKING_BUDGET_CEILING]."""
    try:
        value = int(budget)
    except (TypeError, ValueError):
        return THINKING_BUDGET_OFF
    return max(THINKING_BUDGET_OFF, min(THINKING_BUDGET_CEILING, value))


def build_chat_template_kwargs(budget: int) -> dict[str, Any]:
    """Build `chat_template_kwargs` for llama-server / Gemma4 canonical template.

    budget <= 0 → enable_thinking False (current safe path).
    budget >  0 → enable_thinking True with a clamped thinking_budget.
    """
    clamped = clamp_thinking_budget(budget)
    if clamped <= THINKING_BUDGET_OFF:
        return {"enable_thinking": False}
    return {"enable_thinking": True, "thinking_budget": clamped}


def build_thinking_payload_fields(budget: int) -> dict[str, Any]:
    """Payload fields that control thinking on a single request.

    `reasoning_format` stays "none" so the HoH contract text (Epistemic_Decision,
    Expected_Evidence) remains in message.content rather than reasoning_content.
    """
    return {
        "reasoning_format": "none",
        "chat_template_kwargs": build_chat_template_kwargs(budget),
    }


def resolve_budget_from(
    thinking_budget: int | None = None,
    epistemic_decision: str | Any | None = None,
) -> int:
    """Prefer an explicit budget; else resolve from the decision; else default.

    Default (neither given) is THINKING_BUDGET_OFF so callers that have not
    opted into dynamic budgeting keep the historical force-disable behavior.
    Opt-in paths pass resolve_thinking_budget(decision) or an explicit int.
    """
    if thinking_budget is not None:
        return clamp_thinking_budget(thinking_budget)
    if epistemic_decision is not None:
        return resolve_thinking_budget(epistemic_decision)
    return THINKING_BUDGET_OFF
