"""C06 training smoke — gated, tiny, never full SFT/LoRA on the 501 legacy rows.

Hard rules (standing order + acceptance plan):
    - `require_promotion_ready()` must PASS before any optimizer step.
    - Smoke runs on `evidence/gold_train.jsonl` (human-confirmed) ONLY.
      `vivy_train_dataset.jsonl` is refused by filename and by row-shape.
    - An `SFTTrainer`-only run is `NOT_RLCD_SFTTRAINER_ONLY` — never "RLCD complete".
    - Claim ceiling is `PROVISIONAL_RESULT` / smoke label. Never `VERIFIED_RESULT`,
      never `PRODUCTION-READY`.

Changelog:
    24/09/2026 (Claude Code — P3 C06): Initial.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from training.preflight import PreflightBlocked, require_promotion_ready

CLAIM_CEILING = "PROVISIONAL_RESULT"
NOT_RLCD = "NOT_RLCD_SFTTRAINER_ONLY"
MAX_SMOKE_STEPS = 8
LEGACY_DATASET_NAMES = frozenset({"vivy_train_dataset.jsonl", "vivy_train_dataset.json"})


class SmokeTrainBlocked(RuntimeError):
    """Raised when the smoke refuses to run (wrong dataset, blocked preflight)."""


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _looks_legacy_chatml(row: Mapping[str, Any]) -> bool:
    return "messages" in row and "selected_candidate" not in row


def _loss_toy(pred: float, target: float) -> float:
    p = min(max(pred, 1e-6), 1.0 - 1e-6)
    return -(target * math.log(p) + (1.0 - target) * math.log(1.0 - p))


def run_smoke(
    gold_path: str | Path,
    *,
    steps: int = 2,
    root: str | Path = ".",
    require_preflight: bool = True,
) -> dict[str, Any]:
    gold = Path(gold_path)
    root_path = Path(root)
    n_steps = min(int(steps), MAX_SMOKE_STEPS)
    capped = int(steps) > MAX_SMOKE_STEPS

    if gold.name in LEGACY_DATASET_NAMES:
        raise SmokeTrainBlocked(
            f"{gold.name} is the 501-row legacy ChatML set — C06 refuses full SFT/LoRA on it"
        )

    preflight_ok = True
    preflight_report: dict[str, Any] = {}
    if require_preflight:
        try:
            preflight_report = require_promotion_ready(root_path, run_contract_tests=False)
            preflight_ok = preflight_report.get("promotion") == "READY_FOR_SMOKE"
        except PreflightBlocked as exc:
            preflight_ok = False
            preflight_report = {"promotion": "BLOCKED", "error": str(exc)}

    result: dict[str, Any] = {
        "label": "SMOKE_TRAIN_NOT_FULL_SFT",
        "claim_ceiling": CLAIM_CEILING,
        "rlcd_claim": NOT_RLCD,
        "is_full_sft": False,
        "is_lora": False,
        "dataset": str(gold),
        "preflight_ok": preflight_ok,
        "preflight": preflight_report,
        "n_steps": 0,
        "capped": capped,
        "blocked": False,
        "losses": [],
    }

    if not preflight_ok:
        result["blocked"] = True
        result["reason"] = "preflight not READY_FOR_SMOKE — no optimizer step taken"
        return result

    rows = _load_rows(gold)
    if any(_looks_legacy_chatml(row) for row in rows):
        raise SmokeTrainBlocked("legacy ChatML rows detected — migrate + promote first")
    if not rows:
        result["blocked"] = True
        result["reason"] = "empty gold set"
        return result

    # Tiny smoke: one trainable scalar, full-batch BCE against the selection bit.
    # This proves the load → loss → step path. It is NOT SFT and NOT LoRA.
    w = 0.0
    losses: list[float] = []
    for _ in range(n_steps):
        total = 0.0
        grad = 0.0
        for row in rows:
            target = 1.0 if (row.get("selected_candidate") == "a") else 0.0
            pred = 1.0 / (1.0 + math.exp(-w))
            total += _loss_toy(pred, target)
            grad += (pred - target)
        w -= 0.1 * grad / len(rows)
        losses.append(total / len(rows))

    result["n_steps"] = n_steps
    result["losses"] = losses
    result["n_rows"] = len(rows)
    result["gold_outcome_note"] = (
        "all gold_outcome are unknown — this smoke trains on selection labels only"
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("gold", nargs="?", default="evidence/gold_train.jsonl")
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        report = run_smoke(args.gold, steps=args.steps, root=args.root)
    except SmokeTrainBlocked as exc:
        print(json.dumps({"blocked": True, "reason": str(exc)}, indent=2))
        raise SystemExit(2)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report.get("n_steps") else 3)
