"""
llama.cpp HTTP Bridge — ViVy Sprint 3.

Thin OpenAI-compatible client cho llama.cpp server (`llama-server`).
Không có LangChain, không có wrapper. Chỉ stdlib + httpx.

llama-server expose /v1/chat/completions theo OpenAI spec — Gemma 4 E4B
hỗ trợ vision + audio + tool calling qua JSON schema.

Cách dùng:
    bridge = LlamaCppBridge()
    response = bridge.chat([
        ChatMessage(role="system", content="..."),
        ChatMessage(role="user", content="Hello"),
    ])
    print(response.content)

CAUTREO Boundary Contract (Sync from vivyChatGPT, 2026-09-21):
    Nếu llama-server unreachable hoặc timeout → emit DELEGATE signal thay vì
    raise hard exception. Process success ≠ semantic cognition.
    Xem: fallback_to_delegate() và chat_safe().

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
    21/09/2026 (Antigravity IDE, Sync S2): Added fallback_to_delegate(), chat_safe(),
        DelegateSignal. Mirrors CAUTREO fail-fast contract from vivyChatGPT.
    23/09/2026 (Claude Code — P1 Dynamic Thinking Budget): Per-request thinking
        budget via orchestrator.thinking_budget (0/384/1024). # [ISOLATED 23/09/2026]
        prior payload: 'chat_template_kwargs={"enable_thinking": False}' hardcoded.
    29/09/2026 (Claude Code — WP-3 / O-04): Config nay lấy từ
        llm_bridge.backend.LLMBackend — MỘT cấu hình URL / model-id / timeout /
        num_ctx (F-A09). Timeout tách riêng LLMTimeoutError (không gộp vào lỗi
        suy luận). ChatResponse mang backend_id + model_id để mọi receipt ghi
        đúng model đã trả lời (F-B06).
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from llm_bridge.backend import LLMBackend, LLMTimeoutError
from orchestrator.thinking_budget import (
    build_thinking_payload_fields,
    resolve_budget_from,
)

_GEMMA_TOOL_RE = re.compile(
    r"<\|tool_call\>call:(?P<name>[A-Za-z_][\w.-]*)\{(?P<body>.*?)\}<tool_call\|>",
    re.DOTALL,
)


def _parse_gemma_native_tool_calls(content: str) -> list[dict[str, Any]]:
    """Adapt Gemma4 PEG tool text to the existing OpenAI shape."""
    def fields(text: str) -> list[str]:
        parts, start, depth, quoted = [], 0, 0, False
        for index, char in enumerate(text):
            if char == '"' and (index == 0 or text[index - 1] != "\\"):
                quoted = not quoted
            elif not quoted and char == "{":
                depth += 1
            elif not quoted and char == "}":
                depth -= 1
            elif not quoted and char == "," and depth == 0:
                parts.append(text[start:index].strip())
                start = index + 1
        if depth or quoted:
            raise ValueError("unbalanced PEG value")
        tail = text[start:].strip()
        if tail:
            parts.append(tail)
        return parts

    def value(text: str) -> Any:
        text = text.strip().strip('"')
        if text.startswith("{") and text.endswith("}"):
            return object_value(text[1:-1])
        return text

    def object_value(text: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in fields(text):
            key, separator, raw = item.partition(":")
            if not separator or not key.strip():
                raise ValueError("invalid PEG field")
            result[key.strip()] = value(raw)
        return result

    calls: list[dict[str, Any]] = []
    for index, match in enumerate(_GEMMA_TOOL_RE.finditer(content)):
        try:
            arguments = object_value(match.group("body").strip())
        except ValueError:
            return []
        calls.append({
            "id": f"gemma-call-{index}",
            "type": "function",
            "function": {
                "name": match.group("name"),
                "arguments": json.dumps(arguments, ensure_ascii=False),
            },
        })
    return calls

logger = logging.getLogger(__name__)


def build_request_payload(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    top_p: float,
    max_tokens: int,
    thinking_budget: int | None = None,
    epistemic_decision: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
    stream: bool = False,
) -> dict[str, Any]:
    """Build the /v1/chat/completions payload with per-request thinking budget.

    thinking_budget wins over epistemic_decision; neither → force-disable
    (historical default). See orchestrator.thinking_budget.
    """
    budget = resolve_budget_from(thinking_budget, epistemic_decision)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": stream,
        **build_thinking_payload_fields(budget),
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    return payload


def _extract_content(message: dict[str, Any]) -> str:
    """Prefer message.content; fall back to reasoning_content.

    Gemma4 can route the whole answer into reasoning_content when thinking is
    enabled. Keep the fallback so HoH QA sees the directive instead of an empty
    response.
    """
    return message.get("content") or message.get("reasoning_content") or ""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class LlamaCppConfig:
    """Configuration for the OpenAI-compatible model server.

    [REPLACED 29/09/2026 · WP-3 / F-A09] the values used to be read straight
    from env vars here, in parallel with ``llm_bridge.client`` and
    ``training.backend_registry`` — three sources of truth for one model.  They
    now come from ``llm_bridge.backend.LLMBackend`` (one URL, one model-id, one
    timeout, one num_ctx).  Field names are unchanged so existing callers and
    launchers keep working.

    The endpoint is OpenAI-compatible ``/v1/chat/completions`` at
    ``http://127.0.0.1:8080`` by default (``VIVY_LLAMA_URL``).  That contract is
    served by llama-server / Ollama during development and by ``cautreo-server``
    after the D-4 parity measurement — see ``llm_bridge.backend``.
    """

    base_url: str = field(default_factory=lambda: LLMBackend.from_env().base_url)
    model_name: str = field(default_factory=lambda: LLMBackend.from_env().model_id)
    temperature: float = field(default_factory=lambda: LLMBackend.from_env().temperature)
    top_p: float = field(default_factory=lambda: LLMBackend.from_env().top_p)
    max_tokens: int = field(default_factory=lambda: LLMBackend.from_env().max_tokens)
    timeout_s: float = field(default_factory=lambda: LLMBackend.from_env().timeout_s)
    num_ctx: int = field(default_factory=lambda: LLMBackend.from_env().num_ctx)
    backend: LLMBackend = field(default_factory=LLMBackend.from_env)

    def __post_init__(self) -> None:
        # Keep the explicit values the caller passed; only fill the identity
        # fields that are allowed to be blank.  The backend object is the SSOT
        # for *defaults*, never an override of a caller's choice.
        if not self.base_url:
            self.base_url = self.backend.base_url
        if not self.model_name:
            self.model_name = self.backend.model_id

    def identity(self) -> dict[str, Any]:
        """Receipt shard naming the backend and model that will answer."""
        return self.backend.with_model(self.model_name).identity()


# ---------------------------------------------------------------------------
# Message schema
# ---------------------------------------------------------------------------


@dataclass
class ChatMessage:
    """Single message in a conversation.

    Attributes
    ----------
    role:
        "system" | "user" | "assistant" | "tool"
    content:
        Text content of the message.
    tool_call_id:
        If role="tool", the ID of the tool call being responded to.
    images:
        List of base64-encoded image strings (for vision input).
    """

    role: str
    content: str
    tool_call_id: str | None = None
    images: list[str] = field(default_factory=list)

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize to OpenAI-compatible message dict."""
        d: dict[str, Any] = {"role": self.role}

        if self.images:
            # Gemma 4 E4B vision format: content as list of parts
            parts: list[dict[str, Any]] = []
            for img_b64 in self.images:
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                })
            parts.append({"type": "text", "text": self.content})
            d["content"] = parts
        else:
            d["content"] = self.content

        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ChatResponse:
    """Response from llama.cpp /v1/chat/completions.

    Attributes
    ----------
    content:
        Generated text content.
    tool_calls:
        List of tool call requests from the model (if any).
    finish_reason:
        "stop" | "tool_calls" | "length"
    prompt_tokens:
        Tokens used in prompt.
    completion_tokens:
        Tokens generated.
    elapsed_ms:
        Wall-clock time of the HTTP request.
    raw:
        Raw JSON response dict.
    is_delegate:
        True nếu response là DELEGATE signal (llama-server unavailable/timeout).
        Mirrors CAUTREO boundary contract: process success ≠ semantic cognition.
    delegate_reason:
        Human-readable reason for delegation (set when is_delegate=True).
    delegate_kind:
        [WP-3 29/09/2026] "timeout" | "unavailable" | "error" | "" — timeout is
        reported separately from an inference failure (acceptance: *"timeout báo
        riêng khỏi lỗi suy luận"*).  Empty on a successful response.
    backend_id / model_id:
        [WP-3 29/09/2026] what actually served this response (F-B06).  Every
        downstream receipt must carry these so an answer can never be filed
        under a model that did not produce it.
    """

    content: str
    tool_calls: list[dict[str, Any]]
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    elapsed_ms: float
    raw: dict[str, Any]
    is_delegate: bool = False
    delegate_reason: str = ""
    delegate_kind: str = ""
    backend_id: str = ""
    model_id: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# ---------------------------------------------------------------------------
