"""Typed-decision metrics track (Laya / Verdict 2.0) on human-confirmed gold.

Scores what is honestly measurable on selection labels: schema validity,
independence/provenance, order-stability under candidate permutation, and
descriptive agreement with an independent proposer.

Outcome metrics (Brier / ECE on action success) require `gold_outcome`. While
every gold row carries `unknown`, those fields stay `None` and report
UNVERIFIED — this module never invents an outcome and never writes the gold
file.

The shadow router copies `selected_candidate` on independently reviewed rows,
so agreement with it is a tautology on this set and is not scored here.

Cấm: full SFT / LoRA training on the legacy rows. This module scores decisions;
it does not train. Claim ceiling is PROVISIONAL_RESULT — selection labels only.

Changelog:
    23/09/2026 (Claude Code — P6 typed-decision metrics): Initial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import log
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from training import gold_oracle
from training.perturbation import order_flip_rate, permute_candidates
from training.typed_decision import validate_typed_decision

METRICS_STATUS_LABEL = "PROVISIONAL_RESULT"
GATE10_STATUS = "UNVERIFIED"
ORACLE_AGREEMENT_STATUS = "DESCRIPTIVE_ONLY"
SHADOW_ROUTER_NOTE = "CIRCULAR_ON_INDEPENDENTLY_REVIEWED"

_SUCCESS_OUTCOMES = frozenset({"success", "ok", "pass", "1", "true"})
_FAILURE_OUTCOMES = frozenset({"failure", "fail", "error", "0", "false"})
_UNKNOWN_OUTCOMES = frozenset({"unknown", "", "none", "null"})


@dataclass(frozen=True)
class TypedDecisionMetricsReceipt:
    status_label: str
    gate10_status: str
    generated_at: str
    gold_path: str
    input_sha256: str
    policy: str
    permutation_seeds: int
    metrics: Mapping[str, Any]


def selection_brier(dist: Mapping[str, float], gold_id: str | None) -> float:
    """Mean multi-class Brier score of `dist` against a one-hot at `gold_id`.

    Range [0, 2] over the union of keys and the gold id; 0 when the
    distribution is a one-hot on the gold id.
    """
    keys = list(dict.fromkeys(list(dist.keys()) + ([] if gold_id is None else [gold_id])))
    if not keys:
        return 0.0
    total = 0.0
    for key in keys:
        p = float(dist.get(key, 0.0))
        y = 1.0 if (gold_id is not None and key == gold_id) else 0.0
        total += (p - y) ** 2
    return total / len(keys)


def permutation_kl(original: str | None, predictions: Sequence[str | None]) -> float:
    """KL(empirical_predictions || one_hot(original)) with light smoothing.

    Exactly 0.0 when every prediction equals the original selection (stable
    under permutation). Once any prediction diverges, P is a smoothed one-hot
    so the score stays finite. `None` is its own label.
    """
    preds = list(predictions)
    if not preds:
        return 0.0
    if all(pred == original for pred in preds):
        return 0.0
    labels = list(dict.fromkeys([original, *preds]))
    n = len(preds)
    eps = 1e-6
    share = eps / max(1, len(labels) - 1) if len(labels) > 1 else eps
    counts: dict[str | None, int] = {}
    for pred in preds:
        counts[pred] = counts.get(pred, 0) + 1
    kl = 0.0
    for label in labels:
        q = counts.get(label, 0) / n
        if q <= 0.0:
            continue
        p = (1.0 - eps) if label == original else share
        if p <= 0.0:
            p = eps
        kl += q * log(q / p)
    return max(0.0, kl)


def _oracle_pick(record: Mapping[str, Any]) -> str | None:
    proposal = gold_oracle.propose(
        str(record.get("context_state", "")),
        list(record.get("candidates") or []),
    )
    return proposal.proposed_selected_candidate


def _first_candidate_pick(record: Mapping[str, Any]) -> str | None:
    candidates = list(record.get("candidates") or [])
    if not candidates:
        return None
    cid = candidates[0].get("id")
    return None if cid is None else str(cid)


def _last_candidate_pick(record: Mapping[str, Any]) -> str | None:
    candidates = list(record.get("candidates") or [])
    if not candidates:
        return None
    cid = candidates[-1].get("id")
    return None if cid is None else str(cid)


_POLICIES: dict[str, Callable[[Mapping[str, Any]], str | None]] = {
    "oracle": _oracle_pick,
    "first_candidate": _first_candidate_pick,
    "last_candidate": _last_candidate_pick,
}


def _outcome_label(value: Any) -> float | None:
    """Map a review outcome to 1/0/None. Unrecognized values stay None."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _UNKNOWN_OUTCOMES:
        return None
    if text in _SUCCESS_OUTCOMES:
        return 1.0
    if text in _FAILURE_OUTCOMES:
        return 0.0
    return None


