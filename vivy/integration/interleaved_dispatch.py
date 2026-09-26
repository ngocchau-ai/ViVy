"""
Interleaved Dispatch — ViVy P3.

In-memory tool-calling loop: chat → ToolDispatcher → CautreoContextMemory (C-ABI),
interleaved with the LLM turns. Replaces the file-JSON handoff round-trip as the
primary result path. File write remains available as a secondary export only.

Pipeline:
  bridge.chat_safe(messages)
  → tool_calls list
  → ToolDispatcher.dispatch_tool_calls()   (in-process engine + cautreo_* tools)
  → results archived into CautreoContextMemory (SUMMARY)
  → tool messages appended in-memory → next chat_safe round

Gate 9: this module does not assert a latency number. Any timing claim needs a
reproducible benchmark receipt (see P5 / ACCEPTANCE_GATES.md Gate 9).

Changelog:
    23/09/2026 (Claude Code — P3 Interleaved in-memory tool dispatch): Initial.
        # [ISOLATED 23/09/2026] prior HoH handoff: write .vivy_handoff.json /
        # .vivy_last_response.json and wait for the next process to read them.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from integration.tool_dispatcher import DispatchResult, ToolDispatcher

logger = logging.getLogger(__name__)

DEFAULT_MAX_ROUNDS = 10
TOOL_ARCHIVE_KEY = "tool_archive_last"


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a dict response or an attribute-bearing object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class InterleavedResult:
    """Outcome of one interleaved in-memory dispatch run."""

    final_content: str
    rounds: int
    dispatch_results: list[DispatchResult] = field(default_factory=list)
    hit_round_limit: bool = False
    memory_archive_id: str | None = None
    tool_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_content": self.final_content,
            "rounds": self.rounds,
            "hit_round_limit": self.hit_round_limit,
            "memory_archive_id": self.memory_archive_id,
            "tool_names": list(self.tool_names),
            "dispatch_count": len(self.dispatch_results),
            "failed_count": sum(1 for dr in self.dispatch_results if not dr.ok),
        }


class InterleavedDispatchLoop:
    """Run chat → dispatch → chat entirely in-process.

    Parameters
    ----------
    bridge:
        Object with ``chat_safe(messages, **kwargs) -> response``. The response
        may be a dict or any object exposing ``content`` / ``tool_calls`` /
        ``finish_reason``.
    dispatcher:
        ToolDispatcher used to execute tool calls.
    context_memory:
        Optional CautreoContextMemory. When bound, each run archives tool
        results under SUMMARY (C-ABI put) so later readers skip the file path.
    max_rounds:
        Hard cap on LLM turns. Hit → ``hit_round_limit=True``.
    """

    def __init__(
        self,
        bridge: Any,
        dispatcher: ToolDispatcher | None = None,
        context_memory: Any | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
    ) -> None:
        self._bridge = bridge
        self._dispatcher = dispatcher or ToolDispatcher()
        self._context_memory = context_memory
        self._max_rounds = max(1, int(max_rounds))

    def run(self, messages: list[Any], **chat_kwargs: Any) -> InterleavedResult:
        """Execute the interleaved loop. Mutates ``messages`` in place."""
        rounds = 0
        all_dispatch: list[DispatchResult] = []
        tool_names: list[str] = []
        final_content = ""

        while rounds < self._max_rounds:
            rounds += 1
            response = self._bridge.chat_safe(messages, **chat_kwargs)
            content = _get(response, "content") or ""
            tool_calls = _get(response, "tool_calls") or []
            finish_reason = _get(response, "finish_reason") or ""

            if not tool_calls:
                final_content = content
                return InterleavedResult(
                    final_content=final_content,
                    rounds=rounds,
                    dispatch_results=all_dispatch,
                    hit_round_limit=False,
                    memory_archive_id=self._archive(all_dispatch, tool_names),
                    tool_names=tool_names,
                )

            dispatch_results = self._dispatcher.dispatch_tool_calls(tool_calls)
            all_dispatch.extend(dispatch_results)
            for dr in dispatch_results:
                tool_names.append(dr.tool_name)

            messages.append({"role": "assistant", "content": content or ""})
            for dr in dispatch_results:
                messages.append(
                    {
                        "role": "tool",
                        "content": dr.to_tool_response_content(),
                        "tool_call_id": dr.tool_call_id,
                    }
                )

            if finish_reason == "stop":
                final_content = content
                return InterleavedResult(
                    final_content=final_content,
                    rounds=rounds,
                    dispatch_results=all_dispatch,
                    hit_round_limit=False,
                    memory_archive_id=self._archive(all_dispatch, tool_names),
                    tool_names=tool_names,
                )

        # Round limit: report honestly, do not invent a final answer.
        return InterleavedResult(
            final_content="",
            rounds=rounds,
            dispatch_results=all_dispatch,
            hit_round_limit=True,
            memory_archive_id=self._archive(all_dispatch, tool_names),
            tool_names=tool_names,
        )

    def _archive(
        self,
        dispatch_results: list[DispatchResult],
        tool_names: list[str],
    ) -> str | None:
        """Persist a compact tool-result summary into Cautreo (SUMMARY kind)."""
        if self._context_memory is None or not dispatch_results:
            return None
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "tool_names": list(tool_names),
            "results": [
                {
                    "tool_name": dr.tool_name,
                    "tool_call_id": dr.tool_call_id,
                    "ok": dr.ok,
                    "elapsed_ms": dr.elapsed_ms,
                }
                for dr in dispatch_results
            ],
        }
        try:
            self._context_memory.store_summary(
                TOOL_ARCHIVE_KEY, json.dumps(payload, ensure_ascii=False)
            )
            return TOOL_ARCHIVE_KEY
        except Exception as e:  # pragma: no cover - native put can fail closed
            logger.warning("InterleavedDispatchLoop._archive failed: %s", e)
            return None
