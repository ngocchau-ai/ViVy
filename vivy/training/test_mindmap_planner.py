"""Tests for mindmap_planner (TD-6 integration — plan + auto-reroute).

Changelog:
    25/09/2026 (Claude Code — TD-6 integration): Initial.
"""
from __future__ import annotations

import time
import unittest
from typing import Any

from training.cautreo_resource_monitor import ResourceMonitor, SystemMetrics
from training.cross_model_adapter import CrossModelAdapter
from training.load_governor import LoadGovernor
from training.mindmap_planner import MindmapPlanner, SubtaskSpec
from training.weight_pager import WeightPager


def _diamond_specs() -> list[SubtaskSpec]:
    """A → B → D, A → C → E.  C scores higher, so plan() prefers A→C→E."""
    return [
        SubtaskSpec("A", input_context="task-1", strategy="root", score=0.9),
        SubtaskSpec("B", strategy="left", model_target="gemma4", score=0.4, parent="A"),
        SubtaskSpec("C", strategy="right", model_target="qwen", score=0.8, parent="A"),
        SubtaskSpec("D", strategy="leaf-left", score=0.5, parent="B"),
        SubtaskSpec("E", strategy="leaf-right", score=0.7, parent="C"),
    ]


def _ok_executor(calls: list[str]):
    """Executor that always succeeds, recording node order."""
    def _exec(node_id: str, route: Any) -> tuple[str, float, bool]:
        calls.append(node_id)
        return f"out-{node_id}", 0.9, True
    return _exec


def _fail_on(*bad: str, calls: list[str] | None = None):
    """Executor that fails every node in *bad*, succeeds elsewhere."""
    seen: list[str] = calls if calls is not None else []

    def _exec(node_id: str, route: Any) -> tuple[str, float, bool]:
        seen.append(node_id)
        if node_id in bad:
            return f"fail-{node_id}", 0.1, False
        return f"out-{node_id}", 0.9, True

    return _exec, seen


def _provider(available_mb: float = 10_000):
    def _get() -> SystemMetrics:
        return SystemMetrics(
            physical_total_mb=16384,
            physical_available_mb=available_mb,
            process_rss_mb=2750,
            timestamp=time.time(),
        )
    return _get


def _planner(**kw: Any) -> MindmapPlanner:
    """Planner whose adapter has a fallback so routing always resolves."""
    adapter = CrossModelAdapter()
    adapter.set_fallback("gemma4-e4b")
    return MindmapPlanner(adapter, **kw)


class TestSubtaskSpec(unittest.TestCase):
    def test_score_range_validated(self) -> None:
        with self.assertRaises(ValueError):
            SubtaskSpec("x", score=1.5)
        with self.assertRaises(ValueError):
            SubtaskSpec("x", score=-0.1)

    def test_defaults(self) -> None:
        s = SubtaskSpec("x")
        self.assertEqual(s.score, 0.5)
        self.assertIsNone(s.parent)


class TestPlannerConstruction(unittest.TestCase):
    def test_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            MindmapPlanner(score_threshold=1.5)

    def test_invalid_max_reroutes(self) -> None:
        with self.assertRaises(ValueError):
            MindmapPlanner(max_reroutes=-1)

    def test_default_adapter(self) -> None:
        p = MindmapPlanner()
        self.assertIsInstance(p.adapter, CrossModelAdapter)


class TestBuild(unittest.TestCase):
    def test_build_wires_parent_edges(self) -> None:
        p = _planner()
        dag = p.build(_diamond_specs())
        self.assertEqual(dag.node_count, 5)
        a = dag.get_node("A")
        assert a is not None
        self.assertEqual(sorted(a.children), ["B", "C"])
        b = dag.get_node("B")
        assert b is not None
        self.assertEqual(b.children, ["D"])

    def test_build_unknown_parent_raises(self) -> None:
        p = _planner()
        with self.assertRaises(KeyError):
            p.build([SubtaskSpec("a", parent="ghost")])

    def test_build_duplicate_raises(self) -> None:
        p = _planner()
        with self.assertRaises(ValueError):
            p.build([SubtaskSpec("a"), SubtaskSpec("a")])

    def test_run_before_build_raises(self) -> None:
        p = _planner()
        with self.assertRaises(ValueError):
            p.run("task-1", _ok_executor([]))


