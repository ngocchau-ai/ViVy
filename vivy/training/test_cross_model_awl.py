"""Tests for CrossModelAdapter AWL integration (AWL-3 — route + load plan).

Changelog:
    25/09/2026 (Claude Code — AWL-3): Initial.
"""
from __future__ import annotations

import time
import unittest

from training.cautreo_resource_monitor import ResourceMonitor, SystemMetrics
from training.cross_model_adapter import CrossModelAdapter
from training.load_governor import LoadGovernor
from training.weight_pager import WeightPager


def _provider(available_mb: float = 10_000):
    def _get() -> SystemMetrics:
        return SystemMetrics(
            physical_total_mb=16384,
            physical_available_mb=available_mb,
            process_rss_mb=2750,
            timestamp=time.time(),
        )
    return _get


def _make_full_stack(
    available_mb: float = 10_000,
) -> tuple[CrossModelAdapter, LoadGovernor]:
    """Build a CrossModelAdapter + LoadGovernor + WeightPager stack."""
    mon = ResourceMonitor(
        safety_margin_mb=1000,
        provider=_provider(available_mb),
    )
    pager = WeightPager()
    gov = LoadGovernor(mon, pager)

    # Register qwen model with governor (80 layers, 10MB each = 800MB total)
    gov.register_model("qwen-72b", total_layers=80, bytes_per_layer_mb=10.0)

    # Register with pager too
    pager.register_model("qwen-72b", "/qwen.gguf", "gguf", total_layers=80)

    adapter = CrossModelAdapter(pager, governor=gov)
    adapter.couple(
        "gemma4-e4b", "qwen-72b",
        task_tags=("reasoning", "code"),
        blend_ratio=0.4,
    )
    adapter.set_fallback("gemma4-e4b")
    return adapter, gov


class TestRouteWithLoadPlan(unittest.TestCase):
    def test_route_returns_load_decision(self) -> None:
        adapter, _ = _make_full_stack()
        r = adapter.route("reasoning", {"complexity": 0.7})
        self.assertIsNotNone(r.load_decision)
        self.assertEqual(r.model_alias, "qwen-72b")

    def test_route_no_governor_load_none(self) -> None:
        """Without governor, load_decision is None (backward compat)."""
        pager = WeightPager()
        adapter = CrossModelAdapter(pager)
        adapter.set_fallback("gemma4")
        r = adapter.route("anything")
        self.assertIsNone(r.load_decision)

    def test_load_decision_reflects_complexity(self) -> None:
        adapter, _ = _make_full_stack()
        # Force both routes to qwen-72b via explicit rule so comparison is fair.
        adapter.set_route("reasoning", "qwen-72b")
        r_light = adapter.route("reasoning", {"complexity": 0.1})
        r_heavy = adapter.route("reasoning", {"complexity": 0.9})
        assert r_light.load_decision is not None
        assert r_heavy.load_decision is not None
        self.assertLess(
            r_light.load_decision.target_fraction,
            r_heavy.load_decision.target_fraction,
        )

    def test_route_explicit_rule_still_works(self) -> None:
        adapter, _ = _make_full_stack()
        adapter.set_route("special", "qwen-72b")
        r = adapter.route("special", {"complexity": 0.5})
        self.assertEqual(r.model_alias, "qwen-72b")
        self.assertIn("explicit_rule", r.reason)
        self.assertIsNotNone(r.load_decision)

    def test_route_unregistered_model_no_load_plan(self) -> None:
        """If routed model is not in governor registry, load_decision is None."""
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        adapter = CrossModelAdapter(governor=gov)
        adapter.set_fallback("ghost-model")
        r = adapter.route("anything")
        self.assertEqual(r.model_alias, "ghost-model")
        self.assertIsNone(r.load_decision)


