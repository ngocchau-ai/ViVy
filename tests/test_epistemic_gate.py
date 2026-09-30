"""Tests for EpistemicGate — V5.0 Sprint 1B.

20 tests covering:
  GROUP 1 — Unit tests for EpistemicGate.assess() (8 tests)
  GROUP 2 — Integration tests: Gate in orchestrator context (7 tests)
  GROUP 3 — Edge cases (5 tests)

Changelog:
  19/09/2026 (Antigravity IDE, Sprint 1B): Initial implementation.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from enum import StrEnum

import numpy as np
import pytest

from core.state import QuantumState
from orchestrator.epistemic_gate import (
    EpistemicDecision,
    EpistemicGate,
    GateContext,
    GateResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalized_state() -> QuantumState:
    """A normalized 1-qubit state with norm = 1.0."""
    return QuantumState(np.array([1.0, 0.0], dtype=np.complex128))


def _zero_norm_state() -> QuantumState:
    """A 1-qubit state with near-zero amplitude (not normalized)."""
    # normalize=False not supported; use a tiny value instead
    s = QuantumState(np.array([1e-300, 0.0], dtype=np.complex128), normalize=False)
    return s


class _MockState:
    """Duck-type state that returns a fixed norm value."""

    def __init__(self, norm_value: float) -> None:
        self._norm = norm_value

    def norm(self) -> float:
        return self._norm


class _BrokenState:
    """State whose .norm() raises to test exception handling."""

    def norm(self) -> float:
        raise RuntimeError("norm failed")


# ---------------------------------------------------------------------------
# GROUP 1: Unit tests for EpistemicGate.assess() — 8 tests
# ---------------------------------------------------------------------------


def test_high_confidence_no_unknowns_returns_execute_directly() -> None:
    """High confidence + no unknown entities → EXECUTE_DIRECTLY."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="test", unknown_entities=[])
    result = gate.assess(_MockState(1.0), ctx)
    assert result.decision == EpistemicDecision.EXECUTE_DIRECTLY


def test_confidence_below_threshold_returns_delegate_model() -> None:
    """Confidence below threshold + no unknowns → DELEGATE_MODEL."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="test", unknown_entities=[])
    result = gate.assess(_MockState(0.3), ctx)
    assert result.decision == EpistemicDecision.DELEGATE_MODEL


def test_unknown_entities_triggers_foraging() -> None:
    """Any unknown entity → NEED_KNOWLEDGE_FORAGING regardless of confidence."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="test", unknown_entities=["black hole"])
    # Even with high confidence, unknowns trigger foraging
    result = gate.assess(_MockState(0.9), ctx)
    assert result.decision == EpistemicDecision.NEED_KNOWLEDGE_FORAGING


def test_confidence_threshold_is_configurable() -> None:
    """Custom confidence_threshold must be respected."""
    gate = EpistemicGate(confidence_threshold=0.95)
    ctx = GateContext(task_description="test", unknown_entities=[])
    # 0.85 < 0.95 → DELEGATE_MODEL
    result = gate.assess(_MockState(0.85), ctx)
    assert result.decision == EpistemicDecision.DELEGATE_MODEL
    # 0.99 >= 0.95 → EXECUTE_DIRECTLY
    result2 = gate.assess(_MockState(0.99), ctx)
    assert result2.decision == EpistemicDecision.EXECUTE_DIRECTLY


def test_gate_result_has_rationale_string() -> None:
    """GateResult.rationale must be a non-empty string."""
    gate = EpistemicGate()
    ctx = GateContext(task_description="explain gravity")
    result = gate.assess(_MockState(1.0), ctx)
    assert isinstance(result.rationale, str)
    assert len(result.rationale) > 0


def test_gate_result_has_confidence_float_between_0_and_1() -> None:
    """GateResult.confidence must be a float in [0.0, 1.0]."""
    gate = EpistemicGate()
    ctx = GateContext(task_description="test")
    result = gate.assess(_MockState(0.8), ctx)
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0


def test_unknown_entities_list_preserved_in_foraging_result() -> None:
    """Unknown entities are preserved in the NEED_KNOWLEDGE_FORAGING result."""
    gate = EpistemicGate()
    entities = ["quark", "gluon"]
    ctx = GateContext(task_description="particle physics", unknown_entities=entities)
    result = gate.assess(_MockState(0.5), ctx)
    assert result.decision == EpistemicDecision.NEED_KNOWLEDGE_FORAGING
    assert result.unknown_entities == entities


def test_suggested_model_set_in_delegate_result() -> None:
    """DELEGATE_MODEL result must include suggested_model."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="test", unknown_entities=[])
    result = gate.assess(_MockState(0.1), ctx)
    assert result.decision == EpistemicDecision.DELEGATE_MODEL
    assert result.suggested_model is not None
    assert isinstance(result.suggested_model, str)


# ---------------------------------------------------------------------------
# GROUP 2: Integration tests — 7 tests
# ---------------------------------------------------------------------------


def test_gate_context_task_description_stored() -> None:
    """GateContext stores task_description correctly."""
    ctx = GateContext(task_description="what is 2+2?")
    assert ctx.task_description == "what is 2+2?"


def test_execute_directly_confidence_above_threshold() -> None:
    """EXECUTE_DIRECTLY result has confidence >= threshold."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="basic math", unknown_entities=[])
    result = gate.assess(_MockState(0.9), ctx)
    assert result.decision == EpistemicDecision.EXECUTE_DIRECTLY
    assert result.confidence >= gate.confidence_threshold


