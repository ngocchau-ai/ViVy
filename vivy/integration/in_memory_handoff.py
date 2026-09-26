"""
In-Memory Handoff — ViVy P3.

HoH / Antigravity handoff published to CautreoContextMemory (C-ABI) first.
File write (``.vivy_handoff.json`` style) is an optional secondary export for
processes that cannot share the in-process pointer.

Gate 9: no latency claim. The file path is retained for compatibility; the
in-memory path is the primary result surface.

Changelog:
    23/09/2026 (Claude Code — P3 Interleaved in-memory tool dispatch): Initial.
        # [ISOLATED 23/09/2026] prior: handoff only via .vivy_handoff.json /
        # .vivy_last_response.json file write (file-JSON round-trip).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

HANDOFF_PREFIX = "handoff_"


class InMemoryHandoff:
    """Publish / read HoH handoff payloads through Cautreo in-process memory."""

    def __init__(self, context_memory: Any | None = None) -> None:
        self._context_memory = context_memory

    def publish(
        self,
        task_id: str,
        status: str,
        response: str,
        validation: dict[str, Any],
        *,
        file_path: str | None = None,
        executor: str = "Codex/ViVy worker",
        files_modified: list[str] | None = None,
        invariants_checked: list[str] | None = None,
    ) -> dict[str, Any]:
        """Store the handoff in Cautreo and optionally mirror it to ``file_path``.

        Returns a payload describing where the handoff landed. ``in_memory`` is
        True only when the Cautreo put succeeded.
        """
        if self._context_memory is None:
            raise RuntimeError(
                "InMemoryHandoff.publish requires a bound CautreoContextMemory"
            )

        violations = list(validation.get("violations") or [])
        body: dict[str, Any] = {
            "task_id": task_id,
            "executor": executor,
            "status": status,
            "files_modified": list(files_modified or []),
            "evidence": {
                "directive_valid": bool(validation.get("valid")),
                "tests_run": 0,
                "tests_passed": 0,
                "build_warnings": None,
                "diff_clean": None,
            },
            "invariants_checked": list(
                invariants_checked
                or [
                    "VM-11: no blind repeat",
                    "Immutability: legacy content is preserved",
                    "Antigravity-only COMPLETE authority",
                ]
            ),
            "remaining_risks": violations,
            "response": response,
            "validation": validation,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "transport": "cautreo_c_abi_in_process",
        }

        memory_id = f"{HANDOFF_PREFIX}{task_id}"
        version = self._context_memory.put(memory_id, _summary_kind(), json.dumps(body, ensure_ascii=False))
        in_memory = version >= 0
        if not in_memory:
            logger.warning("InMemoryHandoff.publish: Cautreo put failed for %s", memory_id)

        file_written: str | None = None
        if file_path:
            try:
                import os

                parent = os.path.dirname(file_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(body, f, ensure_ascii=False, indent=2)
                file_written = file_path
            except OSError as e:
                logger.warning("InMemoryHandoff.publish: secondary file write failed: %s", e)

        return {
            "in_memory": in_memory,
            "memory_id": memory_id if in_memory else None,
            "version": version,
            "file_path": file_written,
            "task_id": task_id,
            "status": status,
        }

    def read(self, memory_id: str) -> dict[str, Any] | None:
        """Read a handoff body previously published to Cautreo memory."""
        if self._context_memory is None:
            return None
        item = self._context_memory.get(memory_id)
        if item is None:
            return None
        try:
            return json.loads(item.content)
        except json.JSONDecodeError as e:
            logger.warning("InMemoryHandoff.read: corrupt payload at %s: %s", memory_id, e)
            return None


def _summary_kind():
    """Resolve CautreoMemoryKind.SUMMARY without a hard import at module load."""
    try:
        from integration.cautreo_binding import CautreoMemoryKind
    except ImportError:  # pragma: no cover - flat import fallback
        from cautreo_binding import CautreoMemoryKind  # type: ignore
    return CautreoMemoryKind.SUMMARY