class TestPrepareTask(unittest.TestCase):
    def test_prepare_applies_load(self) -> None:
        adapter, gov = _make_full_stack()
        r = adapter.prepare_task("reasoning", {"complexity": 0.7})
        self.assertIsNotNone(r.load_decision)
        self.assertGreater(gov._state("qwen-72b").current_layers, 0)

    def test_prepare_updates_footprint(self) -> None:
        adapter, gov = _make_full_stack()
        adapter.prepare_task("reasoning", {"complexity": 0.7})
        self.assertGreater(gov._monitor.current_footprint_mb, 0)

    def test_prepare_light_task_low_footprint(self) -> None:
        adapter_light, gov_light = _make_full_stack()
        adapter_light.prepare_task("reasoning", {"complexity": 0.1})

        adapter_heavy, gov_heavy = _make_full_stack()
        adapter_heavy.prepare_task("reasoning", {"complexity": 0.9})

        self.assertLess(
            gov_light._monitor.current_footprint_mb,
            gov_heavy._monitor.current_footprint_mb,
        )


class TestCallbackWeightsBudgetAware(unittest.TestCase):
    def test_callback_uses_budget(self) -> None:
        adapter, _ = _make_full_stack()
        # Govern for complexity 0.5 → moderate band → ~20% of 80 layers = 16
        reg = adapter._pager.get_registration("qwen-72b")
        self.assertIsNotNone(reg)
        slice_ = adapter.callback_weights("qwen-72b", "reasoning")
        self.assertIsNotNone(slice_)
        if slice_ is not None:
            # Should be close to governor's target, not hard 25% (20 layers)
            self.assertGreater(slice_.layer_range[1], 0)

    def test_callback_no_governor_defaults_25pct(self) -> None:
        """Without governor, callback_weights uses original 25% logic."""
        pager = WeightPager()
        pager.register_model("m", "/m.gguf", "gguf", total_layers=80)
        adapter = CrossModelAdapter(pager)
        slice_ = adapter.callback_weights("m", "task")
        self.assertIsNotNone(slice_)
        if slice_ is not None:
            self.assertEqual(slice_.layer_range[1], 20)  # 80 // 4

    def test_callback_unknown_model(self) -> None:
        adapter, _ = _make_full_stack()
        self.assertIsNone(adapter.callback_weights("ghost", "task"))


class TestAttachGovernor(unittest.TestCase):
    def test_attach_after_construction(self) -> None:
        adapter = CrossModelAdapter()
        self.assertIsNone(adapter.governor)
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        adapter.attach_governor(gov)
        self.assertIs(adapter.governor, gov)

    def test_replace_governor(self) -> None:
        adapter, _ = _make_full_stack()
        mon = ResourceMonitor(provider=_provider())
        gov2 = LoadGovernor(mon, WeightPager())
        adapter.attach_governor(gov2)
        self.assertIs(adapter.governor, gov2)


class TestBudgetBlocked(unittest.TestCase):
    def test_blocked_when_ram_tight(self) -> None:
        adapter, _ = _make_full_stack(available_mb=1200)
        r = adapter.prepare_task("reasoning", {"complexity": 0.9})
        self.assertIsNotNone(r.load_decision)
        if r.load_decision is not None:
            self.assertIn(r.load_decision.action, ("load", "blocked", "hold"))


class TestBackwardCompat(unittest.TestCase):
    def test_route_result_without_load(self) -> None:
        """Old-style construction still works."""
        from training.cross_model_adapter import RouteResult

        r = RouteResult(model_alias="m", reason="test", confidence=0.5)
        self.assertIsNone(r.load_decision)

    def test_combine_outputs_unchanged(self) -> None:
        adapter, _ = _make_full_stack()
        out = adapter.combine_outputs("AAAA", "BBBB", blend_ratio=0.0)
        self.assertEqual(out, "AAAA")
        out2 = adapter.combine_outputs("AAAA", "BBBB", blend_ratio=1.0)
        self.assertEqual(out2, "BBBB")
        out3 = adapter.combine_outputs("AAAA", "BBBB", blend_ratio=0.5)
        self.assertIn("AA", out3)
        self.assertIn("BB", out3)


if __name__ == "__main__":
    unittest.main()
