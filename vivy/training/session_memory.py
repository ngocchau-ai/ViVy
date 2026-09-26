"""C10 — session-isolated memory store (put/get/delete, version, TTL, restart).

Acceptance-plan C10.1: correctness put/get/delete-isolation theo session,
Unicode, long values, overwrite/version, TTL, restart và concurrent access.

Semantics follow `engine/include/context_memory.h` (CT_MEMORY_*),
with an explicit session namespace so two sessions sharing one hub cannot
leak keys, versions, or deletes into each other.

Changelog:
    2026-09-24 (Claude Code — P5 C10): Initial.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

CT_MEMORY_CONTENT_MAX = 1024 * 1024
CT_MEMORY_ID_MAX = 96

KINDS = ("HARD_FACT", "TASK", "CONSTRAINT", "SUMMARY")


class MemoryConflict(RuntimeError):
    """expected_version does not match the stored version."""


class MemoryNotFound(KeyError):
    """id is absent, deleted, or expired."""


class MemoryInvalid(ValueError):
    """Input fails the C-ABI contract (bad kind, empty id, overlong content)."""


@dataclass
class MemoryItem:
    id: str
    kind: str
    content: str
    version: int
    created_at_ms: int
    updated_at_ms: int
    expires_at_ms: int
    session_id: str
    provenance: dict[str, Any] = field(default_factory=dict)
    deleted: bool = False


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


class SessionMemory:
    """One session's view of context memory. No cross-session key space."""

    def __init__(
        self,
        session_id: str,
        *,
        max_items: int = 1024,
        persist_path: str | Path | None = None,
    ) -> None:
        if not session_id:
            raise MemoryInvalid("session_id must be non-empty")
        self.session_id = session_id
        self.max_items = max_items
        self.persist_path = Path(persist_path) if persist_path else None
        self._lock = threading.RLock()
        self._items: dict[str, MemoryItem] = {}
        if self.persist_path and self.persist_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def put(
        self,
        item_id: str,
        *,
        kind: str,
        content: str,
        expected_version: int = 0,
        ttl_ms: int = 0,
        provenance: dict[str, Any] | None = None,
        now_ms: int | None = None,
    ) -> int:
        if not item_id or len(item_id.encode("utf-8")) > CT_MEMORY_ID_MAX:
            raise MemoryInvalid(f"invalid item_id: {item_id!r}")
        if kind not in KINDS:
            raise MemoryInvalid(f"invalid kind: {kind!r}")
        if not isinstance(content, str):
            raise MemoryInvalid("content must be str")
        raw = content.encode("utf-8")
        if len(raw) > CT_MEMORY_CONTENT_MAX:
            raise MemoryInvalid(
                f"content length {len(raw)} exceeds CT_MEMORY_CONTENT_MAX={CT_MEMORY_CONTENT_MAX}"
            )
        now = now_ms if now_ms is not None else _now_ms()

        with self._lock:
            current = self._items.get(item_id)
            if current is not None and not current.deleted and self._alive(current, now):
                if expected_version == 0:
                    raise MemoryConflict(
                        f"create requires expected_version=0 on empty slot; {item_id} exists v{current.version}"
                    )
                if current.version != expected_version:
                    raise MemoryConflict(
                        f"version mismatch for {item_id}: expected {expected_version}, have {current.version}"
                    )
                new_version = current.version + 1
                created = current.created_at_ms
            else:
                if expected_version != 0:
                    raise MemoryConflict(
                        f"version mismatch for {item_id}: expected {expected_version}, have 0 (create)"
                    )
                if len(self._items) >= self.max_items:
                    raise MemoryInvalid(f"max_items={self.max_items} reached")
                new_version = 1
                created = now

            expires = (now + ttl_ms) if ttl_ms and ttl_ms > 0 else 0
            item = MemoryItem(
                id=item_id,
                kind=kind,
                content=content,
                version=new_version,
                created_at_ms=created,
                updated_at_ms=now,
                expires_at_ms=expires,
                session_id=self.session_id,
                provenance=dict(provenance or {}),
                deleted=False,
            )
            self._items[item_id] = item
            self._append_log({"op": "put", "item": self._to_row(item)})
            return new_version

    def get(self, item_id: str, *, now_ms: int | None = None) -> MemoryItem | None:
        now = now_ms if now_ms is not None else _now_ms()
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.deleted or not self._alive(item, now):
                return None
            return self._copy(item)

    def delete(self, item_id: str, *, expected_version: int, now_ms: int | None = None) -> None:
        now = now_ms if now_ms is not None else _now_ms()
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.deleted or not self._alive(item, now):
                raise MemoryNotFound(item_id)
            if item.version != expected_version:
                raise MemoryConflict(
                    f"version mismatch for {item_id}: expected {expected_version}, have {item.version}"
                )
            item.deleted = True
            item.updated_at_ms = now
            item.version = item.version + 1
            self._append_log({"op": "delete", "id": item_id, "version": item.version})

    def count(self, *, now_ms: int | None = None) -> int:
        now = now_ms if now_ms is not None else _now_ms()
        with self._lock:
            return sum(1 for it in self._items.values() if not it.deleted and self._alive(it, now))

    def checkpoint(self) -> None:
        """Durably flush the session log (restart restores versions and content)."""
        if not self.persist_path:
            return
        with self._lock:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            rows = [self._to_row(it) for it in self._items.values()]
            tmp = self.persist_path.with_suffix(".tmp")
            tmp.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            tmp.replace(self.persist_path)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _alive(item: MemoryItem, now_ms: int) -> bool:
        return item.expires_at_ms == 0 or now_ms < item.expires_at_ms

    @staticmethod
    def _copy(item: MemoryItem) -> MemoryItem:
        return MemoryItem(
            id=item.id,
            kind=item.kind,
            content=item.content,
            version=item.version,
            created_at_ms=item.created_at_ms,
            updated_at_ms=item.updated_at_ms,
            expires_at_ms=item.expires_at_ms,
            session_id=item.session_id,
            provenance=dict(item.provenance),
            deleted=item.deleted,
        )

    @staticmethod
    def _to_row(item: MemoryItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "kind": item.kind,
            "content": item.content,
            "version": item.version,
            "created_at_ms": item.created_at_ms,
            "updated_at_ms": item.updated_at_ms,
            "expires_at_ms": item.expires_at_ms,
            "session_id": item.session_id,
            "provenance": item.provenance,
            "deleted": item.deleted,
        }

    def _append_log(self, record: dict[str, Any]) -> None:
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with self.persist_path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load(self) -> None:
        assert self.persist_path is not None
        # Checkpoint format is one MemoryItem row per line (post-checkpoint state).
        # Append-only ops before the last checkpoint are folded into that snapshot.
        text = self.persist_path.read_text(encoding="utf-8")
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if rows and rows[0].get("op") in {"put", "delete"}:
            # replay append-only log
            for rec in rows:
                if rec.get("op") == "put":
                    row = rec["item"]
                    self._items[row["id"]] = MemoryItem(**row)
                elif rec.get("op") == "delete":
                    item = self._items.get(rec["id"])
                    if item is not None:
                        item.deleted = True
                        item.version = rec["version"]
            return
        for row in rows:
            if row.get("session_id") not in (None, self.session_id):
                continue
            self._items[row["id"]] = MemoryItem(**row)


class SessionMemoryHub:
    """Named sessions with disjoint key spaces. Shared hub must not leak."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = threading.RLock()

    def for_session(self, session_id: str, **kwargs: Any) -> SessionMemory:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory(session_id, **kwargs)
            return self._sessions[session_id]

    def session_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._sessions)
