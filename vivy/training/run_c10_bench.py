"""C10 live evidence: multi-size Hebbian + memory-on/off + ABI layout report.

Writes `evidence/c10_memory_c_abi_hebbian.json` (new file only; io_guard
refuses overwrite). Numbers are wall-clock observations on this machine.

Changelog:
    2026-09-24 (Claude Code — P5 C10): Initial.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from training.abi_layout import check_struct_layout, ownership_rules
from training.hebbian_bench import run_hebbian_scaling
from training.io_guard import open_write
from training.memory_retrieval_ab import MemoryCase, RetrievalTask, run_memory_on_off
from training.session_memory import SessionMemoryHub


def _memory_demo() -> dict:
    hub = SessionMemoryHub()
    a = hub.for_session("sess-a")
    b = hub.for_session("sess-b")
    a.put("secret-a", kind="HARD_FACT", content="only in session A", now_ms=0)
    b.put("shared-id", kind="TASK", content="b-value", now_ms=0)
    a.put("shared-id", kind="TASK", content="a-value", now_ms=0)
    a.put("stale-a", kind="SUMMARY", content="old", ttl_ms=10, now_ms=0)
    return {
        "cross_session_get_is_none": b.get("secret-a", now_ms=0) is None,
        "session_a_count": a.count(now_ms=0),
        "session_b_count": b.count(now_ms=0),
        "shared_id_versions_independent": (
            a.get("shared-id", now_ms=0).version == 1
            and b.get("shared-id", now_ms=0).version == 1
        ),
        "stale_hidden_after_ttl": a.get("stale-a", now_ms=50) is None,
        "session_ids": hub.session_ids(),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("evidence/c10_memory_c_abi_hebbian.json")

    hebbian = run_hebbian_scaling(
        dim=32,
        ns=(8, 16, 32, 64, 128, 256),
        reps=30,
        seed=42,
    )

    store = [
        MemoryCase(
            memory_id="m-focus",
            content="focused window is #3",
            tags={"relevant"},
            session_id="s1",
            created_at_ms=1,
            expires_at_ms=0,
        ),
        MemoryCase(
            memory_id="m-policy",
            content="do not place unauthorized trades",
            tags={"relevant"},
            session_id="s1",
            created_at_ms=1,
            expires_at_ms=0,
        ),
        MemoryCase(
            memory_id="m-other",
            content="unrelated filler text",
            tags=set(),
            session_id="s1",
            created_at_ms=1,
            expires_at_ms=0,
        ),
        MemoryCase(
            memory_id="m-foreign",
            content="focused window is #3",
            tags={"relevant"},
            session_id="OTHER",
            created_at_ms=1,
            expires_at_ms=0,
        ),
    ]
    tasks = [
        RetrievalTask("t1", "which window is focused", "m-focus", ("m-focus", "m-other")),
        RetrievalTask("t2", "what is the trade prohibition", "m-policy", ("m-policy", "m-other")),
        RetrievalTask("t3", "unrelated question with no memory", None, ("m-focus", "m-policy")),
    ]
    ab = run_memory_on_off(tasks, store, session_id="s1", seed=0)

    payload = {
        "component": "C10",
        "title": "Memory / C-ABI / Hebbian multi-size",
        "status_label": "PROVISIONAL_RESULT",
        "abi_layout": check_struct_layout(),
        "ownership_rules": ownership_rules(),
        "session_isolation": _memory_demo(),
        "hebbian_scaling": hebbian,
        "memory_on_off": ab,
        "claims": {
            "no_cross_session_leak": "TESTED_ON_HUB_FIXTURES",
            "hebbian_wx_separated_from_scan": "TESTED",
            "o1_from_two_points": "REFUSED",
            "physical_zero_latency": "NOT_CLAIMED",
            "dll_load_equals_memory_correctness": "NOT_CLAIMED",
        },
        "note": (
            "wall-clock observations on this machine; W@x and node-ID scan are "
            "separate; no O(1), 0ms, or production-router claim"
        ),
    }

    with open_write(out, protected=()) as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(json.dumps({
        "output": str(out),
        "hebbian_n_sizes": hebbian["n_sizes"],
        "hebbian_dim": hebbian["dim"],
        "gain": ab["gain"],
        "harm": ab["harm"],
        "tie": ab["tie"],
        "cross_session_get_is_none": payload["session_isolation"]["cross_session_get_is_none"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
