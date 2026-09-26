"""Create a human-review queue without changing labels or source data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def create_queue(source: str | Path, output: str | Path) -> int:
    count = 0
    with Path(output).open("w", encoding="utf-8") as out:
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            row["review"] = {
                "gold_selected_candidate": None,
                "gold_outcome": None,
                "reviewer": None,
                "reviewed_at": None,
                "independent_receipt_id": None,
                "status": "PENDING",
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    print(create_queue(args.source, args.output))
