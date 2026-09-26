"""Audit ChatML JSONL for provenance and typed-decision readiness.

Change log: Codex, 2026-09-23 — add read-only stdlib audit; legacy records
remain rejected and are never relabeled.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DECISION_TYPES = {"choice", "score", "noul"}
REQUIRED_PROVENANCE = ("source", "producer", "receipt_id", "timestamp")
DEFAULT_INPUT = Path(__file__).resolve().parent.parent / "vivy_train_dataset.jsonl"


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_task_context(record: dict[str, Any]) -> bool:
    for key in ("task_context", "context_state"):
        if _nonempty_string(record.get(key)):
            return True
    messages = record.get("messages")
    if isinstance(messages, list):
        return any(
            isinstance(message, dict)
            and message.get("role") == "user"
            and _nonempty_string(message.get("content"))
            and not message["content"].strip().lower().startswith("task execution:")
            for message in messages
        )
    return False


def _has_noul(record: dict[str, Any]) -> bool:
    if record.get("decision_type") == "noul":
        return True
    candidates = record.get("candidates")
    if isinstance(candidates, list):
        return any(
            isinstance(candidate, dict)
            and (
                str(candidate.get("id", "")).strip().lower() == "noul"
                or str(candidate.get("action_type", "")).strip().lower() == "noul"
            )
            for candidate in candidates
        )
    return False


def _typed_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decision_type = record.get("decision_type")
    if decision_type not in DECISION_TYPES:
        errors.append("untyped")

    candidates = record.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("missing_candidates")
    else:
        ids = [candidate.get("id") if isinstance(candidate, dict) else None for candidate in candidates]
        if any(not _nonempty_string(candidate_id) for candidate_id in ids):
            errors.append("invalid_candidates")
        elif len(set(candidate_id for candidate_id in ids if isinstance(candidate_id, str))) != len(ids):
            errors.append("duplicate_candidate_ids")

    candidate_ids = {
        candidate.get("id")
        for candidate in (candidates if isinstance(candidates, list) else [])
        if isinstance(candidate, dict) and _nonempty_string(candidate.get("id"))
    }

    if not _has_noul(record):
        errors.append("missing_noul")
    if not _has_task_context(record):
        errors.append("missing_task_context")

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or any(
        not _nonempty_string(provenance.get(field)) for field in REQUIRED_PROVENANCE
    ):
        errors.append("missing_provenance")

    if decision_type == "choice":
        if not _nonempty_string(record.get("selected_candidate")) or (
            isinstance(candidates, list) and record.get("selected_candidate") not in candidate_ids
        ):
            errors.append("invalid_choice")
    elif decision_type == "score":
        score = record.get("score")
        if (
            not _nonempty_string(record.get("selected_candidate"))
            or (
                isinstance(candidates, list) and record.get("selected_candidate") not in candidate_ids
            )
            or not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 1
        ):
            errors.append("invalid_score")
    elif decision_type == "noul":
        if record.get("selected_candidate") is not None or record.get("score") is not None:
            errors.append("invalid_noul")

    confidence = record.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("invalid_confidence")
    evidence = record.get("evidence_required")
    if not isinstance(evidence, list) or any(not _nonempty_string(item) for item in evidence):
        errors.append("missing_evidence")
    if record.get("split") not in {"train", "dev", "test"}:
        errors.append("invalid_split")
    return errors


def audit_jsonl(path: str | Path) -> dict[str, Any]:
    """Read *path* without writing to it and return a JSON-serializable report."""
    report: dict[str, Any] = {
        "total": 0,
        "parse_errors": 0,
        "missing_candidates": 0,
        "missing_noul": 0,
        "missing_task_context": 0,
        "untyped": 0,
        "source_counts": {},
        "ready_count": 0,
        "rejected_count": 0,
        "reasons": {},
    }
    sources: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            report["total"] += 1
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                report["parse_errors"] += 1
                report["rejected_count"] += 1
                reasons["parse_error"] += 1
                continue
            if not isinstance(value, dict):
                report["parse_errors"] += 1
                report["rejected_count"] += 1
                reasons["record_not_object"] += 1
                continue

            provenance = value.get("provenance")
            source = value.get("source")
            if not _nonempty_string(source) and isinstance(provenance, dict):
                source = provenance.get("source")
            sources[source.strip() if _nonempty_string(source) else "<missing>"] += 1

            errors = _typed_errors(value)
            for reason in errors:
                reasons[reason] += 1
            for key in ("missing_candidates", "missing_noul", "missing_task_context", "untyped"):
                if key in errors:
                    report[key] += 1
            if errors:
                report["rejected_count"] += 1
            else:
                report["ready_count"] += 1

    report["source_counts"] = dict(sorted(sources.items()))
    report["reasons"] = dict(sorted(reasons.items()))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, help="write JSON report to this path")
    args = parser.parse_args(argv)
    report = audit_jsonl(args.input)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
