"""Retry Dream receipts after the runtime regains access to 2brain."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pending-dir", default=".vivy_pending_sync")
    parser.add_argument("--target", default=r"D:\2brain\hot-memory")
    args = parser.parse_args()

    pending = Path(args.pending_dir)
    target = Path(args.target)
    files = sorted(pending.glob("dream-*.md")) if pending.exists() else []
    copied = 0
    for source in files:
        try:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target / source.name)
        except OSError as exc:
            print(f"PENDING {source}: {exc}")
            continue
        source.unlink()
        copied += 1
        print(f"SYNCED {source.name}")
    print(f"RESULT copied={copied} pending={len(files) - copied}")
    return 0 if copied == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