class TestPlanSelection(unittest.TestCase):
    def test_run_picks_highest_score_path(self) -> None:
        p = _planner()
        p.build(_diamond_specs())
        calls: list[str] = []
        receipt = p.run("task-1", _ok_executor(calls))
        # C (0.8) beats B (0.4) → A→C→E.
        self.assertEqual(receipt.path, ("A", "C", "E"))
        self.assertEqual(calls, ["A", "C", "E"])
        self.assertTrue(receipt.completed)
        self.assertEqual(receipt.reroutes, ())

    def test_no_fail_no_reroute(self) -> None:
        p = _planner()
        p.build(_diamond_specs())
        receipt = p.run("task-1", _ok_executor([]))
        self.assertEqual(len(receipt.reroutes), 0)

    def test_conclusion_is_last_successful_output(self) -> None:
        p = _planner()
        p.build(_diamond_specs())
        receipt = p.run("task-1", _ok_executor([]))
        self.assertEqual(receipt.conclusion, "out-E")

    def test_node_records_carry_model_target(self) -> None:
        p = _planner()
        p.build(_diamond_specs())
        receipt = p.run("task-1", _ok_executor([]))
        targets = [r["model_target"] for r in receipt.node_records]
        self.assertIn("qwen", targets)


class TestAutoReroute(unittest.TestCase):
    def test_auto_reroute_on_subtask_failure(self) -> None:
        """Core evidence: subtask C fails → planner reroutes to A→B→D."""
        p = _planner()
        p.build(_diamond_specs())
        exec_fn, calls = _fail_on("C")

        receipt = p.run("task-1", exec_fn)

        # Reroute happened and landed on the alternative branch.
        self.assertEqual(len(receipt.reroutes), 1)
        ev = receipt.reroutes[0]
        self.assertEqual(ev.node_id, "C")
        self.assertEqual(ev.new_path, ("A", "B", "D"))
        self.assertEqual(receipt.path, ("A", "B", "D"))

        # C was attempted once and never retried; A was not re-executed.
        self.assertEqual(calls.count("C"), 1)
        self.assertEqual(calls.count("A"), 1)
        self.assertIn("B", calls)
        self.assertIn("D", calls)

        self.assertTrue(receipt.completed)
        self.assertEqual(receipt.conclusion, "out-D")

    def test_reroute_below_threshold(self) -> None:
        """A node that succeeds but scores under threshold also reroutes."""
        p = _planner(score_threshold=0.5)
        p.build(_diamond_specs())

        def exec_fn(node_id: str, route: Any) -> tuple[str, float, bool]:
            if node_id == "C":
                return "weak", 0.2, True  # ok=True but score < 0.5
            return f"out-{node_id}", 0.9, True

        receipt = p.run("task-1", exec_fn)
        self.assertEqual(len(receipt.reroutes), 1)
        self.assertEqual(receipt.reroutes[0].node_id, "C")
        self.assertIn("below threshold", receipt.reroutes[0].reason)
        self.assertEqual(receipt.path, ("A", "B", "D"))
        self.assertTrue(receipt.completed)

    def test_reroute_event_serialises(self) -> None:
        p = _planner()
        p.build(_diamond_specs())
        exec_fn, _ = _fail_on("C")
        receipt = p.run("task-1", exec_fn)
        d = receipt.reroutes[0].to_dict()
        self.assertEqual(d["node_id"], "C")
        self.assertEqual(d["new_path"], ["A", "B", "D"])
        self.assertIsInstance(d["failed_score"], float)

    def test_receipt_to_dict(self) -> None:
        p = _planner()
        p.build(_diamond_specs())
        exec_fn, _ = _fail_on("C")
        d = p.run("task-1", exec_fn).to_dict()
        self.assertIn("path", d)
        self.assertIn("reroutes", d)
        self.assertTrue(d["completed"])


