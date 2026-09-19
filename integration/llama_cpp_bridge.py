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

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class LlamaCppConfig:
    """Configuration for llama.cpp server connection.

    Attributes
    ----------
    base_url:
        URL of the llama-server. Default: http://127.0.0.1:8080
        Override via VIVY_LLAMA_URL env var.
    model_name:
        Model identifier sent to /v1/chat/completions. Default: "gemma4-e4b"
    temperature:
        Sampling temperature. 0.15 for ViVy (deterministic-ish).
    top_p:
        Nucleus sampling. 0.9.
    max_tokens:
        Maximum tokens to generate per response.
    timeout_s:
        HTTP request timeout in seconds.
    num_ctx:
        Context window size. Gemma 4 E4B supports 128K.
    """

    base_url: str = field(
        default_factory=lambda: os.environ.get("VIVY_LLAMA_URL", "http://127.0.0.1:8080")
    )
    model_name: str = field(
        default_factory=lambda: os.environ.get("VIVY_MODEL", "gemma4-e4b")
    )
    temperature: float = 0.15
    top_p: float = 0.9
    max_tokens: int = 2048
    timeout_s: float = 120.0
    num_ctx: int = 32768  # 32K default; Gemma 4 E4B supports 128K


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
    """

    content: str
    tool_calls: list[dict[str, Any]]
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    elapsed_ms: float
    raw: dict[str, Any]

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


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
        """Ping llama-server health endpoint. Returns True if server is up."""
        try:
            r = self._client.get(f"{self.config.base_url}/health", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        stream: bool = False,
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
            If True, stream tokens (not yet implemented in this bridge).

        Returns
        -------
        ChatResponse
        """
        if tools is None:
            tools = self.VIVY_TOOLS

        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": [m.to_api_dict() for m in messages],
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        t0 = time.perf_counter()
        try:
            response = self._client.post(
                f"{self.config.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"LlamaCppBridge: HTTP {e.response.status_code} from llama-server: {e.response.text[:200]}"
            ) from e
        except httpx.ConnectError:
            raise RuntimeError(
                f"LlamaCppBridge: Cannot connect to llama-server at {self.config.base_url}. "
                "Is `llama-server` running? See scripts/setup_vivy.ps1"
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        raw = response.json()

        choice = raw["choices"][0]
        msg = choice["message"]
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        finish_reason = choice.get("finish_reason", "stop")
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
        )

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

    def __enter__(self) -> "LlamaCppBridge":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
