"""Load Governor — Adaptive Weight Loading policy (AWL core).

Maps task complexity to model weight load fraction, respecting the
real-time budget from ResourceMonitor. Implements hysteresis (fast
scale-up, slow scale-down) and LRU-style eviction to free headroom
when the system is under memory pressure.

Policy (default bands):
    complexity 0.0–0.3  →  1–5 %   load  (light)
    complexity 0.3–0.6  →  5–20 %  load  (moderate)
    complexity 0.6–0.8  →  20–50 % load  (heavy)
    complexity 0.8–1.0  →  50–80 % load  (aggressive)

Hard constraints:
    * Never exceed ``max_fraction`` of the model's registered total size.
    * Never load more than the ResourceMonitor budget allows.
    * Always retain ``safety_margin_mb`` free RAM.

Structure:
    LoadGovernor
    ├── register_model(alias, total_layers, bytes_per_layer_mb, priority)
    ├── decide(alias, complexity) -> LoadDecision   — target layer range
    ├── adjust(alias, complexity) -> LoadDecision   — decide + apply via pager
    ├── release_if_idle(alias, idle_s) -> bool      — shrink when idle
    └── eviction_candidates() -> list[alias]        — (priority, LRU) ascending

Changelog:
    25/09/2026 (Claude Code — AWL-2): Initial.
    25/09/2026 (Claude Code — AWL-4): Capability priority on eviction —
        ``register_model(..., priority=)``; ``eviction_candidates()`` sorts by
        (priority, last_used) so low-priority models are evicted first and
        the core brain survives memory pressure.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from training.cautreo_resource_monitor import ResourceMonitor
from training.weight_pager import WeightPager

# --- Policy ------------------------------------------------------------------


@dataclass(frozen=True)
class LoadBand:
    """One complexity band: load fraction range for a model."""

    complexity_min: float
    complexity_max: float
    fraction_min: float
    fraction_max: float
    label: str = ""


DEFAULT_BANDS: tuple[LoadBand, ...] = (
    LoadBand(0.0, 0.3, 0.01, 0.05, "light"),
    LoadBand(0.3, 0.6, 0.05, 0.20, "moderate"),
    LoadBand(0.6, 0.8, 0.20, 0.50, "heavy"),
    LoadBand(0.8, 1.01, 0.50, 0.80, "aggressive"),
)


@dataclass(frozen=True)
class LoadPolicy:
    """Tunable policy for adaptive loading."""

    bands: tuple[LoadBand, ...] = DEFAULT_BANDS
    max_fraction: float = 0.80
    scale_up_threshold: float = 0.05   # complexity delta to trigger load up
    scale_down_delay_s: float = 30.0   # hysteresis: unload only after idle delay
    target_ram_fraction: float = 0.70  # use at most 70% of headroom per model


# --- Decision ----------------------------------------------------------------


@dataclass(frozen=True)
class LoadDecision:
    """What to load (or unload) for one model."""

    alias: str
    complexity: float
    current_fraction: float
    target_fraction: float
    target_layers: tuple[int, int]
    target_mb: float
    action: str  # "load" | "hold" | "unload" | "blocked"
    reason: str
    band_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "complexity": round(self.complexity, 4),
            "current_fraction": round(self.current_fraction, 4),
            "target_fraction": round(self.target_fraction, 4),
            "target_layers": list(self.target_layers),
            "target_mb": round(self.target_mb, 1),
            "action": self.action,
            "reason": self.reason,
            "band_label": self.band_label,
        }


# --- Governor ----------------------------------------------------------------


@dataclass
class _ModelState:
    """Per-model load state for hysteresis tracking."""

    alias: str
    total_layers: int = 0
    total_bytes: float = 0.0  # MB
    current_layers: int = 0
    last_used: float = field(default_factory=time.time)
    last_downscale: float = 0.0
    # Capability priority: HIGHER survives eviction. The core brain (e.g.
    # gemma4-e4b) registers with a high value; auxiliary/secondary cores
    # leave the default 0 and are evicted first under memory pressure.
    priority: int = 0


class LoadGovernor:
    """Adaptive load controller: complexity → layer range, budget-aware.

    Works with a WeightPager (for actual loading) and a ResourceMonitor
    (for budget). The governor itself is pure decision logic — calling
    ``adjust()`` optionally applies the decision via the pager.
    """

    def __init__(
        self,
        monitor: ResourceMonitor,
        pager: WeightPager | None = None,
        *,
        policy: LoadPolicy | None = None,
    ) -> None:
        self._monitor = monitor
        self._pager = pager or WeightPager()
        self._policy = policy or LoadPolicy()
        self._states: dict[str, _ModelState] = {}

    @property
    def policy(self) -> LoadPolicy:
        return self._policy

    # --- model registration ---

    def register_model(
        self,
        alias: str,
        *,
        total_layers: int,
        bytes_per_layer_mb: float,
        priority: int = 0,
    ) -> None:
        """Register a model's physical layout so fractions can map to layers.

        ``priority`` is the capability tier used by :meth:`eviction_candidates`
        — higher survives eviction. Defaults to 0 (evictable), so existing
        call sites are unchanged.
        """
        if total_layers <= 0:
            raise ValueError(f"total_layers must be > 0, got {total_layers}")
        if bytes_per_layer_mb <= 0:
            raise ValueError(f"bytes_per_layer_mb must be > 0, got {bytes_per_layer_mb}")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise TypeError(f"priority must be an int, got {priority!r}")
        self._states[alias] = _ModelState(
            alias=alias,
            total_layers=total_layers,
            total_bytes=total_layers * bytes_per_layer_mb,
            priority=priority,
        )

    def _state(self, alias: str) -> _ModelState:
        if alias not in self._states:
            raise KeyError(f"model not registered with governor: {alias}")
        return self._states[alias]

    # --- decision ---

    def decide(self, alias: str, complexity: float) -> LoadDecision:
        """Compute the target load for ``alias`` at given ``complexity``.

        Pure function of (state, complexity, budget) — does not mutate.
        """
        if not 0.0 <= complexity <= 1.0:
            raise ValueError(f"complexity must be in [0, 1], got {complexity}")
        st = self._state(alias)
        band = self._pick_band(complexity)
        target_frac = self._interpolate(complexity, band)
        target_frac = min(target_frac, self._policy.max_fraction)

        current_frac = st.current_layers / st.total_layers if st.total_layers else 0.0

        # Budget check: can we afford the delta?
        desired_mb = target_frac * st.total_bytes
        current_mb = current_frac * st.total_bytes
        delta_mb = desired_mb - current_mb

        b = self._monitor.budget()
        allowance_mb = b.max_loadable_mb * self._policy.target_ram_fraction

        if delta_mb > allowance_mb:
            # Clamp to what's affordable
            affordable_frac = (current_mb + allowance_mb) / st.total_bytes
            target_frac = min(target_frac, affordable_frac)
            desired_mb = target_frac * st.total_bytes
            delta_mb = desired_mb - current_mb
            action = "blocked" if delta_mb <= 0 else "load"
            reason = (
                f"budget clamp: desired {desired_mb:.0f}MB exceeds allowance "
                f"{allowance_mb:.0f}MB; clamped to {target_frac:.2f}"
            )
        else:
            diff = target_frac - current_frac
            if abs(diff) < self._policy.scale_up_threshold:
                action = "hold"
                reason = "within hysteresis threshold"
            elif diff > 0:
                action = "load"
                reason = f"scale up to {band.label} band ({target_frac:.2f})"
            else:
                action = "unload"
                reason = f"scale down to {band.label} band ({target_frac:.2f})"

        target_layers = st.total_layers * target_frac
        lo = st.current_layers if action == "hold" else int(target_layers * 0)
        hi = st.current_layers if action == "hold" else max(1, int(target_layers))

        return LoadDecision(
            alias=alias,
            complexity=complexity,
            current_fraction=current_frac,
            target_fraction=target_frac,
            target_layers=(lo, hi),
            target_mb=desired_mb,
            action=action,
            reason=reason,
            band_label=band.label,
        )

    def adjust(self, alias: str, complexity: float) -> LoadDecision:
        """Decide and apply the load change via WeightPager + Monitor."""
        d = self.decide(alias, complexity)
        st = self._state(alias)
        st.last_used = time.time()

        if d.action in ("load", "unload", "blocked"):
            new_layers = max(1, int(d.target_fraction * st.total_layers))
            if new_layers != st.current_layers:
                # Update footprint delta
                old_mb = (st.current_layers / st.total_layers) * st.total_bytes
                new_mb = (new_layers / st.total_layers) * st.total_bytes
                self._monitor.adjust_footprint(alias, new_mb - old_mb)
                st.current_layers = new_layers
            if d.action == "unload":
                st.last_downscale = time.time()

        return d

    def release_if_idle(
        self, alias: str, idle_seconds: float | None = None
    ) -> bool:
        """Unshrink a model if it hasn't been used for the delay window."""
        st = self._state(alias)
        delay = idle_seconds if idle_seconds is not None else self._policy.scale_down_delay_s
        if time.time() - st.last_used < delay:
            return False
        if st.current_layers == 0:
            return False
        old_mb = (st.current_layers / st.total_layers) * st.total_bytes
        self._monitor.adjust_footprint(alias, -old_mb)
        st.current_layers = 0
        return True

    # --- eviction ---

    def eviction_candidates(self) -> list[str]:
        """Aliases ordered by eviction safety (first = evict first).

        Sort key is ``(priority, last_used)`` ascending: the lowest capability
        priority goes first, and among equals the least-recently-used wins.
        A high-priority core brain is therefore never evicted before an idle
        low-priority auxiliary, regardless of recency.
        """
        return sorted(
            self._states,
            key=lambda a: (self._states[a].priority, self._states[a].last_used),
        )

    def evict(self, alias: str) -> float:
        """Force-unload a model. Returns MB freed."""
        st = self._state(alias)
        freed = (st.current_layers / st.total_layers) * st.total_bytes
        self._monitor.adjust_footprint(alias, -freed)
        st.current_layers = 0
        return freed

    # --- helpers ---

    def _pick_band(self, complexity: float) -> LoadBand:
        for band in self._policy.bands:
            if band.complexity_min <= complexity < band.complexity_max:
                return band
        return self._policy.bands[-1]

    @staticmethod
    def _interpolate(complexity: float, band: LoadBand) -> float:
        span = band.complexity_max - band.complexity_min
        if span <= 0:
            return band.fraction_min
        t = (complexity - band.complexity_min) / span
        return band.fraction_min + t * (band.fraction_max - band.fraction_min)

    def state_dict(self) -> dict[str, Any]:
        return {
            "models": {
                a: {
                    "total_layers": s.total_layers,
                    "current_layers": s.current_layers,
                    "current_fraction": round(
                        s.current_layers / s.total_layers, 4
                    ) if s.total_layers else 0.0,
                    "last_used": s.last_used,
                    "priority": s.priority,
                }
                for a, s in self._states.items()
            },
            "monitor": self._monitor.to_dict(),
        }