class TestMaxReroutes(unittest.TestCase):
    def test_max_reroutes_cap(self) -> None:
        """Every branch fails → stops, completed=False, no success claimed."""
        p = _planner(max_reroutes=3)
        p.build(_diamond_specs())
        exec_fn, calls = _fail_on("A", "B", "C", "D", "E")

        receipt = p.run("task-1", exec_fn)

        self.assertFalse(receipt.completed)
        self.assertEqual(receipt.conclusion, "")
        self.assertLessEqual(len(receipt.reroutes), 3)
        # Root failed — there is no alternative root, so at most one attempt.
        self.assertEqual(calls.count("A"), 1)

    def test_no_alternative_branch_records_reason(self) -> None:
        """A single-branch DAG has nowhere to reroute to."""
        p = _planner()
        p.build([
            SubtaskSpec("A", strategy="root", score=0.9),
            SubtaskSpec("B", strategy="only", score=0.8, parent="A"),
        ])
        exec_fn, _ = _fail_on("B")
        receipt = p.run("", exec_fn)
        self.assertFalse(receipt.completed)
        self.assertEqual(len(receipt.reroutes), 1)
        self.assertIn("no alternative branch", receipt.reroutes[0].reason)

    def test_reroute_budget_exhausted(self) -> None:
        p = _planner(max_reroutes=1)
        p.build(_diamond_specs())
        # Fail the preferred leaf's branch node, then the alternative too.
        exec_fn, _ = _fail_on("C", "D")
        receipt = p.run("task-1", exec_fn)
        self.assertFalse(receipt.completed)
        self.assertLessEqual(len(receipt.reroutes), 1)


class TestRouteIntegration(unittest.TestCase):
    def test_route_result_feeds_executor(self) -> None:
        """Executor sees a RouteResult carrying the AWL load decision."""
        mon = ResourceMonitor(safety_margin_mb=1000, provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        gov.register_model("qwen-72b", total_layers=80, bytes_per_layer_mb=10.0)
        adapter = CrossModelAdapter(WeightPager(), governor=gov)
        adapter.set_route("right", "qwen-72b")
        adapter.set_route("root", "qwen-72b")
        adapter.set_route("leaf-right", "qwen-72b")

        p = MindmapPlanner(adapter)
        p.build(_diamond_specs())

        seen: list[Any] = []

        def exec_fn(node_id: str, route: Any) -> tuple[str, float, bool]:
            seen.append(route)
            return f"out-{node_id}", 0.9, True

        receipt = p.run("task-1", exec_fn)
        self.assertTrue(receipt.completed)
        self.assertEqual(len(seen), 3)
        for route in seen:
            self.assertEqual(route.model_alias, "qwen-72b")
            self.assertIsNotNone(route.load_decision)

    def test_load_applied_on_prepare(self) -> None:
        mon = ResourceMonitor(safety_margin_mb=1000, provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        gov.register_model("qwen-72b", total_layers=80, bytes_per_layer_mb=10.0)
        adapter = CrossModelAdapter(WeightPager(), governor=gov)
        adapter.set_route("root", "qwen-72b")
        adapter.set_route("left", "qwen-72b")
        adapter.set_route("leaf-left", "qwen-72b")
        adapter.set_route("right", "qwen-72b")
        adapter.set_route("leaf-right", "qwen-72b")

        p = MindmapPlanner(adapter)
        p.build(_diamond_specs())
        exec_fn, _ = _fail_on("C")
        p.run("task-1", exec_fn)
        self.assertGreater(gov._monitor.current_footprint_mb, 0)


class TestThresholdValidation(unittest.TestCase):
    def test_score_clamped_to_unit_interval(self) -> None:
        p = _planner()
        p.build(_diamond_specs())

        def exec_fn(node_id: str, route: Any) -> tuple[str, float, bool]:
            return f"out-{node_id}", 5.0, True  # out of range → clamped

        receipt = p.run("task-1", exec_fn)
        self.assertTrue(receipt.completed)
        self.assertLessEqual(receipt.final_score, 1.0)


if __name__ == "__main__":
    unittest.main()
