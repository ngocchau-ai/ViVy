"""Non-actuating shadow router for typed ViVy decisions.

Changelog: 2026-09-24 (Antigravity/Claude Code — P0 CORRECTIONS §2.3, §2.5)
    Label-leakage isolation. `recommend()` no longer copies selected_candidate
    as the recommendation — that path is retained only as `replay_copy_label()`
    for fixture/replay tests and is explicitly tagged LEAKY. A real predictor
    must consume `predict_input()` (task/context/candidates only). Abstain
    semantics cover cand_abstain / refusal / reobserve, not just decision_type=noul.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

# Candidate ids / action types that mean abstain even when decision_type != noul.
ABSTAIN_TOKENS = frozenset({
    "abstain", "cand_abstain", "noul", "refusal", "refuse", "reobserve",
    "halt", "no_action", "wait",
})


@dataclass(frozen=True)
class ShadowResult:
    recommendation: str | None
    observed: str | None
    agree: bool | None
    confidence: float
    actuated: bool = False
    policy: str = "abstain"
    note: str = ""


def predict_input(record: Mapping[str, Any]) -> dict[str, Any]:
    """Strip label fields so a predictor cannot read the answer.

    Returns only task/context/candidates — never selected_candidate, gold_*,
    reviewer score, or outcome.
    """
    candidates = []
    for candidate in record.get("candidates", []) or []:
        if isinstance(candidate, Mapping):
            candidates.append({
                "id": candidate.get("id"),
                "description": candidate.get("description", ""),
                "action_type": candidate.get("action_type", ""),
            })
    return {
        "decision_type": record.get("decision_type"),
        "context_state": record.get("context_state", ""),
        "candidates": candidates,
    }


def _is_abstain_record(record: Mapping[str, Any]) -> bool:
    if record.get("decision_type") == "noul":
        return True
    for candidate in record.get("candidates", []) or []:
        if not isinstance(candidate, Mapping):
            continue
        cid = str(candidate.get("id", "")).strip().lower()
        action = str(candidate.get("action_type", "")).strip().lower()
        if cid in ABSTAIN_TOKENS or action in ABSTAIN_TOKENS:
            return True
    return False


def recommend(record: Mapping[str, Any]) -> ShadowResult:
    """Return a bounded recommendation; this function never executes actions.

    Non-leaky default: abstain unless a real predictor supplies a candidate id
    via `predicted_candidate`. Does NOT copy selected_candidate.
    """
    observed = record.get("selected_candidate")
    confidence = float(record.get("confidence", 0.0) or 0.0)
    if _is_abstain_record(record):
        return ShadowResult(None, observed, observed is None, confidence,
                            policy="abstain_semantics",
                            note="ABSTAIN_OR_NOUL")
    if record.get("label_quality") != "independently_reviewed":
        return ShadowResult(None, observed, None, confidence,
                            policy="abstain_unverified",
                            note="UNVERIFIED_LABEL_NOT_RECOMMENDED")
    predicted = record.get("predicted_candidate")
    if isinstance(predicted, str) and predicted:
        ids = {str(c.get("id")) for c in record.get("candidates", []) or [] if isinstance(c, Mapping)}
        if ids and predicted not in ids:
            return ShadowResult(None, observed, None, confidence,
                                policy="abstain_invalid_prediction",
                                note="PREDICTED_CANDIDATE_NOT_IN_SET")
        return ShadowResult(predicted, observed, predicted == observed if observed is not None else None,
                            confidence, policy="external_predictor",
                            note="PREDICTION_FROM_MODEL_NOT_LABEL")
    # No external predictor: abstain. Copying the label is leakage (§2.3).
    return ShadowResult(None, observed, None, confidence,
                        policy="abstain_no_predictor",
                        note="NO_INDEPENDENT_PREDICTOR")


def replay_copy_label(record: Mapping[str, Any]) -> ShadowResult:
    """[ISOLATED 24/09/2026] LEAKY fixture/replay helper.

    Copies selected_candidate as the recommendation. Agreement from this path
    is tautological and must never be reported as accuracy. Retained only so
    existing shadow receipts remain reproducible.
    """
    observed = record.get("selected_candidate")
    confidence = float(record.get("confidence", 0.0) or 0.0)
    recommendation = observed if isinstance(observed, str) else None
    return ShadowResult(
        recommendation, observed,
        recommendation == observed if recommendation is not None else None,
        confidence,
        policy="LEAKY_COPY_LABEL_ISOLATED",
        note="CIRCULAR_ON_INDEPENDENTLY_REVIEWED",
    )
