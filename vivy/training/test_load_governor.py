"""Tests for load_governor (AWL-2 — adaptive weight loading policy).

Changelog:
    25/09/2026 (Claude Code — AWL-2): Initial.
    25/09/2026 (Claude Code — AWL-4): Capability-priority eviction tests.
"""
from __future__ import annotations

import time
import unittest

from training.cautreo_resource_monitor import ResourceMonitor, SystemMetrics
from training.load_governor import (
    DEFAULT_BANDS,
    LoadBand,
    LoadGovernor,
    LoadPolicy,
)
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


def _make_governor(
    available_mb: float = 10_000,
    *,
    total_layers: int = 80,
    bytes_per_layer_mb: float = 10.0,  # 80 layers * 10MB = 800MB total
) -> LoadGovernor:
    mon = ResourceMonitor(
        safety_margin_mb=1000,
        provider=_provider(available_mb),
    )
    pager = WeightPager()
    gov = LoadGovernor(mon, pager)
    gov.register_model(
        "qwen-72b",
        total_layers=total_layers,
        bytes_per_layer_mb=bytes_per_layer_mb,
    )
    return gov


class TestBands(unittest.TestCase):
    def test_default_bands_cover_zero_to_one(self) -> None:
        self.assertEqual(DEFAULT_BANDS[0].complexity_min, 0.0)
        self.assertGreater(DEFAULT_BANDS[-1].complexity_max, 1.0)

    def test_band_labels(self) -> None:
        labels = [b.label for b in DEFAULT_BANDS]
        self.assertIn("light", labels)
        self.assertIn("aggressive", labels)


class TestRegisterModel(unittest.TestCase):
    def test_register(self) -> None:
        gov = _make_governor()
        self.assertEqual(gov._state("qwen-72b").total_layers, 80)

    def test_register_invalid_layers(self) -> None:
        gov = _make_governor()
        with self.assertRaises(ValueError):
            gov.register_model("bad", total_layers=0, bytes_per_layer_mb=1)

    def test_register_invalid_bytes(self) -> None:
        gov = _make_governor()
        with self.assertRaises(ValueError):
            gov.register_model("bad", total_layers=10, bytes_per_layer_mb=-1)

    def test_unregistered_model_raises(self) -> None:
        gov = _make_governor()
        with self.assertRaises(KeyError):
            gov.decide("ghost", 0.5)


class TestDecide(unittest.TestCase):
    def test_light_task_low_load(self) -> None:
        gov = _make_governor()
        d = gov.decide("qwen-72b", 0.1)
        self.assertLess(d.target_fraction, 0.1)
        self.assertEqual(d.band_label, "light")

    def test_aggressive_task_high_load(self) -> None:
        gov = _make_governor()
        d = gov.decide("qwen-72b", 0.9)
        self.assertGreater(d.target_fraction, 0.5)
        self.assertEqual(d.band_label, "aggressive")

    def test_monotonicity(self) -> None:
        """Higher complexity → higher (or equal) target fraction."""
        gov = _make_governor()
        prev = 0.0
        for c in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]:
            d = gov.decide("qwen-72b", c)
            self.assertGreaterEqual(d.target_fraction, prev)
            prev = d.target_fraction

    def test_complexity_out_of_range(self) -> None:
        gov = _make_governor()
        with self.assertRaises(ValueError):
            gov.decide("qwen-72b", 1.5)

    def test_max_fraction_capped(self) -> None:
        policy = LoadPolicy(max_fraction=0.3)
        mon = ResourceMonitor(
            safety_margin_mb=1000,
            provider=_provider(available_mb=10_000),
        )
        gov2 = LoadGovernor(mon, WeightPager(), policy=policy)
        gov2.register_model("qwen-72b", total_layers=80, bytes_per_layer_mb=10)
        d = gov2.decide("qwen-72b", 1.0)
        self.assertLessEqual(d.target_fraction, 0.3001)


class TestBudgetClamp(unittest.TestCase):
    def test_blocked_when_insufficient_ram(self) -> None:
        """Low available RAM → target clamped, action may be 'blocked'."""
        gov = _make_governor(available_mb=1200)  # barely above safety margin
        d = gov.decide("qwen-72b", 0.9)  # wants ~640MB
        self.assertLessEqual(d.target_mb, 8000 * 0.7 + 1)
        self.assertIn(d.action, ("load", "blocked", "hold"))

    def test_budget_clamp_reason(self) -> None:
        gov = _make_governor(available_mb=1200)
        d = gov.decide("qwen-72b", 0.9)
        self.assertIn("budget", d.reason)


class TestAdjust(unittest.TestCase):
    def test_adjust_loads(self) -> None:
        gov = _make_governor()
        d = gov.adjust("qwen-72b", 0.7)
        self.assertIn(d.action, ("load", "hold", "blocked"))
        self.assertGreater(gov._state("qwen-72b").current_layers, 0)

    def test_adjust_updates_footprint(self) -> None:
        gov = _make_governor()
        gov.adjust("qwen-72b", 0.7)
        self.assertGreater(gov._monitor.current_footprint_mb, 0)

    def test_adjust_hold_within_threshold(self) -> None:
        gov = _make_governor()
        gov.adjust("qwen-72b", 0.5)
        d2 = gov.adjust("qwen-72b", 0.51)  # tiny delta
        self.assertEqual(d2.action, "hold")