# DELEGATE signal factory (CAUTREO boundary contract)
# ---------------------------------------------------------------------------


def _make_delegate_response(
    reason: str,
    elapsed_ms: float = 0.0,
    kind: str = "error",
    backend_id: str = "",
    model_id: str = "",
) -> ChatResponse:
    """Create a DELEGATE ChatResponse — used when llama-server is unavailable.

    CAUTREO contract: nếu native inference backend fails, fail-fast và emit
    DELEGATE instead of crashing. Caller (VivyInferenceLoop) decides what to do.

    This is NOT an error response — it's a structured signal that the inference
    path must be rerouted. Process failure ≠ cognitive failure.

    ``kind`` separates a timeout from any other failure (WP-3): a slow model is
    not a wrong model, and a latency budget cannot be measured if both land in
    the same bucket.
    """
    return ChatResponse(
        content=f"DELEGATE: {reason}",
        tool_calls=[],
        finish_reason="delegate",
        prompt_tokens=0,
        completion_tokens=0,
        elapsed_ms=elapsed_ms,
        raw={"delegate": True, "reason": reason, "kind": kind},
        is_delegate=True,
        delegate_reason=reason,
        delegate_kind=kind,
        backend_id=backend_id,
        model_id=model_id,
    )


# ---------------------------------------------------------------------------
# Tool schema helper
# ---------------------------------------------------------------------------


