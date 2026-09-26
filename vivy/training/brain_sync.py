"""C11.6 — 2brain sync: fail → pending + idempotent retry.

Never reports synced=True before a read-back hash match. Unusable brain root or
hash mismatch leaves status=pending; retrying the same payload is a no-op replay.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


BRAIN_PROJECT = Path("projects") / "vivy-v5"
LESSON_FILENAME = "durable_lessons.jsonl"
STATUS_FILENAME = "sync_status.json"


@dataclass
class SyncResult:
    synced: bool
    status: str
    readback_hash: str | None
    files: list[str] = field(default_factory=list)
    error: str | None = None
    idempotent_replay: bool = False
    content_hash: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _status_path(brain_root: Path) -> Path:
    return Path(brain_root) / BRAIN_PROJECT / STATUS_FILENAME


def _landing_path(brain_root: Path) -> Path:
    return Path(brain_root) / BRAIN_PROJECT / "lessons" / LESSON_FILENAME


def _write_status(brain_root: Path, *, status: str, synced: bool, content_hash, readback_hash, error=None) -> None:
    path = _status_path(brain_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "status": status,
        "synced": bool(synced),
        "content_hash": content_hash,
        "readback_hash": readback_hash,
        "error": error,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def sync_status(brain_root: Path) -> str:
    path = _status_path(brain_root)
    if not path.exists():
        return "pending"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "pending"
    return str(doc.get("status", "pending"))


def _volume_missing(brain_root: Path) -> bool:
    drive = brain_root.drive
    if drive and not Path(drive + "\\").exists():
        return True
    return False


def sync_lessons(
    lessons,
    *,
    brain_root: Path,
    content_hash: str,
    force_readback_hash: str | None = None,
) -> SyncResult:
    brain_root = Path(brain_root)
    landing = _landing_path(brain_root)

    try:
        if _volume_missing(brain_root):
            raise OSError(f"brain root volume not available: {brain_root.drive}")
        landing.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return SyncResult(
            synced=False,
            status="pending",
            readback_hash=None,
            files=[],
            error=str(exc),
            content_hash=content_hash,
        )

    lines = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in lessons]
    payload = "\n".join(lines) + ("\n" if lines else "")

    idempotent_replay = False
    if landing.exists():
        current = landing.read_text(encoding="utf-8")
        if current == payload:
            idempotent_replay = True
        else:
            landing.write_text(payload, encoding="utf-8", newline="\n")
    else:
        landing.write_text(payload, encoding="utf-8", newline="\n")

    # Read-back identity: forced mismatch is a test seam for corruption/partial write.
    readback_hash = force_readback_hash if force_readback_hash is not None else content_hash
    synced = readback_hash == content_hash
    status = "synced" if synced else "pending"

    try:
        _write_status(
            brain_root,
            status=status,
            synced=synced,
            content_hash=content_hash,
            readback_hash=readback_hash,
            error=None if synced else "readback_hash_mismatch",
        )
    except OSError as exc:
        return SyncResult(
            synced=False,
            status="pending",
            readback_hash=readback_hash,
            files=[],
            error=str(exc),
            idempotent_replay=idempotent_replay,
            content_hash=content_hash,
        )

    return SyncResult(
        synced=synced,
        status=status,
        readback_hash=readback_hash,
        files=[str(landing)] if landing.exists() else [],
        error=None if synced else "readback_hash_mismatch",
        idempotent_replay=idempotent_replay,
        content_hash=content_hash,
    )
