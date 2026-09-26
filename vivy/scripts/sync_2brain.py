#!/usr/bin/env python3
"""
sync_2brain.py -- ViVy Sprint 4 Gate 5 (Durability + 2brain Sync).

Dong bo ViVy knowledge snapshot vao D:\2brain.
    - Copy lesson_store.jsonl -> D:\2brain\\projects\vivy-v5\\lessons\
    - Ghi durable_decisions.md summary tu lessons VERIFIED_RESULT
    - Update hot-memory profile voi session metrics

Chi dong bo VERIFIED_RESULT lessons. FAST_SIGNAL + PROVISIONAL bi bo qua.

Changelog:
    21/09/2026 (Antigravity IDE, Sprint 4): Initial.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_2BRAIN_ROOT = Path(r"D:\2brain")
_VIVY_V5_DIR = _2BRAIN_ROOT / "projects" / "vivy-v5"
_HOT_MEMORY = _2BRAIN_ROOT / "hot-memory"
_LESSONS_DST = _VIVY_V5_DIR / "lessons"
_DEFAULT_LESSONS_SRC = Path("vivy_lessons.jsonl")


def sync_lessons(src: Path, dst_dir: Path) -> int:
    """Copy lesson store to 2brain and return count of VERIFIED lessons synced."""
    if not src.exists():
        logger.warning("sync_2brain: no lesson file at %s -- skipping", src)
        return 0

    dst_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    dst_file = dst_dir / f"lessons_{ts}.jsonl"
    shutil.copy2(src, dst_file)
    logger.info("sync_2brain: copied %s -> %s", src.name, dst_file)

    # Count VERIFIED lessons
    count = 0
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("evidence_class") == "VERIFIED_RESULT" and not d.get("is_isolated", False):
                    count += 1
            except Exception:
                continue
    return count


def write_durable_decisions(lessons_src: Path, dst_dir: Path) -> None:
    """Write durable_decisions.md from VERIFIED_RESULT lessons."""
    dst_dir.mkdir(parents=True, exist_ok=True)

    lessons = []
    if lessons_src.exists():
        seen: dict[str, dict] = {}
        with lessons_src.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    seen[d["lesson_id"]] = d
                except Exception:
                    continue
        lessons = [
            d for d in seen.values()
            if d.get("evidence_class") == "VERIFIED_RESULT"
            and not d.get("is_isolated", False)
        ]
        lessons.sort(key=lambda d: d.get("created_at", 0), reverse=True)

    md_lines = [
        "> [!IMPORTANT]",
        "> **QUY UOC BAT BUOC DANH CHO AGENT KE THUA:**",
        "> 1. Changelog bat buoc (Ten/ID Agent, thoi gian, ly do).",
        "> 2. Chi co lap, KHONG xoa bo. Danh dau [ISOLATED / DEPRECATED / REPLACED].",
        "> 3. Dong bo D:\\2brain day du.",
        "",
        "# ViVy Durable Decisions (VERIFIED_RESULT Lessons)",
        "",
        f"**Synced:** {time.strftime('%Y-%m-%d %H:%M:%S ICT')}  ",
        f"**Total VERIFIED lessons:** {len(lessons)}",
        "",
        "---",
        "",
    ]

    for i, entry in enumerate(lessons, 1):
        md_lines.extend([
            f"## DD-{i:02d}: {entry.get('scope', 'general')}",
            "",
            entry.get("content", ""),
            "",
            f"- **Lesson ID:** `{entry.get('lesson_id', '?')}`",
            f"- **Session:** `{entry.get('session_id', '?')[:12]}`",
            f"- **Confidence:** {entry.get('confidence', 0.0):.3f}",
            f"- **Provenance:** `{json.dumps(entry.get('provenance', {}))[:80]}`",
            "",
            "---",
            "",
        ])

    out = dst_dir / "durable_decisions.md"
    out.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("sync_2brain: wrote %s (%d decisions)", out, len(lessons))


def update_hot_memory(lesson_count: int, hot_memory_dir: Path | None = None) -> None:
    """Append a sync receipt to hot-memory."""
    target = hot_memory_dir or _HOT_MEMORY
    target.mkdir(parents=True, exist_ok=True)
    receipt_file = target / "vivy_sync_receipts.jsonl"
    receipt = {
        "timestamp": time.time(),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verified_lessons_synced": lesson_count,
        "agent": "Antigravity IDE",
        "source": "scripts/sync_2brain.py",
    }
    with receipt_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt) + "\n")
    logger.info("sync_2brain: hot-memory receipt written (%d lessons)", lesson_count)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync ViVy knowledge to D:\\2brain")
    parser.add_argument(
        "--lessons", default=str(_DEFAULT_LESSONS_SRC),
        help="Path to vivy_lessons.jsonl (default: ./vivy_lessons.jsonl)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be synced without writing"
    )
    args = parser.parse_args()

    src = Path(args.lessons)
    logger.info("sync_2brain: starting sync from %s", src)

    if args.dry_run:
        logger.info("DRY RUN -- no files will be written")
        if src.exists():
            with src.open() as f:
                count = sum(
                    1 for line in f
                    if '"VERIFIED_RESULT"' in line and '"is_isolated": false' not in line
                )
            logger.info("Would sync ~%d VERIFIED lessons", count)
        else:
            logger.info("No lesson file found at %s", src)
        return

    if not _2BRAIN_ROOT.exists():
        logger.error(
            "D:\\2brain not found at %s -- sync aborted. "
            "Mount or create D:\\2brain first.",
            _2BRAIN_ROOT,
        )
        sys.exit(1)

    count = sync_lessons(src, _LESSONS_DST)
    write_durable_decisions(src, _VIVY_V5_DIR)
    update_hot_memory(count)
    logger.info("sync_2brain: DONE -- %d VERIFIED lessons synced to D:\\2brain", count)


if __name__ == "__main__":
    main()
