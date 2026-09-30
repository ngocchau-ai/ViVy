"""T2 evaluation harness — does the pipeline earn its complexity? (WP-7 / O-02)

Runs three arms over one eval split and writes a receipt:

    (a) baseline            plain Gemma, one chat call per item
    (b) pipeline            ``VivyInferenceLoop.infer`` — the product path
    (c) pipeline+decoder    the pipeline, then ``Decoder.decode`` with the
                            **original question** in the LogicForm query so the
                            synthesiser sees what was actually asked

Plan wording: *"Nghiệm thu (T2): pipeline ≥ baseline − 2 điểm %. Nếu <
baseline − 5 điểm % → dừng, thiết kế lại."*

D-7 (29/09/2026): held-out is **not in this repo**.  The harness fails closed
without the owner-supplied file and verifies every item against the committed
``heldout_manifest.json`` hash before scoring, so a substituted file cannot
quietly redefine the test.

D-8 (29/09/2026): a *hang ceiling* only (120 s/item, 4096 completion tokens).
The point of the ceiling is to stop a runaway, not to declare a budget — raw
latency and token counts are recorded per item and the real T11 numbers are
fixed from this baseline.  Any latency figure in a receipt is a measurement;
any latency figure in a document that has not run this is ``UNMEASURED``.

Gate 9: every reply records ``model_call_made`` as ``True`` / ``False`` /
``None`` (unknown).  A timed-out arm reports ``None`` — we never claim a call
happened that we did not observe, and never claim one did not when we cannot
tell.

Usage
-----
    python benchmarks/harness.py --split dev --arms baseline
    python benchmarks/harness.py --split heldout \\
        --heldout D:\\91s_heldout\\vivy_T2\\heldout_set.jsonl \\
        --arms baseline,pipeline,pipeline_decoder

Changelog:
    29/09/2026 (Claude Code — WP-7/O-02): Initial.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.checker import check_answer  # noqa: E402
from benchmarks.eval_set.schema import (  # noqa: E402
    EvalItem,
    read_jsonl,
    sha256_item,
)

BENCHMARKS_DIR = Path(__file__).resolve().parent
EVAL_SET_DIR = BENCHMARKS_DIR / "eval_set"
DEV_SET_PATH = EVAL_SET_DIR / "dev_set.jsonl"
MANIFEST_PATH = EVAL_SET_DIR / "heldout_manifest.json"
EVIDENCE_DIR = ROOT / "evidence"

#: D-8.  Stop a runaway; do not treat these as a budget.
HANG_CEILING_S = 120.0
MAX_COMPLETION_TOKENS = 4096

#: T2 thresholds, in accuracy points (1.0 = 100%).
T2_FLOOR_DELTA = -0.02          # pipeline >= baseline - 2pp  -> PASS
T2_STOP_DELTA = -0.05           # pipeline <  baseline - 5pp  -> STOP, redesign
QUANTUM_RETENTION_DELTA = 0.05  # keep quantum only at >= baseline + 5pp
QUANTUM_LATENCY_FACTOR = 2.0    # ... at <= 2x baseline latency


# ---------------------------------------------------------------------------
# What one arm produced for one item
# ---------------------------------------------------------------------------


@dataclass
class ArmReply:
    """One arm's answer to one item.  ``model_call_made`` is three-valued on
    purpose: ``None`` means we do not know (timeout / crash before the arm
    reported)."""

    text: str = ""
    latency_ms: float = 0.0
    completion_tokens: int = 0
    model_call_made: bool | None = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArmRunner(Protocol):
    """A scoring arm.  Implementations must be synchronously callable."""

    name: str

    def run(self, item: EvalItem) -> ArmReply: ...


# ---------------------------------------------------------------------------
# Hang ceiling (D-8)
# ---------------------------------------------------------------------------


def run_with_ceiling(
    fn: Callable[[EvalItem], ArmReply],
    item: EvalItem,
    ceiling_s: float = HANG_CEILING_S,
) -> ArmReply:
    """Run one arm on one item, abandoning it at the ceiling.

    A **daemon** thread, not a ``ThreadPoolExecutor``.  That distinction is the
    whole point of D-8: ``with ThreadPoolExecutor(...)`` calls
    ``shutdown(wait=True)`` on exit, so a timed-out arm would still block the
    run and the process — the ceiling would be decorative.  A daemon thread is
    genuinely abandoned and does not hold the interpreter open.

    The arm cannot be killed, only left behind, so the reply is recorded as
    unknown-call rather than "no model call": we do not know what the abandoned
    thread did, and Gate 9 forbids claiming otherwise.
    """
    started = time.perf_counter()
    box: dict[str, ArmReply] = {}
    failure: list[BaseException] = []

    def _target() -> None:
        try:
            box["reply"] = fn(item)
        except BaseException as exc:  # noqa: BLE001 — surfaced as a scored miss
            failure.append(exc)

    thread = threading.Thread(
        target=_target, daemon=True, name=f"t2-ceiling-{item.id}"
    )
    thread.start()
    thread.join(timeout=ceiling_s)

    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if thread.is_alive():
        return ArmReply(
            text="",
            latency_ms=elapsed_ms,
            completion_tokens=0,
            model_call_made=None,
            error=f"timeout_after_{ceiling_s:g}s",
        )
    if failure:
        exc = failure[0]
        return ArmReply(
            text="",
            latency_ms=elapsed_ms,
            completion_tokens=0,
            model_call_made=None,
            error=f"{type(exc).__name__}: {exc}",
        )
    return box.get("reply", ArmReply(latency_ms=elapsed_ms, error="arm_returned_nothing"))


# ---------------------------------------------------------------------------
# Live arms
# ---------------------------------------------------------------------------


def fresh_client() -> Any:
    """A new ``LLMClient`` for one call.

    ``LLMClient`` caches its ``httpx.AsyncClient`` on the event loop that first
    used it.  The harness drives each call through ``asyncio.run``, which builds
    a new loop every time, so a *reused* client dies on the second call with
    ``RuntimeError: Event loop is closed`` and the item is scored wrong for a
    plumbing reason.  A fresh client per call keeps every loop self-contained.

    The underlying lifecycle is a real ``LLMClient`` defect worth its own fix
    in ``llm_bridge/``; it is not repaired here because WP-7 is the measurement,
    not the shared client.
    """
    from llm_bridge.client import LLMClient

    return LLMClient(backend=_backend())


def _backend() -> Any:
    from llm_bridge.backend import LLMBackend

    return LLMBackend.from_env()


class PlainModelArm:
    """(a) baseline — one plain chat call, no pipeline."""

    name = "baseline"

    def __init__(self, client: Any = None, model: str | None = None) -> None:
        self.client = client
        self.model = model

    def run(self, item: EvalItem) -> ArmReply:
        started = time.perf_counter()
        text = asyncio.run(self._chat(item.prompt))
        return ArmReply(
            text=text,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            completion_tokens=0,
            model_call_made=True,
            error=None,
        )

    async def _chat(self, prompt: str) -> str:
        client = self.client if self.client is not None else fresh_client()
        return await client.chat(
            prompt,
            model=self.model,
            temperature=0.0,
            max_tokens=MAX_COMPLETION_TOKENS,
            fallback=False,
        )


class PipelineArm:
    """(b) the product path — ``VivyInferenceLoop.infer``."""

    name = "pipeline"

    def __init__(self, loop: Any) -> None:
        self.loop = loop

    def run(self, item: EvalItem) -> ArmReply:
        started = time.perf_counter()
        result = self.loop.infer(item.prompt, session_id=f"t2-{item.id}")
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        error = getattr(result, "error", None)
        return ArmReply(
            text=getattr(result, "response_text", "") or "",
            latency_ms=elapsed_ms,
            completion_tokens=int(getattr(result, "llm_tokens_used", 0) or 0),
            model_call_made=True,
            error=error,
        )


class PipelineDecoderArm:
    """(c) the pipeline, then ``Decoder`` with the **original question**.

    The Decoder's prompt template prints ``QUERY: {logic_form.query}``, so this
    is where the original question is put back in front of the synthesiser.
    Without it the Decoder would only see the pipeline's own conclusion and
    could not restate a numeric answer in the declared form.
    """

    name = "pipeline_decoder"

    def __init__(self, loop: Any, decoder: Any = None) -> None:
        self.loop = loop
        self.decoder = decoder

    def run(self, item: EvalItem) -> ArmReply:
        started = time.perf_counter()
        result = self.loop.infer(item.prompt, session_id=f"t2-{item.id}")
        core = build_core_result(item, getattr(result, "response_text", ""))
        from llm_bridge.decoder import Decoder

        decoder = self.decoder if self.decoder is not None else Decoder(fresh_client())
        text = asyncio.run(decoder.decode(core))
        return ArmReply(
            text=text,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            completion_tokens=int(getattr(result, "llm_tokens_used", 0) or 0),
            model_call_made=True,
            error=getattr(result, "error", None),
        )


def build_core_result(item: EvalItem, pipeline_text: str) -> Any:
    """Pack one pipeline run into the ``CoreResult`` the Decoder expects."""
    from llm_bridge.decoder import CoreResult
    from llm_bridge.encoder import LogicForm

    return CoreResult(
        logic_form=LogicForm(
            propositions=[f"pipeline_output: {pipeline_text.strip()[:500]}"],
            relations=[("pipeline", "produced", "output")],
            query=item.prompt,
        ),
        conclusion=pipeline_text.strip(),
        confidence=1.0,
        control_signal="continue",
        details={"eval_item_id": item.id, "expected_kind": item.expected_kind},
    )


# ---------------------------------------------------------------------------
# Loading — D-7 fail-closed
# ---------------------------------------------------------------------------


class HeldOutError(RuntimeError):
    """Raised when the held-out set cannot be trusted.  Never swallowed."""


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("items", [])
    return {row["id"]: row for row in rows}


def verify_heldout_items(
    items: Sequence[EvalItem],
    manifest: dict[str, dict[str, Any]],
) -> list[str]:
    """Return a list of problems.  Empty means the file is the real one."""
    problems: list[str] = []
    for item in items:
        row = manifest.get(item.id)
        if row is None:
            problems.append(f"{item.id}: not in the committed held-out manifest")
            continue
        actual = sha256_item(item)
        if actual != row["sha256"]:
            problems.append(
                f"{item.id}: sha256 mismatch — committed {row['sha256'][:16]}…, "
                f"file {actual[:16]}… (the held-out file was substituted)"
            )
        for key in ("domain", "split", "kind", "expected_kind"):
            if row.get(key) != getattr(item, key):
                problems.append(
                    f"{item.id}: {key} is {getattr(item, key)!r}, manifest says {row.get(key)!r}"
                )
    return problems


def load_heldout_items(
    heldout_path: str | os.PathLike[str] | None,
    *,
    env_var: str = "VIVY_HELDOUT_PATH",
    manifest_path: Path = MANIFEST_PATH,
) -> list[EvalItem]:
    """Load and authenticate the owner-supplied held-out file.

    Fail-closed: no file, no read, no score.  The repo never holds the prompts
    (D-7), so there is no fallback to a committed copy.
    """
    raw = heldout_path or os.environ.get(env_var) or ""
    if not str(raw).strip():
        raise HeldOutError(
            "held-out set required and not supplied: pass --heldout <path outside "
            "Vivy_final/> or set VIVY_HELDOUT_PATH.  The repo does not hold the "
            "held-out prompts (D-7, 29/09/2026) — regenerate them with "
            "`python -m benchmarks.eval_set.generate --split heldout --out <path>`."
        )
    path = Path(str(raw)).expanduser()
    if not path.is_file():
        raise HeldOutError(f"held-out file not found: {path}")

    items = read_jsonl(str(path))
    if not items:
        raise HeldOutError(f"held-out file is empty: {path}")

    manifest = load_manifest(manifest_path)
    problems = verify_heldout_items(items, manifest)
    if problems:
        preview = "\n  - ".join(problems[:10])
        raise HeldOutError(
            f"held-out file failed authentication ({len(problems)} problem(s)):\n  - {preview}"
        )

    expected_ids = {i for i, row in manifest.items() if row.get("split") == "heldout"}
    got_ids = {i.id for i in items}
    missing = sorted(expected_ids - got_ids)
    if missing:
        raise HeldOutError(
            f"held-out file is incomplete: {len(missing)} committed item(s) missing, "
            f"e.g. {missing[:5]}"
        )
    return items


def load_dev_items(path: Path = DEV_SET_PATH) -> list[EvalItem]:
    items = read_jsonl(str(path))
    for item in items:
        if item.split != "dev":
            raise HeldOutError(f"{item.id}: dev file contains a non-dev item")
    return items


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass
class ItemScore:
    id: str
    domain: str
    kind: str
    expected: str
    expected_kind: str
    arms: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Per-definition confidence scores (O-05/T3).  Populated when ``--t3``
    #: is active; empty dict otherwise.  Keys are definition names from
    #: ``benchmarks.calibration.features.EXTRACTORS``.
    confidence_by_definition: dict[str, float] = field(default_factory=dict)


def _is_ceiling_hit(arm_row: dict[str, Any]) -> bool:
    error = arm_row.get("error") or ""
    return error.startswith("timeout_after_")


def _summarise(scores: list[ItemScore], arm: str) -> dict[str, Any]:
    n = len(scores)
    correct = [bool(s.arms.get(arm, {}).get("correct")) for s in scores]
    n_correct = sum(correct)

    # A ceiling hit is a *censored* observation, not a wrong answer.  D-8 set
    # 120 s to catch hangs; when the model is merely slow, scoring the miss as
    # wrong would make T2 measure "who finished in time" rather than "who was
    # right".  Both accuracies are reported so the owner can see the difference
    # and fix the number (which is exactly what D-8 deferred to after T2).
    censored = [i for i, s in enumerate(scores) if _is_ceiling_hit(s.arms.get(arm, {}))]
    uncensored = [i for i in range(n) if i not in set(censored)]
    n_uncensored = len(uncensored)
    n_correct_uncensored = sum(1 for i in uncensored if correct[i])

    def _bucket(key: Callable[[ItemScore], str]) -> dict[str, Any]:
        buckets: dict[str, list[bool]] = {}
        for s, ok in zip(scores, correct, strict=True):
            buckets.setdefault(key(s), []).append(ok)
        return {
            k: {"n": len(v), "n_correct": sum(v), "accuracy": sum(v) / len(v)}
            for k, v in sorted(buckets.items())
        }

    latencies = [float(s.arms.get(arm, {}).get("latency_ms") or 0.0) for s in scores]
    latencies_sorted = sorted(latencies)
    median_latency = (
        latencies_sorted[len(latencies_sorted) // 2] if latencies_sorted else 0.0
    )
    return {
        "n_items": n,
        "n_correct": n_correct,
        "accuracy": (n_correct / n) if n else 0.0,
        "n_ceiling_hits": len(censored),
        "n_uncensored": n_uncensored,
        "n_correct_uncensored": n_correct_uncensored,
        "accuracy_uncensored": (n_correct_uncensored / n_uncensored) if n_uncensored else 0.0,
        "by_domain": _bucket(lambda s: s.domain),
        "by_kind": _bucket(lambda s: s.kind),
        "median_latency_ms": median_latency,
        "mean_latency_ms": (sum(latencies) / n) if n else 0.0,
        "n_errors": sum(1 for s in scores if s.arms.get(arm, {}).get("error")),
        "n_model_calls_observed": sum(
            1 for s in scores if s.arms.get(arm, {}).get("model_call_made") is True
        ),
        "n_model_calls_unknown": sum(
            1 for s in scores if s.arms.get(arm, {}).get("model_call_made") is None
        ),
    }


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on the discordant pairs.

    ``b`` = baseline correct and pipeline wrong, ``c`` = the reverse.  Under H0
    the discordant pairs split 50/50, so b ~ Binomial(b+c, 0.5).  No scipy.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    total = 2.0 ** n
    tail = sum(math.comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2.0 * tail / total)


def t2_verdict(baseline_acc: float, pipeline_acc: float) -> dict[str, Any]:
    """Apply the plan's T2 rule.  Returns a structured verdict, not a bool.

    ``_EPS`` exists because the thresholds are exact decimals in the plan
    ("≥ baseline − 2 điểm %") while the accuracies are floats: ``0.48 - 0.50``
    is ``-0.020000000000000018``, which would wrongly read as below the floor.
    """
    _EPS = 1e-9
    delta = pipeline_acc - baseline_acc
    if delta >= T2_FLOOR_DELTA - _EPS:
        status = "PASS"
        note = (
            f"pipeline {pipeline_acc:.4f} >= baseline {baseline_acc:.4f} "
            f"- 2pp (delta {delta * 100:+.2f}pp)"
        )
    elif delta < T2_STOP_DELTA - _EPS:
        status = "STOP_REDESIGN"
        note = (
            f"pipeline {pipeline_acc:.4f} < baseline {baseline_acc:.4f} "
            f"- 5pp (delta {delta * 100:+.2f}pp) — the plan's stop condition: "
            f"pause and redesign rather than tune further"
        )
    else:
        status = "MARGINAL"
        note = (
            f"pipeline {pipeline_acc:.4f} within the 2–5pp grey band "
            f"(delta {delta * 100:+.2f}pp) — no pass, no stop; inspect per-domain"
        )
    return {
        "status": status,
        "delta_accuracy": delta,
        "delta_pp": delta * 100.0,
        "rule": "T2: pipeline >= baseline - 2pp; < baseline - 5pp -> stop and redesign",
        "note": note,
    }


def quantum_retention(
    scores: list[ItemScore],
    baseline: str,
    pipeline: str,
) -> dict[str, Any]:
    """The plan's extra bar for keeping quantum components in the product."""
    quantum = [s for s in scores if s.domain == "quantum"]
    if not quantum:
        return {"status": "NOT_EVALUATED", "note": "no quantum items in this split"}
    b_ok = [bool(s.arms.get(baseline, {}).get("correct")) for s in quantum]
    p_ok = [bool(s.arms.get(pipeline, {}).get("correct")) for s in quantum]
    b_acc = sum(b_ok) / len(b_ok)
    p_acc = sum(p_ok) / len(p_ok)

    # McNemar on the quantum subset only
    only_b = sum(1 for x, y in zip(b_ok, p_ok, strict=True) if x and not y)
    only_p = sum(1 for x, y in zip(b_ok, p_ok, strict=True) if y and not x)
    p_value = mcnemar_exact(only_b, only_p)

    b_lat = sorted(float(s.arms.get(baseline, {}).get("latency_ms") or 0.0) for s in quantum)
    p_lat = sorted(float(s.arms.get(pipeline, {}).get("latency_ms") or 0.0) for s in quantum)
    med = lambda xs: xs[len(xs) // 2] if xs else 0.0  # noqa: E731
    latency_ratio = (med(p_lat) / med(b_lat)) if med(b_lat) > 0 else math.inf

    delta = p_acc - b_acc
    keep = (
        delta >= QUANTUM_RETENTION_DELTA
        and p_value < 0.05
        and latency_ratio <= QUANTUM_LATENCY_FACTOR
    )
    return {
        "status": "KEEP" if keep else "DO_NOT_KEEP",
        "n_items": len(quantum),
        "baseline_accuracy": b_acc,
        "pipeline_accuracy": p_acc,
        "delta_pp": delta * 100.0,
        "mcnemar_p": p_value,
        "baseline_median_latency_ms": med(b_lat),
        "pipeline_median_latency_ms": med(p_lat),
        "latency_ratio": latency_ratio,
        "rule": (
            "keep quantum components only at >= baseline + 5pp with McNemar p<0.05 "
            "and <= 2x baseline latency"
        ),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_eval(
    items: Sequence[EvalItem],
    arms: Sequence[ArmRunner],
    *,
    run_id: str,
    backend_identity: dict[str, Any] | None = None,
    split: str = "dev",
    ceiling_s: float = HANG_CEILING_S,
    t3: bool = False,
) -> dict[str, Any]:
    """Score every item on every arm and assemble the receipt payload."""
    scores: list[ItemScore] = []
    total = len(items)
    for position, item in enumerate(items, start=1):
        row = ItemScore(
            id=item.id,
            domain=item.domain,
            kind=item.kind,
            expected=item.expected,
            expected_kind=item.expected_kind,
        )
        for arm in arms:
            reply = run_with_ceiling(arm.run, item, ceiling_s=ceiling_s)
            checked = check_answer(item, reply.text)
            row.arms[arm.name] = {
                "text": reply.text,
                "correct": checked.correct,
                "reason": checked.reason,
                "parsed": checked.parsed,
                "declared_field": checked.declared_field,
                "latency_ms": reply.latency_ms,
                "completion_tokens": reply.completion_tokens,
                "model_call_made": reply.model_call_made,
                "error": reply.error,
            }
        scores.append(row)
        # A held-out run takes hours; without this the process is a black box
        # and a crash at hour 3 loses every measurement.  Progress goes to
        # stderr so the receipt file on stdout stays clean.
        marks = []
        for arm_name, arm_row in row.arms.items():
            mark = "ok" if arm_row.get("correct") else "no"
            if arm_row.get("error"):
                mark = "err"
            marks.append(f"{arm_name}={mark}")
        print(f"[{position}/{total}] {item.id}  {'  '.join(marks)}",
              file=sys.stderr, flush=True)

    arm_names = [arm.name for arm in arms]
    summaries = {name: _summarise(scores, name) for name in arm_names}

    baseline_name = "baseline" if "baseline" in arm_names else arm_names[0]
    pipeline_name = "pipeline" if "pipeline" in arm_names else arm_names[-1]
    verdict = t2_verdict(
        summaries[baseline_name]["accuracy"], summaries[pipeline_name]["accuracy"]
    ) if len(arm_names) >= 2 else {"status": "NOT_EVALUATED", "note": "need two arms"}
    retention = (
        quantum_retention(scores, baseline_name, pipeline_name)
        if len(arm_names) >= 2
        else {"status": "NOT_EVALUATED", "note": "need two arms"}
    )

    t3_verdict: dict[str, Any] | None = None
    if t3:
        # T3 requires per-item confidence scores populated via extract_all.
        # If no item carries confidence data, the verdict is NOT_MEASURED.
        has_conf = any(s.confidence_by_definition for s in scores)
        if has_conf:
            from benchmarks.calibration.evaluate import run_t3_evaluation
            from benchmarks.calibration.features import EXTRACTORS

            def_names = list(EXTRACTORS.keys())
            scores_by_def: dict[str, list[float]] = {d: [] for d in def_names}
            labels: list[int] = []
            for s in scores:
                labels.append(
                    1 if any(a.get("correct") for a in s.arms.values()) else 0
                )
                for d in def_names:
                    scores_by_def[d].append(s.confidence_by_definition.get(d, 0.0))

            n = len(labels)
            # Use first half as dev, second half as heldout (interleaved for balance)
            dev_idx = list(range(0, n, 2))
            heldout_idx = list(range(1, n, 2))
            if dev_idx and heldout_idx:
                tv = run_t3_evaluation(
                    scores_by_def, labels,
                    dev_indices=dev_idx, heldout_indices=heldout_idx,
                )
                t3_verdict = tv.to_dict()
            else:
                t3_verdict = {"status": "NOT_MEASURED", "note": "insufficient items for dev/heldout split"}
        else:
            t3_verdict = {"status": "NOT_MEASURED", "note": "no confidence_by_definition data on any item"}

    return {
        "run_id": run_id,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "split": split,
        "n_items": len(items),
        "hang_ceiling_s": ceiling_s,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "latency_note": (
            "D-8 (29/09/2026): hang ceiling only. These latency figures are "
            "measurements from this run; the T11 budget is fixed from them and "
            "is UNMEASURED until that decision is made."
        ),
        "backend": backend_identity or {},
        "arms": summaries,
        "arm_order": arm_names,
        "t2_verdict": verdict,
        "quantum_retention": retention,
        "t3_verdict": t3_verdict,
        "per_item": [asdict(s) for s in scores],
    }


def write_receipt(payload: dict[str, Any], out_dir: Path = EVIDENCE_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{payload['run_id']}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Live wiring
# ---------------------------------------------------------------------------


def build_live_arms(arms_spec: str) -> list[ArmRunner]:
    """Construct the requested arms against the configured backend.

    Arms build their own ``LLMClient`` per call (see :func:`fresh_client`); no
    client is shared across event loops.
    """
    wanted = [a.strip() for a in arms_spec.split(",") if a.strip()]
    known = {"baseline", "pipeline", "pipeline_decoder"}
    unknown = sorted(set(wanted) - known)
    if unknown:
        raise ValueError(f"unknown arm(s): {unknown}; known: {sorted(known)}")

    model_id = _backend().model_id
    built: list[ArmRunner] = []
    loop = None

    if {"pipeline", "pipeline_decoder"} & set(wanted):
        from integration.vivy_inference_loop import VivyInferenceLoop

        loop = VivyInferenceLoop.from_env()

    for name in wanted:
        if name == "baseline":
            built.append(PlainModelArm(model=model_id))
        elif name == "pipeline":
            built.append(PipelineArm(loop))
        else:
            built.append(PipelineDecoderArm(loop))
    return built


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "heldout"], default="dev")
    parser.add_argument("--heldout", default=None,
                        help="path to the owner-supplied held-out .jsonl (D-7)")
    parser.add_argument("--arms", default="baseline",
                        help="comma list of: baseline, pipeline, pipeline_decoder")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--receipt-dir", default=str(EVIDENCE_DIR))
    parser.add_argument("--limit", type=int, default=0,
                        help="score only the first N items (smoke runs)")
    parser.add_argument("--ceiling", type=float, default=HANG_CEILING_S)
    parser.add_argument("--t3", action="store_true", default=False,
                        help="run O-05/T3 confidence calibration evaluation")
    args = parser.parse_args(argv)

    try:
        if args.split == "heldout":
            items = load_heldout_items(args.heldout)
        else:
            items = load_dev_items()
    except HeldOutError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    if args.limit and args.limit > 0:
        items = items[: args.limit]

    try:
        arms = build_live_arms(args.arms)
    except Exception as exc:  # noqa: BLE001
        print(f"REFUSED: cannot build arms: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    from llm_bridge.backend import LLMBackend

    run_id = args.run_id or (
        "T2-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    payload = run_eval(
        items,
        arms,
        run_id=run_id,
        backend_identity=LLMBackend.from_env().identity(),
        split=args.split,
        ceiling_s=args.ceiling,
        t3=args.t3,
    )
    receipt = write_receipt(payload, Path(args.receipt_dir))

    print(f"run_id      {run_id}")
    print(f"split       {args.split}  n={payload['n_items']}")
    print(f"backend     {payload['backend'].get('backend_id')}"
          f"/{payload['backend'].get('model_alias')}")
    for name in payload["arm_order"]:
        s = payload["arms"][name]
        print(f"  {name:18s} acc={s['accuracy']:.4f}  "
              f"({s['n_correct']}/{s['n_items']})  "
              f"med_latency={s['median_latency_ms']:.0f}ms  "
              f"errors={s['n_errors']}  "
              f"ceiling_hits={s.get('n_ceiling_hits', 0)}")
        if s.get("n_ceiling_hits"):
            print(f"  {'':18s} uncensored acc={s['accuracy_uncensored']:.4f}  "
                  f"({s['n_correct_uncensored']}/{s['n_uncensored']})")
    v = payload["t2_verdict"]
    print(f"T2 verdict  {v.get('status')}  {v.get('note', '')}")
    t3v = payload.get("t3_verdict")
    if t3v is not None:
        print(f"T3 verdict  {t3v.get('status', '?')}  selected={t3v.get('selected', '?')}")
    q = payload["quantum_retention"]
    if q.get("status") not in (None, "NOT_EVALUATED"):
        print(f"quantum     {q['status']}  Δ{q.get('delta_pp', 0):+.2f}pp  "
              f"p={q.get('mcnemar_p')}")
    print(f"receipt     {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
