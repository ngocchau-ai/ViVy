"""Live auto-reroute evidence for MindmapPlanner against a real model backend.

Runs the diamond DAG (A -> B -> D, A -> C -> E) through
:class:`training.mindmap_planner.MindmapPlanner` with an executor that makes
real HTTP calls to llama-server and scores each live output against a
pre-declared contract. Two arms:

  clean    control — every node contract is a trivial arithmetic fact, so the
           path is expected to complete without a reroute.
  reroute  treatment — node C carries a real capability gap (exact 6-digit x
           6-digit product). The model's own output decides; a contract miss
           drops C and the planner re-plans to A -> B -> D.

Every node request is a real POST to ``/v1/chat/completions`` through
:func:`training.backend_registry.make_llama_server_fn`, which never falls back
to another model. Each call records ``prompt_sha256``, ``output_sha256``,
``latency_ms`` and the raw output length.

Executor semantics (the two signals the planner consumes are kept separate):
  * ``ok``    — transport completed and produced text (no backend error).
  * ``score`` — contract satisfaction in [0, 1], from the live output text.

So a node whose call succeeds but whose answer is wrong reaches the planner as
``ok=True, score=0.0`` and is rerouted on the *below-threshold* path, while a
node whose call itself fails is rerouted on the *executor reported failure*
path. Both paths are real; neither is injected by this harness.

What this measures: the planner's plan -> execute -> auto-reroute path under
live inference, end to end through real HTTP.
What this does NOT measure: model quality, production accuracy, native CAUTREO
semantic parity, or any latency SLA. Auto-reroute here is observed against one
local backend at one decoding config.

Structure:
    Contract          — pre-declared acceptance rule for one node's live output
    score_output()    — deterministic, side-effect free scoring
    LiveExecutor      — Executor that calls the backend and records every call
    run_arm()         — build + run one arm, return its evidence block
    build_receipt()   — assemble the multi-arm evidence receipt
    main()            — CLI

Exit codes:
    0  receipt written, reroute observed under live inference, control clean
    2  run completed but an expected observation is missing (honest FAIL)
    3  infra: backend unreachable / timeout / wrong_alias
    4  usage or receipt write-guard error

Changelog:
    25/09/2026 (Claude Code — TD-6 live evidence): Initial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any

from training.backend_baseline import BackendError, BackendIdentity
from training.backend_registry import (
    DEFAULT_DECODING,
    config_hash,
    make_llama_server_fn,
    probe_health,
    prompt_sha256,
)
from training.cross_model_adapter import CrossModelAdapter, RouteResult
from training.io_guard import open_write
from training.mindmap_planner import MindmapPlanner, SubtaskSpec

# --- Contracts ---------------------------------------------------------------

# check kinds: "exact" | "contains" | "contains_all" | "numeric"
EXPECTED_TYPES = str | float | tuple[str, ...]


@dataclass(frozen=True)
class Contract:
    """Pre-declared acceptance rule for one node's live output.

    The rule is fixed before the run and travels with the receipt, so a reader
    can re-score any recorded output without trusting this harness.
    """

    node_id: str
    prompt: str
    check: str
    expected: EXPECTED_TYPES
    tolerance: float = 0.0
    description: str = ""

    def __post_init__(self) -> None:
        if self.check not in ("exact", "contains", "contains_all", "numeric"):
            raise ValueError(f"unknown contract check: {self.check!r}")
        if self.check == "numeric" and not isinstance(self.expected, (int, float)):
            raise TypeError(
                f"numeric contract expects a number, got {self.expected!r}"
            )
        if self.check == "contains_all" and not isinstance(self.expected, tuple):
            raise TypeError(
                f"contains_all contract expects a tuple of strings, got {self.expected!r}"
            )
        if self.check in ("exact", "contains") and not isinstance(self.expected, str):
            raise TypeError(
                f"{self.check} contract expects a string, got {self.expected!r}"
            )
        if self.tolerance < 0:
            raise ValueError(f"tolerance must be >= 0, got {self.tolerance}")


_NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def all_floats(text: str) -> list[float]:
    """Every number in *text*, in order, tolerating thousands separators."""
    out: list[float] = []
    for match in _NUMBER_RE.finditer(text or ""):
        try:
            out.append(float(match.group(0).replace(",", "")))
        except ValueError:  # pragma: no cover — regex constrains the shape
            continue
    return out


def answer_number(text: str) -> float | None:
    """The model's final numeric answer: the LAST number in its reply.

    A derivation such as ``"6 * 3 = 18"`` puts the operands first and the
    answer last, so the last number is the answer. Recorded in the receipt so
    a reader can re-score the raw output without trusting this rule.
    """
    values = all_floats(text)
    return values[-1] if values else None


def score_output(contract: Contract, text: str) -> tuple[float, bool]:
    """Score a live output against its pre-declared contract.

    Returns ``(score, satisfied)`` with ``score`` in [0, 1]. Deterministic and
    side-effect free — the same text and contract always give the same answer.
    """
    body = (text or "").strip()
    if not body:
        return 0.0, False

    if contract.check == "exact":
        hit = body == str(contract.expected).strip()
        return (1.0 if hit else 0.0), hit

    if contract.check == "contains":
        hit = str(contract.expected).lower() in body.lower()
        return (1.0 if hit else 0.0), hit

    if contract.check == "numeric":
        value = answer_number(body)
        if value is None:
            return 0.0, False
        if not isinstance(contract.expected, (int, float)):
            raise TypeError(f"numeric contract holds non-number: {contract.expected!r}")
        hit = abs(value - float(contract.expected)) <= contract.tolerance
        return (1.0 if hit else 0.0), hit

    # contains_all — graded: score is the fraction of required substrings found.
    if not isinstance(contract.expected, tuple):
        raise TypeError(f"contains_all contract holds non-tuple: {contract.expected!r}")
    terms = tuple(str(t) for t in contract.expected)
    if not terms:
        return 0.0, False
    matched = sum(1 for t in terms if t.lower() in body.lower())
    return matched / len(terms), matched == len(terms)


def expected_repr(contract: Contract) -> Any:
    """JSON-safe view of the contract's ground truth, for the receipt."""
    if isinstance(contract.expected, tuple):
        return list(contract.expected)
    return contract.expected


