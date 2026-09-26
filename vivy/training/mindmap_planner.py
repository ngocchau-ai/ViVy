"""Mindmap Planner — plan-before-generate with auto-reroute (TD-6 integration).

Wires :class:`training.scored_mindmap_dag.MindmapDAG` into the model-routing
flow so ViVy plans the decision structure BEFORE generation, executes each
subtask through :class:`training.cross_model_adapter.CrossModelAdapter`, and
re-routes automatically when a subtask fails or scores below threshold.

Division of labour (composition, not replacement):
  * ``MindmapDAG``  — WHICH path: score-greedy root→leaf planning + reroute.
  * ``CrossModelAdapter`` — WHICH model: routing + adaptive weight load plan.
  * ``MindmapPlanner`` — WHEN to replan: drives both, records the trace.

The executor is injected, so the reroute behaviour is verifiable without a
live model backend. That is a unit-level proof of the reroute mechanism, not
a live-model measurement.

Structure:
    SubtaskSpec            — one planned node (strategy + model_target + score)
    RerouteEvent           — a failed node that triggered a re-plan
    PlannerReceipt         — path taken, node traces, reroutes, conclusion
    MindmapPlanner
    ├── build(specs) -> MindmapDAG          — construct the plan graph
    ├── run(input_context, executor) -> PlannerReceipt
    └── dag / adapter properties

Changelog:
    25/09/2026 (Claude Code — TD-6 integration): Initial.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from training.cross_model_adapter import CrossModelAdapter, RouteResult
from training.scored_mindmap_dag import DecisionNode, MindmapDAG

# executor(node_id, route_result) -> (output_text, score, ok)
Executor = Callable[[str, RouteResult], tuple[str, float, bool]]


@dataclass
class SubtaskSpec:
    """One planned subtask node."""

    node_id: str
    input_context: str = ""
    strategy: str = ""
    model_target: str = ""
    score: float = 0.5
    parent: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")


@dataclass(frozen=True)
class RerouteEvent:
    """A node failure that caused the planner to pick a different path."""

    node_id: str
    failed_score: float
    new_path: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "failed_score": round(self.failed_score, 4),
            "new_path": list(self.new_path),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PlannerReceipt:
    """Outcome of one ``run()`` — the evidence that reroute did (or did not) happen."""

    path: tuple[str, ...]
    node_records: tuple[dict[str, Any], ...]
    reroutes: tuple[RerouteEvent, ...]
    final_score: float
    conclusion: str
    completed: bool
    outputs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": list(self.path),
            "node_records": list(self.node_records),
            "reroutes": [r.to_dict() for r in self.reroutes],
            "final_score": round(self.final_score, 4),
            "conclusion": self.conclusion,
            "completed": self.completed,
            "outputs": dict(self.outputs),
        }


class MindmapPlanner:
    """Plans a scored path, runs it through the adapter, reroutes on failure.

    ``build()`` turns specs into a :class:`MindmapDAG`. ``run()`` plans the
    best path, hands each node to the adapter for model routing + adaptive
    load, then to the caller's executor. A node that fails or scores under
    ``score_threshold`` drops its score and the DAG re-plans to an
    alternative branch.
    """

    def __init__(
        self,
        adapter: CrossModelAdapter | None = None,
        *,
        score_threshold: float = 0.3,
        max_reroutes: int = 3,
    ) -> None:
        if not 0.0 <= score_threshold <= 1.0:
            raise ValueError(f"score_threshold must be in [0, 1], got {score_threshold}")
        if max_reroutes < 0:
            raise ValueError(f"max_reroutes must be >= 0, got {max_reroutes}")
        self._adapter = adapter if adapter is not None else CrossModelAdapter()
        self._score_threshold = score_threshold
        self._max_reroutes = max_reroutes
        self._dag: MindmapDAG | None = None

    # --- properties ---

    @property
    def dag(self) -> MindmapDAG | None:
        return self._dag

    @property
    def adapter(self) -> CrossModelAdapter:
        return self._adapter

    @property
    def score_threshold(self) -> float:
        return self._score_threshold

    @property
    def max_reroutes(self) -> int:
        return self._max_reroutes

    # --- construction ---

    def build(self, specs: Sequence[SubtaskSpec]) -> MindmapDAG:
        """Build the plan DAG from subtask specs (parent → child edges).

        Raises ValueError on duplicate node_id, KeyError on unknown parent,
        ValueError on a cycle — all enforced by :class:`MindmapDAG`.
        """
        dag = MindmapDAG(score_threshold=self._score_threshold)
        for spec in specs:
            dag.add_node(
                DecisionNode(
                    node_id=spec.node_id,
                    input_context=spec.input_context,
                    strategy=spec.strategy,
                    model_target=spec.model_target,
                    score=spec.score,
                )
            )
        for spec in specs:
            if spec.parent is not None:
                dag.add_edge(spec.parent, spec.node_id)
        self._dag = dag
        return dag

    # --- execution ---

    def run(self, input_context: str, executor: Executor) -> PlannerReceipt:
        """Plan, execute, and auto-reroute around failed subtasks.

        Returns a :class:`PlannerReceipt`. ``completed`` is True only when
        every node on the final path succeeded at or above the threshold —
        exhausting ``max_reroutes`` or running out of alternative branches
        yields ``completed=False`` rather than a claimed success.
        """
        if self._dag is None:
            raise ValueError("call build() before run()")
        dag = self._dag

        path = dag.plan(input_context)
        reroutes: list[RerouteEvent] = []
        outputs: dict[str, str] = {}
        succeeded: set[str] = set()
        failed: set[str] = set()
        completed = False

        for _attempt in range(self._max_reroutes + 1):
            failure: tuple[str, float, str] | None = None
            stuck = False

            for node_id in path.node_ids:
                if node_id in succeeded:
                    continue
                if node_id in failed:
                    # Re-plan still routes through a known-failed node:
                    # no alternative branch exists.
                    stuck = True
                    break

                node = dag.get_node(node_id)
                if node is None:  # pragma: no cover — DAG holds its own nodes
                    continue

                route = self._adapter.prepare_task(
                    node.strategy or node_id,
                    {"complexity": node.score},
                )
                output, raw_score, ok = executor(node_id, route)
                outputs[node_id] = output

                score = max(0.0, min(1.0, float(raw_score)))
                node.score = score

                if ok and score >= self._score_threshold:
                    succeeded.add(node_id)
                    continue

                failed.add(node_id)
                reason = (
                    "executor reported failure"
                    if not ok
                    else f"score {score:.3f} below threshold {self._score_threshold:.3f}"
                )
                failure = (node_id, score, reason)
                break

            if failure is None:
                if stuck:
                    break  # no alternative — stop honestly
                completed = True
                break

            node_id, score, reason = failure
            if len(reroutes) >= self._max_reroutes:
                break

            new_path = dag.reroute(node_id, score)
            if new_path.node_ids == path.node_ids:
                reroutes.append(
                    RerouteEvent(node_id, score, new_path.node_ids, f"{reason}; no alternative branch")
                )
                break

            reroutes.append(RerouteEvent(node_id, score, new_path.node_ids, reason))
            path = new_path

        conclusion = ""
        for nid in reversed(path.node_ids):
            if nid in succeeded and nid in outputs:
                conclusion = outputs[nid]
                break

        return PlannerReceipt(
            path=path.node_ids,
            node_records=tuple(dag.trace(path.node_ids)),
            reroutes=tuple(reroutes),
            final_score=dag.score_path(path.node_ids) if path.node_ids else 0.0,
            conclusion=conclusion,
            completed=completed,
            outputs=dict(outputs),
        )
