"""C03 live audit — read-only report over legacy + typed datasets.

Does not rewrite any dataset. Prints JSON for the P2 packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from training.dataset_audit import audit_file, audit_rows
from training.legacy_to_typed import migrate


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", default="vivy_train_dataset.jsonl")
    parser.add_argument("--typed-out", default="evidence/c03_typed_migration.jsonl")
    parser.add_argument("--manifest-out", default="evidence/c03_split_manifest.json")
    parser.add_argument("--report-out", default="evidence/c03_dataset_audit.json")
    args = parser.parse_args()

    legacy = Path(args.legacy)
    legacy_hash = sha256_file(legacy)

    # migrate() is a pure reader over the legacy file
    migrated = list(migrate(legacy, extracted_at="2026-09-24T00:00:00+00:00"))
    typed_report = audit_rows(migrated)

    # raw ChatML audit (source-shape: messages/reward/source only)
    raw_rows = [
        json.loads(line)
        for line in legacy.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # C03: account for every skipped source row — never a silent drop.
    skip_counts = {"no_marker": 0, "no_candidates": 0, "no_selected_or_unknown_id": 0, "parse_error": 0}
    for row in raw_rows:
        messages = row.get("messages") or []
        user = str(messages[1].get("content", "")) if len(messages) > 1 else ""
        assistant = str(messages[2].get("content", "")) if len(messages) > 2 else ""
        if "Bounded Candidate Table:" not in user:
            skip_counts["no_marker"] += 1
            continue
        table = user.split("Bounded Candidate Table:", 1)[1].split("Select the safest", 1)[0]
        import re as _re
        cids = [m.group(1) for m in _re.finditer(r"\[([^\]]+)\]", table)]
        if not cids:
            skip_counts["no_candidates"] += 1
            continue
        sel = _re.search(r"Selected_Candidate_ID:\s*([^\s\r\n]+)", assistant, _re.I)
        if not sel or sel.group(1) not in set(cids):
            skip_counts["no_selected_or_unknown_id"] += 1
            continue
    skip_counts["parsed"] = len(migrated)
    raw_report = audit_rows([
        {
            "context_state": (row.get("messages") or [{}])[-2].get("content", "") if len(row.get("messages", [])) >= 3 else "",
            "candidates": [],
            "selected_candidate": None,
            "gold_outcome": "unknown",
            "split": "unsplit",
            "provenance": {},
        }
        for row in raw_rows
    ])

    split_counts = typed_report.split_counts
    group_count = typed_report.n_unique_groups
    manifest = {
        "extraction_version": "legacy_to_typed.v2.c03-multiline-group-split",
        "source_file": str(legacy),
        "source_file_sha256": legacy_hash,
        "n_migrated_rows": len(migrated),
        "split_counts": split_counts,
        "n_unique_groups": group_count,
        "group_keys": sorted(typed_report.group_split.keys()),
        "group_cross_split": typed_report.group_cross_split,
        "near_duplicate_cross_split": typed_report.near_duplicate_cross_split,
        "notes": [
            "split is a function of provenance.group_key (session/task/template family), never index % 10",
            "same group_key implies identical split by construction",
        ],
    }

    evidence_line_counts = [r.get("evidence_required_line_count", 0) for r in migrated]
    multiline_rows = sum(1 for n in evidence_line_counts if n and n > 1)
    single_line_rows = sum(1 for n in evidence_line_counts if n == 1)
    zero_evidence_rows = sum(1 for n in evidence_line_counts if n == 0)

    report = {
        "component": "C03",
        "raw_chatml": {
            "n_rows": len(raw_rows),
            "keys_present": sorted({k for row in raw_rows[:20] for k in row}),
            "sha256": legacy_hash,
            "skip_counts": skip_counts,
            "note": "raw ChatML has messages/reward/source only — no typed provenance until migrate",
        },
        "typed_migration": typed_report.to_dict(),
        "evidence_extraction": {
            "multiline_rows": multiline_rows,
            "single_line_rows": single_line_rows,
            "zero_evidence_rows": zero_evidence_rows,
            "total_evidence_lines": sum(evidence_line_counts),
        },
        "confidence_policy": "migration_placeholder_not_measured — never a measured probability",
        "outcome_policy": "gold_outcome=unknown for every migrated row; no capture store exists for legacy CUA",
        "selection_eligibility_is_not_outcome_eligibility": True,
    }

    Path(args.manifest_out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.report_out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # write migrated rows through io_guard so we cannot clobber the legacy input
    from training.io_guard import open_write

    out_path = Path(args.typed_out)
    with open_write(out_path, protected=(legacy,), allow_replace=True) as handle:
        for row in migrated:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({
        "legacy_sha256": legacy_hash,
        "n_migrated": len(migrated),
        "skip_counts": skip_counts,
        "split_counts": split_counts,
        "n_unique_groups": group_count,
        "group_cross_split": typed_report.group_cross_split,
        "near_duplicate_cross_split": len(typed_report.near_duplicate_cross_split),
        "evidence": report["evidence_extraction"],
        "typed_out": str(out_path),
        "manifest_out": args.manifest_out,
        "report_out": args.report_out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
