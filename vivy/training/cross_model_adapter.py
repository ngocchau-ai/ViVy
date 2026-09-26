"""Cross-Model Adapter — Output-level composition across model cores (TD-5).

Vivy routes tasks to model cores and combines their outputs at the
orchestration layer. Weights are NEVER shared between models. Instead:
  * `route()` picks which model handles which task + returns load plan
  * `prepare_task()` routes + applies adaptive load via LoadGovernor
  * `combine_outputs()` merges outputs at the text/logit level
  * `callback_weights()` retrieves weight slices from a retired/old model
    for special-case inheritance (via WeightPager)

This is the "ghép nối" (coupling) strategy: Vivy gains intelligence by
using model cores through orchestration, not by copying their weights.

AWL integration: when a LoadGovernor is attached, `route()` computes the
adaptive load decision alongside the routing decision. `prepare_task()`
applies it so the model is paged in before inference.

Structure:
    CrossModelAdapter
    ├── couple(primary_alias, secondary_alias) — register a pairing
    ├── route(task, context) -> RouteResult   — pick model + load plan
    ├── prepare_task(task, context) -> RouteResult  — route + apply load
    ├── combine_outputs(primary_out, secondary_out) -> final_out
    └── callback_weights(old_alias, task) -> WeightSlice | None

    Coupling (dataclass)
    ├── primary, secondary: model aliases
    ├── task_tags: which tasks this coupling serves
    └── blend_ratio: float (0=primary only, 1=secondary only)

Changelog:
    25/09/2026 (Claude Code — Wave 2B): Initial.
    25/09/2026 (Claude Code — AWL-3): route() returns load plan;
        prepare_task() applies adaptive load; callback_weights budget-aware.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from training.weight_pager import WeightPager, WeightSlice

if TYPE_CHECKING:
    from training.load_governor import LoadDecision, LoadGovernor


@dataclass
class Coupling:
    """A pairing between two model cores for output composition."""

    primary: str
    secondary: str
    task_tags: tuple[str, ...] = ()
    blend_ratio: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_task(self, task: str) -> bool:
        return task in self.task_tags or not self.task_tags

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "task_tags": list(self.task_tags),
            "blend_ratio": self.blend_ratio,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RouteResult:
    """Result of routing a task to a model alias.

    When a LoadGovernor is attached, ``load_decision`` carries the adaptive
    load plan (target layers / fraction / action) for the chosen model.
    """

    model_alias: str
    reason: str
    confidence: float
    load_decision: LoadDecision | None = None


class CrossModelAdapter:
    """Orchestrates multi-model routing and output composition.

    Couples model cores together, routes tasks to the best-suited model,
    and combines their outputs at the orchestration level. Optionally uses
    WeightPager to callback weight slices from older model cores when a
    task requires specialized knowledge (weight inheritance without sharing).
    """

    def __init__(
        self,
        weight_pager: WeightPager | None = None,
        *,
        governor: LoadGovernor | None = None,
    ) -> None:
        self._pager = weight_pager or WeightPager()
        self._governor = governor
        self._couplings: list[Coupling] = []
        self._routing_rules: dict[str, str] = {}  # task_tag -> preferred alias
        self._fallback_alias: str = ""

    @property
    def coupling_count(self) -> int:
        return len(self._couplings)

    @property
    def governor(self) -> LoadGovernor | None:
        return self._governor

    def attach_governor(self, governor: LoadGovernor) -> None:
        """Attach (or replace) the LoadGovernor for adaptive loading."""
        self._governor = governor

    def couple(
        self,
        primary_alias: str,
        secondary_alias: str,
        *,
        task_tags: tuple[str, ...] = (),
        blend_ratio: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Coupling:
        """Register a coupling between two model cores.

        Raises ValueError if primary == secondary or blend_ratio out of [0, 1].
        """
        if primary_alias == secondary_alias:
            raise ValueError("primary and secondary must differ")
        if not 0.0 <= blend_ratio <= 1.0:
            raise ValueError(f"blend_ratio must be in [0, 1], got {blend_ratio}")
        c = Coupling(
            primary=primary_alias,
            secondary=secondary_alias,
            task_tags=task_tags,
            blend_ratio=blend_ratio,
            metadata=dict(metadata or {}),
        )
        self._couplings.append(c)
        return c

    def set_route(self, task_tag: str, model_alias: str) -> None:
        """Set preferred model for a task tag (overrides coupling heuristics)."""
        self._routing_rules[task_tag] = model_alias

    def set_fallback(self, model_alias: str) -> None:
        """Set the default model when no routing rule or coupling matches."""
        self._fallback_alias = model_alias

    def route(self, task: str, context: dict[str, Any] | None = None) -> RouteResult:
        """Route a task to the best model alias.

        Priority: explicit routing rule > coupling match > fallback.
        When a LoadGovernor is attached, computes the adaptive load plan
        for the chosen model based on ``context["complexity"]`` (default 0.5).

        Raises ValueError if no route is available.
        """
        ctx = dict(context or {})
        result = self._resolve(task, ctx)
        return self._with_load_plan(result, ctx)

    def prepare_task(self, task: str, context: dict[str, Any] | None = None) -> RouteResult:
        """Route + apply adaptive load in one call.

        Returns the RouteResult with load_decision attached and applied
        via LoadGovernor.adjust(). If no governor is attached, equivalent
        to ``route()``.
        """
        ctx = dict(context or {})
        result = self._resolve(task, ctx)
        result = self._with_load_plan(result, ctx, apply=True)
        return result

    def _resolve(self, task: str, ctx: dict[str, Any]) -> RouteResult:
        """Core routing logic (no load computation)."""
        # 1. Explicit rule wins.
        if task in self._routing_rules:
            return RouteResult(
                model_alias=self._routing_rules[task],
                reason=f"explicit_rule:{task}",
                confidence=0.95,
            )

        # 2. Coupling match: pick primary for primary-biased tasks, secondary otherwise.
        for c in self._couplings:
            if c.matches_task(task):
                complexity = float(ctx.get("complexity", 0.5))
                if complexity > c.blend_ratio:
                    alias = c.secondary
                    reason = f"coupling:{c.secondary}(complexity={complexity:.2f})"
                else:
                    alias = c.primary
                    reason = f"coupling:{c.primary}(complexity={complexity:.2f})"
                return RouteResult(
                    model_alias=alias,
                    reason=reason,
                    confidence=0.75,
                )

        # 3. Fallback.
        if self._fallback_alias:
            return RouteResult(
                model_alias=self._fallback_alias,
                reason="fallback",
                confidence=0.5,
            )

        raise ValueError(f"no route available for task: {task}")

    def _with_load_plan(
        self,
        result: RouteResult,
        ctx: dict[str, Any],
        *,
        apply: bool = False,
    ) -> RouteResult:
        """Attach (and optionally apply) the adaptive load decision."""
        if self._governor is None:
            return result
        alias = result.model_alias
        try:
            self._governor._state(alias)
        except KeyError:
            return result  # model not registered with governor

        complexity = float(ctx.get("complexity", 0.5))
        if apply:
            decision = self._governor.adjust(alias, complexity)
        else:
            decision = self._governor.decide(alias, complexity)

        return RouteResult(
            model_alias=result.model_alias,
            reason=result.reason,
            confidence=result.confidence,
            load_decision=decision,
        )

    def combine_outputs(
        self,
        primary_out: str,
        secondary_out: str,
        *,
        blend_ratio: float = 0.5,
        separator: str = "\n",
    ) -> str:
        """Combine outputs from two model cores at the text level.

        blend_ratio=0.0 -> primary only
        blend_ratio=1.0 -> secondary only
        blend_ratio=0.5 -> interleaved (primary then secondary)

        This is output-level composition (TD-5: không share weights).
        """
        if not 0.0 <= blend_ratio <= 1.0:
            raise ValueError(f"blend_ratio must be in [0, 1], got {blend_ratio}")

        if blend_ratio <= 0.0:
            return primary_out
        if blend_ratio >= 1.0:
            return secondary_out

        # Soft blend: truncate primary by (1-blend), secondary by blend.
        p_len = max(1, int(len(primary_out) * (1.0 - blend_ratio)))
        s_len = max(1, int(len(secondary_out) * blend_ratio))
        return primary_out[:p_len] + separator + secondary_out[:s_len]

    def callback_weights(
        self, old_alias: str, task: str
    ) -> WeightSlice | None:
        """Retrieve weight slices from an older/retired model for inheritance.

        Returns None if the alias is not registered in the WeightPager.
        This implements TD-5's weight inheritance: when Vivy migrates to a
        larger model core, it can still call back valuable weights from the
        old core for special-case tasks.

        Default: first 25% of layers (specialized head). When a LoadGovernor
        is attached and registered for this alias, the layer count is clamped
        to the budget-aware decision instead of a hard 25%.
        """
        reg = self._pager.get_registration(old_alias)
        if reg is None:
            return None

        total = reg.total_layers if reg.total_layers > 0 else 16
        end = max(1, total // 4)

        # Budget-aware clamp via governor.
        if self._governor is not None:
            try:
                self._governor._state(old_alias)
                d = self._governor.decide(old_alias, 0.5)
                end = max(1, int(d.target_layers[1]))
                end = min(end, total)
            except KeyError:
                pass

        return self._pager.load_partial(old_alias, (0, end))

    def coupling_for_task(self, task: str) -> Coupling | None:
        """Find the first coupling that handles this task."""
        for c in self._couplings:
            if c.matches_task(task):
                return c
        return None

    def list_couplings(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._couplings]
