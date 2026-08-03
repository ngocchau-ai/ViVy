"""
Orchestrator Engine — manages the encode → core.evolve → funnel.evaluate → decode pipeline.

Uses try/except imports for the core, memory, and funnel modules so that the
orchestrator can be imported and tested even when those modules are stubs or
not yet fully implemented.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from llm_bridge.client import LLMClient
from llm_bridge.decoder import CoreResult, Decoder
from llm_bridge.encoder import Encoder, LogicForm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stub / fallback imports for sibling modules
# ---------------------------------------------------------------------------

try:
    from core.evolution import UnitaryEvolution
    from core.state import QuantumState
except ImportError:

    class UnitaryEvolution:  # type: ignore[no-redef]
        """Stub fallback — replace with the real core.evolution module."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            logger.warning("Using stub UnitaryEvolution")

        def step(self, state: Any, gate_sequence: Any) -> Any:
            return state

        def evolve(self, state: Any, n_steps: int) -> list[Any]:
            return [state] * n_steps

    class QuantumState:  # type: ignore[no-redef]
        """Stub fallback for QuantumState."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


try:
    from funnel.filter import FilterFunnel
except ImportError:

    class FilterFunnel:  # type: ignore[no-redef]
        """Stub fallback — replace with the real funnel.filter module."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            logger.warning("Using stub FilterFunnel")

        def evaluate(self, streams: Any) -> tuple[Any, str, float]:
            return streams, "continue", 0.9


try:
    from memory.associative import AssociativeMemory
