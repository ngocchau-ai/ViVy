"""Cautreo Resource Monitor — Real-time RAM tracking + load budget (AWL foundation).

Tracks system memory state and computes how much additional model weight
can be safely loaded. Provides the `budget()` that LoadGovernor consumes
to decide how aggressively to page in qwen2-72b (or any secondary core)
without triggering OOM.

Design:
    ResourceMonitor
    ├── snapshot() -> SystemMetrics       — point-in-time RAM state
    ├── budget() -> ResourceBudget        — headroom + per-model allowance
    ├── can_load(bytes) -> bool           — quick guard
    ├── register_footprint(alias, bytes)  — track loaded weight bytes
    ├── adjust_footprint(alias, delta)    — incremental update
    └── history(maxlen) -> list[snapshot] — rolling sample buffer

SystemMetrics are injected via a provider callable, so tests never
depend on real hardware state. The default provider uses psutil.

Changelog:
    25/09/2026 (Claude Code — AWL-1): Initial.
"""
from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# --- Metrics -----------------------------------------------------------------


@dataclass(frozen=True)
class SystemMetrics:
    """Point-in-time system memory snapshot (all values in MB)."""

    physical_total_mb: float
    physical_available_mb: float
    process_rss_mb: float = 0.0
    timestamp: float = 0.0

    @property
    def physical_used_mb(self) -> float:
        return self.physical_total_mb - self.physical_available_mb

    @property
    def used_fraction(self) -> float:
        if self.physical_total_mb <= 0:
            return 0.0
        return self.physical_used_mb / self.physical_total_mb

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_total_mb": round(self.physical_total_mb, 1),
            "physical_available_mb": round(self.physical_available_mb, 1),
            "physical_used_mb": round(self.physical_used_mb, 1),
            "used_fraction": round(self.used_fraction, 4),
            "process_rss_mb": round(self.process_rss_mb, 1),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ResourceBudget:
    """How much more model weight can be safely loaded right now (MB)."""

    headroom_mb: float
    max_loadable_mb: float
    current_footprint_mb: float
    safety_margin_mb: float
    peak_footprint_mb: float
    per_model: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "headroom_mb": round(self.headroom_mb, 1),
            "max_loadable_mb": round(self.max_loadable_mb, 1),
            "current_footprint_mb": round(self.current_footprint_mb, 1),
            "safety_margin_mb": round(self.safety_margin_mb, 1),
            "peak_footprint_mb": round(self.peak_footprint_mb, 1),
            "per_model": {k: round(v, 1) for k, v in self.per_model.items()},
        }


# --- Provider (injectable for tests) -----------------------------------------

MetricsProvider = Callable[[], SystemMetrics]


def _psutil_provider() -> SystemMetrics:
    """Default provider using psutil. Falls back to zeros if unavailable."""
    try:
        import psutil

        vm = psutil.virtual_memory()
        rss = psutil.Process().memory_info().rss
        return SystemMetrics(
            physical_total_mb=vm.total / (1024 * 1024),
            physical_available_mb=vm.available / (1024 * 1024),
            process_rss_mb=rss / (1024 * 1024),
            timestamp=time.time(),
        )
    except (ImportError, OSError, AttributeError):
        return SystemMetrics(
            physical_total_mb=0.0,
            physical_available_mb=0.0,
            timestamp=time.time(),
        )


# --- Monitor -----------------------------------------------------------------


class ResourceMonitor:
    """Tracks RAM state and model weight footprint; computes load budget.

    Safety contract:
      * Never allow a load that would push available RAM below ``safety_margin_mb``.
      * ``max_loadable_mb`` is always ≥ 0 (clamped).
      * Peak footprint is tracked for diagnostics / eviction triggers.
    """

    def __init__(
        self,
        *,
        safety_margin_mb: float = 1500.0,
        hard_cap_mb: float = 100_000.0,
        provider: MetricsProvider | None = None,
        history_size: int = 120,
    ) -> None:
        if safety_margin_mb < 0:
            raise ValueError(f"safety_margin_mb must be >= 0, got {safety_margin_mb}")
        if hard_cap_mb <= 0:
            raise ValueError(f"hard_cap_mb must be > 0, got {hard_cap_mb}")
        self._safety_margin_mb = safety_margin_mb
        self._hard_cap_mb = hard_cap_mb
        self._provider = provider or _psutil_provider
        self._footprint: dict[str, float] = {}  # alias -> MB
        self._peak_mb = 0.0
        self._history: deque[SystemMetrics] = deque(maxlen=history_size)

    # --- snapshot / budget ---

    def snapshot(self) -> SystemMetrics:
        m = self._provider()
        self._history.append(m)
        return m

    def budget(self) -> ResourceBudget:
        m = self.snapshot()
        current = self.current_footprint_mb
        self._peak_mb = max(self._peak_mb, current)
        headroom = m.physical_available_mb - self._safety_margin_mb
        max_loadable = min(max(0.0, headroom), self._hard_cap_mb)
        return ResourceBudget(
            headroom_mb=max(0.0, headroom),
            max_loadable_mb=max_loadable,
            current_footprint_mb=current,
            safety_margin_mb=self._safety_margin_mb,
            peak_footprint_mb=self._peak_mb,
            per_model=dict(self._footprint),
        )

    def can_load(self, size_mb: float) -> bool:
        """True if adding ``size_mb`` won't breach the safety margin."""
        if size_mb < 0:
            raise ValueError(f"size_mb must be >= 0, got {size_mb}")
        b = self.budget()
        return size_mb <= b.max_loadable_mb

    # --- footprint tracking ---

    @property
    def current_footprint_mb(self) -> float:
        return sum(self._footprint.values())

    def register_footprint(self, alias: str, size_mb: float) -> None:
        """Set a model's loaded weight footprint to an absolute value (MB)."""
        if size_mb < 0:
            raise ValueError(f"size_mb must be >= 0, got {size_mb}")
        self._footprint[alias] = size_mb
        self._peak_mb = max(self._peak_mb, self.current_footprint_mb)

    def adjust_footprint(self, alias: str, delta_mb: float) -> float:
        """Incrementally adjust a model's footprint. Returns new value (MB)."""
        cur = self._footprint.get(alias, 0.0)
        new = max(0.0, cur + delta_mb)
        self._footprint[alias] = new
        self._peak_mb = max(self._peak_mb, self.current_footprint_mb)
        return new

    def release(self, alias: str) -> float:
        """Remove a model's footprint entirely. Returns MB released."""
        released = self._footprint.pop(alias, 0.0)
        return released

    def clear_all(self) -> float:
        """Release all tracked footprints. Returns MB released."""
        total = self.current_footprint_mb
        self._footprint.clear()
        return total

    # --- diagnostics ---

    def history(self) -> list[SystemMetrics]:
        return list(self._history)

    def to_dict(self) -> dict[str, Any]:
        b = self.budget()
        return {
            "budget": b.to_dict(),
            "footprint": {k: round(v, 1) for k, v in self._footprint.items()},
            "peak_footprint_mb": round(self._peak_mb, 1),
            "safety_margin_mb": self._safety_margin_mb,
            "hard_cap_mb": self._hard_cap_mb,
        }