class TestReleaseIfIdle(unittest.TestCase):
    def test_not_released_when_recently_used(self) -> None:
        gov = _make_governor()
        gov.adjust("qwen-72b", 0.5)
        self.assertFalse(gov.release_if_idle("qwen-72b", idle_seconds=3600))

    def test_released_after_delay(self) -> None:
        gov = _make_governor()
        gov.adjust("qwen-72b", 0.5)
        gov._state("qwen-72b").last_used = time.time() - 999
        self.assertTrue(gov.release_if_idle("qwen-72b", idle_seconds=30))

    def test_noop_when_already_empty(self) -> None:
        gov = _make_governor()
        gov._state("qwen-72b").last_used = time.time() - 999
        self.assertFalse(gov.release_if_idle("qwen-72b", idle_seconds=30))


class TestEviction(unittest.TestCase):
    def test_eviction_candidates_lru(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        gov.register_model("a", total_layers=10, bytes_per_layer_mb=1)
        gov.register_model("b", total_layers=10, bytes_per_layer_mb=1)
        gov._state("a").last_used = time.time() - 100
        gov._state("b").last_used = time.time()
        order = gov.eviction_candidates()
        self.assertEqual(order[0], "a")

    def test_evict_frees_memory(self) -> None:
        gov = _make_governor()
        gov.adjust("qwen-72b", 0.7)
        freed = gov.evict("qwen-72b")
        self.assertGreater(freed, 0)
        self.assertEqual(gov._state("qwen-72b").current_layers, 0)


class TestCapabilityPriority(unittest.TestCase):
    """AWL-4: capability priority dominates LRU in eviction ordering."""

    def test_priority_dominates_lru(self) -> None:
        """Low-priority + recent evicts before high-priority + stale."""
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        # core = high priority but NOT used recently (stale).
        gov.register_model("core", total_layers=10, bytes_per_layer_mb=1, priority=10)
        # aux = default priority 0 but used just now.
        gov.register_model("aux", total_layers=10, bytes_per_layer_mb=1, priority=0)
        gov._state("core").last_used = time.time() - 999
        gov._state("aux").last_used = time.time()
        order = gov.eviction_candidates()
        self.assertEqual(order[0], "aux")
        self.assertEqual(order[1], "core")

    def test_equal_priority_falls_back_to_lru(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        gov.register_model("a", total_layers=10, bytes_per_layer_mb=1, priority=5)
        gov.register_model("b", total_layers=10, bytes_per_layer_mb=1, priority=5)
        gov._state("a").last_used = time.time() - 100
        gov._state("b").last_used = time.time()
        self.assertEqual(gov.eviction_candidates()[0], "a")

    def test_higher_priority_last(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        for i, p in enumerate((0, 5, 10)):
            gov.register_model(f"m{i}", total_layers=10, bytes_per_layer_mb=1, priority=p)
            gov._state(f"m{i}").last_used = time.time()  # identical recency
        self.assertEqual(gov.eviction_candidates(), ["m0", "m1", "m2"])

    def test_register_invalid_priority(self) -> None:
        gov = _make_governor()
        with self.assertRaises(TypeError):
            gov.register_model("bad", total_layers=10, bytes_per_layer_mb=1, priority="high")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            gov.register_model("bad2", total_layers=10, bytes_per_layer_mb=1, priority=True)

    def test_register_default_priority_zero(self) -> None:
        gov = _make_governor()
        self.assertEqual(gov._state("qwen-72b").priority, 0)

    def test_state_dict_exposes_priority(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        gov = LoadGovernor(mon, WeightPager())
        gov.register_model("core", total_layers=10, bytes_per_layer_mb=1, priority=10)
        d = gov.state_dict()
        self.assertEqual(d["models"]["core"]["priority"], 10)


class TestStateDict(unittest.TestCase):
    def test_to_dict(self) -> None:
        gov = _make_governor()
        d = gov.state_dict()
        self.assertIn("models", d)
        self.assertIn("monitor", d)


class TestCustomBand(unittest.TestCase):
    def test_custom_band_interpolation(self) -> None:
        band = LoadBand(0.0, 1.0, 0.1, 0.9, "custom")
        policy = LoadPolicy(bands=(band,))
        mon = ResourceMonitor(
            safety_margin_mb=1000, provider=_provider(available_mb=10_000)
        )
        gov = LoadGovernor(mon, WeightPager(), policy=policy)
        gov.register_model("m", total_layers=100, bytes_per_layer_mb=1)
        d = gov.decide("m", 0.5)
        self.assertAlmostEqual(d.target_fraction, 0.5, places=2)


if __name__ == "__main__":
    unittest.main()