def build_tool_schema(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Build an OpenAI-compatible tool schema.

    Parameters
    ----------
    name:
        Function name (must be a valid identifier).
    description:
        Human-readable description.
    parameters:
        JSON Schema dict for the function parameters.

    Returns
    -------
    dict compatible with /v1/chat/completions `tools` field.
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


# ---------------------------------------------------------------------------
# LlamaCppBridge
# ---------------------------------------------------------------------------


class LlamaCppBridge:
    """Thin HTTP bridge to llama-server (OpenAI-compatible API).

    Connects ViVy to any llama.cpp-served model. Default target: Gemma 4 E4B.
    No wrappers, no framework. Pure httpx.

    Parameters
    ----------
    config:
        LlamaCppConfig. If None, uses defaults (reads env vars).
    """

    # ViVy engine tool schemas — sent to model on every call
    VIVY_TOOLS: list[dict[str, Any]] = [
        build_tool_schema(
            name="engine_file_io",
            description="Read, write, append, delete, or check existence of a file.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "write", "append", "delete", "exists", "mkdir"]},
                    "path": {"type": "string", "description": "Absolute or relative file path."},
                    "content": {"type": "string", "description": "Content to write (for write/append actions)."},
                },
                "required": ["action", "path"],
            },
        ),
        build_tool_schema(
            name="engine_exec",
            description="Execute a shell command and return stdout/stderr.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "array", "items": {"type": "string"}, "description": "Command and arguments list."},
                    "cwd": {"type": "string", "description": "Working directory for the command."},
                    "timeout_s": {"type": "number", "description": "Timeout in seconds. Default 30."},
                },
                "required": ["command"],
            },
        ),
        build_tool_schema(
            name="engine_media_slice",
            description="Slice a video or audio file using ffmpeg.",
            parameters={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "start_ms": {"type": "number"},
                    "end_ms": {"type": "number"},
                    "output_path": {"type": "string", "description": "Optional output path."},
                },
                "required": ["source_path", "start_ms", "end_ms"],
            },
        ),
        build_tool_schema(
            name="knowledge_forage",
            description="Trigger epistemic foraging: search for knowledge on a topic and return a brief.",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "source_hint": {"type": "string", "description": "Optional URL or file path hint."},
                },
                "required": ["topic"],
            },
        ),
    ]

    def __init__(self, config: LlamaCppConfig | None = None) -> None:
        self.config = config or LlamaCppConfig()
        self._client = httpx.Client(timeout=self.config.timeout_s)
        logger.info(
            "LlamaCppBridge: target=%s model=%s",
            self.config.base_url,
            self.config.model_name,
        )

    def health(self) -> bool:
        """Ping server health endpoint. Supports Ollama (/api/tags) and llama.cpp (/health)."""
        for path in ["/api/tags", "/health", "/"]:
            try:
                r = self._client.get(f"{self.config.base_url}{path}", timeout=3.0)
                if r.status_code == 200:
                    return True
            except Exception:
                continue
        return False

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        stream: bool = False,
        model: str | None = None,
        thinking_budget: int | None = None,
        epistemic_decision: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to llama-server.

        Parameters
        ----------
        messages:
            Conversation history.
        tools:
            Optional list of tool schemas. Defaults to ViVy engine tools.
        tool_choice:
            "auto" | "none" | "required"
        stream:
            If True, stream tokens via Server-Sent Events (SSE) to keep connection alive.
        model:
            Optional model override (e.g. coding specialist model).
        thinking_budget:
            Per-request thinking tokens (0 / 384 / 1024). None + no decision → 0.
        epistemic_decision:
            Optional decision used to resolve the budget when thinking_budget is None.

        Returns
        -------
        ChatResponse
        """
        if tools is None:
            tools = self.VIVY_TOOLS

        target_model = model or self.config.model_name
        payload = build_request_payload(
            model=target_model,
            messages=[m.to_api_dict() for m in messages],
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_tokens=self.config.max_tokens,
            thinking_budget=thinking_budget,
            epistemic_decision=epistemic_decision,
            tools=tools,
            tool_choice=tool_choice,
            stream=False,
        )

        t0 = time.perf_counter()
        if stream:
            return self._chat_streaming(payload, t0)

        try:
            response = self._client.post(
                f"{self.config.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            # WP-3: timeout is its own verdict, never filed as a reasoning error.
            raise LLMTimeoutError(
                f"LlamaCppBridge: request timed out after {self.config.timeout_s}s "
                f"(model={target_model}, url={self.config.base_url})"
            ) from exc
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"LlamaCppBridge: HTTP {e.response.status_code} from llama-server: {e.response.text[:200]}"
            ) from e
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"LlamaCppBridge: Cannot connect to llama-server at {self.config.base_url}. "
                "Is `llama-server` running? See scripts/setup_vivy.ps1"
            ) from exc

        elapsed_ms = (time.perf_counter() - t0) * 1000
        raw = response.json()

        choice = raw["choices"][0]
        msg = choice["message"]
        content = _extract_content(msg)
        tool_calls = msg.get("tool_calls") or []
        finish_reason = choice.get("finish_reason", "stop")
        if not tool_calls and content:
            tool_calls = _parse_gemma_native_tool_calls(content)
            if tool_calls:
                finish_reason = "tool_calls"
        usage = raw.get("usage", {})

        logger.debug(
            "LlamaCppBridge.chat: finish=%s tools=%d tokens=%d+%d %.0fms",
            finish_reason,
            len(tool_calls),
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            elapsed_ms,
        )

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            elapsed_ms=elapsed_ms,
            raw=raw,
            backend_id=self.config.backend.backend_id,
            # Prefer the id the server echoed back: that is the model that
            # actually answered (F-B06 — never file another model's output
            # under the requested identity).
            model_id=str(raw.get("model") or target_model),
        )

    def _chat_streaming(self, payload: dict[str, Any], t0: float) -> ChatResponse:
        """Stream chat completions via SSE, keeping socket alive with every token."""
        payload["stream"] = True
        accumulated_content: list[str] = []
        tool_calls_map: dict[int, dict[str, Any]] = {}
        finish_reason = "stop"
        prompt_tokens = 0
        completion_tokens = 0

        try:
            with self._client.stream(
                "POST",
                f"{self.config.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    line_str = line.strip()
                    if line_str.startswith("data: "):
                        line_str = line_str[6:].strip()
                    if line_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line_str)
                    except Exception:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta", {})
                    if "content" in delta and delta["content"]:
                        accumulated_content.append(delta["content"])
                        completion_tokens += 1

                    if "tool_calls" in delta and delta["tool_calls"]:
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_map:
                                tool_calls_map[idx] = {
                                    "id": tc.get("id", f"call_{idx}"),
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            if "function" in tc:
                                fn = tc["function"]
                                if "name" in fn and fn["name"]:
                                    tool_calls_map[idx]["function"]["name"] += fn["name"]
                                if "arguments" in fn and fn["arguments"]:
                                    tool_calls_map[idx]["function"]["arguments"] += fn["arguments"]

                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

                    if "usage" in chunk and chunk["usage"]:
                        prompt_tokens = chunk["usage"].get("prompt_tokens", prompt_tokens)
                        completion_tokens = chunk["usage"].get("completion_tokens", completion_tokens)

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"LlamaCppBridge: HTTP {e.response.status_code} from llama-server: {e.response.text[:200]}"
            ) from e
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"LlamaCppBridge: Cannot connect to llama-server at {self.config.base_url}. "
                "Is `llama-server` running? See scripts/setup_vivy.ps1"
            ) from exc

        elapsed_ms = (time.perf_counter() - t0) * 1000
        content_str = "".join(accumulated_content)
        tool_calls = list(tool_calls_map.values())

        logger.debug(
            "LlamaCppBridge.chat(stream): finish=%s tools=%d tokens=%d %.0fms",
            finish_reason,
            len(tool_calls),
            completion_tokens,
            elapsed_ms,
        )

        return ChatResponse(
            content=content_str,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            elapsed_ms=elapsed_ms,
            raw={"streamed": True},
            backend_id=self.config.backend.backend_id,
            model_id=str(payload.get("model") or self.config.model_name),
        )

    def backend_identity(self) -> dict[str, Any]:
        """Receipt shard: which backend and model will answer the next call.

        [WP-3 29/09/2026] every receipt carries this (F-A09 / F-B06).  Callers
        should stamp it into ActivityLog / evidence packets rather than naming
        a model by hand.
        """
        return self.config.identity()

    def list_models(self) -> list[str]:
        """List models available on the llama-server."""
        try:
            r = self._client.get(f"{self.config.base_url}/v1/models", timeout=5.0)
            r.raise_for_status()
            data = r.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.warning("LlamaCppBridge.list_models: %s", e)
            return []

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    # ------------------------------------------------------------------
    # CAUTREO boundary contract: fail-fast → DELEGATE
    # ------------------------------------------------------------------

    def chat_safe(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        model: str | None = None,
        stream: bool = False,
        thinking_budget: int | None = None,
        epistemic_decision: str | None = None,
    ) -> ChatResponse:
        """Like chat(), but returns a DELEGATE signal instead of raising on failure.

        Mirrors CAUTREO boundary contract from vivyChatGPT:
            If native inference backend is unreachable or times out → fail-fast,
            persist DELEGATE state, do NOT raise. VivyInferenceLoop decides routing.

        CRITICAL: Process success ≠ semantic cognition.
            A non-delegate response means llama-server responded — it does NOT
            guarantee semantic correctness of the output.

        Parameters
        ----------
        messages:
            Conversation history.
        tools:
            Optional tool schemas. Defaults to ViVy engine tools.
        tool_choice:
            "auto" | "none" | "required"
        model:
            Optional model override.
        stream:
            If True, stream tokens via SSE to keep connection alive.
        thinking_budget:
            Per-request thinking tokens (0 / 384 / 1024).
        epistemic_decision:
            Optional decision used to resolve the budget when thinking_budget is None.

        Returns
        -------
        ChatResponse with is_delegate=False on success,
        or is_delegate=True with delegate_reason on failure.
        """
        t0 = time.perf_counter()
        backend_id = self.config.backend.backend_id
        model_id = model or self.config.model_name
        try:
            return self.chat(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                model=model,
                stream=stream,
                thinking_budget=thinking_budget,
                epistemic_decision=epistemic_decision,
            )
        except LLMTimeoutError as e:
            # WP-3 acceptance: "timeout báo riêng khỏi lỗi suy luận".
            elapsed_ms = (time.perf_counter() - t0) * 1000
            reason = str(e)
            logger.warning(
                "LlamaCppBridge.chat_safe: DELEGATE(timeout) — %s (%.0fms)",
                reason[:120], elapsed_ms,
            )
            return _make_delegate_response(
                reason=reason, elapsed_ms=elapsed_ms, kind="timeout",
                backend_id=backend_id, model_id=model_id,
            )
        except RuntimeError as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            reason = str(e)
            kind = "unavailable" if "Cannot connect" in reason else "error"
            logger.warning(
                "LlamaCppBridge.chat_safe: DELEGATE(%s) — %s (%.0fms)",
                kind, reason[:120], elapsed_ms,
            )
            return _make_delegate_response(
                reason=reason, elapsed_ms=elapsed_ms, kind=kind,
                backend_id=backend_id, model_id=model_id,
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - t0) * 1000
            reason = f"Unexpected: {type(e).__name__}: {e}"
            logger.error(
                "LlamaCppBridge.chat_safe: DELEGATE (unexpected) — %s", reason[:120]
            )
            return _make_delegate_response(
                reason=reason, elapsed_ms=elapsed_ms, kind="error",
                backend_id=backend_id, model_id=model_id,
            )

    def fallback_to_delegate(self, reason: str) -> ChatResponse:
        """Explicitly emit a DELEGATE signal (e.g., caller detects model output is wrong).

        Use this when llama-server responded but output is semantically incorrect
        (e.g., Gemma4 native forward returns wrong first token). Matches the
        CAUTREO pattern: UNVERIFIED → DELEGATE, not a crash.
        """
        logger.info("LlamaCppBridge.fallback_to_delegate: reason=%s", reason[:80])
        return _make_delegate_response(
            reason=reason,
            kind="error",
            backend_id=self.config.backend.backend_id,
            model_id=self.config.model_name,
        )

    def __enter__(self) -> LlamaCppBridge:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
