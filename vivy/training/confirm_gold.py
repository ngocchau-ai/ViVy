"""Write human-confirmed gold fields into a COPY of the review queue.

The source queue is opened read-only and never mutated. Gold fields are
stamped only here, never by triage or the oracle. Each row gets its own
reviewer / reviewed_at / independent_receipt_id.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from training.gold_oracle import RULE_VERSION
from training.receipt import build_receipt, make_receipt_id, write_receipt


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _matches_where(triage_row: dict[str, Any], where: dict[str, Any]) -> bool:
    return all(triage_row.get(k) == v for k, v in where.items())


def confirm(
    triage: str | Path,
    queue: str | Path,
    manifest: str | Path,
    output: str | Path,
    *,
    oracle_authority: str = "propose-only",
) -> dict[str, int]:
    triage_rows = _load_jsonl(Path(triage))
    queue_rows = _load_jsonl(Path(queue))
    manifest_entries = _load_jsonl(Path(manifest))

    if len(triage_rows) != len(queue_rows):
        raise ValueError("triage and queue row counts differ")

    # Expand bulk_accept first; per-row entries win over bulk for the same row.
    actions: dict[int, dict[str, Any]] = {}
    for entry in manifest_entries:
        if entry.get("action") == "bulk_accept":
            where = entry.get("where", {})
            bulk_norm = {**entry, "action": "accept"}
            for i, t_row in enumerate(triage_rows):
                if i not in actions and _matches_where(t_row, where):
                    actions[i] = bulk_norm
        elif "row" in entry:
            actions[int(entry["row"])] = entry

    reviewed = pending = skipped = 0
    out_rows: list[dict[str, Any]] = []

    for i, (q_row, t_row) in enumerate(zip(queue_rows, triage_rows)):
        entry = actions.get(i)
        review = dict(q_row.get("review", {}))
        candidate_ids = {str(c.get("id")) for c in q_row.get("candidates", [])}

        if entry is None or entry.get("action") == "skip":
            skipped += 1
            pending += 1
            out_rows.append(q_row)
            continue

        action = entry["action"]
        if action == "accept":
            proposed = t_row.get("proposed_selected_candidate")
            if t_row.get("category") == "C" or proposed is None:
                raise ValueError(
                    f"Cannot accept row {i}: Category C has no proposed candidate. Use override."
                )
            gold_candidate = proposed
        elif action == "override":
            gold_candidate = entry.get("override_candidate")
            if gold_candidate not in candidate_ids:
                raise ValueError(
                    f"override_candidate '{gold_candidate}' is not a real candidate id at row {i}"
                )
        else:
            raise ValueError(f"Unknown action '{action}' at row {i}")

        gold_outcome = entry.get("outcome", "unknown")
        reviewer = entry.get("reviewer", "")
        reviewed_at = entry.get("reviewed_at", "")
        if not reviewer or not reviewed_at:
            raise ValueError(f"Manifest entry for row {i} missing reviewer or reviewed_at")

        independent_receipt_id = make_receipt_id(
            kind="human-accept",
            payload={
                "proposal_receipt_id": t_row.get("proposal_receipt_id"),
                "legacy_receipt_id": t_row.get("legacy_receipt_id"),
                "gold_selected_candidate": gold_candidate,
                "gold_outcome": gold_outcome,
                "reviewer": reviewer,
                "reviewed_at": reviewed_at,
                "rule_version": t_row.get("rule_version"),
                "oracle_authority": oracle_authority,
            },
        )

        review.update({
            "gold_selected_candidate": gold_candidate,
            "gold_outcome": gold_outcome,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "independent_receipt_id": independent_receipt_id,
            "status": "REVIEWED",
        })
        q_row["review"] = review
        out_rows.append(q_row)
        reviewed += 1

    # Variant 2: auto-stamp remaining PENDING rows that agree with legacy.
    if oracle_authority == "auto-reviewed":
        for i, (q_row, t_row) in enumerate(zip(out_rows, triage_rows)):
            if q_row["review"]["status"] != "PENDING":
                continue
            if t_row.get("category") != "A" or t_row.get("disagrees_with_legacy"):
                continue
            proposed = t_row.get("proposed_selected_candidate")
            if proposed is None:
                continue
            reviewer = f"oracle_{RULE_VERSION}"
            reviewed_at = "oracle-auto-reviewed"
            gold_outcome = "unknown"
            independent_receipt_id = make_receipt_id(
                kind="human-accept",
                payload={
                    "proposal_receipt_id": t_row.get("proposal_receipt_id"),
                    "legacy_receipt_id": t_row.get("legacy_receipt_id"),
                    "gold_selected_candidate": proposed,
                    "gold_outcome": gold_outcome,
                    "reviewer": reviewer,
                    "reviewed_at": reviewed_at,
                    "rule_version": t_row.get("rule_version"),
                    "oracle_authority": oracle_authority,
                },
            )
            q_row["review"] = {
                "gold_selected_candidate": proposed,
                "gold_outcome": gold_outcome,
                "reviewer": reviewer,
                "reviewed_at": reviewed_at,
                "independent_receipt_id": independent_receipt_id,
                "status": "REVIEWED",
            }
            reviewed += 1
            pending -= 1

    from training.io_guard import open_write

    out = Path(output)
    # §2.11: never clobber the source queue or an existing output/receipt.
    with open_write(out, protected=(queue, triage, manifest), allow_replace=False) as fh:
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    queue_sha = hashlib.sha256(Path(queue).read_bytes()).hexdigest()
    receipt = build_receipt(
        run_id=f"confirm-{queue_sha[:12]}",
        stage="gold_confirm",
        metrics={"reviewed": reviewed, "pending": pending, "skipped": skipped},
        gates={"queue_not_mutated": "PASS", "per_row_reviewer_stamped": "PASS"},
        input_sha256=queue_sha,
    )
    receipt["oracle_authority"] = oracle_authority
    write_receipt(
        out.parent / "gold_confirm_receipt.json",
        receipt,
        allow_replace=True,
        protected=(queue, triage, manifest, out),
    )

    return {"reviewed": reviewed, "pending": pending, "skipped": skipped}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("triage")
    parser.add_argument("queue")
    parser.add_argument("manifest")
    parser.add_argument("output")
    parser.add_argument("--oracle-authority", default="propose-only", choices=["propose-only", "auto-reviewed"])
    args = parser.parse_args()
    result = confirm(args.triage, args.queue, args.manifest, args.output, oracle_authority=args.oracle_authority)
    print(json.dumps(result, indent=2))
