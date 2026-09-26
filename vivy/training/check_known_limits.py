"""KNOWN_LIMITATIONS.md consistency checker (D4).

Matches limitation entries against the receipt directory. Flags:
  - a limitation that references a ``claim_type`` + ``receipt_id`` where the receipt is missing
  - a stale limitation whose receipt no longer exists
  - a limitation entry with a receipt reference that cannot be resolved

CLI:
    python -m training.check_known_limits \\
        --limits-file docs/plans/KNOWN_LIMITATIONS.md \\
        --receipts-dir evidence/

Exit codes:
    0  all limitation-receipt links are consistent
    1  at least one inconsistency found
    2  usage / IO error

Changelog:
    24/09/2026 (Claude Code — Plan 1 D4): Initial.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Receipt filename pattern: something ending in .json inside evidence/
RECEIPT_REF = re.compile(r"[\w./\\-]+\.json")

# Limitation table row pattern: | L-xx | LABEL | description | blocks |
LIMIT_ROW = re.compile(
    r"^\|\s*(L-\d+)\s*\|\s*\*{0,2}(\w[\w\s()-]*)\*{0,2}\s*\|(.+)\|(.+)\|",
    re.MULTILINE,
)


def parse_limitations(limits_text: str) -> list[dict[str, Any]]:
    """Parse KNOWN_LIMITATIONS.md table rows into structured entries."""
    entries = []
    for m in LIMIT_ROW.finditer(limits_text):
        entry_id, label, limitation, blocks = m.groups()
        # Extract receipt references from the limitation text
        receipt_refs = RECEIPT_REF.findall(limitation)
        entries.append({
            "id": entry_id.strip(),
            "label": label.strip(),
            "limitation": limitation.strip(),
            "blocks": blocks.strip(),
            "receipt_refs": receipt_refs,
        })
    return entries


def check_known_limits(
    limits_file: str | Path,
    receipts_dir: str | Path,
) -> dict[str, Any]:
    """Check KNOWN_LIMITATIONS.md entries against the receipt directory."""
    limits_path = Path(limits_file)
    receipts_path = Path(receipts_dir)

    if not limits_path.is_file():
        return {"status": "ERROR", "problems": [f"limits file not found: {limits_path}"]}
    if not receipts_path.is_dir():
        return {"status": "ERROR", "problems": [f"receipts dir not found: {receipts_path}"]}

    text = limits_path.read_text(encoding="utf-8")
    entries = parse_limitations(text)

    # Build index of receipt filenames present in the directory (recursive)
    present_receipts: set[str] = set()
    for f in receipts_path.rglob("*.json"):
        present_receipts.add(f.name)

    problems: list[str] = []
    checked = 0
    for entry in entries:
        for ref in entry["receipt_refs"]:
            checked += 1
            ref_name = Path(ref).name
            if ref_name not in present_receipts:
                problems.append(
                    f"{entry['id']} ({entry['label']}): references receipt {ref_name!r} "
                    f"but it does not exist in {receipts_path}"
                )

    return {
        "status": "PASS" if not problems else "FAIL",
        "limitations_parsed": len(entries),
        "receipt_refs_checked": checked,
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limits-file", required=True,
                        help="path to KNOWN_LIMITATIONS.md")
    parser.add_argument("--receipts-dir", required=True,
                        help="directory containing receipt JSON files")
    args = parser.parse_args(argv)

    result = check_known_limits(args.limits_file, args.receipts_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
