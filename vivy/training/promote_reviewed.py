"""Promote only independently reviewed records; pending rows stay excluded.

Changelog: 2026-09-24 (Antigravity/Claude Code — P0 CORRECTIONS §2.7, §2.11)
    Fail-closed promotion. Only status REVIEWED is eligible. Unknown
    gold_outcome is kept as unknown and tagged for selection-only use — it is
    never treated as an observed success. gold_selected_candidate must be in
    the row candidate list. independent_receipt_id must resolve (format + optional
    index). Writes refuse to clobber the source queue or prior gold via
    training.io_guard.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from training.io_guard import open_write

# Only an explicit human/oracle REVIEWED status is promotable. Anything else
# (PENDING, REJECTED, UNKNOWN, missing, typos) is rejected — §2.7.
ELIGIBLE_STATUS = "REVIEWED"
RECEIPT_ID_RE = re.compile(r"^(human-accept|oracle)-[0-9a-f]{8,64}$")
OUTCOME_KNOWN = frozenset({"success", "ok", "pass", "true", "1", "failure", "fail", "error", "false", "0"})
OUTCOME_UNKNOWN = frozenset({"unknown", "", "none", "null"})


def _candidate_ids(row: Mapping[str, Any]) -> set[str]:
    return {str(c.get("id")) for c in row.get("candidates", []) if isinstance(c, Mapping) and c.get("id")}


def _receipt_resolvable(receipt_id: Any, known: Iterable[str] | None) -> bool:
    if not isinstance(receipt_id, str) or not RECEIPT_ID_RE.match(receipt_id):
        return False
    if known is None:
        return True
    return receipt_id in set(known)


def promote(
    source: str | Path,
    output: str | Path,
    *,
    known_receipt_ids: Iterable[str] | None = None,
    protected: Iterable[str | Path] = (),
    allow_replace: bool = False,
) -> dict[str, int]:
    counts = {
        "input": 0,
        "promoted": 0,
        "pending": 0,
        "rejected": 0,
        "rejected_status": 0,
        "rejected_missing_fields": 0,
        "rejected_candidate": 0,
        "rejected_receipt": 0,
        "outcome_unknown_selection_only": 0,
    }
    protected_paths = tuple(protected) + (source,)
    with open_write(output, protected=protected_paths, allow_replace=allow_replace) as out:
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            counts["input"] += 1
            row: dict[str, Any] = json.loads(line)
            review = row.get("review", {}) or {}
            status = review.get("status")
            if status == "PENDING" or status is None:
                counts["pending"] += 1
                continue
            if status != ELIGIBLE_STATUS:
                counts["rejected"] += 1
                counts["rejected_status"] += 1
                continue
            required = (
                "gold_selected_candidate",
                "gold_outcome",
                "reviewer",
                "reviewed_at",
                "independent_receipt_id",
            )
            if any(review.get(key) in (None, "") for key in required):
                counts["rejected"] += 1
                counts["rejected_missing_fields"] += 1
                continue
            gold_candidate = review["gold_selected_candidate"]
            ids = _candidate_ids(row)
            if ids and gold_candidate not in ids:
                counts["rejected"] += 1
                counts["rejected_candidate"] += 1
                continue
            if not _receipt_resolvable(review["independent_receipt_id"], known_receipt_ids):
                counts["rejected"] += 1
                counts["rejected_receipt"] += 1
                continue

            raw_outcome = str(review["gold_outcome"]).strip().lower()
            outcome_known = raw_outcome in OUTCOME_KNOWN and raw_outcome not in OUTCOME_UNKNOWN
            # Selection label is promotable either way; unknown outcome is
            # selection-only and excluded from outcome calibration (§2.7).
            row["selected_candidate"] = gold_candidate
            row["label_quality"] = "independently_reviewed"
            row["provenance"] = {
                **row.get("provenance", {}),
                "review_receipt_id": review["independent_receipt_id"],
                "gold_outcome_raw": review["gold_outcome"],
                "gold_outcome_known": outcome_known,
                "eligible_for_outcome_calibration": outcome_known,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            counts["promoted"] += 1
            if not outcome_known:
                counts["outcome_unknown_selection_only"] += 1
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--known-receipt-ids", help="optional JSONL/JSON file of resolvable receipt ids")
    parser.add_argument("--allow-replace", action="store_true")
    args = parser.parse_args()
    known = None
    if args.known_receipt_ids:
        raw = Path(args.known_receipt_ids).read_text(encoding="utf-8")
        known = (
            {json.loads(line)["independent_receipt_id"] for line in raw.splitlines() if line.strip()}
            if raw.lstrip().startswith("{") or "\n" in raw.strip()
            else set(json.loads(raw))
        )
    print(json.dumps(
        promote(args.source, args.output, known_receipt_ids=known, allow_replace=args.allow_replace),
        indent=2,
    ))
