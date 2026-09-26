"""
VivyHost — Cautreo C11 Runtime Bridge (DD-11, Sprint VIVY-HOST-001).

Native bridge between ViVy Python Core and Cautreo 91sCT C11 runtime.
Enables ViVy to leverage Cautreo's 4 capability rings:
  - Mắt (Eyes)  : vision_slicer, web_fetcher
  - Tai (Ears)  : audio_stream, vad_gate, audio_slicer
  - Tay (Hands) : directive_contract, sandbox_runner
  - Thư Viện   : knowledge_store, brain_sync, ct_ssd_library, ct_2brain_plugin

Architecture: CAUTREO 91sCT = Bounded Host Runtime (C11)
              ViVy Python Core owns ALL cognition/decisions.
              VivyHost is the thin interface layer only.

Design Principles (from 91sCT MASTER_SPEC.md):
  1. ViVy owns cognition → Cautreo owns primitives
  2. Thin over fat — expose primitives, no business logic in Cautreo
  3. No external engine lock-in
  4. Graceful degradation: ViVy continues without Cautreo if unavailable

Phase 1 (current): CLI bridge via cautreo.exe subprocess (~3–50ms)
Phase 2 (future):  IPC/daemon via named pipe or Unix socket (<1ms)

Cautreo binary: D:\\cautreov2\\91sCT\\build\\cautreo.exe
ViVy repo: d:\\91s_Vivy\\unitary-reasoner

Changelog:
    20/09/2026 (Antigravity IDE — Sprint VIVY-HOST-001, DD-11):
        Initial implementation — Phase 1 CLI Bridge.
        7 core methods: status, exec_directive, dream, sync_2brain,
        query_knowledge, store_artifact, version.
        Graceful degradation if binary unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default path to Cautreo binary — can be overridden via CAUTREO_EXE env var
_DEFAULT_CAUTREO_EXE = Path(r"D:\cautreov2\91sCT\build\cautreo.exe")

# Timeouts per command type (seconds)
_TIMEOUT_STATUS  = 5
_TIMEOUT_QUERY   = 10
_TIMEOUT_STORE   = 15
_TIMEOUT_EXEC    = 60
_TIMEOUT_DREAM   = 90
_TIMEOUT_SYNC    = 30
_TIMEOUT_VERSION = 5

# Error rate threshold to trigger dream consolidation
DREAM_TRIGGER_ERROR_RATE = 0.10   # 10%


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class CautreoStatus(Enum):
    """Health status of the Cautreo Room."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    OFFLINE   = "offline"
    UNKNOWN   = "unknown"


@dataclass
class RoomStatus:
    """Parsed output from `cautreo.exe status`."""
    status: CautreoStatus = CautreoStatus.UNKNOWN
    ssd_tier1_ok: bool = False
    ssd_tier2_ok: bool = False
    brain_mounted: bool = False
    knowledge_entries: int = 0
    raw: str = ""

    @classmethod
    def offline(cls) -> RoomStatus:
        return cls(status=CautreoStatus.OFFLINE, raw="binary_unavailable")

    @classmethod
    def from_raw(cls, raw: str) -> RoomStatus:
        """Parse cautreo.exe status output.

        Cautreo outputs either JSON or human-readable lines.
        We try JSON first, then fall back to keyword scan.
        """
        obj = cls(raw=raw)
        # Try JSON parse
        try:
            data = json.loads(raw.strip())
            obj.status        = CautreoStatus(data.get("status", "unknown"))
            obj.ssd_tier1_ok  = bool(data.get("ssd_tier1", False))
            obj.ssd_tier2_ok  = bool(data.get("ssd_tier2", False))
            obj.brain_mounted = bool(data.get("brain_mounted", False))
            obj.knowledge_entries = int(data.get("knowledge_entries", 0))
            return obj
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        # Fallback: keyword scan (human-readable output)
        low = raw.lower()
        if "ok" in low or "healthy" in low or "status: ok" in low:
            obj.status = CautreoStatus.HEALTHY
        elif "degraded" in low:
            obj.status = CautreoStatus.DEGRADED
        elif "error" in low or "fail" in low:
            obj.status = CautreoStatus.DEGRADED
        else:
            obj.status = CautreoStatus.UNKNOWN

        obj.ssd_tier1_ok  = "ssd" in low and "ok" in low
        obj.brain_mounted = "2brain" in low and ("mount" in low or "ok" in low)
        return obj


