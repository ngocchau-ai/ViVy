"""EpistemicGate — blocking assessment gate for ViVy V5.0.

Architecture:
    encode → evolve → [EPISTEMIC GATE] → evaluate → decode
                              ↑
                        This is the gate.

The gate emits one of three decisions:
    EXECUTE_DIRECTLY:         high confidence, no unknowns — proceed immediately
    NEED_KNOWLEDGE_FORAGING:  unknown entities detected — acquire knowledge first
    DELEGATE_MODEL:           low confidence, no foraging path — route to specialist

V5.0 Changelog:
    - 19/09/2026 (Antigravity IDE, Sprint 1A): Initial implementation.
      Replaces parallel FilterFunnel execution with a blocking gate call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EpistemicDecision(StrEnum):
    """Three-way routing decision emitted by EpistemicGate.assess()."""

    EXECUTE_DIRECTLY = "EXECUTE_DIRECTLY"
    NEED_KNOWLEDGE_FORAGING = "NEED_KNOWLEDGE_FORAGING"
    DELEGATE_MODEL = "DELEGATE_MODEL"


@dataclass
class GateContext:
    """Context supplied to the gate alongside the evolved quantum state.

    Parameters
    ----------
    task_description:
        One-line natural-language description of the current task.
    confidence_threshold:
        Minimum confidence score to allow EXECUTE_DIRECTLY.  Defaults to 0.7.
    unknown_entities:
        List of entity names ViVy cannot resolve from its current knowledge.
        Populated by the encoder in V5.0; empty list means full knowledge coverage.
    metadata:
        Optional extra key-value context for downstream handlers.
    """

    task_description: str
    confidence_threshold: float = 0.7
    unknown_entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateResult:
    """Result returned by EpistemicGate.assess().

    Parameters
    ----------
    decision:
        The routing decision.
    confidence:
        Confidence score derived from the quantum state, in [0.0, 1.0].
    unknown_entities:
        Entities that triggered NEED_KNOWLEDGE_FORAGING (empty otherwise).
    rationale:
        Human-readable explanation of why this decision was made.
    suggested_modality:
        For NEED_KNOWLEDGE_FORAGING: preferred knowledge modality (e.g. "text").
    suggested_model:
        For DELEGATE_MODEL: preferred specialist model name (e.g. "general").
    """

    decision: EpistemicDecision
    confidence: float
    unknown_entities: list[str]
    rationale: str
    suggested_modality: str | None = None
    suggested_model: str | None = None


class EpistemicGate:
    """Blocking epistemic assessment gate.

    Usage (in orchestrator pipeline)::

        state = evolve(encoded)
        gate = EpistemicGate(confidence_threshold=0.7)
        ctx = GateContext(task_description=question, unknown_entities=[])
        result = gate.assess(state, ctx)

        if result.decision == EpistemicDecision.EXECUTE_DIRECTLY:
            pass  # proceed to evaluate/decode
        elif result.decision == EpistemicDecision.NEED_KNOWLEDGE_FORAGING:
            pass  # Sprint 2: trigger foraging loop
        elif result.decision == EpistemicDecision.DELEGATE_MODEL:
            pass  # Sprint 2: route to model_router
    """

    def __init__(self, confidence_threshold: float = 0.7) -> None:
        self.confidence_threshold = confidence_threshold

    def assess(self, state: Any, context: GateContext) -> GateResult:
        """Assess epistemic readiness and emit a routing decision.

        This is the BLOCKING step that replaces parallel funnel execution.
        Must be called between evolve() and evaluate() in the orchestrator.

        Parameters
        ----------
        state:
            The evolved quantum state (QuantumState or compatible duck-type).
            Any object with a callable .norm() -> float method is accepted.
        context:
            GateContext containing task description and unknown entities.

        Returns
        -------
        GateResult
            Routing decision with confidence score and rationale.
        """
        confidence = self._compute_confidence(state)
        unknown_entities = self._detect_unknown_entities(state, context)

        if confidence >= self.confidence_threshold and not unknown_entities:
            return GateResult(
                decision=EpistemicDecision.EXECUTE_DIRECTLY,
                confidence=confidence,
                unknown_entities=[],
                rationale=(
                    f"Confidence {confidence:.2f} >= threshold "
                    f"{self.confidence_threshold:.2f}, no unknown entities."
                ),
            )

        if unknown_entities:
            return GateResult(
                decision=EpistemicDecision.NEED_KNOWLEDGE_FORAGING,
                confidence=confidence,
                unknown_entities=unknown_entities,
                rationale=f"Unknown entities detected: {unknown_entities}",
                suggested_modality="text",
            )

        return GateResult(
            decision=EpistemicDecision.DELEGATE_MODEL,
            confidence=confidence,
            unknown_entities=[],
            rationale=(
                f"Confidence {confidence:.2f} below threshold "
                f"{self.confidence_threshold:.2f}, no foraging target."
            ),
            suggested_model="general",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_confidence(self, state: Any) -> float:
        """Derive a confidence score from the state's L2 norm.

        A normalized QuantumState has norm ≈ 1.0, so confidence ≈ 1.0.
        Unnormalized or degraded states yield confidence < 1.0.
        Result is clamped to [0.0, 1.0].
        """
        try:
            norm = float(state.norm())
            return min(1.0, max(0.0, norm))
        except Exception:  # noqa: BLE001
            return 0.0

    def _detect_unknown_entities(
        self, state: Any, context: GateContext
    ) -> list[str]:
        """Return the list of unknown entities from context.

        In V5.0, the encoder populates context.unknown_entities before calling
        the gate.  This method is a clean extension point for future heuristics.
        """
        return list(context.unknown_entities)