def _expected_calibration_error(pairs: Sequence[tuple[float, float]], n_bins: int = 10) -> float:
    """Standard ECE over (predicted confidence, binary outcome) pairs."""
    if not pairs:
        return 0.0
    bins: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for conf, y in pairs:
        idx = min(n_bins - 1, max(0, int(conf * n_bins)))
        bins[idx].append((conf, y))
    total = len(pairs)
    ece = 0.0
    for bucket in bins:
        if not bucket:
            continue
        mean_conf = sum(c for c, _ in bucket) / len(bucket)
        mean_y = sum(y for _, y in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(mean_conf - mean_y)
    return ece


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_gold(
    gold_path: str | Path,
    *,
    permutation_seeds: int = 5,
    policy: str = "oracle",
) -> TypedDecisionMetricsReceipt:
    """Score human-confirmed gold rows. Never writes `gold_path`."""
    if policy not in _POLICIES:
        raise ValueError(f"policy must be one of {sorted(_POLICIES)}")
    if permutation_seeds < 1:
        raise ValueError("permutation_seeds must be >= 1")

    pick = _POLICIES[policy]
    path = Path(gold_path)
    raw = path.read_bytes()
    input_sha256 = hashlib.sha256(raw).hexdigest()
    rows = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]

    n_rows = len(rows)
    n_schema_valid = 0
    n_independently_reviewed = 0
    n_outcome_known = 0
    n_outcome_unknown = 0
    outcome_pairs: list[tuple[float, float]] = []
    selection_scores: list[float] = []
    oracle_flips: list[float] = []
    oracle_kls: list[float] = []
    policy_flips: list[float] = []
    policy_kls: list[float] = []
    oracle_agree = 0
    oracle_compared = 0
    first_agree = 0
    last_agree = 0
    n_compared = 0

    for row in rows:
        try:
            validate_typed_decision(row)
            n_schema_valid += 1
        except ValueError:
            pass

        if row.get("label_quality") == "independently_reviewed":
            n_independently_reviewed += 1

        review = row.get("review") or {}
        y = _outcome_label(review.get("gold_outcome"))
        if y is None:
            n_outcome_unknown += 1
        else:
            n_outcome_known += 1
            conf = row.get("confidence")
            try:
                conf_f = float(conf) if conf is not None else 0.0
            except (TypeError, ValueError):
                conf_f = 0.0
            outcome_pairs.append((conf_f, y))

        candidates = list(row.get("candidates") or [])
        gold_sel = review.get("gold_selected_candidate")
        if gold_sel is None:
            continue
        if not candidates:
            continue

        n_compared += 1
        ids = [str(c.get("id")) for c in candidates]
        if str(candidates[0].get("id")) == str(gold_sel):
            first_agree += 1
        if str(candidates[-1].get("id")) == str(gold_sel):
            last_agree += 1

        original = pick(row)
        dist = {cid: 0.0 for cid in ids}
        if original is None and ids:
            for cid in ids:
                dist[cid] = 1.0 / len(ids)
        elif original in dist:
            dist[str(original)] = 1.0
        selection_scores.append(selection_brier(dist, str(gold_sel)))

        policy_preds: list[str | None] = []
        oracle_preds: list[str | None] = []
        for seed in range(permutation_seeds):
            permuted = permute_candidates(row, seed)
            policy_preds.append(pick(permuted))
            oracle_preds.append(_oracle_pick(permuted))

        policy_flips.append(order_flip_rate(row, policy_preds, seeds=permutation_seeds))
        policy_kls.append(permutation_kl(original, policy_preds))
        oracle_flips.append(order_flip_rate(row, oracle_preds, seeds=permutation_seeds))
        oracle_kls.append(permutation_kl(_oracle_pick(row), oracle_preds))

        oracle_proposal = _oracle_pick(row)
        oracle_compared += 1
        if oracle_proposal == str(gold_sel):
            oracle_agree += 1

    if n_outcome_known == 0:
        outcome_brier: float | None = None
        ece: float | None = None
        outcome_brier_status = "UNVERIFIED"
        ece_status = "UNVERIFIED"
    else:
        outcome_brier = _mean([(p - y) ** 2 for p, y in outcome_pairs])
        ece = _expected_calibration_error(outcome_pairs)
        outcome_brier_status = "MEASURED"
        ece_status = "MEASURED"

    metrics: dict[str, Any] = {
        "n_rows": n_rows,
        "n_schema_valid": n_schema_valid,
        "schema_valid_rate": (n_schema_valid / n_rows) if n_rows else 0.0,
        "n_independently_reviewed": n_independently_reviewed,
        "n_outcome_known": n_outcome_known,
        "n_outcome_unknown": n_outcome_unknown,
        "outcome_brier": outcome_brier,
        "outcome_brier_status": outcome_brier_status,
        "ece": ece,
        "ece_status": ece_status,
        "selection_brier_mean": _mean(selection_scores),
        "oracle_agreement_rate": (oracle_agree / oracle_compared) if oracle_compared else 0.0,
        "oracle_agreement_status": ORACLE_AGREEMENT_STATUS,
        "shadow_router_note": SHADOW_ROUTER_NOTE,
        "oracle_permutation_flip_rate": _mean(oracle_flips),
        "oracle_permutation_kl": _mean(oracle_kls),
        "policy_permutation_flip_rate": _mean(policy_flips),
        "policy_permutation_kl": _mean(policy_kls),
        "first_candidate_agreement": (first_agree / n_compared) if n_compared else 0.0,
        "last_candidate_agreement": (last_agree / n_compared) if n_compared else 0.0,
        "sft_lora_executed": False,
    }

    return TypedDecisionMetricsReceipt(
        status_label=METRICS_STATUS_LABEL,
        gate10_status=GATE10_STATUS,
        generated_at=datetime.now(timezone.utc).isoformat(),
        gold_path=str(path),
        input_sha256=input_sha256,
        policy=policy,
        permutation_seeds=permutation_seeds,
        metrics=metrics,
    )


def write_receipt(
    receipt: TypedDecisionMetricsReceipt,
    path: str | Path,
    *,
    allow_replace: bool = False,
) -> str:
    from training.io_guard import open_write

    payload = asdict(receipt)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with open_write(path, protected=(receipt.gold_path,), allow_replace=allow_replace) as handle:
        handle.write(text)
    return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Typed-decision metrics on gold rows")
    parser.add_argument(
        "gold",
        nargs="?",
        default=str(Path("evidence") / "gold_train.jsonl"),
    )
    parser.add_argument(
        "--output",
        default=str(Path("evidence") / "TYPED_DECISION_METRICS_RECEIPT.json"),
    )
    parser.add_argument("--permutation-seeds", type=int, default=5)
    parser.add_argument("--policy", default="oracle", choices=sorted(_POLICIES))
    args = parser.parse_args(argv)
    receipt = evaluate_gold(
        args.gold,
        permutation_seeds=args.permutation_seeds,
        policy=args.policy,
    )
    write_receipt(receipt, args.output)
    print(json.dumps(asdict(receipt), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
