"""
Tool Dispatcher — ViVy Sprint 3.

Map DirectiveExecutionTuple.opcode → engine primitive call.
ViVy Core quyết định action, ToolDispatcher thực thi.

Pipeline:
  LlamaCppBridge.chat() → tool_calls list
  → ToolDispatcher.dispatch_tool_calls() → PrimitiveResult list
  → GraphBridge.evaluate() / record_falsified()

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from engine.primitives import (
    PrimitiveResult,
    engine_cache_control,
    engine_exec,
    engine_file_io,
    engine_media_slice,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class DispatchResult:
    """Result of dispatching one or more tool calls.

    Attributes
    ----------
    tool_name:
        Name of the tool that was called.
    primitive_result:
        PrimitiveResult from the engine primitive.
    tool_call_id:
        The ID from the LLM tool call (for conversation continuity).
    elapsed_ms:
        Wall-clock time of dispatch.
    """

    tool_name: str
    primitive_result: PrimitiveResult
    tool_call_id: str
    elapsed_ms: float

    @property
    def ok(self) -> bool:
        return self.primitive_result.ok

    def to_tool_response_content(self) -> str:
        """Format result as tool response content for the next LLM turn."""
        if self.primitive_result.ok:
            data = self.primitive_result.data
            if isinstance(data, bytes):
                content = f"[binary data: {len(data)} bytes]"
            elif isinstance(data, dict):
                content = json.dumps(data, ensure_ascii=False, indent=2)
            else:
                content = str(data)
            return content
        else:
            return f"ERROR: {self.primitive_result.error_message}"


# ---------------------------------------------------------------------------
# ToolDispatcher
# ---------------------------------------------------------------------------


class ToolDispatcher:
    """Dispatch LLM tool_call requests to ViVy engine primitives.

    The model (Gemma 4 E4B) may request tool calls in the format:
        {
            "id": "call_abc",
            "type": "function",
            "function": {
                "name": "engine_file_io",
                "arguments": "{\"action\": \"read\", \"path\": \"/tmp/data.txt\"}"
            }
        }

    ToolDispatcher parses these and routes to the correct engine primitive.

    Parameters
    ----------
    allowed_tools:
        Optional whitelist of tool names. If None, all tools are allowed.
    """

    # Supported tool → handler mapping
    _TOOL_HANDLERS: dict[str, Any] = {
        "engine_file_io": "_dispatch_file_io",
        "engine_exec": "_dispatch_exec",
        "engine_media_slice": "_dispatch_media_slice",
        "engine_cache_control": "_dispatch_cache_control",
        "knowledge_forage": "_dispatch_knowledge_forage",
    }

    def __init__(self, allowed_tools: list[str] | None = None) -> None:
        self._allowed = set(allowed_tools) if allowed_tools else None

    def dispatch_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[DispatchResult]:
        """Dispatch a list of tool_call requests (from LLM response).

        Parameters
        ----------
        tool_calls:
            List of tool call dicts from ChatResponse.tool_calls.

        Returns
        -------
        List of DispatchResult, one per tool call.
        """
        results: list[DispatchResult] = []
        for tc in tool_calls:
            result = self._dispatch_one(tc)
            results.append(result)
            if not result.ok:
                logger.warning(
                    "ToolDispatcher: tool=%s FAILED: %s",
                    result.tool_name,
                    result.primitive_result.error_message,
                )
        return results

    def _dispatch_one(self, tc: dict[str, Any]) -> DispatchResult:
        """Dispatch a single tool call."""
        call_id = tc.get("id", "unknown")
        fn_info = tc.get("function", {})
        tool_name = fn_info.get("name", "")
        raw_args = fn_info.get("arguments", "{}")

        t0 = time.perf_counter()

        # Parse args
        try:
            args: dict[str, Any] = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError as e:
            result = PrimitiveResult(ok=False, data=None, error_message=f"Invalid JSON args: {e}", elapsed_ms=0.0)
            return DispatchResult(tool_name=tool_name, primitive_result=result, tool_call_id=call_id, elapsed_ms=0.0)

        # Check allowed list
        if self._allowed and tool_name not in self._allowed:
            result = PrimitiveResult(
                ok=False, data=None,
                error_message=f"Tool '{tool_name}' not in allowed list",
                elapsed_ms=0.0,
            )
            return DispatchResult(tool_name=tool_name, primitive_result=result, tool_call_id=call_id, elapsed_ms=0.0)

        # Dispatch
        handler_name = self._TOOL_HANDLERS.get(tool_name)
        if handler_name is None:
            result = PrimitiveResult(
                ok=False, data=None,
                error_message=f"Unknown tool: '{tool_name}'",
                elapsed_ms=0.0,
            )
        else:
            handler = getattr(self, handler_name)
            try:
                result = handler(args)
            except Exception as e:
                logger.exception("ToolDispatcher._dispatch_one: tool=%s exception", tool_name)
                result = PrimitiveResult(ok=False, data=None, error_message=str(e), elapsed_ms=0.0)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return DispatchResult(
            tool_name=tool_name,
            primitive_result=result,
            tool_call_id=call_id,
            elapsed_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _dispatch_file_io(self, args: dict[str, Any]) -> PrimitiveResult:
        return engine_file_io(
            action=args["action"],
            path=args["path"],
            content=args.get("content"),
            offset=args.get("offset", 0),
        )

    def _dispatch_exec(self, args: dict[str, Any]) -> PrimitiveResult:
        return engine_exec(
            command=args["command"],
            cwd=args.get("cwd"),
            env=args.get("env"),
            timeout_s=float(args.get("timeout_s", 30.0)),
        )

    def _dispatch_media_slice(self, args: dict[str, Any]) -> PrimitiveResult:
        return engine_media_slice(
            source_path=args["source_path"],
            start_ms=float(args["start_ms"]),
            end_ms=float(args["end_ms"]),
            output_path=args.get("output_path"),
        )

    def _dispatch_cache_control(self, args: dict[str, Any]) -> PrimitiveResult:
        return engine_cache_control(
            action=args["action"],
            key=args.get("key"),
            value=args.get("value"),
        )

    def _dispatch_knowledge_forage(self, args: dict[str, Any]) -> PrimitiveResult:
        """Stub: Knowledge foraging trigger.

        In production this would kick off the Forager module.
        Returns a placeholder until ForagerIntegration is wired.
        """
        topic = args.get("topic", "")
        source_hint = args.get("source_hint", "")
        logger.info("ToolDispatcher: knowledge_forage triggered for topic='%s'", topic)
        # TODO: wire to forager/ module in Phase 2
        return PrimitiveResult(
            ok=True,
            data={"status": "foraging_stub", "topic": topic, "source_hint": source_hint,
                  "note": "ForagerIntegration not yet wired — returning stub"},
            error_message=None,
            elapsed_ms=0.0,
        )
