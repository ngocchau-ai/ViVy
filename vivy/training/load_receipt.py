"""Load receipt log — SHA256-chained AWL decisions (AWL-5).

Every adaptive load decision is persisted as one sealed receipt JSON in a
directory, linked into a tamper-evident chain:

    receipt[i].prev_receipt_sha256 == receipt[i-1].self_sha256
    receipt[0].prev_receipt_sha256 == "GENESIS"

Any byte-level edit breaks ``self_sha256``; any deletion or reorder breaks
the ``prev_receipt_sha256`` links. ``verify()`` delegates to
:func:`training.verify_receipt.verify_receipts_dir`, so this log is checked
by the same verifier used for every other ViVy receipt chain.

Layout: one file per decision, named ``<seq:06d>-<receipt_id>.json`` so a
lexicographic sort is the chain order.

Structure:
    LoadReceiptLog
    ├── record(decision, budget=, live=) -> dict  — seal + write one receipt
    ├── verify() -> dict                          — chain integrity check
    ├── last_sha256 -> str                        — chain tip ("GENESIS" if empty)
    └── count() -> int                            — receipts on disk

Changelog:
    25/09/2026 (Claude Code — AWL-5): Initial.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from training.receipt import make_receipt_id, write_receipt
from training.verify_receipt import GENESIS, seal_receipt, verify_receipts_dir

if TYPE_CHECKING:
    from training.cautreo_resource_monitor import ResourceBudget
    from training.load_governor import LoadDecision

SEQ_WIDTH = 6


class LoadReceiptLog:
    """Append-only, SHA256-chained log of :class:`LoadDecision` receipts.

    Resumes the chain from whatever is already on disk, so a restarted
    process continues linking rather than resetting to GENESIS.
    """

    def __init__(self, receipts_dir: str | Path, *, run_id: str = "") -> None:
        self._dir = Path(receipts_dir)
        self._run_id = run_id
        self._last_sha256 = GENESIS
        self._seq = 0
        self._resume()

    # --- chain state ---

    def _resume(self) -> None:
        """Pick up seq + chain tip from existing receipt files."""
        if not self._dir.is_dir():
            return
        files = self._sorted_files()
        if not files:
            return
        self._seq = len(files)
        try:
            last = json.loads(files[-1].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        tip = last.get("self_sha256")
        if isinstance(tip, str) and tip:
            self._last_sha256 = tip

    def _sorted_files(self) -> list[Path]:
        return sorted(self._dir.glob("*.json"))

    @property
    def last_sha256(self) -> str:
        """Chain tip hash, or ``GENESIS`` when no receipt has been written."""
        return self._last_sha256

    def count(self) -> int:
        """Number of receipt files currently on disk."""
        return len(self._sorted_files()) if self._dir.is_dir() else 0

    # --- writing ---

    def record(
        self,
        decision: LoadDecision,
        *,
        budget: ResourceBudget | None = None,
        live: str = "SIMULATED_PROTOCOL",
    ) -> dict[str, Any]:
        """Seal and write one load-decision receipt; return the sealed receipt.

        ``live`` must be an honest label — ``"LIVE_MODEL_OBSERVATION"`` only
        when the numbers came from a real measured backend, otherwise the
        default ``"SIMULATED_PROTOCOL"``. Overwriting an existing receipt is
        refused by ``io_guard``.
        """
        payload: dict[str, Any] = {
            "kind": "awl-load",
            "run_id": self._run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "live": live,
            "decision": decision.to_dict(),
            "budget": budget.to_dict() if budget is not None else None,
        }
        payload["receipt_id"] = make_receipt_id(kind="awl-load", payload=payload)

        sealed = seal_receipt(payload, prev_sha256=self._last_sha256)

        self._seq += 1
        filename = f"{self._seq:0{SEQ_WIDTH}d}-{payload['receipt_id']}.json"
        write_receipt(self._dir / filename, sealed, allow_replace=False)

        self._last_sha256 = sealed["self_sha256"]
        return sealed

    # --- verification ---

    def verify(self) -> dict[str, Any]:
        """Verify the whole chain. Returns the verify_receipts_dir report."""
        return verify_receipts_dir(self._dir)
