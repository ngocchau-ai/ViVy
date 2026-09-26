"""A — Native parity fix-or-retire decision (Plan 2, §5.1).

Evaluates parity evidence and decides:
  * **A-fix**   — first-token divergence root-caused and fixed, with regression tests.
  * **A-retire** — no fix in budget; formally retire native forward, isolate not delete.

Consequences (§5.1):
  * A-fix   → Gate 1 native residency closed.
  * A-retire → Gate 1 = llama-server only; native memory path retained if ABI stable.

Isolate-not-delete: A-retire never deletes native code. It tags it
``[ISOLATED / DEPRECATED / REPLACED]`` and routes execution through llama-server.

Changelog:
    24/09/2026 (Claude Code — Plan 2 A): Initial.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# --- Evidence contract --------------------------------------------------------


@dataclass(frozen=True)
class ParityEvidence:
    """One parity check result."""

    check_id: str
    status: str  # PASS | FAIL | NOT_RUN
    detail: str = ""
    receipt_id: str = ""


@dataclass(frozen=True)
class ParityDecision:
    """Structured A-fix / A-retire decision with evidence trail."""

    decision: str  # "A-fix" | "A-retire"
    rationale: str
    evidence: tuple[ParityEvidence, ...]
    gate1_status: str  # "native_residency_closed" | "llama_server_only"
    native_memory_retained: bool
    label: str = "PROVISIONAL_RESULT"
    claim_boundary: str = (
        "Native forward parity only. Does NOT indict llama-server :8080. "
        "PRODUCTION-READY = NOT_CLAIMED. LATENCY_CLAIM = NOT_A_PHYSICAL_ZERO."
    )


# --- Decision logic -----------------------------------------------------------


def decide_native_parity(
    evidence: list[ParityEvidence],
    *,
    fix_available: bool = False,
    fix_has_regression: bool = False,
    budget_exhausted: bool = True,
    abi_stable: bool = True,
) -> ParityDecision:
    """Decide A-fix or A-retire from parity evidence and budget state.

    A-fix requires ALL of:
      1. ``fix_available`` — root cause of first-token divergence identified.
      2. ``fix_has_regression`` — regression tests pass after the fix.

    Otherwise → A-retire (isolate, do not delete).
    """
    evid = tuple(evidence)

    if fix_available and fix_has_regression and not budget_exhausted:
        return ParityDecision(
            decision="A-fix",
            rationale=(
                "First-token divergence root-caused and fixed with regression tests. "
                "Gate 1 native residency is closed."
            ),
            evidence=evid,
            gate1_status="native_residency_closed",
            native_memory_retained=True,
        )

    # A-retire path
    reasons = []
    if not fix_available:
        reasons.append("root cause of first-token divergence not identified")
    if fix_available and not fix_has_regression:
        reasons.append("fix proposed but regression tests missing or failing")
    if budget_exhausted:
        reasons.append("budget exhausted")
    rationale = (
        "A-retire: " + "; ".join(reasons) + ". "
        "Formally retire native forward (isolate, not delete). "
        "Gate 1 = llama-server only. "
        + ("Native memory path retained (ABI stable)." if abi_stable
           else "Native memory path also retired (ABI unstable).")
    )
    return ParityDecision(
        decision="A-retire",
        rationale=rationale,
        evidence=evid,
        gate1_status="llama_server_only",
        native_memory_retained=abi_stable,
    )


# --- L-40 evidence builder ---------------------------------------------------


def l40_evidence() -> list[ParityEvidence]:
    """Build the known L-40 parity evidence (native CAUTREO forward/logits FAIL)."""
    return [
        ParityEvidence(
            check_id="tokenizer-parity",
            status="PASS",
            detail="prompt/tokenizer parity 24/24 IDs",
            receipt_id="VIVY-CAUTREO-TOKENIZER-PARITY-167",
        ),
        ParityEvidence(
            check_id="template-parity",
            status="PASS",
            detail="chat template parity matched",
            receipt_id="VIVY-CAUTREO-TEMPLATE-PARITY-170",
        ),
        ParityEvidence(
            check_id="forward-logits-parity",
            status="FAIL",
            detail=(
                "first token 177869/gug vs reference 26391/Four for 2+2=4"
            ),
            receipt_id="VIVY-CAUTREO-GEMMA4-CHAT-171",
        ),
        ParityEvidence(
            check_id="exact-prompt-parity",
            status="FAIL",
            detail="exact prompt reproduction still diverges on first token",
            receipt_id="VIVY-CAUTREO-GEMMA4-EXACT-PROMPT-196",
        ),
    ]


# --- Decision to dict (for receipts) ------------------------------------------


def decision_to_dict(decision: ParityDecision) -> dict[str, Any]:
    """Serialize a ParityDecision to a plain dict for receipt writing."""
    return {
        "decision": decision.decision,
        "rationale": decision.rationale,
        "gate1_status": decision.gate1_status,
        "native_memory_retained": decision.native_memory_retained,
        "label": decision.label,
        "claim_boundary": decision.claim_boundary,
        "evidence": [
            {
                "check_id": e.check_id,
                "status": e.status,
                "detail": e.detail,
                "receipt_id": e.receipt_id,
            }
            for e in decision.evidence
        ],
    }
