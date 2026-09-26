"""C09 thinking-budget A/B — server-side verify of 0 / 384 / 1024.

A budget result is `PASS` only when the server echoes the requested budget and
reports the thinking-token count. Missing server fields are `NOT_RUN`, never
`PASS`. Self-attestation is not verification.

Changelog:
    24/09/2026 (Claude Code — P4 C09): Initial.
"""
from __future__ import annotations

from typing import Any

BUDGETS = (0, 384, 1024)


def verify_server_thinking(
    *,
    requested_budget_tokens: int,
    server_reported_thinking_tokens: int | None,
    server_reported_budget: int | None,
) -> dict[str, Any]:
    if server_reported_thinking_tokens is None or server_reported_budget is None:
        return {
            "verdict": "NOT_RUN",
            "verified": False,
            "requested_budget_tokens": requested_budget_tokens,
            "reason": "server did not report thinking tokens / budget — not a PASS",
        }
    budget_match = int(server_reported_budget) == int(requested_budget_tokens)
    if not budget_match:
        return {
            "verdict": "FAIL",
            "verified": False,
            "requested_budget_tokens": requested_budget_tokens,
            "server_reported_budget": server_reported_budget,
            "server_reported_thinking_tokens": server_reported_thinking_tokens,
            "reason": "server-reported budget does not match the request",
        }
    if requested_budget_tokens == 0 and int(server_reported_thinking_tokens) != 0:
        return {
            "verdict": "FAIL",
            "verified": False,
            "requested_budget_tokens": 0,
            "server_reported_thinking_tokens": server_reported_thinking_tokens,
            "reason": "budget 0 must produce 0 thinking tokens",
        }
    return {
        "verdict": "PASS",
        "verified": True,
        "requested_budget_tokens": requested_budget_tokens,
        "server_reported_budget": server_reported_budget,
        "server_reported_thinking_tokens": server_reported_thinking_tokens,
    }


class ThinkingBudgetHarness:
    def __init__(self) -> None:
        self.requested_budget_tokens: int | None = None

    def arm(self, *, requested_budget_tokens: int) -> int:
        if requested_budget_tokens not in BUDGETS:
            raise ValueError(f"budget must be one of {BUDGETS}, got {requested_budget_tokens}")
        self.requested_budget_tokens = requested_budget_tokens
        return requested_budget_tokens

    def close(
        self,
        *,
        server_reported_thinking_tokens: int | None,
        server_reported_budget: int | None,
        latency_ms: float | None,
    ) -> dict[str, Any]:
        if self.requested_budget_tokens is None:
            raise RuntimeError("arm(requested_budget_tokens=…) before close")
        verdict = verify_server_thinking(
            requested_budget_tokens=self.requested_budget_tokens,
            server_reported_thinking_tokens=server_reported_thinking_tokens,
            server_reported_budget=server_reported_budget,
        )
        record = {
            "budget": self.requested_budget_tokens,
            "verdict": verdict["verdict"],
            "server_side_verified": verdict["verified"],
            "self_attested": False,
            "latency_ms": latency_ms if verdict["verified"] else None,
            "verify": verdict,
            "status_label": "VERIFIED_RESULT" if verdict["verified"] else "NOT_RUN",
        }
        self.requested_budget_tokens = None
        return record
