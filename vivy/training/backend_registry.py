"""C01 backend registry — real backends only, every request tagged, no silent fallback.

Enumerates the real inference surfaces in this workspace:
  * llama-server  (llama.cpp / Ollama OpenAI-compatible HTTP, default :8080)
  * native-cautreo (native CAUTREO forward — semantic parity UNVERIFIED)
  * unitary-llm-client (OpenAI-compatible delegate pool via llm_bridge.client)

`LLMClient.chat(..., fallback=True)` is [ISOLATED] for C01: it silently walks a
17-model catalogue, which would file another model's answer under the requested
identity (acceptance plan §2.1 / C01 "no silent fallback"). Use
`make_unitary_fn(model=...)` — it calls with fallback=False and maps
ModelUnavailableError to BackendError("wrong_alias"|"unavailable").

Changelog:
    24/09/2026 (Claude Code — P1 C01): Initial.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from training.backend_baseline import BackendError, BackendIdentity

# Decoding config that must travel with every identity (C01: record decoding config).
DEFAULT_DECODING = {
    "temperature": 0.15,
    "top_p": 0.9,
    "max_tokens": 2048,
    "timeout_s": 180.0,
}


def config_hash(decoding: Mapping[str, Any] | None = None) -> str:
    payload = dict(DEFAULT_DECODING)
    if decoding:
        payload.update(decoding)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RegisteredBackend:
    identity: BackendIdentity
    describe: str
    # "reference-candidate" | "isolated-unverified" | "delegate-pool"
    role: str


def enumerate_backends(*, decoding: Mapping[str, Any] | None = None) -> list[RegisteredBackend]:
    """List real backends. Do not invent backends that are not wired in this tree."""
    chash = config_hash(decoding)
    llama_url = os.environ.get("VIVY_LLAMA_URL", "http://127.0.0.1:8080")
    llama_model = os.environ.get("VIVY_MODEL", "gemma4-e4b")
    unitary_url = os.environ.get("UNITARY_API_BASE", "http://localhost:8000/v1")
    unitary_model = os.environ.get("UNITARY_DEFAULT_MODEL", "gpt-4o-mini")
    return [
        RegisteredBackend(
            identity=BackendIdentity(
                backend_id="llama-server",
                model_alias=llama_model,
                model_hash="",  # filled by live probe when /v1/models is reachable
                config_hash=chash,
                base_url=llama_url,
                extra={"bridge": "vivy/integration/llama_cpp_bridge.py",
                       "thinking_budget_default": 1024},
            ),
            describe="llama.cpp / Ollama OpenAI-compatible HTTP server (C01 reference candidate)",
            role="reference-candidate",
        ),
        RegisteredBackend(
            identity=BackendIdentity(
                backend_id="native-cautreo",
                model_alias=llama_model,
                model_hash="",
                config_hash=chash,
                base_url="native://cautreo",
                extra={
                    "semantic_parity": "UNVERIFIED",
                    "known_gap_receipts": [
                        "VIVY-CAUTREO-GEMMA4-CHAT-188",
                        "VIVY-CAUTREO-GEMMA4-CHAT-171",
                        "VIVY-CAUTREO-GEMMA4-EXACT-PROMPT-196",
                    ],
                    "scope": "native CAUTREO only — NOT llama-server :8080 (§2.1)",
                },
            ),
            describe="Native CAUTREO forward. Semantic gap isolated; do not generalize (§2.1).",
            role="isolated-unverified",
        ),
        RegisteredBackend(
            identity=BackendIdentity(
                backend_id="unitary-llm-client",
                model_alias=unitary_model,
                model_hash="",
                config_hash=chash,
                base_url=unitary_url,
                extra={
                    "fallback": False,  # C01: never silent-fallback
                    "isolated_path": "LLMClient.chat(fallback=True) walks 17 models — DO NOT USE",
                    "catalogue_size": 17,
                },
            ),
            describe="OpenAI-compatible delegate pool (unitary). Single model only.",
            role="delegate-pool",
        ),
    ]


def get_backend(backend_id: str) -> RegisteredBackend:
    for item in enumerate_backends():
        if item.identity.backend_id == backend_id:
            return item
    raise KeyError(f"unknown backend_id: {backend_id!r}")


# ---------------------------------------------------------------------------
# Live adapters — stdlib only, map transport errors to distinct verdicts
# ---------------------------------------------------------------------------


def make_llama_server_fn(
    *,
    base_url: str | None = None,
    model_alias: str | None = None,
    timeout_s: float = 180.0,
    temperature: float = 0.15,
    top_p: float = 0.9,
) -> Callable[[str, int], str]:
    """BackendFn against llama-server /v1/chat/completions. Never falls back."""
    url = (base_url or os.environ.get("VIVY_LLAMA_URL", "http://127.0.0.1:8080")).rstrip("/")
    model = model_alias or os.environ.get("VIVY_MODEL", "gemma4-e4b")
    endpoint = f"{url}/v1/chat/completions"

    def fn(prompt: str, max_tokens: int) -> str:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            if exc.code in (404, 400) and ("model" in detail.lower() or "not found" in detail.lower()):
                raise BackendError("wrong_alias", f"HTTP {exc.code}: {detail}") from exc
            if exc.code in (404, 422, 503):
                raise BackendError("unavailable", f"HTTP {exc.code}: {detail}") from exc
            raise BackendError("incomplete", f"HTTP {exc.code}: {detail}") from exc
        except TimeoutError as exc:
            raise BackendError("timeout", f"timeout after {timeout_s}s") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            text = str(reason)
            if isinstance(reason, ConnectionRefusedError) or "refused" in text.lower():
                raise BackendError("unavailable", text) from exc
            if "timed out" in text.lower() or isinstance(reason, TimeoutError):
                raise BackendError("timeout", text) from exc
            raise BackendError("unavailable", text) from exc

        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("incomplete", f"malformed response: {str(body)[:200]}") from exc
        text = message.get("content") or message.get("reasoning_content") or ""
        if not str(text).strip():
            raise BackendError("incomplete", "empty content in chat completion")
        return str(text)

    return fn


def make_unitary_fn(
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout_s: float = 60.0,
) -> Callable[[str, int], str]:
    """BackendFn against the unitary OpenAI-compatible endpoint. fallback=False.

    [ISOLATED] LLMClient.chat(fallback=True) is not used here. A missing model
    is WRONG_ALIAS, not a silent hop to the next catalogue entry.
    """
    url = (base_url or os.environ.get("UNITARY_API_BASE", "http://localhost:8000/v1")).rstrip("/")
    model_alias = model or os.environ.get("UNITARY_DEFAULT_MODEL", "gpt-4o-mini")

    def fn(prompt: str, max_tokens: int) -> str:
        payload = json.dumps({
            "model": model_alias,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{url}/chat/completions", data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            if exc.code == 404 or "model" in detail.lower():
                raise BackendError("wrong_alias", f"HTTP {exc.code}: {detail}") from exc
            raise BackendError("unavailable", f"HTTP {exc.code}: {detail}") from exc
        except TimeoutError as exc:
            raise BackendError("timeout", f"timeout after {timeout_s}s") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            text = str(reason)
            if isinstance(reason, ConnectionRefusedError) or "refused" in text.lower():
                raise BackendError("unavailable", text) from exc
            if "timed out" in text.lower() or isinstance(reason, TimeoutError):
                raise BackendError("timeout", text) from exc
            raise BackendError("unavailable", text) from exc

        try:
            text = body["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("incomplete", f"malformed response: {str(body)[:200]}") from exc
        if not str(text).strip():
            raise BackendError("incomplete", "empty content")
        return str(text)

    return fn


def probe_health(backend_id: str, *, timeout_s: float = 5.0) -> dict[str, Any]:
    """Best-effort reachability check. Never substitutes another backend."""
    registered = get_backend(backend_id)
    identity = registered.identity
    url = identity.base_url.rstrip("/")
    if identity.backend_id == "native-cautreo":
        return {
            "backend_id": identity.backend_id,
            "reachable": None,
            "detail": "native CAUTREO has no HTTP health endpoint in this harness; use existing receipts",
        }
    target = f"{url}/v1/models" if identity.backend_id == "llama-server" else f"{url}/models"
    try:
        with urllib.request.urlopen(target, timeout=timeout_s) as response:
            body = json.loads(response.read().decode("utf-8"))
        models = [m.get("id") for m in body.get("data", []) if isinstance(m, Mapping)]
        return {
            "backend_id": identity.backend_id,
            "reachable": True,
            "base_url": url,
            "models": models,
            "model_alias": identity.model_alias,
        }
    except Exception as exc:  # noqa: BLE001 — health probe must not crash the suite
        return {
            "backend_id": identity.backend_id,
            "reachable": False,
            "base_url": url,
            "detail": f"{type(exc).__name__}: {exc}",
        }
