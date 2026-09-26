"""Append-only, redacted activity log for ViVy optimization."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*[^,\s}]+")


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET.sub(r"\1=[REDACTED]", value)[:8000]
    if isinstance(value, dict):
        return {str(k): _redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    return value


class ActivityLog:
    """JSONL activity ledger; records operational facts, never claims completion."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("VIVY_ACTIVITY_LOG", ".vivy_activity.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, *, session_id: str = "", status: str = "OBSERVED",
               **fields: Any) -> dict[str, Any]:
        entry = {
            "event_id": uuid.uuid4().hex,
            "timestamp": time.time(),
            "event": event,
            "session_id": session_id,
            "status": status,
            **_redact(fields),
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return entry
