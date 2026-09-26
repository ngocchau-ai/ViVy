"""
Engine Primitives — ViVy Final V1.0 Sprint 1.

Bốn Engine Primitives cấp thấp (Wrapperless) mà ViVy gọi trực tiếp
thay vì thông qua wrapper framework (LangChain, AutoGen, REST API).

Architecture:
    ViVy (Directive) → engine/primitives.py → OS / File / Process / Media

Design rules:
    - Stdlib + numpy ONLY. No requests, no langchain, no external deps.
    - Every function returns a typed dataclass (PrimitiveResult) so the
      caller gets a uniform evidence surface.
    - All failures surface as .ok=False + .error_message, never bare
      exceptions propagating up to ViVy's orchestration loop.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 1 — HOH-VIVY-FINAL-V1): Initial implementation.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared result schema
# ---------------------------------------------------------------------------


@dataclass
class PrimitiveResult:
    """Unified evidence object returned by every Engine Primitive.

    Attributes
    ----------
    ok:
        True when the operation succeeded.
    data:
        Operation-specific payload (bytes content, stdout str, etc.).
    error_message:
        Human-readable error description when ok=False.
    elapsed_ms:
        Wall-clock time of the primitive call in milliseconds.
    metadata:
        Optional extra key/value evidence (exit_code, bytes_freed, ...).
    """

    ok: bool
    data: Any = None
    error_message: str = ""
    elapsed_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class FileAction(StrEnum):
    """Supported actions for engine_file_io."""

    READ = "read"
    WRITE = "write"
    APPEND = "append"
    DELETE = "delete"
    EXISTS = "exists"
    MKDIR = "mkdir"


class CacheOp(StrEnum):
    """Supported operations for engine_cache_control."""

    PURGE_TRANSIENT = "purge_transient"
    LOAD_ARTIFACT = "load_artifact"
    SNAPSHOT = "snapshot"
    STATS = "stats"


# ---------------------------------------------------------------------------
# Primitive 1: engine_file_io
# ---------------------------------------------------------------------------


def engine_file_io(
    action: str | FileAction,
    path: str,
    content: str | bytes | None = None,
    offset: int = 0,
    length: int = -1,
    encoding: str = "utf-8",
) -> PrimitiveResult:
    """Read / write / manage files at byte or text level — no library shim.

    Parameters
    ----------
    action:
        One of ``FileAction`` values: read | write | append | delete |
        exists | mkdir.
    path:
        Absolute or relative file path.
    content:
        Data to write (for write/append). Ignored for read/exists/delete.
    offset:
        Byte offset for read operations. 0 = beginning of file.
    length:
        Number of bytes to read. -1 = entire file (from offset).
    encoding:
        Text encoding used when *content* is a str and for text reads.

    Returns
    -------
    PrimitiveResult
        .data = file content (str) for read; bool for exists; None otherwise.
    """
    t0 = time.perf_counter()
    action = FileAction(action)
    p = Path(path)

    try:
        match action:
            case FileAction.EXISTS:
                result = PrimitiveResult(ok=True, data=p.exists(), elapsed_ms=0.0)

            case FileAction.MKDIR:
                p.mkdir(parents=True, exist_ok=True)
                result = PrimitiveResult(ok=True, data=str(p), elapsed_ms=0.0)

            case FileAction.READ:
                if not p.exists():
                    return PrimitiveResult(
                        ok=False,
                        error_message=f"File not found: {path}",
                        elapsed_ms=(time.perf_counter() - t0) * 1000,
                    )
                raw = p.read_bytes()
                if offset > 0:
                    raw = raw[offset:]
                if length > 0:
                    raw = raw[:length]
                try:
                    data: str | bytes = raw.decode(encoding)
                except UnicodeDecodeError:
                    data = raw  # return bytes when non-text
                result = PrimitiveResult(
                    ok=True,
                    data=data,
                    metadata={"size_bytes": len(raw), "path": str(p)},
                    elapsed_ms=0.0,
                )

            case FileAction.WRITE:
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = content.encode(encoding) if isinstance(content, str) else (content or b"")
                p.write_bytes(payload)
                result = PrimitiveResult(
                    ok=True,
                    data=str(p),
                    metadata={"bytes_written": len(payload)},
                    elapsed_ms=0.0,
                )

            case FileAction.APPEND:
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = content.encode(encoding) if isinstance(content, str) else (content or b"")
                with p.open("ab") as fh:
                    fh.write(payload)
                result = PrimitiveResult(
                    ok=True,
                    data=str(p),
                    metadata={"bytes_appended": len(payload)},
                    elapsed_ms=0.0,
                )

            case FileAction.DELETE:
                if p.exists():
                    p.unlink()
                    result = PrimitiveResult(ok=True, data=True, elapsed_ms=0.0)
                else:
                    result = PrimitiveResult(ok=True, data=False, elapsed_ms=0.0)

            case _:  # pragma: no cover
                result = PrimitiveResult(ok=False, error_message=f"Unknown action: {action}", elapsed_ms=0.0)

    except PermissionError as exc:
        result = PrimitiveResult(ok=False, error_message=f"Permission denied: {exc}", elapsed_ms=0.0)
    except OSError as exc:
        result = PrimitiveResult(ok=False, error_message=f"OS error: {exc}", elapsed_ms=0.0)

    result.elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.debug("engine_file_io: action=%s path=%s ok=%s %.2fms", action, path, result.ok, result.elapsed_ms)
    return result


# ---------------------------------------------------------------------------
# Primitive 2: engine_exec
# ---------------------------------------------------------------------------


def engine_exec(
    cmd: str | list[str],
    timeout: float = 30.0,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    capture_stderr: bool = True,
) -> PrimitiveResult:
    """Execute an OS-level command and capture output — zero HTTP overhead.

    Parameters
    ----------
    cmd:
        Command string (shell-parsed) or list of args (no shell).
    timeout:
        Max seconds to wait. Process is killed on timeout; ok=False.
    env:
        Environment variables (merged with os.environ when provided).
    cwd:
        Working directory. None = inherit.
    capture_stderr:
        If True, stderr is captured and included in .metadata['stderr'].

    Returns
    -------
    PrimitiveResult
        .data = stdout (str), .metadata = {exit_code, stderr, pid}.
    """
    t0 = time.perf_counter()
    use_shell = isinstance(cmd, str)

    merged_env: dict[str, str] | None = None
    if env is not None:
        merged_env = {**os.environ, **env}

    stderr_target = subprocess.PIPE if capture_stderr else subprocess.DEVNULL

    try:
        proc = subprocess.run(
            cmd,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=stderr_target,
            timeout=timeout,
            env=merged_env,
            cwd=cwd,
            text=True,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        ok = proc.returncode == 0
        stderr_out = proc.stderr or ""
        result = PrimitiveResult(
            ok=ok,
            data=proc.stdout,
            error_message="" if ok else f"Exit code {proc.returncode}",
            elapsed_ms=elapsed,
            metadata={
                "exit_code": proc.returncode,
                "stderr": stderr_out,
            },
        )
        logger.debug(
            "engine_exec: ok=%s exit=%d %.2fms cmd=%s",
            ok,
            proc.returncode,
            elapsed,
            cmd if isinstance(cmd, str) else " ".join(cmd),
        )
        return result

    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - t0) * 1000
        logger.warning("engine_exec: timeout after %.1fs cmd=%s", timeout, cmd)
        return PrimitiveResult(
            ok=False,
            data="",
            error_message=f"Command timed out after {timeout}s",
            elapsed_ms=elapsed,
            metadata={"exit_code": -1, "stderr": "", "timed_out": True},
        )
    except FileNotFoundError as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return PrimitiveResult(
            ok=False,
            data="",
            error_message=f"Command not found: {exc}",
            elapsed_ms=elapsed,
            metadata={"exit_code": -1, "stderr": ""},
        )
    except OSError as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return PrimitiveResult(
            ok=False,
            data="",
            error_message=f"OS error executing command: {exc}",
            elapsed_ms=elapsed,
            metadata={"exit_code": -1, "stderr": ""},
        )


# ---------------------------------------------------------------------------
# Primitive 3: engine_media_slice
# ---------------------------------------------------------------------------


def engine_media_slice(
    source: str,
    start_ms: float = 0.0,
    end_ms: float = -1.0,
    output_path: str | None = None,
) -> PrimitiveResult:
    """Extract a time-bounded slice from a media file (video/audio).

    This is a *wrapperless* primitive: it calls ffmpeg directly via
    engine_exec rather than importing a Python media library.  On systems
    where ffmpeg is not installed, the primitive returns ok=False with a
    clear error — ViVy can then emit NEED_KNOWLEDGE_FORAGING instead of
    crashing.

    Parameters
    ----------
    source:
        Path to source media file (mp4, mkv, mp3, wav, ...).
    start_ms:
        Start position in milliseconds.
    end_ms:
        End position in milliseconds. -1 = until end of file.
    output_path:
        Destination path for the extracted slice. Auto-generated if None.

    Returns
    -------
    PrimitiveResult
        .data = path to output file (str) when ok=True.
        .metadata = {source, start_ms, end_ms, duration_ms}.
    """
    t0 = time.perf_counter()
    src = Path(source)
    if not src.exists():
        return PrimitiveResult(
            ok=False,
            error_message=f"Media source not found: {source}",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )

    # Auto-generate output path next to source
    if output_path is None:
        suffix = src.suffix or ".mp4"
        output_path = str(src.parent / f"{src.stem}_slice_{int(start_ms)}_{int(end_ms)}{suffix}")

    start_s = start_ms / 1000.0
    ss_arg = f"{start_s:.3f}"

    cmd: list[str] = ["ffmpeg", "-y", "-ss", ss_arg, "-i", str(src)]
    if end_ms > 0:
        duration_s = (end_ms - start_ms) / 1000.0
        cmd.extend(["-t", f"{duration_s:.3f}"])
    cmd.extend(["-c", "copy", output_path])

    exec_result = engine_exec(cmd, timeout=120.0)
    elapsed = (time.perf_counter() - t0) * 1000

    if exec_result.ok:
        return PrimitiveResult(
            ok=True,
            data=output_path,
            elapsed_ms=elapsed,
            metadata={
                "source": str(src),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": max(0, end_ms - start_ms) if end_ms > 0 else -1,
                "output_path": output_path,
            },
        )
    else:
        # Check if ffmpeg is missing (common on dev machines)
        if "Command not found" in exec_result.error_message:
            err = "ffmpeg not installed — install ffmpeg or use NEED_KNOWLEDGE_FORAGING"
        else:
            err = exec_result.error_message
        return PrimitiveResult(
            ok=False,
            error_message=err,
            elapsed_ms=elapsed,
            metadata={"exit_code": exec_result.metadata.get("exit_code", -1)},
        )


# ---------------------------------------------------------------------------
# Primitive 4: engine_cache_control
# ---------------------------------------------------------------------------

# Module-level in-memory KV store shared across calls (singleton pattern)
_CACHE_STORE: dict[str, dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()


def engine_cache_control(
    op: str | CacheOp,
    scope: str = "transient",
    artifact_path: str | None = None,
    chunk_ids: list[str] | None = None,
) -> PrimitiveResult:
    """Manage ViVy's in-memory KV cache — Purge & Reload primitive.

    Operations
    ----------
    purge_transient:
        Remove all transient chunks from *scope*. Pass chunk_ids to
        selectively purge; omit to purge the entire scope.
    load_artifact:
        Load a Knowledge Artifact file into the cache under *scope*.
        Returns artifact content as .data.
    snapshot:
        Return stats snapshot of *scope* without modifying it.
    stats:
        Return global cache stats across all scopes.

    Parameters
    ----------
    op:
        One of CacheOp values.
    scope:
        Cache scope key (e.g. ``"transient"``, ``"session_42"``).
    artifact_path:
        Path to artifact file (required for load_artifact op).
    chunk_ids:
        Chunk IDs to purge (optional for purge_transient — all if omitted).

    Returns
    -------
    PrimitiveResult
        .data varies by op: purge=PurgeStats dict; load=str content;
        snapshot/stats=dict.
    """
    t0 = time.perf_counter()
    op = CacheOp(op)

    with _CACHE_LOCK:
        try:
            match op:
                case CacheOp.PURGE_TRANSIENT:
                    if scope not in _CACHE_STORE:
                        result = PrimitiveResult(
                            ok=True,
                            data={"chunks_removed": 0, "bytes_freed": 0, "scope": scope},
                            elapsed_ms=0.0,
                        )
                    else:
                        store = _CACHE_STORE[scope]
                        if chunk_ids is not None:
                            targets = [cid for cid in chunk_ids if cid in store]
                        else:
                            targets = list(store.keys())
                        bytes_freed = sum(len(str(store[cid]).encode()) for cid in targets)
                        for cid in targets:
                            del store[cid]
                        if not store:
                            del _CACHE_STORE[scope]
                        result = PrimitiveResult(
                            ok=True,
                            data={
                                "chunks_removed": len(targets),
                                "bytes_freed": bytes_freed,
                                "scope": scope,
                            },
                            elapsed_ms=0.0,
                        )
                        logger.info(
                            "engine_cache_control: purged scope=%s chunks=%d bytes=%d",
                            scope,
                            len(targets),
                            bytes_freed,
                        )

                case CacheOp.LOAD_ARTIFACT:
                    if artifact_path is None:
                        return PrimitiveResult(
                            ok=False,
                            error_message="artifact_path required for load_artifact op",
                            elapsed_ms=(time.perf_counter() - t0) * 1000,
                        )
                    ap = Path(artifact_path)
                    if not ap.exists():
                        return PrimitiveResult(
                            ok=False,
                            error_message=f"Artifact not found: {artifact_path}",
                            elapsed_ms=(time.perf_counter() - t0) * 1000,
                        )
                    content = ap.read_text(encoding="utf-8")
                    # Store artifact reference in cache scope
                    if scope not in _CACHE_STORE:
                        _CACHE_STORE[scope] = {}
                    _CACHE_STORE[scope]["__artifact__"] = content
                    result = PrimitiveResult(
                        ok=True,
                        data=content,
                        metadata={"artifact_path": str(ap), "chars": len(content)},
                        elapsed_ms=0.0,
                    )

                case CacheOp.SNAPSHOT:
                    scope_data = _CACHE_STORE.get(scope, {})
                    result = PrimitiveResult(
                        ok=True,
                        data={
                            "scope": scope,
                            "chunk_count": len(scope_data),
                            "chunk_ids": list(scope_data.keys()),
                        },
                        elapsed_ms=0.0,
                    )

                case CacheOp.STATS:
                    total_chunks = sum(len(v) for v in _CACHE_STORE.values())
                    result = PrimitiveResult(
                        ok=True,
                        data={
                            "scopes": list(_CACHE_STORE.keys()),
                            "total_chunks": total_chunks,
                        },
                        elapsed_ms=0.0,
                    )

                case _:  # pragma: no cover
                    result = PrimitiveResult(ok=False, error_message=f"Unknown op: {op}", elapsed_ms=0.0)

        except Exception as exc:  # noqa: BLE001
            result = PrimitiveResult(
                ok=False,
                error_message=f"Cache control error: {exc}",
                elapsed_ms=0.0,
            )

    result.elapsed_ms = (time.perf_counter() - t0) * 1000
    return result