# --- Live executor -----------------------------------------------------------


class LiveExecutor:
    """Executor that calls a real backend and records every call.

    ``ok`` is transport success (the call returned text); ``score`` is contract
    satisfaction from that text. Keeping them apart lets the planner reroute on
    a quality miss without pretending the HTTP call failed.
    """

    def __init__(
        self,
        fn: Callable[[str, int], str],
        contracts: Mapping[str, Contract],
        *,
        max_tokens: int = 64,
    ) -> None:
        self._fn = fn
        self._contracts = dict(contracts)
        self._max_tokens = max_tokens
        self.calls: list[dict[str, Any]] = []

    def __call__(self, node_id: str, route: RouteResult) -> tuple[str, float, bool]:
        contract = self._contracts.get(node_id)
        if contract is None:
            self.calls.append({
                "node_id": node_id,
                "check": "",
                "expected": None,
                "prompt_sha256": "",
                "output_sha256": "",
                "output_chars": 0,
                "latency_ms": None,
                "score": 0.0,
                "ok": False,
                "contract_satisfied": False,
                "error": f"no contract registered for node {node_id!r}",
                "route_alias": getattr(route, "model_alias", ""),
                "load_action": (
                    route.load_decision.action if route.load_decision else ""
                ),
            })
            return "", 0.0, False

        started = time.perf_counter()
        text = ""
        error = ""
        try:
            text = self._fn(contract.prompt, self._max_tokens)
        except BackendError as exc:
            error = f"{exc.kind}: {exc.detail}"
        except Exception as exc:  # noqa: BLE001 — a transport fault must not abort the run
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = (time.perf_counter() - started) * 1000.0

        if error:
            score, satisfied = 0.0, False
            ok = False
        else:
            score, satisfied = score_output(contract, text)
            ok = bool(text.strip())

        self.calls.append({
            "node_id": node_id,
            "check": contract.check,
            "expected": expected_repr(contract),
            "contract_description": contract.description,
            "prompt_sha256": prompt_sha256(contract.prompt),
            "output_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "output_chars": len(text),
            "output_text": text[:400],
            "answer_number": answer_number(text) if contract.check == "numeric" else None,
            "latency_ms": round(latency_ms, 3),
            "score": round(score, 4),
            "ok": ok,
            "contract_satisfied": satisfied,
            "error": error,
            "route_alias": getattr(route, "model_alias", ""),
            "load_action": (
                route.load_decision.action if route.load_decision else ""
            ),
        })
        return text, score, ok


