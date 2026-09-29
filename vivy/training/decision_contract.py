"""C02 typed contract split: DecisionInput / DecisionPrediction / DecisionLabel.

A predictor may only see DecisionInput. DecisionLabel is scoring truth and is
never an input field. Authority is checked independently of model confidence.

Schema note (C02): NOUL decision_type, abstain policy, and action HALT are
distinct objects — they must not be collapsed into one "no-op" bucket.
Score (ordinal/utility) is not a probability.

Changelog:
    24/09/2026 (Claude Code — P1/P2 C02): Initial.
    29/09/2026 (Claude Code — WP-6/O-10): named the ChatML-vs-typed schema
        split and made the typed APIs refuse a ChatML row with
        :class:`SchemaMismatchError` instead of a misleading field error.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "vivy-decision-contract-v1"

# --- enums kept separate (C02: schema/version distinguishes these) -----------
DECISION_TYPES = frozenset({"choice", "score", "noul"})
SPLITS = frozenset({"train", "dev", "test"})
OUTCOMES = frozenset({"success", "failure", "unknown"})
# Abstain *policy* reasons — not the same as decision_type=noul or action HALT.
ABSTAIN_POLICIES = frozenset({
    "abstain_no_predictor",
    "abstain_unverified",
    "abstain_semantics",
    "abstain_invalid_prediction",
    "policy_abstain",
    "none",
})
# Action-level HALT is a candidate action_type, not a decision_type.
HALT_ACTIONS = frozenset({"halt", "abort", "cand_halt", "no_action", "wait"})

RECEIPT_ID_RE = re.compile(r"^(human-accept|oracle|legacy|shadow|c01)-[0-9a-f]{4,64}$")

# --- WP-6 / O-10 — the two row schemas, and the wall between them ------------
#
# ``dataset_extractor`` emits ChatML (``messages`` / ``source`` / ``reward``).
# This contract, ``dataset_audit`` and every gate downstream expect typed rows
# (``context_state`` / ``candidates`` / ``provenance``).  Feeding one to the
# other used to fail with "candidates must be a list", which reads like a
# corrupt row rather than a wrong schema.  Naming the schema is the fix; the
# conversion itself lives in ``training.legacy_to_typed.migrate``.
SCHEMA_CHATML = "chatml"
SCHEMA_TYPED = "typed"

#: Fields that only ever exist on a typed row.
_TYPED_ONLY_FIELDS = ("context_state", "candidates", "decision_type", "provenance")


def detect_schema(record: Mapping[str, Any]) -> str:
    """``SCHEMA_CHATML`` or ``SCHEMA_TYPED``.  Same rule as dataset_audit."""
    if "messages" in record and "context_state" not in record:
        return SCHEMA_CHATML
    if "conversations" in record and "context_state" not in record:
        return SCHEMA_CHATML
    return SCHEMA_TYPED


class SchemaMismatchError(ValueError):
    """A ChatML row was handed to a typed-row API (or the reverse)."""


def require_typed(record: Mapping[str, Any], *, api: str = "decision contract") -> Mapping[str, Any]:
    """Return *record* if it is typed; raise :class:`SchemaMismatchError` if not.

    Call this at every boundary that feeds a row to ``validate_decision_input``
    / ``validate_decision_label``.  It turns a shape error into a named one.
    """
    schema = detect_schema(record)
    if schema == SCHEMA_CHATML:
        raise SchemaMismatchError(
            f"{api} expects a typed row (one of {sorted(_TYPED_ONLY_FIELDS)}); "
            f"got a ChatML row (messages/conversations). "
            f"Migrate it first: training.legacy_to_typed.migrate(...)"
        )
    return record


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite_unit(value: Any, field_name: str) -> float:
    if not _is_number(value):
        raise ValueError(f"{field_name} must be a number, not {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite (got {number})")
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field_name} must be in [0, 1]")
    return number


def _require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


# ---------------------------------------------------------------------------
# DecisionInput — what a predictor may see (never the answer)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionInput:
    """task / context / candidates only. No selected/gold/outcome/reviewer."""

    task_id: str
    decision_type: str
    context_state: str
    candidates: tuple[Mapping[str, Any], ...]
    contract_version: str = CONTRACT_VERSION

    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(str(c["id"]) for c in self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "task_id": self.task_id,
            "decision_type": self.decision_type,
            "context_state": self.context_state,
            "candidates": [dict(c) for c in self.candidates],
        }


# Label / outcome / reviewer field names that must never appear on input.
FORBIDDEN_INPUT_FIELDS = frozenset({
    "selected_candidate", "gold_selected_candidate", "gold_outcome",
    "label", "label_quality", "review", "reviewer", "reviewed_at",
    "independent_receipt_id", "outcome", "observed_outcome", "reward",
    "expected_evidence", "postcondition_observed",
})


def validate_decision_input(record: Mapping[str, Any]) -> DecisionInput:
    if not isinstance(record, Mapping):
        raise ValueError("DecisionInput must be a mapping")
    require_typed(record, api="validate_decision_input")
    leaked = FORBIDDEN_INPUT_FIELDS.intersection(record.keys())
    if leaked:
        raise ValueError(f"DecisionInput must not carry label fields: {sorted(leaked)}")

    task_id = _require_str(record.get("task_id"), "task_id")
    decision_type = record.get("decision_type")
    if decision_type not in DECISION_TYPES:
        raise ValueError("decision_type must be one of choice, score, noul")
    context_state = record.get("context_state")
    if not isinstance(context_state, str):
        raise ValueError("context_state must be a string")

    raw_candidates = record.get("candidates")
    if not isinstance(raw_candidates, Sequence) or isinstance(raw_candidates, (str, bytes)):
        raise ValueError("candidates must be a list")
    if not raw_candidates:
        raise ValueError("candidates must be non-empty")
    candidates: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("each candidate must be a mapping")
        cid = candidate.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("each candidate needs a non-empty string id")
        if cid in seen:
            raise ValueError(f"duplicate candidate id: {cid}")
        seen.add(cid)
        description = candidate.get("description")
        if not isinstance(description, str):
            raise ValueError(f"candidate {cid} description must be a string")
        action_type = candidate.get("action_type", "")
        if action_type is not None and not isinstance(action_type, str):
            raise ValueError(f"candidate {cid} action_type must be a string")
        candidates.append({
            "id": cid, "description": description, "action_type": action_type or "",
        })
    return DecisionInput(
        task_id=task_id,
        decision_type=decision_type,
        context_state=context_state,
        candidates=tuple(candidates),
    )


def decision_input_from_record(record: Mapping[str, Any]) -> DecisionInput:
    """Build a DecisionInput from a full dataset row by *dropping* label fields.

    Use this at the prediction boundary. Do not pass the raw row to a model.
    """
    require_typed(record, api="decision_input_from_record")
    candidates = []
    for candidate in record.get("candidates", []) or []:
        if isinstance(candidate, Mapping):
            candidates.append({
                "id": candidate.get("id"),
                "description": candidate.get("description", ""),
                "action_type": candidate.get("action_type", ""),
            })
    return validate_decision_input({
        "task_id": record.get("task_id") or record.get("provenance", {}).get("receipt_id") or "unknown-task",
        "decision_type": record.get("decision_type"),
        "context_state": record.get("context_state", ""),
        "candidates": candidates,
    })


# ---------------------------------------------------------------------------
# DecisionPrediction — what a model emits (probabilities ≠ ordinal score)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionPrediction:
    predicted_candidate: str | None
    probabilities: Mapping[str, float] | None   # distribution over candidate ids
    abstain: bool
    abstain_policy: str
    confidence: float                          # model confidence, NOT authority
    # ordinal/utility score is a separate channel and is NOT a probability
    score: float | None = None
    score_kind: str = "none"                   # none | ordinal | utility
    contract_version: str = CONTRACT_VERSION


def validate_decision_prediction(
    raw: Mapping[str, Any],
    *,
    allowed_ids: Sequence[str] | None = None,
) -> DecisionPrediction:
    if not isinstance(raw, Mapping):
        raise ValueError("DecisionPrediction must be a mapping")
    predicted = raw.get("predicted_candidate")
    if predicted is not None and (not isinstance(predicted, str) or not predicted.strip()):
        raise ValueError("predicted_candidate must be a non-empty string or null")
    if allowed_ids is not None and predicted is not None and predicted not in set(allowed_ids):
        raise ValueError(f"predicted_candidate not in candidate set: {predicted}")

    probs_raw = raw.get("probabilities")
    probabilities: dict[str, float] | None = None
    if probs_raw is not None:
        if not isinstance(probs_raw, Mapping):
            raise ValueError("probabilities must be a mapping of id -> number")
        probabilities = {}
        for key, value in probs_raw.items():
            if not isinstance(key, str):
                raise ValueError("probability keys must be candidate ids")
            probabilities[key] = _finite_unit(value, f"probabilities[{key}]")
        if allowed_ids is not None and set(probabilities) - set(allowed_ids):
            raise ValueError("probability keys must be candidate ids in the set")
        total = sum(probabilities.values())
        if probabilities and abs(total - 1.0) > 1e-3:
            raise ValueError(f"probabilities must sum to 1 (got {total})")

    abstain = raw.get("abstain", False)
    if not isinstance(abstain, bool):
        raise ValueError("abstain must be a bool")
    policy = raw.get("abstain_policy", "none")
    if policy not in ABSTAIN_POLICIES:
        raise ValueError(f"abstain_policy must be one of {sorted(ABSTAIN_POLICIES)}")
    if abstain and predicted is not None:
        raise ValueError("abstain prediction must not also name predicted_candidate")

    confidence = _finite_unit(raw.get("confidence", 0.0), "confidence")

    score = raw.get("score")
    score_kind = raw.get("score_kind", "none")
    if score is None:
        score_kind = "none"
    else:
        if not _is_number(score):
            raise ValueError("score must be a number (ordinal/utility), not a probability alias")
        score = float(score)
        if score_kind not in ("ordinal", "utility"):
            raise ValueError("score_kind must be ordinal or utility when score is set")
        # C02: score is not a probability — reject the conflated 0..1 "probability score"
        if raw.get("score_is_probability"):
            raise ValueError("score is ordinal/utility; do not label it a probability")

    return DecisionPrediction(
        predicted_candidate=predicted,
        probabilities=probabilities,
        abstain=abstain,
        abstain_policy=policy if abstain or policy != "none" else "none",
        confidence=confidence,
        score=score,
        score_kind=score_kind,
    )


# ---------------------------------------------------------------------------
# DecisionLabel — reviewed truth (scoring only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionLabel:
    gold_selected_candidate: str | None
    gold_outcome: str
    outcome_known: bool
    reviewer: str
    reviewed_at: str
    independent_receipt_id: str
    label_quality: str
    allowed_outcome: str | None = None        # pre-registered expected outcome, not observed
    postcondition_expected: str | None = None
    contract_version: str = CONTRACT_VERSION


def validate_decision_label(record: Mapping[str, Any]) -> DecisionLabel:
    require_typed(record, api="validate_decision_label")
    review = record.get("review") if isinstance(record.get("review"), Mapping) else record
    if not isinstance(review, Mapping):
        raise ValueError("DecisionLabel must be a mapping or record.review mapping")

    gold = review.get("gold_selected_candidate")
    if gold is not None and (not isinstance(gold, str) or not gold.strip()):
        raise ValueError("gold_selected_candidate must be a non-empty string or null")

    outcome = review.get("gold_outcome", "unknown")
    if not isinstance(outcome, str):
        raise ValueError("gold_outcome must be a string")
    outcome = outcome.strip().lower()
    if outcome not in OUTCOMES:
        raise ValueError(f"gold_outcome must be one of {sorted(OUTCOMES)}")
    outcome_known = outcome != "unknown"

    reviewer = _require_str(review.get("reviewer"), "reviewer")
    reviewed_at = _require_str(review.get("reviewed_at"), "reviewed_at")
    receipt_id = _require_str(review.get("independent_receipt_id"), "independent_receipt_id")
    if not RECEIPT_ID_RE.match(receipt_id):
        raise ValueError(f"independent_receipt_id has invalid format: {receipt_id}")

    quality = review.get("label_quality", "independently_reviewed")
    if quality not in ("independently_reviewed", "unverified", "oracle_confirmed"):
        raise ValueError("label_quality must be independently_reviewed | unverified | oracle_confirmed")

    allowed = review.get("allowed_outcome")
    if allowed is not None and allowed not in OUTCOMES:
        raise ValueError("allowed_outcome must be in OUTCOMES when set")
    post = review.get("postcondition_expected")
    if post is not None and not isinstance(post, str):
        raise ValueError("postcondition_expected must be a string or null")

    return DecisionLabel(
        gold_selected_candidate=gold,
        gold_outcome=outcome,
        outcome_known=outcome_known,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        independent_receipt_id=receipt_id,
        label_quality=quality,
        allowed_outcome=allowed,
        postcondition_expected=post,
    )


# ---------------------------------------------------------------------------
# Authority — independent of model confidence (C02)
# ---------------------------------------------------------------------------

DANGEROUS_ACTION_STEMS = frozenset({
    "delete", "wipe", "kill", "format", "drop", "trade_buy", "trade_sell",
    "transfer", "execute", "exec", "send", "publish", "force", "override",
})


@dataclass(frozen=True)
class AuthorityVerdict:
    allowed: bool
    reason: str
    requires_approval: bool
    checks: Mapping[str, bool] = field(default_factory=dict)


def check_authority(
    decision_input: DecisionInput,
    *,
    approved_task_ids: Sequence[str] = (),
    allowed_action_types: Sequence[str] = (),
    preconditions_met: Mapping[str, bool] | None = None,
    prediction: DecisionPrediction | None = None,
) -> AuthorityVerdict:
    """Authority gate. Model confidence is intentionally not consulted."""
    checks: dict[str, bool] = {}
    chosen_id = prediction.predicted_candidate if prediction else None
    chosen = next((c for c in decision_input.candidates if c["id"] == chosen_id), None)
    action = str((chosen or {}).get("action_type", "")).lower()
    dangerous = any(stem in action for stem in DANGEROUS_ACTION_STEMS)

    checks["task_allowlisted"] = decision_input.task_id in set(approved_task_ids) if approved_task_ids else not dangerous
    if allowed_action_types:
        checks["action_allowlisted"] = action in set(allowed_action_types)
    if preconditions_met:
        checks["preconditions_met"] = all(bool(v) for v in preconditions_met.values())
    if dangerous:
        checks["dangerous_requires_approval"] = decision_input.task_id in set(approved_task_ids)

    if not all(checks.values()):
        return AuthorityVerdict(
            allowed=False,
            reason="authority_check_failed:" + ",".join(k for k, v in checks.items() if not v),
            requires_approval=dangerous,
            checks=checks,
        )
    return AuthorityVerdict(allowed=True, reason="ok", requires_approval=dangerous, checks=checks)


# ---------------------------------------------------------------------------
# Receipt linkage — self-declared IDs are not enough (C02)
# ---------------------------------------------------------------------------


def verify_receipt_linkage(
    label: DecisionLabel,
    *,
    known_receipts: Mapping[str, Mapping[str, Any]],
    task_id: str | None = None,
    expect_hash: str | None = None,
    expect_producer: str | None = None,
) -> bool:
    """True only when the receipt exists and links to this task/hash/producer."""
    receipt = known_receipts.get(label.independent_receipt_id)
    if not isinstance(receipt, Mapping):
        return False
    if expect_hash and receipt.get("payload_sha256") != expect_hash:
        return False
    if expect_producer and receipt.get("producer") != expect_producer:
        return False
    if task_id is not None and receipt.get("task_id") not in (None, task_id):
        return False
    linked = receipt.get("task_id") or receipt.get("payload_sha256") or receipt.get("producer")
    return bool(linked)


def dumps_canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
