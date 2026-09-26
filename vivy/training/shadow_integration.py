"""C07 shadow integration — default OFF, instrumented no-tool-call proof.

A shadow router may score and recommend. It must never call a tool, never
actuate, and never fall through to EXECUTE_DIRECTLY. Every attempt is counted;
every receipt carries `no_tool_call_proof`.

Changelog:
    24/09/2026 (Claude Code — P4 C07): Initial.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from training.shadow_router import recommend


class ShadowIntegrationBlocked(RuntimeError):
    """Raised when shadow is invoked while disabled, or when a tool is attempted."""


class ShadowIntegration:
    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self.tool_calls_allowed = False  # never, even when enabled
        self.tool_calls_attempted = 0
        self.tool_calls_executed = 0
        self.actuations_executed = 0

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise ShadowIntegrationBlocked(
                "shadow integration is default-off; pass enable_shadow=True to score (still no tools)"
            )

    def call_tool(self, name: str, payload: Mapping[str, Any] | None = None) -> None:
        self.tool_calls_attempted += 1
        raise ShadowIntegrationBlocked(
            f"tool call '{name}' refused — shadow path is instrumented no-tool-call"
        )

    def actuate(self, action: str) -> None:
        self.tool_calls_attempted += 1
        raise ShadowIntegrationBlocked(
            f"actuation '{action}' refused — shadow path is never actuating"
        )

    def receipt_for(self, record: Mapping[str, Any]) -> dict[str, Any]:
        self._require_enabled()
        result = recommend(record)
        return {
            "router": result.policy,
            "policy_note": result.note,
            "recommendation": result.recommendation,
            "observed": result.observed,
            "agree": result.agree,
            "confidence": result.confidence,
            "actuated": False,
            "tool_calls_attempted": self.tool_calls_attempted,
            "tool_calls_executed": self.tool_calls_executed,
            "actuations_executed": self.actuations_executed,
            "no_tool_call_proof": self.tool_calls_executed == 0 and self.actuations_executed == 0,
            "default_off_boundary": not self.tool_calls_allowed,
            "label_quality": record.get("label_quality", "unknown"),
            "status": "SHADOW_ONLY",
        }


def run_shadow_integration(
    source: str | Path,
    output: str | Path,
    *,
    enable_shadow: bool = False,
    allow_replace: bool = False,
) -> int:
    if not enable_shadow:
        raise ShadowIntegrationBlocked(
            "shadow integration is default-off; pass enable_shadow=True (still non-actuating)"
        )
    from training.io_guard import open_write

    si = ShadowIntegration(enabled=True)
    count = 0
    with open_write(output, protected=(source,), allow_replace=allow_replace) as out:
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            receipt = si.receipt_for(json.loads(line))
            out.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            count += 1
    return count
