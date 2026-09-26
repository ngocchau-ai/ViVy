"""Small immutable-style JSON receipt writer for ViVy experiments.

Changelog:
    24/09/2026 (Claude Code — Plan 1 D5): Added validate_live_shape() for
    live/model/hash/config/denominator shape validation. Consolidated from
    live_receipt_shape.py per D5.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def gates_pass(gates: Mapping[str, str]) -> bool:
    """True only when gates are present and every gate is PASS.

    Empty gate maps must not promote: `all([]) is True` is a fail-open bug
    (acceptance plan §2.8). Callers that need a specific gate set should
    require it before calling this helper.
    """
    return bool(gates) and all(value == "PASS" for value in gates.values())


def build_receipt(*, run_id: str, stage: str, metrics: Mapping[str, Any],
                  gates: Mapping[str, str], input_sha256: str) -> dict[str, Any]:
    gate_map = dict(gates)
    return {
        "run_id": run_id,
        "stage": stage,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": input_sha256,
        "metrics": dict(metrics),
        "gates": gate_map,
        "promotion": "PROMOTED" if gates_pass(gate_map) else "BLOCKED",
    }


def make_receipt_id(*, kind: str, payload: Mapping[str, Any]) -> str:
    """Content-addressed receipt id: f"{kind}-" + sha256(canonical_json)[:16].

    Canonical json = sorted keys, no whitespace, ensure_ascii=False.
    Callers MUST NOT put the legacy selected_candidate in payload.
    """
    canonical = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return f"{kind}-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def write_receipt(
    path: str | Path,
    receipt: Mapping[str, Any],
    *,
    allow_replace: bool = False,
    protected: tuple[str | Path, ...] = (),
) -> None:
    """Write *receipt* as JSON. Refuses to clobber inputs or prior receipts
    unless *allow_replace* is set (§2.11).
    """
    from training.io_guard import open_write

    with open_write(path, protected=protected, allow_replace=allow_replace) as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")


# --- Live shape validation (D5) -----------------------------------------------

_LIVE_SHAPE_REQUIRED = ("live", "model", "model_hash", "config_hash", "denominator")


class LiveShapeError(ValueError):
    """Raised when a receipt payload is missing required live/model/hash/config/denominator fields."""


def validate_live_shape(payload: Mapping[str, Any]) -> None:
    """Validate that *payload* has all required live-model fields.

    Required fields: ``live``, ``model``, ``model_hash``, ``config_hash``, ``denominator``.
    Raises :class:`LiveShapeError` listing all missing fields.
    """
    missing = [f for f in _LIVE_SHAPE_REQUIRED if f not in payload]
    if missing:
        raise LiveShapeError(f"receipt payload missing required fields: {missing}")
