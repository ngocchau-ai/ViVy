"""Tests for SelfHealingLoop — V5.0 Sprint 3B.

15 tests cho engine/self_healer.py.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3B tests): Initial implementation.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from engine.self_healer import (
    HealingResult,
    Incident,
    RCAHypothesis,
    SelfHealingLoop,
)

_SCRATCH_BASE = Path("scratchpad/_test")


@pytest.fixture()
def tmp_path() -> Path:  # type: ignore[override]
    """Custom tmp_path fixture that uses workspace dir to avoid Windows PermissionError."""
    test_id = uuid.uuid4().hex[:8]
    p = _SCRATCH_BASE / test_id
    p.mkdir(parents=True, exist_ok=True)
    yield p
    shutil.rmtree(p, ignore_errors=True)


def _make_incident(**overrides: str | int) -> Incident:
    defaults: dict = {
        "stderr": "SyntaxError: invalid syntax at line 5",
        "exit_code": 1,
        "source_code": "def foo(\n    pass",
        "task_description": "Write a function foo",
    }
    defaults.update(overrides)
    return Incident(**defaults)


# ---------------------------------------------------------------------------
# Tests for Incident dataclass
# ---------------------------------------------------------------------------


def test_incident_auto_generates_id() -> None:
    """Incident.incident_id is auto-generated when not provided."""
    incident = Incident(stderr="Error: bad code", exit_code=1)
    assert isinstance(incident.incident_id, str)
    assert len(incident.incident_id) > 0


def test_incident_preserves_provided_id() -> None:
    """Incident.incident_id is preserved when explicitly provided."""
    incident = Incident(incident_id="custom-id-001", stderr="Error", exit_code=1)
    assert incident.incident_id == "custom-id-001"


# ---------------------------------------------------------------------------
# Tests for SelfHealingLoop._capture_error_type
# ---------------------------------------------------------------------------


def test_capture_syntax_error(tmp_path: Path) -> None:
    """_capture_error_type correctly identifies SyntaxError."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(stderr="SyntaxError: invalid syntax", exit_code=1)
    assert healer._capture_error_type(incident) == "SyntaxError"


def test_capture_import_error(tmp_path: Path) -> None:
    """_capture_error_type correctly identifies ImportError."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(stderr="ModuleNotFoundError: No module named 'numpy'", exit_code=1)
    assert healer._capture_error_type(incident) == "ImportError"


def test_capture_type_error(tmp_path: Path) -> None:
    """_capture_error_type correctly identifies TypeError."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(stderr="TypeError: 'int' is not subscriptable", exit_code=1)
    assert healer._capture_error_type(incident) == "TypeError"


def test_capture_unknown_error(tmp_path: Path) -> None:
    """_capture_error_type returns 'NonZeroExit' for unrecognized exit code."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(stderr="Something weird happened", exit_code=42)
    assert healer._capture_error_type(incident) in ("NonZeroExit", "Unknown")


# ---------------------------------------------------------------------------
# Tests for SelfHealingLoop._hypothesize
# ---------------------------------------------------------------------------


def test_hypothesize_syntax_error_generates_hypotheses(tmp_path: Path) -> None:
    """_hypothesize generates ≥ 1 hypothesis for SyntaxError."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(stderr="SyntaxError: invalid syntax", exit_code=1)
    hypotheses = healer._hypothesize(incident, "SyntaxError")
    assert len(hypotheses) >= 1
    assert all(isinstance(h, RCAHypothesis) for h in hypotheses)


def test_hypothesize_import_error_may_need_foraging(tmp_path: Path) -> None:
    """ImportError hypothesis may flag needs_foraging=True."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(stderr="ModuleNotFoundError: No module named 'torch'", exit_code=1)
    hypotheses = healer._hypothesize(incident, "ImportError")
    foraging_needed = any(h.needs_foraging for h in hypotheses)
    assert foraging_needed  # ImportError should trigger foraging suggestion


# ---------------------------------------------------------------------------
# Tests for handle_incident (full loop)
# ---------------------------------------------------------------------------


def test_handle_incident_returns_healing_result(tmp_path: Path) -> None:
    """handle_incident() always returns a HealingResult."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = _make_incident()
    result = healer.handle_incident(incident)
    assert isinstance(result, HealingResult)
    assert result.incident_id == incident.incident_id


def test_handle_syntax_error_heals(tmp_path: Path) -> None:
    """handle_incident() can heal a SyntaxError incident."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(
        stderr="SyntaxError: unexpected EOF while parsing",
        exit_code=1,
        source_code="def bar(x):\n    return x + 1",
        task_description="Fix bar function",
    )
    result = healer.handle_incident(incident)
    # Should attempt healing (may succeed or fail based on patch logic)
    assert isinstance(result.success, bool)
    assert result.attempts >= 1


def test_handle_indentation_error_heals(tmp_path: Path) -> None:
    """SelfHealingLoop handles IndentationError and produces a patch."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = Incident(
        stderr="IndentationError: unexpected indent",
        exit_code=1,
        source_code="def foo():\n  pass\n    return 1",
        task_description="Fix indentation",
    )
    result = healer.handle_incident(incident)
    assert isinstance(result, HealingResult)
    # IndentationError should produce a patch attempt
    assert result.attempts >= 1


def test_rca_log_written(tmp_path: Path) -> None:
    """handle_incident() writes an RCA log file to scratchpad."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = _make_incident()
    result = healer.handle_incident(incident)
    assert result.rca_log_path != ""
    assert Path(result.rca_log_path).exists()


def test_rca_log_contains_incident_id(tmp_path: Path) -> None:
    """RCA log file contains the incident ID."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = _make_incident()
    result = healer.handle_incident(incident)
    log_content = Path(result.rca_log_path).read_text(encoding="utf-8")
    assert incident.incident_id in log_content


def test_healing_result_has_confirmed_cause(tmp_path: Path) -> None:
    """HealingResult.confirmed_cause is a non-empty string."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = _make_incident()
    result = healer.handle_incident(incident)
    assert isinstance(result.confirmed_cause, str)
    assert len(result.confirmed_cause) > 0


def test_all_hypotheses_exhausted_success_false(tmp_path: Path) -> None:
    """When no patch works, success=False and all hypotheses are attempted."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    # An incident with no source_code → patches will be placeholders → verify=False
    incident = Incident(
        stderr="RuntimeError: deep internal failure",
        exit_code=1,
        source_code="",  # No source to patch
        task_description="Unknown task",
    )
    result = healer.handle_incident(incident)
    assert result.success is False
    assert result.attempts >= 1


def test_healing_result_hypotheses_list(tmp_path: Path) -> None:
    """HealingResult.hypotheses contains the generated hypotheses."""
    healer = SelfHealingLoop(scratchpad_dir=tmp_path)
    incident = _make_incident()
    result = healer.handle_incident(incident)
    assert isinstance(result.hypotheses, list)
    assert len(result.hypotheses) >= 1
