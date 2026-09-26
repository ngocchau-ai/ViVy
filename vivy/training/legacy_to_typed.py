"""Conservative migration of legacy CUA ChatML rows into typed records.

Changelog:
    24/09/2026 (Codex): initial.
    24/09/2026 (Claude Code — P0 CORRECTIONS §2.6): confidence/timestamp tagging.
    24/09/2026 (Claude Code — P2 C03): multiline Expected_Evidence; group split by
        session/task/template family (not `index % 10`); extraction_version;
        source vs extraction timestamps kept distinct.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

CID = re.compile(r"\[([^\]]+)\]")
SELECTED = re.compile(r"Selected_Candidate_ID:\s*([^\s\r\n]+)", re.I)
# C03: keep the whole Expected_Evidence block, not only the first line.
# Stops at the next labeled field (Key:) or end of assistant text.
EVIDENCE = re.compile(
    r"Expected_Evidence:\s*(.*?)(?=\n[A-Z][A-Za-z0-9_]+:|\Z)",
    re.I | re.S,
)
FIELD_LINE = re.compile(r"^[A-Z][A-Za-z0-9_]+:")
TEMPLATE_GOAL = re.compile(
    r"^(?:Task\s+Goal:|Goal:)?\s*(Execute automated bounded workspace task)\s*#\d+",
    re.I,
)

EXTRACTION_VERSION = "legacy_to_typed.v2.c03-multiline-group-split"


def extract_expected_evidence(assistant: str) -> list[str]:
    """Return every Expected_Evidence line (C03: multiline preserved)."""
    match = EVIDENCE.search(assistant)
    if not match:
        return []
    block = match.group(1)
    lines: list[str] = []
    for raw in block.splitlines():
        text = raw.strip()
        if not text:
            continue
        if FIELD_LINE.match(text):
            break
        lines.append(text)
    return lines


def group_key(context_state: str, candidates: list[dict[str, Any]] | None = None) -> str:
    """Session / task / template family — rows in one group never cross splits."""
    context = (context_state or "").strip()
    first = context.splitlines()[0] if context else ""
    template = TEMPLATE_GOAL.match(first)
    if template:
        return f"template:{template.group(1).strip().lower()}"
    if first:
        # Distinct tasks stay distinct groups. Digit-normalization would collapse
        # "Goal unique-1" and "Goal unique-2" into one family and force one split.
        # Template tasks already group via TEMPLATE_GOAL above.
        return f"goal:{first[:80].lower()}"
    # fall back to candidate-set shape so identical decision frames group together
    ids = ",".join(sorted(str(c.get("id", "")) for c in (candidates or [])))
    return f"cands:{hashlib.sha256(ids.encode('utf-8')).hexdigest()[:12]}"


def split_for_group(key: str) -> str:
    """Deterministic group split. Same group → same split (never `index % 10`)."""
    bucket = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "dev"
    if bucket == 1:
        return "test"
    return "train"


def migrate(path: str | Path, *, extracted_at: str | None = None) -> Iterator[dict[str, Any]]:
    p = Path(path)
    file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
    when = extracted_at or datetime.now(timezone.utc).isoformat()
    for index, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(line)
            user = str(row["messages"][1]["content"])
            assistant = str(row["messages"][2]["content"])
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            continue
        marker = "Bounded Candidate Table:"
        if marker not in user:
            continue
        table = user.split(marker, 1)[1].split("Select the safest", 1)[0]
        candidates = [{"id": m.group(1), "description": line.strip()} for line in table.splitlines() if (m := CID.search(line))]
        selected = SELECTED.search(assistant)
        evidence_lines = extract_expected_evidence(assistant)
        if not candidates or not selected or selected.group(1) not in {c["id"] for c in candidates}:
            continue
        context_state = user.split(marker, 1)[0].strip()
        key = group_key(context_state, candidates)
        yield {
            "decision_type": "choice",
            "task_id": f"legacy-{index}-{file_hash[:12]}",
            "context_state": context_state,
            "candidates": candidates,
            "selected_candidate": selected.group(1),
            # §2.6: migration does not measure confidence. 0.0 here is a schema
            # placeholder, not a model probability — tagged below.
            "confidence": 0.0,
            "confidence_source": "migration_placeholder_not_measured",
            # C03: full multiline block, never the first line only.
            "evidence_required": evidence_lines,
            "evidence_required_line_count": len(evidence_lines),
            "provenance": {
                "source": row.get("source", "legacy_chatml"),
                "producer": "legacy_to_typed",
                "receipt_id": f"legacy-{index}-{file_hash[:12]}",
                # §2.6: extraction time is not an action-observation timestamp.
                "timestamp": "extracted-not-observed",
                "timestamp_kind": "extraction",
                "action_observed_at": None,
                "source_timestamp": row.get("timestamp"),  # may be missing → null
                "extracted_at": when,
                "expected_evidence_kind": "extracted_from_assistant_text",
                "expected_evidence_is_observed": False,
                "source_file_sha256": file_hash,
                "source_line_index": index,
                "extraction_version": EXTRACTION_VERSION,
                "group_key": key,
            },
            "label_quality": "unverified",
            "gold_outcome": "unknown",
            "split": split_for_group(key),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--allow-replace", action="store_true")
    args = parser.parse_args()
    from training.io_guard import open_write

    with open_write(args.output, protected=(args.input,), allow_replace=args.allow_replace) as out:
        for item in migrate(args.input):
            out.write(json.dumps(item, ensure_ascii=False) + "\n")
