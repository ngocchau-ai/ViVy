"""Regression tests for WP-1 / O-01 — fail-fast wiring, no silent stubs.

These pin the behaviour that F-A07 documented as broken:

* ``orchestrator.engine`` must import the real siblings directly, not shadow
  them with ``except ImportError -> stub`` classes.
* component factories must return real components, never ``object()`` via
  ``SomeClass.__mro__[1]()`` (an ADR-005 violation).
* ``Orchestrator._evaluate`` must propagate a funnel failure instead of
  fabricating ``("continue", 0.9)``.
* ``orchestrator.wiring_report`` must receipt what is wired and refuse to
  declare production clean while a stub or missing component is present.
"""

from __future__ import annotations

import pytest

from core.evolution import UnitaryEvolution as RealEvolution
from core.knowledge_injector import KnowledgeInjector as RealKnowledge
from funnel.filter import FilterFunnel as RealFunnel
from memory.associative import AssociativeMemory as RealMemory
from orchestrator.engine import (
    Orchestrator,
    _make_evolution,
    _make_funnel,
    _make_knowledge,
    _make_memory,
)
from orchestrator.wiring_report import (
    ComponentWiring,
    WiringError,
    WiringReport,
    WiringStatus,
    build_wiring_report,
)

# ---------------------------------------------------------------------------
# 1. engine.py binds the real siblings, not stub shadows
# ---------------------------------------------------------------------------


def test_engine_binds_real_sibling_modules() -> None:
    """The names used by engine.py must be the real classes, not fallbacks."""
    import orchestrator.engine as engine

    assert engine.UnitaryEvolution is RealEvolution
    assert engine.KnowledgeInjector is RealKnowledge
    assert engine.FilterFunnel is RealFunnel
    assert engine.AssociativeMemory is RealMemory


def test_engine_defines_no_stub_shadow_classes() -> None:
    """No ``_StubEvolution`` / fallback classes may remain in orchestrator.engine."""
    import orchestrator.engine as engine

    for banned in ("_StubEvolution",):
        assert not hasattr(engine, banned), f"{banned} must not exist in engine.py"


# ---------------------------------------------------------------------------
# 2. factories construct real components
# ---------------------------------------------------------------------------


def test_factories_return_real_types() -> None:
    assert isinstance(_make_evolution(), RealEvolution)
    assert isinstance(_make_funnel(), RealFunnel)
    assert isinstance(_make_memory(), RealMemory)
    assert isinstance(_make_knowledge(), RealKnowledge)


def test_factories_are_not_object_mro_hack() -> None:
    """A factory must never hand back a bare ``object()``.

    The pre-fix code did ``FilterFunnel.__mro__[1]()`` on the error path, which
    builds ``object()`` — a silent, typeless stand-in.
    """
    for factory in (_make_evolution, _make_funnel, _make_memory, _make_knowledge):
        built = factory()
        assert type(built) is not object, f"{factory.__name__} returned bare object()"


# ---------------------------------------------------------------------------
# 3. funnel failures propagate instead of becoming confident continues
# ---------------------------------------------------------------------------


class _ExplodingFunnel:
    def evaluate(self, streams):
        raise RuntimeError("funnel exploded")


@pytest.mark.asyncio
async def test_evaluate_does_not_fabricate_confident_continue() -> None:
    """A failed funnel evaluation must surface, not become ``('continue', 0.9)``."""

    class _Client:
        async def chat(self, *args, **kwargs):
            return '{"propositions": ["P"], "relations": [], "query": "Q?"}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    orch = Orchestrator(_Client())  # type: ignore[arg-type]
    orch.funnel = _ExplodingFunnel()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="funnel exploded"):
        orch._evaluate([{"singular_value": 1.0}])


# ---------------------------------------------------------------------------
# 4. wiring report
# ---------------------------------------------------------------------------


def test_build_wiring_report_marks_required_components_real() -> None:
    report = build_wiring_report(probe_trading=False)
    assert report.missing == [], f"unexpected MISSING: {report.missing}"
    assert report.stubs == [], f"unexpected STUB: {report.stubs}"
    assert report.is_production_clean()


def test_wiring_report_covers_every_required_sibling() -> None:
    report = build_wiring_report(probe_trading=False)
    names = {c.name for c in report.components}
    assert {
        "evolution",
        "knowledge_injector",
        "filter_funnel",
        "associative_memory",
        "llm_client",
        "orchestrator",
    } <= names


def test_raise_if_unwired_passes_when_clean() -> None:
    report = WiringReport(
        components=[ComponentWiring("x", WiringStatus.REAL, "ok", required=True)]
    )
    report.raise_if_unwired()  # must not raise


def test_raise_if_unwired_rejects_missing() -> None:
    report = WiringReport(
        components=[
            ComponentWiring("good", WiringStatus.REAL, required=True),
            ComponentWiring("bad", WiringStatus.MISSING, "nope", required=True),
        ]
    )
    with pytest.raises(WiringError, match="bad=MISSING"):
        report.raise_if_unwired()


def test_raise_if_unwired_rejects_stubs() -> None:
    report = WiringReport(
        components=[
            ComponentWiring("good", WiringStatus.REAL, required=True),
            ComponentWiring("mock", WiringStatus.STUB, "test double", required=True),
        ]
    )
    with pytest.raises(WiringError, match="mock=STUB"):
        report.raise_if_unwired()


