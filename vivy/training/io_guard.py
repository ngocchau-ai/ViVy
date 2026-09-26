"""Output-path guards so reruns cannot clobber inputs or prior receipts.

Changelog: 2026-09-24 (Antigravity/Claude Code — P0 CORRECTIONS §2.11)
    Initial. Resolves alias/junction via Path.resolve(); refuses to write over
    a protected source or an existing artifact unless allow_replace is set.
"""
from __future__ import annotations

from pathlib import Path
from typing import IO, Iterable


class RefuseOverwriteError(RuntimeError):
    """Raised when a write would destroy an input or a prior receipt."""


def resolved(path: str | Path) -> Path:
    """Absolute path with junction/symlink aliases collapsed."""
    return Path(path).expanduser().resolve()


def assert_not_protected(output: str | Path, protected: Iterable[str | Path]) -> Path:
    out = resolved(output)
    for item in protected:
        other = resolved(item)
        if out == other or (other.exists() and out.exists() and out.samefile(other)):
            raise RefuseOverwriteError(
                f"refusing to overwrite protected path: {out} (protected: {other})"
            )
    return out


def open_write(
    output: str | Path,
    *,
    protected: Iterable[str | Path] = (),
    allow_replace: bool = False,
) -> IO[str]:
    """Open *output* for write after overwrite checks.

    Refuses when the target equals any *protected* path, or when the target
    already exists and *allow_replace* is false. Protects inputs and prior
    receipts across reruns, including via directory alias/junction.
    """
    out = assert_not_protected(output, protected)
    if out.exists() and not allow_replace:
        raise RefuseOverwriteError(
            f"refusing to overwrite existing file: {out} (pass allow_replace=True to replace)"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    return out.open("w", encoding="utf-8")