@dataclass
class KnowledgeEntry:
    """A single entry from Cautreo knowledge store."""
    key: str
    content: str
    verified: bool = False
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DirectiveResult:
    """Result from `cautreo.exe exec <directive>`."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# VivyHost — main class
# ---------------------------------------------------------------------------


class VivyHost:
    """Thin bridge between ViVy Python Core and Cautreo C11 Runtime.

    All methods degrade gracefully if Cautreo binary is unavailable.
    ViVy MUST NOT crash if Cautreo is offline.

    Usage::

        host = VivyHost()           # auto-discovers binary
        s = host.status()           # → RoomStatus
        host.store_artifact("k", "content", verified=True)
        hits = host.query_knowledge("robot arm torque")
        host.dream()                # consolidate memory
        host.sync_2brain()          # persist to D:\\2brain

    Phase 2 upgrade path:
        Replace _run_cli() with _run_ipc() once vivy_host daemon is ready.
        Public API stays identical — callers need zero changes.
    """

    def __init__(
        self,
        cautreo_exe: Path | str | None = None,
        timeout_override: dict[str, float] | None = None,
    ) -> None:
        # Resolve binary path: env var > ctor arg > default
        env_path = os.environ.get("CAUTREO_EXE")
        if env_path:
            self._exe = Path(env_path)
        elif cautreo_exe is not None:
            self._exe = Path(cautreo_exe)
        else:
            self._exe = _DEFAULT_CAUTREO_EXE

        self._available: bool | None = None   # lazily detected
        self._timeouts: dict[str, float] = {
            "status":  _TIMEOUT_STATUS,
            "query":   _TIMEOUT_QUERY,
            "store":   _TIMEOUT_STORE,
            "exec":    _TIMEOUT_EXEC,
            "dream":   _TIMEOUT_DREAM,
            "sync":    _TIMEOUT_SYNC,
            "version": _TIMEOUT_VERSION,
        }
        if timeout_override:
            self._timeouts.update(timeout_override)

        self._call_count = 0
        self._error_count = 0

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True if cautreo.exe is present and executable."""
        if self._available is None:
            self._available = self._exe.exists() and os.access(self._exe, os.X_OK)
            if not self._available:
                logger.warning(
                    "[VivyHost] Cautreo binary not found at %s. "
                    "ViVy will operate without Cautreo capabilities. "
                    "Set CAUTREO_EXE env var to override path.",
                    self._exe,
                )
        return self._available

    def reset_availability_cache(self) -> None:
        """Force re-check on next call (e.g., after cautreo.exe is installed)."""
        self._available = None

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def status(self) -> RoomStatus:
        """Check health of the Cautreo Room.

        Returns RoomStatus.offline() if binary unavailable.
        Never raises.
        """
        if not self.available:
            return RoomStatus.offline()

        out, _err, rc = self._run_cli(["status"], timeout=self._timeouts["status"])
        if rc != 0:
            return RoomStatus(status=CautreoStatus.DEGRADED, raw=out + _err)
        return RoomStatus.from_raw(out)

    def version(self) -> str:
        """Return Cautreo version string, or 'unavailable'."""
        if not self.available:
            return "unavailable"
        out, _, rc = self._run_cli(["version"], timeout=self._timeouts["version"])
        return out.strip() if rc == 0 else "unavailable"

    def exec_directive(self, directive: str) -> DirectiveResult:
        """Execute a raw directive via Cautreo Hands sandbox.

        The directive is a structured string understood by Cautreo:
          e.g. "DIRECTIVE: EXEC_CMD target=whoami"
               "DIRECTIVE: FILE_WRITE path=/tmp/out.txt content=hello"

        Returns DirectiveResult with success=False on any error.
        """
        if not self.available:
            return DirectiveResult(success=False, stderr="cautreo_unavailable")

        t0 = time.monotonic()
        out, err, rc = self._run_cli(
            ["exec", directive],
            timeout=self._timeouts["exec"],
        )
        elapsed = (time.monotonic() - t0) * 1000
        success = rc == 0
        self._track_call(success)

        if not success:
            logger.warning("[VivyHost.exec] Directive failed (rc=%d): %s", rc, err[:200])

        return DirectiveResult(
            success=success,
            stdout=out,
            stderr=err,
            returncode=rc,
            elapsed_ms=elapsed,
        )

    def dream(self) -> bool:
        """Trigger Cautreo Dream Engine — SVD memory consolidation.

        Dream consolidates ephemeral ring buffer (Tier 1) into bimodal
        store (Tier 2), applying SVD interference to crystallize knowledge.
        Should be triggered when ViVy error rate exceeds threshold.

        Returns True on success, False if unavailable or failed.
        """
        if not self.available:
            logger.debug("[VivyHost.dream] Cautreo unavailable — skipping dream cycle.")
            return False

        logger.info("[VivyHost.dream] Triggering dream consolidation cycle...")
        out, err, rc = self._run_cli(["dream"], timeout=self._timeouts["dream"])
        success = rc == 0
        self._track_call(success)

        if success:
            logger.info("[VivyHost.dream] Dream cycle complete.")
        else:
            logger.warning("[VivyHost.dream] Dream cycle failed: %s", err[:200])

        return success

    def sync_2brain(self) -> bool:
        """Sync ViVy decisions and learnings → D:\\2brain via Cautreo.

        Uses ct_2brain_plugin (VFS direct mount, atomic .tmp replacement).
        Call after each Durable Decision and at session end.

        Returns True on success.
        """
        if not self.available:
            logger.debug("[VivyHost.sync] Cautreo unavailable — 2brain sync skipped.")
            return False

        logger.info("[VivyHost.sync] Syncing to D:\\2brain...")
        out, err, rc = self._run_cli(["sync"], timeout=self._timeouts["sync"])
        success = rc == 0
        self._track_call(success)

        if success:
            logger.info("[VivyHost.sync] Sync complete.")
        else:
            logger.warning("[VivyHost.sync] Sync failed (rc=%d): %s", rc, err[:200])

        return success

    def query_knowledge(self, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        """Query Cautreo knowledge store for relevant entries.

        ViVy should call this BEFORE inference to leverage cached knowledge.
        Returns empty list if Cautreo unavailable or no matches.

        Args:
            query: Natural language search query.
            limit: Maximum number of entries to return (default 5).
        """
        if not self.available:
            return []

        # Use content hash as cache key prefix
        query_key = hashlib.sha256(query.encode()).hexdigest()[:16]
        out, err, rc = self._run_cli(
            ["query", query, "--limit", str(limit), "--key-prefix", query_key],
            timeout=self._timeouts["query"],
        )
        if rc != 0 or not out.strip():
            return []

        return self._parse_knowledge_results(out)

    def store_artifact(
        self,
        key: str,
        content: str,
        verified: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store a knowledge artifact in Cautreo library.

        Staging (verified=False): Raw data waiting Evidence Gate.
        Verified (verified=True): Crystallized knowledge, persisted permanently.

        Args:
            key:      Unique identifier for the artifact.
            content:  Markdown or plain text content.
            verified: True = Evidence Gate passed → permanent store.
                      False = Raw staging area (may be purged).
            metadata: Optional metadata dict (JSON-serializable).
        """
        if not self.available:
            return False

        flags = ["--verified"] if verified else ["--staging"]
        if metadata:
            flags += ["--meta", json.dumps(metadata)]

        out, err, rc = self._run_cli(
            ["store", key] + flags,
            stdin=content.encode(),
            timeout=self._timeouts["store"],
        )
        success = rc == 0
        self._track_call(success)

        if success:
            tier = "verified" if verified else "staging"
            logger.debug("[VivyHost.store] Stored artifact '%s' → %s tier.", key, tier)
        else:
            logger.warning("[VivyHost.store] Failed to store '%s': %s", key, err[:200])

        return success

    # ------------------------------------------------------------------
    # Composite helpers — used by VivyInferenceLoop
    # ------------------------------------------------------------------

    def pre_inference_check(self, task: str) -> list[KnowledgeEntry]:
        """Query knowledge BEFORE inference. Called by VivyInferenceLoop.

        Returns cached entries if found. Empty list = proceed with inference.
        """
        return self.query_knowledge(task, limit=3)

    def post_inference_store(
        self,
        task: str,
        result_markdown: str,
        confidence: float,
        threshold: float = 0.80,
    ) -> bool:
        """Store inference result AFTER inference. Called by VivyInferenceLoop.

        Only stores if confidence exceeds threshold (Evidence Gate).
        """
        if confidence < threshold:
            logger.debug(
                "[VivyHost.post_store] Confidence %.2f < %.2f — staging only.",
                confidence, threshold,
            )

        key = f"vivy-{hashlib.sha256(task.encode()).hexdigest()[:12]}"
        return self.store_artifact(
            key=key,
            content=result_markdown,
            verified=confidence >= threshold,
            metadata={"task_hash": key, "confidence": confidence},
        )

    def maybe_dream(self, error_rate: float) -> bool:
        """Trigger dream if error rate exceeds DREAM_TRIGGER_ERROR_RATE.

        Called by VivyInferenceLoop after each inference round.
        """
        if error_rate >= DREAM_TRIGGER_ERROR_RATE:
            logger.info(
                "[VivyHost] Error rate %.1f%% ≥ %.1f%% threshold → triggering dream.",
                error_rate * 100, DREAM_TRIGGER_ERROR_RATE * 100,
            )
            return self.dream()
        return False

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def error_rate(self) -> float:
        """Fraction of failed Cautreo calls this session."""
        if self._call_count == 0:
            return 0.0
        return self._error_count / self._call_count

    def stats(self) -> dict[str, Any]:
        """Return runtime stats for logging/monitoring."""
        return {
            "available": self.available,
            "exe_path": str(self._exe),
            "call_count": self._call_count,
            "error_count": self._error_count,
            "error_rate": round(self.error_rate, 4),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_cli(
        self,
        args: list[str],
        stdin: bytes | None = None,
        timeout: float = 10.0,
    ) -> tuple[str, str, int]:
        """Run cautreo.exe with args. Returns (stdout, stderr, returncode).

        Never raises — all subprocess exceptions are caught and logged.
        Returns ("", "<error>", 1) on any failure.
        """
        cmd = [str(self._exe)] + args
        try:
            proc = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                timeout=timeout,
            )
            stdout = proc.stdout.decode("utf-8", errors="replace")
            stderr = proc.stderr.decode("utf-8", errors="replace")
            return stdout, stderr, proc.returncode

        except subprocess.TimeoutExpired:
            logger.warning("[VivyHost] Command timed out after %.1fs: %s", timeout, cmd)
            return "", "timeout", 1

        except FileNotFoundError:
            # Binary disappeared after availability check
            self._available = False
            logger.error("[VivyHost] cautreo.exe not found at %s", self._exe)
            return "", "binary_not_found", 1

        except OSError as exc:
            logger.error("[VivyHost] OS error running cautreo: %s", exc)
            return "", str(exc), 1

    def _track_call(self, success: bool) -> None:
        self._call_count += 1
        if not success:
            self._error_count += 1

    @staticmethod
    def _parse_knowledge_results(raw: str) -> list[KnowledgeEntry]:
        """Parse knowledge query output from Cautreo.

        Cautreo outputs newline-delimited JSON objects or structured text.
        """
        entries: list[KnowledgeEntry] = []

        # Try newline-delimited JSON
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(KnowledgeEntry(
                    key=data.get("key", ""),
                    content=data.get("content", line),
                    verified=bool(data.get("verified", False)),
                    timestamp=float(data.get("ts", time.time())),
                    metadata=data.get("meta", {}),
                ))
            except json.JSONDecodeError:
                # Fallback: treat line as plain-text entry
                if len(line) > 5:
                    entries.append(KnowledgeEntry(
                        key=hashlib.sha256(line.encode()).hexdigest()[:12],
                        content=line,
                        verified=False,
                    ))

        return entries

    def __repr__(self) -> str:
        av = "available" if self.available else "OFFLINE"
        return (
            f"VivyHost(exe={self._exe.name!r}, status={av}, "
            f"calls={self._call_count}, errors={self._error_count})"
        )
