"""Run the non-actuating router over a JSONL queue and emit receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training.shadow_router import recommend


def run(
    source: str | Path,
    output: str | Path,
    *,
    allow_replace: bool = False,
) -> int:
    from training.io_guard import open_write

    count = 0
    with open_write(output, protected=(source,), allow_replace=allow_replace) as out:
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = line.encode("utf-8")
            row = json.loads(line)
            result = recommend(row)
            receipt = {
                "receipt_id": "shadow-" + hashlib.sha256(raw).hexdigest()[:16],
                "router": result.policy,
                "policy_note": result.note,
                "recommendation": result.recommendation,
                "observed": result.observed,
                "agree": result.agree,
                "confidence": result.confidence,
                "actuated": result.actuated,
                "label_quality": row.get("label_quality", "unknown"),
                "status": "SHADOW_ONLY",
            }
            out.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    print(run(args.source, args.output))
