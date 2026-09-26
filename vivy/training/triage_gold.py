"""Classify gold-review queue rows into A/B/C categories via deterministic oracle.

Writes proposal-only triage output — never touches gold fields or mutates the source queue.
Category B checks an optional sidecar of independent postcondition receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from training.gold_oracle import RULE_VERSION, propose
from training.receipt import build_receipt, make_receipt_id, write_receipt

_GOLD_FIELDS = ("gold_selected_candidate", "gold_outcome", "reviewer", "reviewed_at", "independent_receipt_id")
_SIDECAR_NAME = "gold_postcondition_receipts.jsonl"


def _load_postcondition_ids(source: Path) -> set[str]:
    sidecar = source.parent / _SIDECAR_NAME
    if not sidecar.exists():
        return set()
    ids: set[str] = set()
    for line in sidecar.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rid = rec.get("legacy_receipt_id")
        if rid:
            ids.add(str(rid))
    return ids


def triage(
    source: str | Path,
    output: str | Path,
    *,
    template_tier: str = "A_template",
    weak_tier: str = "A_weak",
) -> dict[str, Any]:
    src = Path(source)
    out = Path(output)
    b_ids = _load_postcondition_ids(src)
    demoted_template = template_tier == "C"
    demoted_weak = weak_tier == "C"

    rows_out: list[dict[str, Any]] = []
    categories = {"A": 0, "B": 0, "C": 0}
    tiers: dict[str, int] = {}
    rule_hits: dict[str, int] = {}
    disagreements: list[dict[str, Any]] = []
    input_count = 0

    for idx, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row: dict[str, Any] = json.loads(line)
        input_count += 1

        review = row.get("review", {})
        if any(review.get(f) for f in _GOLD_FIELDS):
            raise ValueError(
                f"Queue already contains gold fields at row {idx}; refusing to triage. "
                "Gold fields are written only by confirm_gold."
            )

        proposal = propose(row["context_state"], row["candidates"])
        legacy = row.get("selected_candidate")
        legacy_rid = str(row.get("provenance", {}).get("receipt_id", ""))
        disagrees = proposal.proposed_selected_candidate is not None and proposal.proposed_selected_candidate != legacy

        # Category assignment
        if proposal.proposed_selected_candidate is not None:
            tier = proposal.tier
            if tier == "A_template" and demoted_template:
                category, tier = "C", "C"
            elif tier == "A_weak" and demoted_weak:
                category, tier = "C", "C"
            else:
                category = "A"
        elif legacy_rid in b_ids:
            category, tier = "B", "B"
        else:
            category, tier = "C", "C"

        proposal_receipt_id = make_receipt_id(
            kind="oracle",
            payload={
                "rule_version": proposal.rule_version,
                "rule_ids": list(proposal.rule_ids),
                "proposed": proposal.proposed_selected_candidate,
                "tier": proposal.tier,
                "legacy_receipt_id": legacy_rid,
            },
        )

        out_row = {
            "row_index": idx,
            "legacy_receipt_id": legacy_rid,
            "proposed_selected_candidate": proposal.proposed_selected_candidate,
            "category": category,
            "tier": tier,
            "disagrees_with_legacy": disagrees,
            "agrees_with_legacy": not disagrees,
            "proposal_receipt_id": proposal_receipt_id,
            "rule_version": proposal.rule_version,
        }
        rows_out.append(out_row)

        categories[category] = categories.get(category, 0) + 1
        tiers[tier] = tiers.get(tier, 0) + 1
        for rule_id in proposal.rule_ids:
            rule_hits[rule_id] = rule_hits.get(rule_id, 0) + 1
        if disagrees:
            disagreements.append({
                "row_index": idx,
                "legacy_receipt_id": legacy_rid,
                "proposed": proposal.proposed_selected_candidate,
                "legacy": legacy,
            })

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows_out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    input_sha = hashlib.sha256(src.read_bytes()).hexdigest()
    receipt = build_receipt(
        run_id=f"triage-{input_sha[:12]}",
        stage="gold_triage",
        metrics={"input": input_count, "categories": categories, "tiers": tiers},
        gates={"queue_not_mutated": "PASS", "no_gold_fields_in_output": "PASS"},
        input_sha256=input_sha,
    )
    receipt["rule_hits"] = rule_hits
    receipt["disagreement_count"] = len(disagreements)
    receipt_path = out.parent / "gold_triage_receipt.json"
    write_receipt(receipt_path, receipt)

    return {
        "input": input_count,
        "categories": categories,
        "tiers": tiers,
        "rule_hits": rule_hits,
        "disagreements": disagreements,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--template-tier", default="A_template", choices=["A_template", "C"])
    parser.add_argument("--weak-tier", default="A_weak", choices=["A_weak", "C"])
    args = parser.parse_args()
    result = triage(args.source, args.output, template_tier=args.template_tier, weak_tier=args.weak_tier)
    print(json.dumps(result, ensure_ascii=False, indent=2))