# --- Arms --------------------------------------------------------------------


# Plan-time prior scores: they steer dag.plan() toward A -> C -> E so that C is
# executed first and a C miss forces a visible re-plan. They are NOT the live
# scores — those come from the model through the contract checker.
PLAN_PRIOR_SCORES: dict[str, float] = {
    "A": 0.9, "B": 0.4, "C": 0.8, "D": 0.5, "E": 0.7,
}
_PARENTS: dict[str, str] = {"B": "A", "C": "A", "D": "B", "E": "C"}


def make_specs() -> list[SubtaskSpec]:
    """Diamond DAG: A -> B -> D and A -> C -> E, with C preferred at plan time."""
    return [
        SubtaskSpec(node_id=n, input_context="live-reroute", strategy=n,
                    score=PLAN_PRIOR_SCORES[n], parent=_PARENTS.get(n))
        for n in ("A", "B", "C", "D", "E")
    ]


# Ground truth for the treatment arm's capability gap, computed at runtime so
# the receipt cannot carry a hand-typed product.
GAP_A = 123456
GAP_B = 789012
GAP_PRODUCT = GAP_A * GAP_B


def clean_contracts() -> dict[str, Contract]:
    """Control arm: trivial arithmetic every model should satisfy."""
    return {
        "A": Contract("A", "What is 3 + 4? Reply with just the number.",
                      "numeric", 7.0, description="trivial addition"),
        "B": Contract("B", "What is 10 - 2? Reply with just the number.",
                      "numeric", 8.0, description="trivial subtraction"),
        "C": Contract("C", "What is 6 * 3? Reply with just the number.",
                      "numeric", 18.0, description="trivial multiplication"),
        "D": Contract("D", "What is 9 / 3? Reply with just the number.",
                      "numeric", 3.0, description="trivial division"),
        "E": Contract("E", "What is 5 + 5? Reply with just the number.",
                      "numeric", 10.0, description="trivial addition"),
    }


def reroute_contracts() -> dict[str, Contract]:
    """Treatment arm: node C carries a real, verifiable capability gap.

    The ground truth is the exact integer product, so any reader can check the
    miss with a calculator — no trust in this harness required.
    """
    contracts = clean_contracts()
    contracts["C"] = Contract(
        "C",
        f"What is {GAP_A} * {GAP_B}? Reply with just the digits of the product.",
        "numeric",
        float(GAP_PRODUCT),
        description=(
            "exact 6-digit x 6-digit product; beyond this local model's "
            "reliable arithmetic — a miss is a real capability gap, not a "
            "rigged sentinel"
        ),
    )
    return contracts


ARM_BUILDERS: dict[str, Callable[[], dict[str, Contract]]] = {
    "clean": clean_contracts,
    "reroute": reroute_contracts,
}


# --- One arm -----------------------------------------------------------------


