"""C04 fixture OUTCOME_RECIPTS — sandbox scenarios only, clearly labeled SYNTHETIC.

These prove the capture contract, not action quality. Never feed them to
gold_train and never cite them as observed production outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.io_guard import open_write
from training.outcome_capture import (
    OUTCOME_ACTION_FAILURE,
    OUTCOME_FOCUS_CHANGE,
    OUTCOME_PARTIAL,
    OUTCOME_RETRY,
    OUTCOME_ROLLBACK,
    OUTCOME_STALE_CAPTURE,
    OUTCOME_SUCCESS,
    OUTCOME_TIMEOUT,
    OUTCOME_WRONG_STATE,
    record_capture,
)


def _snap(fid: str, at: str, kind: str) -> dict:
    return {
        "capture_id": f"cap-{kind}-{fid}",
        "captured_at": at,
        "state_fingerprint": fid,
        "state_kind": kind,
    }


def _fixture(name: str, **overrides) -> dict:
    base = {
        "task_id": f"fixture-{name}",
        "goal": f"Sandbox fixture scenario: {name}",
        "candidate_set": ["cand_save", "cand_halt"],
        "chosen_action": "cand_save",
        "permission": "sandbox",
        "tool_result": {"ok": True, "tool": "click", "detail": name},
        "capture_before": _snap("aaa111", "2026-09-24T10:00:00+00:00", "before"),
        "capture_after": _snap("bbb222", "2026-09-24T10:00:02+00:00", "after"),
        "expected_postcondition": ["fixture file persisted"],
        "observed_postcondition": ["fixture file persisted"],
        "independent_checker": {
            "checker_id": "fixture-fs-checker-v1",
            "checked_at": "2026-09-24T10:00:03+00:00",
            "verdict": "met",
            "evidence": "fixture stat() ok",
        },
    }
    base.update(overrides)
    return base


def build_fixtures() -> list[tuple[str, dict]]:
    return [
        ("success", record_capture(_fixture("success"))),
        (
            "tool_success_wrong_state",
            record_capture(_fixture(
                "tool_success_wrong_state",
                observed_postcondition=[],
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "not_met", "evidence": "file missing after click",
                },
            )),
        ),
        (
            "timeout",
            record_capture(_fixture(
                "timeout",
                tool_result={"ok": False, "error": "timeout"},
                capture_after=None,
                observed_postcondition=[],
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "timeout", "evidence": "no after capture",
                },
            )),
        ),
        (
            "focus_change",
            record_capture(_fixture(
                "focus_change",
                independent_checker={
                    "checker_id": "fixture-focus-checker-v1", "checked_at": "t",
                    "verdict": "focus_change", "evidence": "window left foreground",
                },
            )),
        ),
        (
            "stale_capture",
            record_capture(_fixture(
                "stale_capture",
                capture_after=_snap("aaa111", "2026-09-24T09:59:00+00:00", "after"),
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "stale", "evidence": "after capture predates action",
                },
            )),
        ),
        (
            "partial",
            record_capture(_fixture(
                "partial",
                observed_postcondition=["file created"],
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "partial", "evidence": "one of two postconditions",
                },
            )),
        ),
        (
            "retry",
            record_capture(_fixture(
                "retry",
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "retry", "evidence": "transient miss, retry allowed",
                },
            )),
        ),
        (
            "rollback",
            record_capture(_fixture(
                "rollback",
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "rolled_back", "evidence": "state restored to before",
                },
            )),
        ),
        (
            "action_failure",
            record_capture(_fixture(
                "action_failure",
                tool_result={"ok": False, "error": "permission denied"},
                independent_checker={
                    "checker_id": "fixture-fs-checker-v1", "checked_at": "t",
                    "verdict": "tool_error", "evidence": "tool refused the call",
                },
            )),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence/c04_outcome_fixtures.jsonl")
    args = parser.parse_args()
    out_path = Path(args.output)
    expected = {
        "success": OUTCOME_SUCCESS,
        "tool_success_wrong_state": OUTCOME_WRONG_STATE,
        "timeout": OUTCOME_TIMEOUT,
        "focus_change": OUTCOME_FOCUS_CHANGE,
        "stale_capture": OUTCOME_STALE_CAPTURE,
        "partial": OUTCOME_PARTIAL,
        "retry": OUTCOME_RETRY,
        "rollback": OUTCOME_ROLLBACK,
        "action_failure": OUTCOME_ACTION_FAILURE,
    }
    lines = []
    mismatches = []
    for name, record in build_fixtures():
        if record["gold_outcome"] != expected[name]:
            mismatches.append({"scenario": name, "got": record["gold_outcome"], "want": expected[name]})
        lines.append(json.dumps({
            "fixture": True,
            "synthetic": True,
            "scenario": name,
            "note": "SYNTHETIC FIXTURE — not a production observed outcome; do not promote to gold_train",
            "record": record,
        }, ensure_ascii=False))
    with open_write(out_path, allow_replace=True) as handle:
        handle.write("\n".join(lines) + "\n")
    print(json.dumps({
        "n_fixtures": len(lines),
        "mismatches": mismatches,
        "output": str(out_path),
        "label": "SYNTHETIC_FIXTURES_NOT_OBSERVED_PRODUCTION",
    }, ensure_ascii=False, indent=2))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