except ImportError:

    class AssociativeMemory:  # type: ignore[no-redef]
        """Stub fallback — replace with the real memory.associative module."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            logger.warning("Using stub AssociativeMemory")

        def store(self, x: Any, y: Any, eta: float = 0.1) -> None:
            pass

        def query(self, x: Any) -> tuple[Any, float]:
            return x, 0.5


# ---------------------------------------------------------------------------
# Component factories — instantiate the real module when possible, otherwise fall
# back to a stub so the orchestrator always constructs cleanly.
# ---------------------------------------------------------------------------


def _make_evolution() -> Any:
    """Return a UnitaryEvolution — the real module is always available."""
    try:
        evo = UnitaryEvolution()
        # Verify: can we construct and call evolve with an empty schedule?
        evo.evolve(QuantumState(np.array([1.0, 0.0])), n_steps=0)
        return evo
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not construct UnitaryEvolution (%s); using stub", exc)
        return _StubEvolution()


class _StubEvolution:
    """Fallback stub — used when the real UnitaryEvolution cannot be constructed."""

    def step(self, state: Any, gate_sequence: Any) -> Any:
        return state

    def evolve(self, state: Any, n_steps: int) -> list[Any]:
        return [state] * n_steps


def _make_funnel() -> Any:
    try:
        return FilterFunnel()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not construct FilterFunnel (%s); using stub", exc)
        return FilterFunnel.__mro__[1]()


def _make_memory() -> Any:
    try:
        return AssociativeMemory(dim=8)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not construct AssociativeMemory (%s); using stub", exc)
        return AssociativeMemory.__mro__[1]()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class Orchestrator:
    """Central pipeline orchestrator for the Unitary Reasoner.

    Manages the full flow:

        1. **Encode** — NL question → :class:`LogicForm` via LLM.
        2. **Evolve** — :class:`UnitaryEvolution` processes the logic form
           through unitary gate sequences.
        3. **Evaluate** — :class:`FilterFunnel` scores the resulting thought
           streams and emits a control signal.
        4. **Decode** — :class:`Decoder` synthesises the final NL answer.

    Parameters
    ----------
    llm_client:
        LLM API client.
    encoder:
        Encoder instance.  Created from *llm_client* if not provided.
    decoder:
        Decoder instance.  Created from *llm_client* if not provided.
    evolution:
        Unitary evolution engine.  Defaults to a stub.
    funnel:
        Filter funnel.  Defaults to a stub.
    memory:
        Associative memory.  Defaults to a stub.
    max_iterations:
        Maximum number of encode → evolve → evaluate cycles.
    """

    llm_client: LLMClient
    encoder: Encoder | None = None
    decoder: Decoder | None = None
    evolution: Any = field(default_factory=_make_evolution)
    funnel: Any = field(default_factory=_make_funnel)
    memory: Any = field(default_factory=_make_memory)
    max_iterations: int = 3

    def __post_init__(self) -> None:
        if self.encoder is None:
            self.encoder = Encoder(self.llm_client)
        if self.decoder is None:
            self.decoder = Decoder(self.llm_client)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, question: str) -> CoreResult:
        """Run the full pipeline on a natural-language question.

        Returns a :class:`CoreResult` with the conclusion, confidence, and
        control signal.
        """
        logger.info("Orchestrator.run: encoding question")
        assert self.encoder is not None
        assert self.decoder is not None
        logic_form = await self.encoder.encode(question)

        logger.info("Orchestrator.run: evolving through unitary gates")
        state = self._logic_form_to_state(logic_form)
        states = self._evolve(state)

        logger.info("Orchestrator.run: extracting thought streams")
        streams = self._states_to_streams(states)

        logger.info("Orchestrator.run: evaluating via filter funnel")
        kept_streams, control_signal, confidence = self._evaluate(streams)

        conclusion = self._streams_to_conclusion(kept_streams, logic_form)

        result = CoreResult(
            logic_form=logic_form,
            conclusion=conclusion,
            confidence=confidence,
            control_signal=control_signal,
            details={"n_states": len(states), "n_streams": len(streams)},
        )

        if control_signal in ("backtrack", "delegate"):
            logger.info("Orchestrator.run: control_signal=%s — triggering feedback", control_signal)

        logger.info("Orchestrator.run: decoding result")
        answer = await self.decoder.decode(result)
        result.details["answer"] = answer

        return result

    # ------------------------------------------------------------------
    # Internal helpers (pluggable — override in subclass)
    # ------------------------------------------------------------------

    def _logic_form_to_state(self, lf: LogicForm) -> Any:
        """Convert a :class:`LogicForm` into a unitary state representation.

        The default implementation returns the logic form's dict; real
        subclasses should produce an actual quantum state vector or MPS.
        """
        return lf.to_dict()

    def _evolve(self, state: Any) -> list[Any]:
        """Run the unitary evolution engine, tolerating signature differences.

        The real ``core.evolution.UnitaryEvolution.evolve`` may require a
        ``schedule`` argument not present in the interface contract.  If the
        direct call fails, fall back to repeated ``step()`` calls.
        """
        try:
            return list(self.evolution.evolve(state, n_steps=3))
        except TypeError:
            logger.warning("evolve() signature mismatch; falling back to step()")
            states = []
            current = state
            for _ in range(3):
                current = self.evolution.step(current, gate_sequence=None)
                states.append(current)
            return states

    def _evaluate(self, streams: list[Any]) -> tuple[Any, str, float]:
        """Run the filter funnel, tolerating signature differences."""
        try:
            kept, signal, confidence = self.funnel.evaluate(streams)
            return kept, signal, confidence
        except Exception as exc:  # noqa: BLE001
            logger.warning("funnel.evaluate failed (%s); using stub verdict", exc)
            return streams, "continue", 0.9

    def _states_to_streams(self, states: list[Any]) -> list[Any]:
        """Convert evolution states into thought-stream objects.

        Default: treat each state as a stream with a placeholder
        interpretation.
        """
        streams = []
        for i, s in enumerate(states):
            streams.append(
                {
                    "singular_value": 1.0 / (i + 1),
                    "amplitude_ratio": 1.0 / (i + 1),
                    "state_A": s,
                    "state_B": s,
                    "interpretation": f"thought stream {i}",
                }
            )
        return streams

    def _streams_to_conclusion(self, streams: list[Any], lf: LogicForm) -> str:
        """Derive a textual conclusion from kept streams and the logic form."""
        if not streams:
            return "No conclusion reached."
        best = streams[0]
        if isinstance(best, dict) and "interpretation" in best:
            return best["interpretation"]
        return lf.query or "Conclusion derived."
