"""SHA256 receipt chain integrity verifier (D3).

Each receipt stores:
  - ``self_sha256``: sha256 of the canonical JSON (excluding the ``self_sha256`` field)
  - ``prev_receipt_sha256``: ``self_sha256`` of the previous receipt, or ``"GENESIS"`` for the first

Tamper detection: any byte-level change breaks ``self_sha256``. Chain break:
any deletion/reorder breaks the ``prev_receipt_sha256`` links.

CLI:
    python -m training.verify_receipt --receipts-dir evidence/shadow_receipts/

Exit codes:
    0  chain intact
    1  chain broken (tamper or gap detected)
    2  usage / IO error

Changelog:
    24/09/2026 (Claude Code — Plan 1 D3): Initial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

GENESIS = "GENESIS"


def compute_self_sha256(receipt: dict[str, Any]) -> str:
    """Compute the content hash of *receipt*, excluding its own ``self_sha256`` field."""
    payload = {k: v for k, v in receipt.items() if k != "self_sha256"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seal_receipt(receipt: dict[str, Any], *, prev_sha256: str = GENESIS) -> dict[str, Any]:
    """Return a copy of *receipt* with ``prev_receipt_sha256`` and ``self_sha256`` filled in."""
    sealed = dict(receipt)
    sealed["prev_receipt_sha256"] = prev_sha256
    sealed["self_sha256"] = compute_self_sha256(sealed)
    return sealed


def verify_receipt(receipt: dict[str, Any]) -> list[str]:
    """Verify a single receipt's self-hash. Return list of problems (empty = OK)."""
    problems: list[str] = []
    stored = receipt.get("self_sha256")
    if stored is None:
        problems.append("missing self_sha256")
        return problems
    recomputed = compute_self_sha256(receipt)
    if recomputed != stored:
        problems.append(f"self_sha256 mismatch: stored={stored[:16]}… recomputed={recomputed[:16]}…")
    return problems


def verify_chain(receipts: list[dict[str, Any]]) -> list[str]:
    """Verify a sequence of sealed receipts. Return list of problems (empty = OK)."""
    problems: list[str] = []
    if not receipts:
        return ["empty receipt chain"]

    # First receipt must have prev == GENESIS
    first_prev = receipts[0].get("prev_receipt_sha256")
    if first_prev != GENESIS:
        problems.append(f"first receipt prev_receipt_sha256 is {first_prev!r}, expected {GENESIS!r}")

    for i, receipt in enumerate(receipts):
        rid = receipt.get("receipt_id") or receipt.get("run_id") or f"[{i}]"
        problems.extend(f"receipt {rid}: {p}" for p in verify_receipt(receipt))

        # Chain link: prev of receipt[i] must equal self_sha256 of receipt[i-1]
        if i > 0:
            expected_prev = receipts[i - 1].get("self_sha256")
            actual_prev = receipt.get("prev_receipt_sha256")
            if actual_prev != expected_prev:
                problems.append(
                    f"receipt {rid}: chain break — prev_receipt_sha256={str(actual_prev)[:16]}… "
                    f"but previous self_sha256={str(expected_prev)[:16]}…"
                )

    return problems


def verify_receipts_dir(receipts_dir: str | Path) -> dict[str, Any]:
    """Verify all receipt JSON files in *receipts_dir*, sorted by filename."""
    d = Path(receipts_dir)
    if not d.is_dir():
        return {"status": "ERROR", "problems": [f"not a directory: {d}"]}

    files = sorted(d.glob("*.json"))
    if not files:
        return {"status": "ERROR", "problems": [f"no receipt JSON files in {d}"]}

    receipts: list[dict[str, Any]] = []
    load_problems: list[str] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            receipts.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            load_problems.append(f"{f.name}: load error: {exc}")

    chain_problems = verify_chain(receipts) if receipts else ["no receipts loaded"]
    all_problems = load_problems + chain_problems
    return {
        "status": "PASS" if not all_problems else "FAIL",
        "receipt_count": len(receipts),
        "files": [f.name for f in files],
        "problems": all_problems,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts-dir", required=True,
                        help="directory containing receipt JSON files")
    args = parser.parse_args(argv)

    result = verify_receipts_dir(args.receipts_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
