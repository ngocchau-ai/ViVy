"""Tests for cautreo_resource_monitor (AWL-1 — real-time resource tracking).

Changelog:
    25/09/2026 (Claude Code — AWL-1): Initial.
"""
from __future__ import annotations

import unittest

from training.cautreo_resource_monitor import (
    ResourceMonitor,
    SystemMetrics,
)


def _provider(
    total_mb: float = 16384,
    available_mb: float = 6144,
    rss_mb: float = 2750,
):
    """Build a stub metrics provider with fixed values."""
    def _get() -> SystemMetrics:
        return SystemMetrics(
            physical_total_mb=total_mb,
            physical_available_mb=available_mb,
            process_rss_mb=rss_mb,
            timestamp=1000.0,
        )
    return _get


class TestSystemMetrics(unittest.TestCase):
    def test_used_fraction(self) -> None:
        m = SystemMetrics(physical_total_mb=1000, physical_available_mb=600)
        self.assertAlmostEqual(m.physical_used_mb, 400)
        self.assertAlmostEqual(m.used_fraction, 0.4)

    def test_zero_total(self) -> None:
        m = SystemMetrics(physical_total_mb=0, physical_available_mb=0)
        self.assertEqual(m.used_fraction, 0.0)

    def test_to_dict(self) -> None:
        m = SystemMetrics(physical_total_mb=1000, physical_available_mb=400)
        d = m.to_dict()
        self.assertIn("used_fraction", d)
        self.assertIn("physical_available_mb", d)


class TestSnapshot(unittest.TestCase):
    def test_snapshot_records_history(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        for _ in range(5):
            mon.snapshot()
        self.assertEqual(len(mon.history()), 5)

    def test_history_bounded(self) -> None:
        mon = ResourceMonitor(provider=_provider(), history_size=3)
        for _ in range(10):
            mon.snapshot()
        self.assertEqual(len(mon.history()), 3)


class TestBudget(unittest.TestCase):
    def test_headroom_subtracts_safety_margin(self) -> None:
        mon = ResourceMonitor(
            safety_margin_mb=1500,
            provider=_provider(available_mb=6144),
        )
        b = mon.budget()
        self.assertAlmostEqual(b.headroom_mb, 4644)
        self.assertAlmostEqual(b.max_loadable_mb, 4644)

    def test_headroom_clamped_to_zero(self) -> None:
        mon = ResourceMonitor(
            safety_margin_mb=5000,
            provider=_provider(available_mb=3000),
        )
        b = mon.budget()
        self.assertEqual(b.headroom_mb, 0.0)
        self.assertEqual(b.max_loadable_mb, 0.0)

    def test_hard_cap_limits_loadable(self) -> None:
        mon = ResourceMonitor(
            safety_margin_mb=0,
            hard_cap_mb=500,
            provider=_provider(available_mb=6144),
        )
        b = mon.budget()
        self.assertAlmostEqual(b.max_loadable_mb, 500)

    def test_budget_tracks_footprint(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        mon.register_footprint("gemma4", 2700)
        mon.register_footprint("qwen", 50)
        b = mon.budget()
        self.assertAlmostEqual(b.current_footprint_mb, 2750)
        self.assertAlmostEqual(b.per_model["gemma4"], 2700)

    def test_peak_tracking(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        mon.register_footprint("m", 3000)
        mon.register_footprint("m", 100)
        b = mon.budget()
        self.assertAlmostEqual(b.peak_footprint_mb, 3000)


class TestCanLoad(unittest.TestCase):
    def test_within_budget(self) -> None:
        mon = ResourceMonitor(
            safety_margin_mb=1000,
            provider=_provider(available_mb=6144),
        )
        self.assertTrue(mon.can_load(5000))

    def test_exceeds_budget(self) -> None:
        mon = ResourceMonitor(
            safety_margin_mb=1000,
            provider=_provider(available_mb=2000),
        )
        self.assertFalse(mon.can_load(5000))

    def test_negative_rejected(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        with self.assertRaises(ValueError):
            mon.can_load(-1)


class TestFootprint(unittest.TestCase):
    def test_register_and_adjust(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        mon.register_footprint("m", 100)
        self.assertAlmostEqual(mon.current_footprint_mb, 100)
        mon.adjust_footprint("m", 50)
        self.assertAlmostEqual(mon.current_footprint_mb, 150)

    def test_adjust_clamped_to_zero(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        mon.register_footprint("m", 10)
        mon.adjust_footprint("m", -50)
        self.assertAlmostEqual(mon.current_footprint_mb, 0)

    def test_release(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        mon.register_footprint("m", 200)
        released = mon.release("m")
        self.assertAlmostEqual(released, 200)
        self.assertAlmostEqual(mon.current_footprint_mb, 0)

    def test_release_unknown_returns_zero(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        self.assertEqual(mon.release("ghost"), 0.0)

    def test_clear_all(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        mon.register_footprint("a", 100)
        mon.register_footprint("b", 200)
        total = mon.clear_all()
        self.assertAlmostEqual(total, 300)
        self.assertEqual(mon.current_footprint_mb, 0)


class TestValidation(unittest.TestCase):
    def test_negative_safety_margin(self) -> None:
        with self.assertRaises(ValueError):
            ResourceMonitor(safety_margin_mb=-1)

    def test_zero_hard_cap(self) -> None:
        with self.assertRaises(ValueError):
            ResourceMonitor(hard_cap_mb=0)

    def test_negative_footprint_register(self) -> None:
        mon = ResourceMonitor(provider=_provider())
        with self.assertRaises(ValueError):
            mon.register_footprint("m", -5)


class TestDefaults(unittest.TestCase):
    def test_default_provider_works(self) -> None:
        """Smoke: default psutil provider returns plausible numbers."""
        mon = ResourceMonitor()
        m = mon.snapshot()
        self.assertGreaterEqual(m.physical_total_mb, 0)


if __name__ == "__main__":
    unittest.main()