def test_foraging_suggested_modality_is_text() -> None:
    """NEED_KNOWLEDGE_FORAGING result suggests 'text' modality."""
    gate = EpistemicGate()
    ctx = GateContext(task_description="test", unknown_entities=["graviton"])
    result = gate.assess(_MockState(0.5), ctx)
    assert result.suggested_modality == "text"


def test_delegate_result_suggested_model_is_general() -> None:
    """DELEGATE_MODEL result suggests 'general' as the fallback model."""
    gate = EpistemicGate(confidence_threshold=0.9)
    ctx = GateContext(task_description="test", unknown_entities=[])
    result = gate.assess(_MockState(0.1), ctx)
    assert result.decision == EpistemicDecision.DELEGATE_MODEL
    assert result.suggested_model == "general"


def test_gate_runs_with_empty_task_description() -> None:
    """Gate must not raise on empty task_description."""
    gate = EpistemicGate()
    ctx = GateContext(task_description="")
    result = gate.assess(_MockState(1.0), ctx)
    assert isinstance(result, GateResult)


def test_gate_context_unknown_entities_passed_through() -> None:
    """Unknown entities from context reach the GateResult unchanged."""
    gate = EpistemicGate()
    entities = ["entity_A", "entity_B", "entity_C"]
    ctx = GateContext(task_description="complex task", unknown_entities=entities)
    result = gate.assess(_MockState(0.8), ctx)
    # All entities flow through to the result
    assert set(result.unknown_entities) == set(entities)


def test_gate_result_is_dataclass() -> None:
    """GateResult must be a proper dataclass."""
    assert is_dataclass(GateResult)


# ---------------------------------------------------------------------------
# GROUP 3: Edge cases — 5 tests
# ---------------------------------------------------------------------------


def test_confidence_clamped_to_1_even_if_norm_exceeds_1() -> None:
    """Confidence must be clamped to 1.0 even when state norm > 1."""
    gate = EpistemicGate()
    ctx = GateContext(task_description="test", unknown_entities=[])
    result = gate.assess(_MockState(9999.0), ctx)
    assert result.confidence == pytest.approx(1.0)
    assert result.decision == EpistemicDecision.EXECUTE_DIRECTLY


def test_confidence_clamped_to_0_when_norm_is_negative() -> None:
    """Confidence must be clamped to 0.0 for negative norm values."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="test", unknown_entities=[])
    result = gate.assess(_MockState(-5.0), ctx)
    assert result.confidence == pytest.approx(0.0)
    assert result.decision == EpistemicDecision.DELEGATE_MODEL


def test_epistemic_decision_values_are_strings() -> None:
    """EpistemicDecision must be a StrEnum — values compare equal to str."""
    assert EpistemicDecision.EXECUTE_DIRECTLY == "EXECUTE_DIRECTLY"
    assert EpistemicDecision.NEED_KNOWLEDGE_FORAGING == "NEED_KNOWLEDGE_FORAGING"
    assert EpistemicDecision.DELEGATE_MODEL == "DELEGATE_MODEL"
    assert issubclass(EpistemicDecision, StrEnum)


def test_gate_assess_returns_gate_result_type() -> None:
    """gate.assess() must return a GateResult instance."""
    gate = EpistemicGate()
    ctx = GateContext(task_description="type check")
    result = gate.assess(_MockState(0.5), ctx)
    assert isinstance(result, GateResult)


def test_gate_with_multiple_unknown_entities() -> None:
    """Gate handles multiple unknown entities correctly."""
    gate = EpistemicGate()
    entities = ["e1", "e2", "e3", "e4", "e5"]
    ctx = GateContext(task_description="complex", unknown_entities=entities)
    result = gate.assess(_MockState(0.95), ctx)
    # High confidence but unknowns → foraging (not execute directly)
    assert result.decision == EpistemicDecision.NEED_KNOWLEDGE_FORAGING
    assert len(result.unknown_entities) == 5


def test_broken_state_returns_zero_confidence() -> None:
    """When state.norm() raises, confidence must default to 0.0."""
    gate = EpistemicGate(confidence_threshold=0.7)
    ctx = GateContext(task_description="broken state test", unknown_entities=[])
    result = gate.assess(_BrokenState(), ctx)
    assert result.confidence == pytest.approx(0.0)
    assert result.decision == EpistemicDecision.DELEGATE_MODEL


def test_gate_with_real_quantum_state_normalized() -> None:
    """Gate works correctly with a real normalized QuantumState (norm = 1.0)."""
    gate = EpistemicGate(confidence_threshold=0.7)
    state = _normalized_state()
    ctx = GateContext(task_description="quantum test", unknown_entities=[])
    result = gate.assess(state, ctx)
    # Normalized state has norm = 1.0 → confidence = 1.0 → EXECUTE_DIRECTLY
    assert result.decision == EpistemicDecision.EXECUTE_DIRECTLY
    assert result.confidence == pytest.approx(1.0, abs=1e-10)
