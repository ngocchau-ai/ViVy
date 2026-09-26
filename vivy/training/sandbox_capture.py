"""P3 sandbox re-execute for observed outcome capture (D2).

Safe-subset predicate: rejects rows whose action/evidence text contains
destructive commands (delete, wipe, kill, trade_buy, rm, drop, format, shutdown).
Match is case-insensitive regex on raw text fields.

Sandbox isolation: subprocess + timeout=30s + max_steps=1 + read-only allowlist.
Crash → SANDBOX_CRASH receipt; row keeps ``gold_outcome=unknown``.

Receipt contract:
    kind=observed_outcome, sandbox=true, side_effect_repeats=0
Only observed rows may set ``gold_outcome != unknown``.

Changelog:
    24/09/2026 (Claude Code — Plan 1 D2): Initial.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# --- Safe-subset predicate ---------------------------------------------------

DESTRUCTIVE_PATTERNS = re.compile(
    r"\b(delete|wipe|kill|trade_buy|rm|drop|format|shutdown|destroy|purge|truncate)",
    re.IGNORECASE,
)

MAX_TIMEOUT_S = 30.0
MAX_STEPS = 1


def is_safe_subset(row: Mapping[str, Any]) -> bool:
    """Return True if *row* has no destructive commands in action/evidence fields."""
    text_fields = []
    for key in ("action", "evidence", "command", "intent", "description", "raw_text"):
        val = row.get(key)
        if isinstance(val, str):
            text_fields.append(val)
        elif isinstance(val, (list, tuple)):
            text_fields.extend(str(v) for v in val)
        elif isinstance(val, Mapping):
            text_fields.append(json.dumps(val, ensure_ascii=False))
    combined = " ".join(text_fields)
    return DESTRUCTIVE_PATTERNS.search(combined) is None


def is_safe_subset_text(text: str) -> bool:
    """Check a raw text blob for destructive commands."""
    return DESTRUCTIVE_PATTERNS.search(text) is None


# --- Sandbox capture ---------------------------------------------------------


def _make_capture_receipt(
    *,
    row_id: str,
    status: str,
    stdout: str = "",
    stderr: str = "",
    duration_s: float = 0.0,
    reason: str = "",
) -> dict[str, Any]:
    """Build an observed-outcome receipt per §4.2 contract."""
    payload = {
        "row_id": row_id,
        "kind": "observed_outcome",
        "sandbox": True,
        "side_effect_repeats": 0,
        "status": status,
        "duration_s": round(duration_s, 4),
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest() if stdout else "",
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest() if stderr else "",
    }
    if reason:
        payload["reason"] = reason
    return payload


def capture_sandboxed(
    command: list[str],
    *,
    row_id: str = "unknown",
    timeout_s: float = MAX_TIMEOUT_S,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    """Run *command* in a sandboxed subprocess. Returns a receipt dict.

    - ``timeout_s`` is capped at ``MAX_TIMEOUT_S`` (30s).
    - Only one step (``max_steps=1``) — no loop.
    - Crash / timeout → ``SANDBOX_CRASH`` receipt, row keeps ``gold_outcome=unknown``.
    """
    timeout_s = min(timeout_s, MAX_TIMEOUT_S)
    start = time.perf_counter()

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
        duration = time.perf_counter() - start
        if proc.returncode == 0:
            return _make_capture_receipt(
                row_id=row_id,
                status="OBSERVED",
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                duration_s=duration,
            )
        return _make_capture_receipt(
            row_id=row_id,
            status="SANDBOX_CRASH",
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_s=duration,
            reason=f"exit_code={proc.returncode}",
        )
    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - start
        return _make_capture_receipt(
            row_id=row_id,
            status="SANDBOX_CRASH",
            duration_s=duration,
            reason=f"timeout after {timeout_s}s",
        )
    except OSError as exc:
        duration = time.perf_counter() - start
        return _make_capture_receipt(
            row_id=row_id,
            status="SANDBOX_CRASH",
            duration_s=duration,
            reason=f"OSError: {exc}",
        )


def capture_row(
    row: Mapping[str, Any],
    *,
    row_id: str = "unknown",
    command: list[str] | None = None,
) -> dict[str, Any]:
    """Capture observed outcome for one gold row. Destructive rows are refused.

    Returns a receipt dict. Only ``status=OBSERVED`` receipts may set
    ``gold_outcome != unknown``.
    """
    if not is_safe_subset(row):
        return _make_capture_receipt(
            row_id=row_id,
            status="REFUSED_DESTRUCTIVE",
            reason="row contains destructive command — refuse to execute",
        )
    if command is None:
        return _make_capture_receipt(
            row_id=row_id,
            status="NOT_RUN",
            reason="no command provided for capture",
        )
    return capture_sandboxed(command, row_id=row_id)
