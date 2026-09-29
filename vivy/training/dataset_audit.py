"""C03 dataset audit — group-split leakage, near-duplicates, provenance completeness.

Read-only. Does not rewrite datasets and does not invent labels/outcomes.

Changelog:
    24/09/2026 (Claude Code — P2 C03): Initial.
    29/09/2026 (Claude Code — WP-6/O-10/F-H01): owns FABRICATED_EVIDENCE_LABELS;
        detects the two row schemas (ChatML ``messages`` vs typed
        ``context_state``/``candidates``) instead of silently auditing a
        ChatML row as if it were typed and reporting zeros.
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
    # --- WP-6 / O-10 / F-H01 -------------------------------------------------
    n_schema_chatml: int = 0
    n_schema_typed: int = 0
    n_fabricated_evidence: int = 0
    fabricated_evidence_rows: list[str] = field(default_factory=list)
    n_missing_evidence_receipt: int = 0
    missing_evidence_receipt_rows: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def has_fabricated_labels(self) -> bool:
        return self.n_fabricated_evidence > 0

    @property
    def exportable(self) -> bool:
        """T9: 0 nhãn bịa, và mọi mẫu có evidence_receipt_id."""
        return not self.has_fabricated_labels and self.n_missing_evidence_receipt == 0

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
            "n_schema_chatml": self.n_schema_chatml,
            "n_schema_typed": self.n_schema_typed,
            "n_fabricated_evidence": self.n_fabricated_evidence,
            "fabricated_evidence_rows": self.fabricated_evidence_rows,
            "n_missing_evidence_receipt": self.n_missing_evidence_receipt,
            "missing_evidence_receipt_rows": self.missing_evidence_receipt_rows,
            "exportable": self.exportable,
            "notes": self.notes,
        }


# --- WP-6 / O-10 / F-H01 — fabricated hard-evidence labels --------------------
#
# These three strings were written by the pre-WP-6 extractor as constants into
# every sample's ``Expected_Evidence``, regardless of what the source record
# actually contained.  None of them names a real gate in any real system, and
# none was ever measured.  They are never legitimate — receipt or not.
#
# This tuple is the single source of truth: the extractor refuses to emit
# them, the audit flags them, and tests/test_no_fabricated_labels.py fails
# the build when they show up in a live SFT set.
FABRICATED_EVIDENCE_LABELS: tuple[str, ...] = (
    "AST_VALID_AND_TEST_PASS",
    "COGNITIVE_CONSENSUS_VERIFIED",
    "MULTIMODAL_GROUNDING_VERIFIED",
)

#: ``capture_id_matched: True`` is a real check name, so it is legitimate when
#: the source record reports it.  The extractor wrote it unconditionally; that
#: specific emission is what WP-6 stops.  It is not in FABRICATED_EVIDENCE_LABELS
#: because a record that genuinely observed a match may say so.
ALWAYS_TRUE_CHECK_ASSERTIONS: tuple[str, ...] = (
    "capture_id_matched: True",
)

#: What ``Expected_Evidence`` says when no receipt backs it.  Not a claim.
UNVERIFIED_EVIDENCE = "UNVERIFIED"

#: Marker a sample must carry to be exportable (T9).
EVIDENCE_RECEIPT_FIELD = "evidence_receipt_id"


def detect_schema(row: Mapping[str, Any]) -> str:
    """``"chatml"`` (messages/source/reward) or ``"typed"`` (context_state/candidates).

    The two schemas were being fed to the same auditor, which read a ChatML
    row as a typed row with every field missing and reported a wall of zeros
    that looked like a clean bill of health.  Detecting the shape is the fix.
    """
    if "messages" in row and "context_state" not in row:
        return "chatml"
    if "conversations" in row and "context_state" not in row:
        return "chatml"
    return "typed"


def chatml_assistant_text(row: Mapping[str, Any]) -> str:
    """Assistant text of a ChatML/ShareGPT row ("" when there is none)."""
    messages = row.get("messages")
    if not isinstance(messages, list):
        messages = row.get("conversations")
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        role = message.get("role") or message.get("from")
        if role in ("assistant", "gpt"):
            content = message.get("content", message.get("value", ""))
            if isinstance(content, str):
                parts.append(content)
    return "\n".join(parts)


def find_fabricated_labels(text: str) -> list[str]:
    """Return the fabricated hard-evidence labels present in *text*."""
    return [label for label in FABRICATED_EVIDENCE_LABELS if label in (text or "")]


#: A migration id is provenance, not verification — ``legacy_to_typed.migrate``
#: stamps one on every row it touches.  It must not satisfy the T9 receipt rule.
MIGRATION_ID_PREFIX = "legacy-"


def evidence_receipt_of(row: Mapping[str, Any]) -> str | None:
    """The receipt that actually backs this row's label, or None.

    Checked in descending order of strength.  ``legacy-*`` migration ids are
    skipped on purpose: every migrated row has one, so counting them would make
    the T9 receipt rule vacuous on exactly the set that needs it most.
    """
    provenance = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
    review = row.get("review") if isinstance(row.get("review"), Mapping) else {}
    candidates: list[Any] = [
        row.get(EVIDENCE_RECEIPT_FIELD),
        review.get("independent_receipt_id"),
        provenance.get("review_receipt_id"),
        provenance.get("receipt_id"),
        row.get("receipt_id"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            text = candidate.strip()
            if text.startswith(MIGRATION_ID_PREFIX):
                continue
            return text
    return None


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
        schema = detect_schema(row)
        if schema == "chatml":
            report.n_schema_chatml += 1
        else:
            report.n_schema_typed += 1

        provenance = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
        if provenance.get("receipt_id") and provenance.get("source_file_sha256"):
            report.n_with_provenance += 1
        else:
            report.n_missing_provenance += 1

        # WP-6 / T9: a sample without a backing receipt is not exportable.
        if evidence_receipt_of(row) is None:
            report.n_missing_evidence_receipt += 1
            report.missing_evidence_receipt_rows.append(f"row:{index}")

        # WP-6 / F-H01: fabricated hard-evidence labels, in whichever field the
        # schema puts them — assistant text for ChatML, evidence_required for typed.
        if schema == "chatml":
            haystack = chatml_assistant_text(row)
        else:
            evidence_list = row.get("evidence_required") or []
            haystack = "\n".join(str(e) for e in evidence_list)
        found = find_fabricated_labels(haystack)
        if found:
            report.n_fabricated_evidence += 1
            report.fabricated_evidence_rows.append(f"row:{index}:{','.join(found)}")

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
    if report.n_schema_chatml and report.n_schema_typed:
        report.notes.append(
            "WP-6: mixed schemas in one file — chatml rows carry no context_state/"
            "candidates and cannot be scored as typed rows. Split the sets."
        )
    if report.has_fabricated_labels:
        report.notes.append(
            "WP-6/F-H01: fabricated hard-evidence labels present. These strings are "
            "asserted without a receipt and must not reach SFT."
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


class FabricatedLabelError(ValueError):
    """Raised when a sample would export a hard-evidence claim with no receipt."""


def assert_exportable(rows: Sequence[Mapping[str, Any]]) -> AuditReport:
    """T9 gate: raise unless every row is clean and receipt-backed.

    This is the pipeline wiring point. ``DatasetExtractor.export_jsonl`` calls
    it before writing, so a fabricated label cannot reach an SFT set even if
    an ingest path regresses.
    """
    report = audit_rows(rows)
    if report.has_fabricated_labels:
        raise FabricatedLabelError(
            f"{report.n_fabricated_evidence} row(s) assert hard-evidence labels with "
            f"no receipt: {report.fabricated_evidence_rows[:5]} — see "
            f"FABRICATED_EVIDENCE_LABELS in training/dataset_audit.py"
        )
    if report.n_missing_evidence_receipt:
        raise FabricatedLabelError(
            f"{report.n_missing_evidence_receipt} row(s) have no {EVIDENCE_RECEIPT_FIELD} "
            f"({report.missing_evidence_receipt_rows[:5]}) — T9 requires every exported "
            f"sample to be receipt-backed or dropped"
        )
    return report
