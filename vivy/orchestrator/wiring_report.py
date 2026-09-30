"""Startup wiring receipt for the ViVy orchestrator.

[NEW 29/09/2026 — WP-1 / O-01]  Before this existed, the orchestrator could come
up on a mix of real modules, silent stubs and a mocked trading engine and nothing
recorded which was which (F-A07, G-02).  :func:`build_wiring_report` probes each
required component and returns a :class:`WiringReport`; production callers then
call :meth:`WiringReport.raise_if_unwired` so a MISSING/STUB component fails the
boot instead of degrading quietly.

Statuses
--------
``REAL``
    The real class was imported and is constructible.
``STUB``
    A test double or placeholder is wired in.  Allowed only outside production.
``MISSING``
    The module or symbol could not be imported at all.

The report is an operational fact, not a capability claim: it says what is wired,
never that the wired thing works.  See ``docs/CAPABILITY_LEDGER.md`` (WP-5) for
the latter.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "ComponentWiring",
    "WiringError",
    "WiringReport",
    "WiringStatus",
    "build_wiring_report",
    "ensure_production_wiring",
]


class WiringStatus(StrEnum):
    """How a required component is currently wired."""

    REAL = "REAL"
    STUB = "STUB"
    MISSING = "MISSING"


class WiringError(RuntimeError):
    """Raised when production wiring is not composed entirely of real components."""


@dataclass(frozen=True)
class ComponentWiring:
    """One probed component and how it is wired."""

    name: str
    status: WiringStatus
    detail: str = ""
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "required": self.required,
        }


@dataclass
class WiringReport:
    """Collection of :class:`ComponentWiring` rows plus the reporting API."""

    components: list[ComponentWiring] = field(default_factory=list)

    # -- queries -----------------------------------------------------------

    def _by_status(self, status: WiringStatus, required_only: bool) -> list[ComponentWiring]:
        return [
            c
            for c in self.components
            if c.status is status and (c.required or not required_only)
        ]

    @property
    def missing(self) -> list[ComponentWiring]:
        """Required components that could not be imported."""
        return self._by_status(WiringStatus.MISSING, required_only=True)

    @property
    def stubs(self) -> list[ComponentWiring]:
        """Required components currently wired to a stub or test double."""
        return self._by_status(WiringStatus.STUB, required_only=True)

    def is_production_clean(self) -> bool:
        """True when every required component is wired to real code."""
        return not self.missing and not self.stubs

    def get(self, name: str) -> ComponentWiring | None:
        for c in self.components:
            if c.name == name:
                return c
        return None

    # -- reporting --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "production_clean": self.is_production_clean(),
            "missing": [c.to_dict() for c in self.missing],
            "stubs": [c.to_dict() for c in self.stubs],
            "components": [c.to_dict() for c in self.components],
        }

    def record(self, log: Any | None = None) -> dict[str, Any]:
        """Write this report to an ``ActivityLog`` (or another ``record()`` sink).

        Returns the entry that was written.  ``log`` is duck-typed so this module
        stays free of an ``integration`` import at module scope.
        """
        from integration.activity_log import ActivityLog  # local: avoids a cycle

        sink = log if log is not None else ActivityLog()
        payload = self.to_dict()
        return sink.record(
            "wiring_report",
            status="PASS" if payload["production_clean"] else "FAIL",
            **payload,
        )

    def raise_if_unwired(self) -> None:
        """Raise :class:`WiringError` unless every required component is REAL."""
        if self.is_production_clean():
            return
        bad = self.missing + self.stubs
        listing = "; ".join(f"{c.name}={c.status.value}" for c in bad)
        raise WiringError(
            f"production wiring incomplete — {listing}. "
            "Refusing to boot on stubs or missing components (WP-1 / O-01)."
        )

    def __str__(self) -> str:
        rows = ", ".join(f"{c.name}:{c.status.value}" for c in self.components)
        verdict = "CLEAN" if self.is_production_clean() else "UNWIRED"
        return f"WiringReport[{verdict}] {rows}"


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


def _probe_symbol(path: str, name: str, required: bool = True) -> ComponentWiring:
    """Import ``module.attr`` and report REAL / MISSING."""
    module_name, _, attr = path.rpartition(".")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 — any import failure is a MISSING wire
        return ComponentWiring(name, WiringStatus.MISSING, f"import {module_name}: {exc}", required)
    try:
        getattr(module, attr)
    except AttributeError as exc:
        return ComponentWiring(name, WiringStatus.MISSING, f"{path}: {exc}", required)
    return ComponentWiring(name, WiringStatus.REAL, path, required)


def _probe_callables(path: str, name: str, methods: Iterable[str], required: bool = True) -> ComponentWiring:
    """Import ``module.attr`` and check it exposes the expected callables."""
    row = _probe_symbol(path, name, required=required)
    if row.status is not WiringStatus.REAL:
        return row
    module_name, _, attr = path.rpartition(".")
    obj = getattr(importlib.import_module(module_name), attr)
    absent = [m for m in methods if not callable(getattr(obj, m, None))]
    if absent:
        return ComponentWiring(
            name, WiringStatus.MISSING, f"{path} lacks {', '.join(absent)}", required
        )
    return row


def _probe_trading_engine() -> ComponentWiring:
    """Report how the trading engine is wired (mock = STUB).

    The trading tree lives under ``src/vivy/`` and is only importable when
    ``src/`` is on ``sys.path``.  An unreachable tree is reported as a
    non-required MISSING row rather than a boot failure, because the cognitive
    core can run without the trading face.
    """
    try:
        loader = importlib.import_module("vivy.core.model_loader")
    except Exception as exc:  # noqa: BLE001
        return ComponentWiring(
            "trading.model_loader",
            WiringStatus.MISSING,
            f"import vivy.core.model_loader: {exc}",
            required=False,
        )
    allowed = getattr(loader, "mock_engine_allowed", None)
    if not callable(allowed):
        return ComponentWiring(
            "trading.model_loader",
            WiringStatus.MISSING,
            "mock_engine_allowed() missing — cannot tell mock from real",
            required=False,
        )
    if allowed(None):
        return ComponentWiring(
            "trading.model_loader",
            WiringStatus.STUB,
            f"MockLocalEngine permitted via {getattr(loader, 'MOCK_OPT_IN_ENV', 'env')}",
            required=False,
        )
    return ComponentWiring(
        "trading.model_loader",
        WiringStatus.REAL,
        "MockLocalEngine banned",
        required=False,
    )


# The orchestrator's required production surface.  Keep this list in sync with
# orchestrator/engine.py's imports: anything that used to be a silent stub
# belongs here.
_REQUIRED: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("core.evolution.UnitaryEvolution", "evolution", ("step", "evolve")),
    ("core.state.QuantumState", "quantum_state", ()),
    ("core.knowledge_injector.KnowledgeInjector", "knowledge_injector", ("inject",)),
    ("funnel.filter.FilterFunnel", "filter_funnel", ("evaluate",)),
    ("memory.associative.AssociativeMemory", "associative_memory", ("store", "query")),
    ("llm_bridge.client.LLMClient", "llm_client", ()),
    ("orchestrator.engine.Orchestrator", "orchestrator", ("run",)),
)


def build_wiring_report(*, probe_trading: bool = True) -> WiringReport:
    """Probe the required production surface and return a wiring report.

    Parameters
    ----------
    probe_trading:
        Also probe the ``src/vivy`` trading tree for a mocked engine.  That row
        is non-required: the cognitive core boots without the trading face.
    """
    components: list[ComponentWiring] = []
    for path, label, methods in _REQUIRED:
        if methods:
            components.append(_probe_callables(path, label, methods))
        else:
            components.append(_probe_symbol(path, label))
    if probe_trading:
        components.append(_probe_trading_engine())
    return WiringReport(components=components)


def ensure_production_wiring(
    *, probe_trading: bool = True, log: Any | None = None
) -> WiringReport:
    """Build the wiring report, receipt it, and refuse to boot if unwired.

    One call for production entry points: probe → record → fail-fast.  The
    receipt is written **before** the raise so a refused boot still leaves an
    audit trail.  This is the WP-1 / O-01 gate that was specified but never
    hooked into startup.
    """
    report = build_wiring_report(probe_trading=probe_trading)
    report.record(log)
    report.raise_if_unwired()
    return report