def test_optional_stub_does_not_block_production() -> None:
    """A non-required STUB (e.g. the trading mock) is reported, not fatal."""
    report = WiringReport(
        components=[
            ComponentWiring("good", WiringStatus.REAL, required=True),
            ComponentWiring("trading", WiringStatus.STUB, "mock allowed", required=False),
        ]
    )
    report.raise_if_unwired()  # must not raise
    assert report.to_dict()["stubs"] == []
    stub_rows = [c for c in report.components if c.status is WiringStatus.STUB]
    assert [c.name for c in stub_rows] == ["trading"]


def test_report_serialises_and_is_receipt_shaped() -> None:
    payload = build_wiring_report(probe_trading=False).to_dict()
    assert set(payload) == {"production_clean", "missing", "stubs", "components"}
    assert payload["production_clean"] is True
    for row in payload["components"]:
        assert set(row) == {"name", "status", "detail", "required"}
        assert row["status"] in {s.value for s in WiringStatus}


# ---------------------------------------------------------------------------
# 5. production startup gate — the report must actually run at boot
#    (WP-1 close-out: the module existed but nothing called it)
# ---------------------------------------------------------------------------


def test_ensure_production_wiring_returns_clean_report() -> None:
    """``ensure_production_wiring`` builds + records + fail-fasts in one call."""
    from orchestrator.wiring_report import ensure_production_wiring

    report = ensure_production_wiring(probe_trading=False)
    assert report.is_production_clean()


def test_ensure_production_wiring_raises_on_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boot must refuse when a required component is a STUB."""
    import orchestrator.wiring_report as wr

    stub_report = wr.WiringReport(
        components=[
            wr.ComponentWiring("good", wr.WiringStatus.REAL, required=True),
            wr.ComponentWiring("mock", wr.WiringStatus.STUB, "test double", required=True),
        ]
    )
    monkeypatch.setattr(wr, "build_wiring_report", lambda **kw: stub_report)
    with pytest.raises(WiringError, match="mock=STUB"):
        wr.ensure_production_wiring(probe_trading=False)


def test_ensure_production_wiring_raises_on_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boot must refuse when a required component cannot be imported."""
    import orchestrator.wiring_report as wr

    missing_report = wr.WiringReport(
        components=[
            wr.ComponentWiring("good", wr.WiringStatus.REAL, required=True),
            wr.ComponentWiring("gone", wr.WiringStatus.MISSING, "nope", required=True),
        ]
    )
    monkeypatch.setattr(wr, "build_wiring_report", lambda **kw: missing_report)
    with pytest.raises(WiringError, match="gone=MISSING"):
        wr.ensure_production_wiring(probe_trading=False)


def test_ensure_production_wiring_records_to_activity_log() -> None:
    """The startup receipt lands in ActivityLog, not only on stdout."""
    from orchestrator.wiring_report import ensure_production_wiring

    class _Sink:
        def __init__(self) -> None:
            self.entries: list[dict] = []

        def record(self, event: str, **fields: object) -> dict:
            entry = {"event": event, **fields}
            self.entries.append(entry)
            return entry

    sink = _Sink()
    ensure_production_wiring(probe_trading=False, log=sink)
    assert len(sink.entries) == 1
    assert sink.entries[0]["event"] == "wiring_report"
    assert sink.entries[0]["status"] == "PASS"
    assert sink.entries[0]["production_clean"] is True


def test_ensure_production_wiring_records_fail_status_then_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even on refusal the receipt is written — audit trail before the crash."""
    import orchestrator.wiring_report as wr

    bad_report = wr.WiringReport(
        components=[wr.ComponentWiring("mock", wr.WiringStatus.STUB, "x", required=True)]
    )
    monkeypatch.setattr(wr, "build_wiring_report", lambda **kw: bad_report)

    class _Sink:
        def __init__(self) -> None:
            self.entries: list[dict] = []

        def record(self, event: str, **fields: object) -> dict:
            entry = {"event": event, **fields}
            self.entries.append(entry)
            return entry

    sink = _Sink()
    with pytest.raises(WiringError):
        wr.ensure_production_wiring(probe_trading=False, log=sink)
    assert sink.entries[0]["status"] == "FAIL"


def test_run_vivy_main_gates_startup_on_wiring_report(monkeypatch: pytest.MonkeyPatch) -> None:
    """``run_vivy.main()`` must run the wiring gate before serving traffic."""
    import importlib

    rv = importlib.import_module("scripts.run_vivy")

    calls: list[str] = []

    monkeypatch.setattr(
        rv,
        "ensure_production_wiring",
        lambda **kw: calls.append("wiring") or build_wiring_report(probe_trading=False),
    )

    class _FakeBridge:
        def __init__(self) -> None:
            self.config = type("C", (), {"base_url": "http://test"})()

        def health(self) -> bool:
            calls.append("health")
            return False  # stop before VivyInferenceLoop

        def list_models(self) -> list[str]:
            return []

    monkeypatch.setattr(rv, "LlamaCppBridge", _FakeBridge)

    def _fake_exit(code: int = 0) -> None:
        calls.append(f"exit:{code}")
        raise SystemExit(code)

    monkeypatch.setattr(rv.sys, "exit", _fake_exit)

    monkeypatch.setattr(
        "sys.argv", ["run_vivy.py", "--mode", "chat"]
    )
    with pytest.raises(SystemExit):
        rv.main()

    assert "wiring" in calls, (
        "run_vivy.main() never called ensure_production_wiring — "
        "production can boot on stubs (WP-1 / O-01 gap)"
    )
    assert calls.index("wiring") < calls.index("health"), (
        "wiring gate must run BEFORE the bridge health check"
    )
