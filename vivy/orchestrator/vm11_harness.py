"""VM-11 Error-Dampening Measurement Harness.

Measures repeated-error-rate over N consecutive tasks against the
CognitiveStateGraph dampener and emits a receipt.

VM-11 (VMEM): Pass ≤10% repeat, Excellence ≤2% on 100 consecutive tasks.

Repeat error definition (binding):
    A trial is a repeat error when the selector chooses an action whose
    graph node already has falsified_count > 0 at selection time AND the
    action fails again on that trial. That is a blind repeat of a known error.

Protocol (deterministic, seeded):
    - A fixed action set; each action has a failure probability.
    - The selector temperature-samples over confidence * dampen_factor
      (dampener ON) or over confidence alone (baseline, dampener OFF).
    - On failure, add_edge_falsified() increments falsified_count so the
      next selection sees the dampened weight.
    - All tasks share one CognitiveStateGraph (dampening persists).

Gate 9: receipts are labelled SIMULATED_PROTOCOL. This measures the dampener
mechanism on a synthetic action loop — it is NOT a live-model accuracy claim
and NOT a production repeat-rate claim.

Changelog:
    23/09/2026 (Claude Code — P2 VM-11 Measurement Harness): Initial.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from memory.cognitive_graph import CognitiveStateGraph, NodeType

# VMEM VM-11 thresholds (BO_TIEU_CHI_DANH_GIA_VA_PHAN_BIEN_VIVY.md)
VM11_PASS_THRESHOLD = 0.10
VM11_EXCELLENCE_THRESHOLD = 0.02

# Default synthetic action set: one trap (always fails) + two safe actions.
DEFAULT_ACTIONS: tuple[str, ...] = ("trade_buy", "retry_backoff", "read_depth")
DEFAULT_FAIL_PROBS: dict[str, float] = {
    "trade_buy": 1.0,
    "retry_backoff": 0.0,
    "read_depth": 0.0,
}


@dataclass
class TrialRecord:
    """One consecutive task in the measurement."""

    task_id: int
    chosen: str
    previously_falsified: bool
    failed: bool
    repeat_error: bool
    dampen_factor_at_selection: float


@dataclass
class VM11Receipt:
    """Receipt for a VM-11 measurement run."""

    n_tasks: int
    n_repeat_errors: int
    repeat_rate: float
    pass_threshold: float
    excellence_threshold: float
    verdict: str
    seed: int
    protocol: str
    generated_at: str
    status_label: str
    use_dampener: bool
    temperature: float
    baseline_repeat_rate: float | None = None
    trials: list[TrialRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _verdict_for(rate: float) -> str:
    if rate <= VM11_EXCELLENCE_THRESHOLD:
        return "EXCELLENCE"
    if rate <= VM11_PASS_THRESHOLD:
        return "PASS"
    return "FAIL"


class VM11Harness:
    """Seeded measurement loop over CognitiveStateGraph dampening.

    Parameters
    ----------
    actions:
        Candidate action node IDs. Each is registered as a HYPOTHESIS.
    fail_probs:
        action_id → probability of failure on each selection (0..1).
    seed:
        RNG seed for reproducible receipts.
    temperature:
        Selection temperature. Lower → more greedy over dampened weights.
    use_dampener:
        True  → score = confidence * dampen_factor (Error-Dampening active).
        False → score = confidence (baseline; falsifications still recorded
                for repeat-error accounting, but do not affect selection).
    """

    def __init__(
        self,
        actions: tuple[str, ...] | list[str] = DEFAULT_ACTIONS,
        fail_probs: dict[str, float] | None = None,
        seed: int = 42,
        temperature: float = 0.5,
        use_dampener: bool = True,
    ) -> None:
        self.actions = list(actions)
        self.fail_probs = dict(fail_probs or DEFAULT_FAIL_PROBS)
        self.seed = seed
        self.temperature = max(0.05, float(temperature))
        self.use_dampener = bool(use_dampener)
        self.graph = CognitiveStateGraph()
        self._rng = random.Random(seed)
        for action in self.actions:
            self.graph.add_node(
                action,
                NodeType.HYPOTHESIS,
                content=action,
                confidence=1.0,
            )

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _selection_weights(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        for action in self.actions:
            node = self.graph.get_node(action)
            if node is None:
                continue
            if self.use_dampener:
                weights[action] = max(1e-6, node.confidence * node.dampen_factor())
            else:
                weights[action] = max(1e-6, node.confidence)
        return weights

    def _sample_action(self) -> tuple[str, float]:
        """Temperature-sample one action. Returns (action_id, dampen_factor)."""
        weights = self._selection_weights()
        if not weights:
            raise RuntimeError("VM11Harness: no selectable actions")
        # p ∝ w^(1/T)
        inv_t = 1.0 / self.temperature
        scores = {a: (w ** inv_t) for a, w in weights.items()}
        total = sum(scores.values())
        roll = self._rng.random() * total
        acc = 0.0
        chosen = self.actions[-1]
        for action, score in scores.items():
            acc += score
            if roll <= acc:
                chosen = action
                break
        node = self.graph.get_node(chosen)
        factor = node.dampen_factor() if node is not None else 1.0
        return chosen, factor

    # ------------------------------------------------------------------
    # Measurement loop
    # ------------------------------------------------------------------

    def run(self, n_tasks: int = 100) -> VM11Receipt:
        """Run n_tasks consecutive trials and build the receipt."""
        if n_tasks <= 0:
            raise ValueError("n_tasks must be positive")

        trials: list[TrialRecord] = []
        n_repeat = 0

        for task_id in range(1, n_tasks + 1):
            chosen, factor = self._sample_action()
            node = self.graph.get_node(chosen)
            previously_falsified = bool(node is not None and node.is_dampened())

            fail_p = self.fail_probs.get(chosen, 0.0)
            failed = self._rng.random() < fail_p

            if failed:
                self.graph.add_edge_falsified(chosen, f"rca_{chosen}", weight=1.0)

            repeat_error = previously_falsified and failed
            if repeat_error:
                n_repeat += 1

            trials.append(
                TrialRecord(
                    task_id=task_id,
                    chosen=chosen,
                    previously_falsified=previously_falsified,
                    failed=failed,
                    repeat_error=repeat_error,
                    dampen_factor_at_selection=factor,
                )
            )

        rate = n_repeat / n_tasks
        return VM11Receipt(
            n_tasks=n_tasks,
            n_repeat_errors=n_repeat,
            repeat_rate=rate,
            pass_threshold=VM11_PASS_THRESHOLD,
            excellence_threshold=VM11_EXCELLENCE_THRESHOLD,
            verdict=_verdict_for(rate),
            seed=self.seed,
            protocol=self._protocol_label(),
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            status_label="SIMULATED_PROTOCOL",
            use_dampener=self.use_dampener,
            temperature=self.temperature,
            trials=trials,
        )

    def _protocol_label(self) -> str:
        mode = "dampener" if self.use_dampener else "baseline (no dampener)"
        return (
            f"CognitiveStateGraph Error-Dampening VM-11 simulated action loop "
            f"[{mode}; temperature={self.temperature}; actions={len(self.actions)}]"
        )


def run_measurement(
    n_tasks: int = 100,
    seed: int = 42,
    use_dampener: bool = True,
    temperature: float = 0.5,
    actions: tuple[str, ...] | list[str] = DEFAULT_ACTIONS,
    fail_probs: dict[str, float] | None = None,
    with_baseline: bool = True,
) -> VM11Receipt:
    """Run a VM-11 measurement and optionally attach the undampened baseline.

    When use_dampener=True and with_baseline=True, the receipt carries
    baseline_repeat_rate from a same-seed undampened run so the dampener's
    effect is visible in a single artifact.
    """
    harness = VM11Harness(
        actions=actions,
        fail_probs=fail_probs,
        seed=seed,
        temperature=temperature,
        use_dampener=use_dampener,
    )
    receipt = harness.run(n_tasks=n_tasks)

    if use_dampener and with_baseline:
        baseline = VM11Harness(
            actions=actions,
            fail_probs=fail_probs,
            seed=seed,
            temperature=temperature,
            use_dampener=False,
        ).run(n_tasks=n_tasks)
        receipt.baseline_repeat_rate = baseline.repeat_rate

    return receipt


def write_receipt(receipt: VM11Receipt, path: str) -> str:
    """Write receipt JSON to path. Returns the path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(receipt.to_json())
        f.write("\n")
    return path


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="VM-11 Error-Dampening measurement harness")
    parser.add_argument("--n-tasks", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.5)
    parser.add_argument("--no-dampener", action="store_true", help="Baseline run (no dampening)")
    parser.add_argument("--output", default="", help="Write receipt JSON to this path")
    args = parser.parse_args()

    receipt = run_measurement(
        n_tasks=args.n_tasks,
        seed=args.seed,
        use_dampener=not args.no_dampener,
        temperature=args.temperature,
    )
    print(receipt.to_json())
    print(
        f"\nVM-11 verdict={receipt.verdict} repeat_rate={receipt.repeat_rate:.4f} "
        f"(Pass ≤{receipt.pass_threshold:.0%}, Excellence ≤{receipt.excellence_threshold:.0%})"
    )
    if receipt.baseline_repeat_rate is not None:
        print(f"baseline_repeat_rate={receipt.baseline_repeat_rate:.4f}")
    print(f"status_label={receipt.status_label}")
    if args.output:
        write_receipt(receipt, args.output)
        print(f"receipt → {args.output}")
    return 0 if receipt.verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