def run_arm(
    arm: str,
    fn: Callable[[str, int], str],
    *,
    model_alias: str,
    max_tokens: int = 64,
    score_threshold: float = 0.3,
    max_reroutes: int = 3,
) -> dict[str, Any]:
    """Build and run one arm, returning its evidence block.

    The executor here is a :class:`LiveExecutor`, so every node trace in the
    returned block corresponds to one real backend call.
    """
    if arm not in ARM_BUILDERS:
        raise ValueError(f"unknown arm: {arm!r}")
    contracts = ARM_BUILDERS[arm]()

    adapter = CrossModelAdapter()
    adapter.set_fallback(model_alias)
    planner = MindmapPlanner(
        adapter, score_threshold=score_threshold, max_reroutes=max_reroutes,
    )
    planner.build(make_specs())

    executor = LiveExecutor(fn, contracts, max_tokens=max_tokens)
    # Snapshot the plan-time preference BEFORE run(): run() overwrites node
    # scores from live output and re-plans, which would erase what the prior
    # scores actually chose.
    preferred = planner.dag.plan("live-reroute") if planner.dag else None
    preferred_before = list(preferred.node_ids) if preferred else []

    receipt = planner.run("live-reroute", executor)

    return {
        "arm": arm,
        "intent": (
            "control — every node contract is a trivial arithmetic fact; "
            "expect completed with zero reroutes"
            if arm == "clean"
            else "treatment — node C carries a real capability gap "
                 f"({GAP_A} * {GAP_B} = {GAP_PRODUCT}); the model's own "
                 "output decides whether a reroute happens"
        ),
        "contracts": {
            nid: {
                "check": c.check,
                "expected": expected_repr(c),
                "tolerance": c.tolerance,
                "prompt_sha256": prompt_sha256(c.prompt),
                "description": c.description,
            }
            for nid, c in contracts.items()
        },
        "plan_prior_scores": dict(PLAN_PRIOR_SCORES),
        "answer_rule": (
            "numeric contracts score the LAST number in the model reply "
            "(a derivation ends with its answer); the raw reply is stored per "
            "node as output_text so this rule can be re-checked"
        ),
        "preferred_path": preferred_before,
        "path": list(receipt.path),
        "completed": receipt.completed,
        "reroute_count": len(receipt.reroutes),
        "reroutes": [r.to_dict() for r in receipt.reroutes],
        "final_score": round(receipt.final_score, 4),
        "conclusion_sha256": hashlib.sha256(
            receipt.conclusion.encode("utf-8")
        ).hexdigest(),
        "conclusion_chars": len(receipt.conclusion),
        "node_calls": executor.calls,
        "node_call_count": len(executor.calls),
        "reroute_observed": len(receipt.reroutes) > 0,
    }


# --- Receipt assembly --------------------------------------------------------


