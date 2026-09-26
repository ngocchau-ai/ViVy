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
    context_memory:
        Optional CautreoContextMemory for cautreo_put / cautreo_get tools.
    """

    # Supported tool → handler mapping
    _TOOL_HANDLERS: dict[str, Any] = {
        "engine_file_io": "_dispatch_file_io",
        "engine_exec": "_dispatch_exec",
        "engine_media_slice": "_dispatch_media_slice",
        "engine_cache_control": "_dispatch_cache_control",
        "knowledge_forage": "_dispatch_knowledge_forage",
        "cautreo_put": "_dispatch_cautreo_put",
        "cautreo_get": "_dispatch_cautreo_get",
    }

    def __init__(
        self,
        allowed_tools: list[str] | None = None,
        context_memory: Any | None = None,
    ) -> None:
        self._allowed = set(allowed_tools) if allowed_tools else None
        self._context_memory = context_memory

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
            cmd=args["command"],
            cwd=args.get("cwd"),
            env=args.get("env"),
            timeout=float(args.get("timeout_s", 30.0)),
        )

    def _dispatch_media_slice(self, args: dict[str, Any]) -> PrimitiveResult:
        return engine_media_slice(
            source=args["source_path"],
            start_ms=float(args["start_ms"]),
            end_ms=float(args["end_ms"]),
            output_path=args.get("output_path"),
        )

    def _dispatch_cache_control(self, args: dict[str, Any]) -> PrimitiveResult:
        return engine_cache_control(
            op=args.get("op") or args.get("action") or "stats",
            scope=args.get("scope") or args.get("key") or "transient",
            artifact_path=args.get("artifact_path") or args.get("value"),
            chunk_ids=args.get("chunk_ids"),
        )

    def _dispatch_cautreo_put(self, args: dict[str, Any]) -> PrimitiveResult:
        """Store an item into Cautreo native context memory."""
        if self._context_memory is None:
            return PrimitiveResult(
                ok=False,
                error_message="Cautreo context_memory not available",
                elapsed_ms=0.0,
            )
        item_id = args.get("item_id") or args.get("id") or ""
        content = args.get("content") or ""
        kind_str = (args.get("kind") or "HARD_FACT").upper()
        if not item_id:
            return PrimitiveResult(ok=False, error_message="item_id required", elapsed_ms=0.0)
        try:
            from integration.cautreo_binding import CautreoMemoryKind
            kind = CautreoMemoryKind[kind_str]
        except (ImportError, KeyError):
            return PrimitiveResult(
                ok=False,
                error_message=f"Unknown memory kind: {kind_str}",
                elapsed_ms=0.0,
            )
        try:
            self._context_memory.put(item_id, kind, content)
            return PrimitiveResult(
                ok=True,
                data={"item_id": item_id, "kind": kind_str, "stored": True},
                error_message="",
                elapsed_ms=0.0,
            )
        except Exception as e:
            return PrimitiveResult(ok=False, error_message=str(e), elapsed_ms=0.0)

    def _dispatch_cautreo_get(self, args: dict[str, Any]) -> PrimitiveResult:
        """Retrieve an item from Cautreo native context memory."""
        if self._context_memory is None:
            return PrimitiveResult(
                ok=False,
                error_message="Cautreo context_memory not available",
                elapsed_ms=0.0,
            )
        item_id = args.get("item_id") or args.get("id") or ""
        if not item_id:
            return PrimitiveResult(ok=False, error_message="item_id required", elapsed_ms=0.0)
        try:
            item = self._context_memory.get(item_id)
            if item is None:
                return PrimitiveResult(
                    ok=False,
                    error_message=f"Item '{item_id}' not found in Cautreo memory",
                    elapsed_ms=0.0,
                )
            return PrimitiveResult(
                ok=True,
                data={"id": item.id, "kind": int(item.kind), "content": item.content},
                error_message="",
                elapsed_ms=0.0,
            )
        except Exception as e:
            return PrimitiveResult(ok=False, error_message=str(e), elapsed_ms=0.0)

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
            error_message="",
            elapsed_ms=0.0,
        )
