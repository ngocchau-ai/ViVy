"""Label-distribution baseline for the current legacy ChatML dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SELECTED = re.compile(r"Selected_Candidate_ID:\s*([^\s\r\n]+)", re.I)


def run_baseline(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_bytes()
    labels: list[str] = []
    skipped = 0
    for line in raw.decode("utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            assistant = str(row["messages"][2]["content"])
        except (ValueError, KeyError, IndexError, TypeError):
            skipped += 1
            continue
        match = SELECTED.search(assistant)
        if match:
            labels.append(match.group(1))
        else:
            skipped += 1
    counts = Counter(labels)
    majority = counts.most_common(1)[0] if counts else (None, 0)
    return {
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "rows_with_label": len(labels),
        "skipped_rows": skipped,
        "label_counts": dict(counts),
        "majority_label": majority[0],
        "majority_share": (majority[1] / len(labels)) if labels else None,
        # §2.4: majority over per-record candidate IDs is NOT a classifier
        # baseline. IDs are only meaningful inside a record's candidate set.
        "baseline_kind": "label_share_description_not_classifier",
        "valid_as_classifier_baseline": False,
        "status": "DESCRIPTIVE_ONLY_NO_INDEPENDENT_GOLD_OUTCOME",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="vivy_train_dataset.jsonl")
    print(json.dumps(run_baseline(parser.parse_args().path), indent=2))