def _latency_stats(calls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = sorted(
        float(c["latency_ms"]) for c in calls
        if c.get("latency_ms") is not None
    )
    if not values:
        return {"n": 0, "unit": "ms"}
    p95_index = min(len(values) - 1, round(0.95 * (len(values) - 1)))
    return {
        "n": len(values),
        "unit": "ms",
        "min": round(values[0], 3),
        "median": round(float(median(values)), 3),
        "p95": round(values[p95_index], 3),
        "max": round(values[-1], 3),
    }


def build_receipt(
    arms: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
    health: Mapping[str, Any],
    backend: BackendIdentity,
) -> dict[str, Any]:
    """Assemble the multi-arm evidence receipt and score its gates.

    Gates are scored against what was actually observed. A missing observation
    is a FAIL, never a silent PASS.
    """
    all_calls = [c for arm in arms for c in arm.get("node_calls", [])]
    reachable = health.get("reachable") is True

    live_tagged = bool(all_calls) and all(
        c.get("prompt_sha256") and c.get("latency_ms") is not None for c in all_calls
    )
    no_silent_fallback = all(
        not str(c.get("error", "")).startswith(("wrong_alias", "unavailable"))
        for c in all_calls
    ) and all(
        c.get("route_alias") in ("", backend.model_alias) for c in all_calls
    )

    control = next((a for a in arms if a.get("arm") == "clean"), None)
    treatment = next((a for a in arms if a.get("arm") == "reroute"), None)

    control_clean = (
        control is not None and control["completed"] and control["reroute_count"] == 0
    )
    reroute_observed = (
        treatment is not None
        and treatment["reroute_observed"]
        and treatment["completed"]
    )

    # Ground truth for the treatment node must be in the receipt, or the miss
    # cannot be re-checked by a reader.
    gap_disclosed = False
    if treatment:
        node_c = treatment.get("contracts", {}).get("C", {})
        gap_disclosed = node_c.get("expected") == float(GAP_PRODUCT)

    gates = {
        "backend_reachable": "PASS" if reachable else "FAIL",
        "every_node_call_is_live": "PASS" if live_tagged else "FAIL",
        "control_arm_clean": "PASS" if control_clean else "FAIL",
        "reroute_observed_under_live_inference": "PASS" if reroute_observed else "FAIL",
        "no_silent_fallback": "PASS" if no_silent_fallback else "FAIL",
        "contract_ground_truth_disclosed": "PASS" if gap_disclosed else "FAIL",
    }

    return {
        "receipt_type": "SCORED_MINDMAP_REROUTE_LIVE",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "backend": backend.to_dict(),
        "health": dict(health),
        "decoding": dict(DEFAULT_DECODING) | {"max_tokens": 64},
        "config_hash": config_hash({"max_tokens": 64}),
        "arms": list(arms),
        "measurements": {
            "live_calls_total": len(all_calls),
            "latency_ms": _latency_stats(all_calls),
            "nodes_executed_per_arm": {
                a["arm"]: a["node_call_count"] for a in arms
            },
            "reroutes_per_arm": {a["arm"]: a["reroute_count"] for a in arms},
        },
        "gates": gates,
        "promotion": "PROMOTED" if gates and all(v == "PASS" for v in gates.values()) else "BLOCKED",
        "gate9_disclaimer": (
            "All numbers here are MEASURED from real calls to one local "
            "backend at one decoding config. No 0% error, no 0ms latency, no "
            "PRODUCTION-READY claim is made. Auto-reroute is observed under "
            "live inference; it is not a model-quality measurement."
        ),
        "scope_limit": (
            "Measures the MindmapPlanner plan -> execute -> auto-reroute path "
            "against llama-server :8080 only. Does not establish production "
            "accuracy, decision quality, or native CAUTREO semantic parity "
            "(2.1). The treatment arm's node C failure is a real capability "
            "gap on one arithmetic contract, not a general failure rate."
        ),
    }


# --- CLI ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--arms", default="clean,reroute",
                        help="comma-separated arm names (clean,reroute)")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model-alias", default=None)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--allow-replace", action="store_true")
    args = parser.parse_args(argv)

    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arm_names if a not in ARM_BUILDERS]
    if unknown:
        print(f"unknown arms: {unknown}", file=sys.stderr)
        return 4

    model_alias = args.model_alias or "gemma4-e4b"
    health = probe_health("llama-server", timeout_s=min(5.0, args.timeout_s))
    if health.get("reachable") is not True:
        print(f"backend unreachable: {health.get('detail')}", file=sys.stderr)
        return 3

    fn = make_llama_server_fn(
        base_url=args.base_url,
        model_alias=model_alias,
        timeout_s=args.timeout_s,
        temperature=float(DEFAULT_DECODING["temperature"]),
        top_p=float(DEFAULT_DECODING["top_p"]),
    )
    backend = BackendIdentity(
        backend_id="llama-server",
        model_alias=model_alias,
        model_hash="",
        config_hash=config_hash({"max_tokens": args.max_tokens}),
        base_url=args.base_url or "http://127.0.0.1:8080",
        extra={"health": dict(health), "harness": "training/run_reroute_live.py"},
    )

    arms: list[dict[str, Any]] = []
    infra_failure = False
    for arm in arm_names:
        block = run_arm(
            arm, fn, model_alias=model_alias, max_tokens=args.max_tokens,
        )
        arms.append(block)
        if all(c.get("error", "").startswith(("timeout", "unavailable", "wrong_alias"))
               for c in block["node_calls"]) and block["node_calls"]:
            infra_failure = True

    receipt = build_receipt(
        arms, run_id=args.run_id, health=health, backend=backend,
    )

    try:
        with open_write(args.output, allow_replace=args.allow_replace) as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    except Exception as exc:  # noqa: BLE001 — write-guard failure = exit 4
        print(f"receipt write error: {exc}", file=sys.stderr)
        return 4

    print(json.dumps({
        "output": str(args.output),
        "promotion": receipt["promotion"],
        "gates": receipt["gates"],
        "measurements": receipt["measurements"],
    }, ensure_ascii=False, indent=2))

    if infra_failure:
        return 3
    return 0 if receipt["promotion"] == "PROMOTED" else 2


if __name__ == "__main__":
    sys.exit(main())
