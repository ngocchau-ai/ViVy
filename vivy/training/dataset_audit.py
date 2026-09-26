"""C03 dataset audit — group-split leakage, near-duplicates, provenance completeness.

Read-only. Does not rewrite datasets and does not invent labels/outcomes.

Changelog:
    24/09/2026 (Claude Code — P2 C03): Initial.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


@dataclass
class AuditReport:
    n_rows: int = 0
    n_with_provenance: int = 0
    n_missing_provenance: int = 0
    n_selection_labels: int = 0
    n_outcome_known: int = 0
    n_outcome_unknown: int = 0
    n_template_family: int = 0
    n_unique_groups: int = 0
    group_split: dict[str, str] = field(default_factory=dict)
    split_counts: dict[str, int] = field(default_factory=dict)
    group_cross_split: list[str] = field(default_factory=list)
    near_duplicate_cross_split: list[dict[str, Any]] = field(default_factory=list)
    fixture_suspects: list[str] = field(default_factory=list)
    missing_evidence_multiline_truncation: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_rows": self.n_rows,
            "n_with_provenance": self.n_with_provenance,
            "n_missing_provenance": self.n_missing_provenance,
            "n_selection_labels": self.n_selection_labels,
            "n_outcome_known": self.n_outcome_known,
            "n_outcome_unknown": self.n_outcome_unknown,
            "n_template_family": self.n_template_family,
            "n_unique_groups": self.n_unique_groups,
            "split_counts": self.split_counts,
            "group_cross_split": self.group_cross_split,
            "near_duplicate_cross_split": self.near_duplicate_cross_split,
            "fixture_suspects": self.fixture_suspects,
            "notes": self.notes,
        }


_TEMPLATE = re.compile(r"execute automated bounded workspace task", re.I)


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "N", (text or "").lower())).strip()


def fingerprint(row: Mapping[str, Any]) -> str:
    context = _norm_text(str(row.get("context_state", "")))
    cands = ",".join(sorted(str(c.get("id", "")) for c in row.get("candidates", []) or []))
    return hashlib.sha256(f"{context}|{cands}".encode("utf-8")).hexdigest()[:16]


def audit_rows(rows: Sequence[Mapping[str, Any]], *, near_dup_threshold: int = 8) -> AuditReport:
    report = AuditReport()
    report.n_rows = len(rows)
    groups: dict[str, set[str]] = defaultdict(set)
    fingerprints: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for index, row in enumerate(rows):
        report.n_rows = index + 1
        provenance = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
        if provenance.get("receipt_id") and provenance.get("source_file_sha256"):
            report.n_with_provenance += 1
        else:
            report.n_missing_provenance += 1

        selected = row.get("selected_candidate") or (row.get("review") or {}).get("gold_selected_candidate")
        if selected:
            report.n_selection_labels += 1
        outcome = str(row.get("gold_outcome", "unknown")).lower()
        if outcome == "unknown" or not outcome:
            report.n_outcome_unknown += 1
        else:
            report.n_outcome_known += 1

        context = str(row.get("context_state", ""))
        if _TEMPLATE.search(context):
            report.n_template_family += 1
            if "template:" not in str(provenance.get("group_key", "")):
                report.fixture_suspects.append(f"row:{index}:template_without_template_group")

        key = str(provenance.get("group_key") or f"auto-{fingerprint(row)}")
        split = str(row.get("split", "train"))
        groups[key].add(split)
        report.group_split.setdefault(key, split)
        report.split_counts[split] = report.split_counts.get(split, 0) + 1

        fp = fingerprint(row)
        fingerprints[fp].append((index, split))

        # C03: evidence_required should keep multiline; a single truncated
        # "capture_id_matched: True" with no further lines is a prior-extraction smell.
        evidence = row.get("evidence_required") or []
        if evidence == ["- capture_id_matched: True"]:
            report.missing_evidence_multiline_truncation.append(f"row:{index}")

    report.n_unique_groups = len(groups)
    for key, splits in groups.items():
        if len(splits) > 1:
            report.group_cross_split.append(key)

    for fp, occurrences in fingerprints.items():
        splits = {split for _, split in occurrences}
        if len(splits) > 1:
            report.near_duplicate_cross_split.append({
                "fingerprint": fp,
                "rows": [i for i, _ in occurrences],
                "splits": sorted(splits),
            })

    if report.missing_evidence_multiline_truncation:
        report.notes.append(
            "C03: rows still holding only the first-line capture_id_matched artifact "
            "were extracted with the pre-v2 regex; re-migrate for full Expected_Evidence."
        )
    report.notes.append(
        "selection labels and observed outcomes are separate sets; "
        "n_selection_labels is not decision-quality evidence."
    )
    return report


def audit_file(path: str | Path) -> AuditReport:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return audit_rows(rows)
