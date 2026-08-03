"""Unitary evolution engine for the Unitary Reasoner.

Provides the UnitaryEvolution class which applies sequences of unitary gates to
a quantum state, with support for gate scheduling.  Also provides the
GateSchedule helper for describing ordered gate applications.

Classes
-------
GateSchedule
    Describes an ordered list of gate applications.
UnitaryEvolution
    Applies gate sequences step-by-step and over multiple evolution steps.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from .gates import apply_gate_to_state
from .mps import MPS
from .state import QuantumState

# Type alias for a gate application: (gate_matrix, qubit_indices)
GateApplication = tuple[NDArray[np.complex128], Sequence[int]]


@dataclass
class GateSchedule:
    """An ordered list of gate applications forming one evolution step.

    Parameters
    ----------
    gates : List[GateApplication]
        List of (gate_matrix, qubit_indices) tuples applied in order.
    label : str, optional
        Optional human-readable label for the schedule.
    """

    gates: list[GateApplication] = field(default_factory=list)
    label: str = ""

    def add(
        self,
        gate: NDArray[np.complex128],
        qubits: Sequence[int],
    ) -> GateSchedule:
        """Append a gate application to this schedule (chainable).

        Parameters
        ----------
        gate : NDArray[np.complex128]
            The unitary gate matrix.
        qubits : Sequence[int]
            Qubit indices the gate acts on.

        Returns
        -------
        GateSchedule
            Self, for chaining.
        """
        self.gates.append((gate, tuple(qubits)))
        return self

    def __len__(self) -> int:
        return len(self.gates)

    def __iter__(self):
        return iter(self.gates)


class UnitaryEvolution:
    """Applies unitary gate sequences to a quantum state.

    Supports both dense state-vector simulation (QuantumState) and MPS-based
    simulation (MPS).  A gate schedule defines one "step"; evolve() applies
    a schedule repeatedly for a number of steps.

    Parameters
    ----------
    mode : str
        "dense" (default) uses full state vectors; "mps" uses MPS.
    max_bond : int, optional
        Maximum bond dimension for MPS truncation.
    truncation : float, optional
        Singular value truncation threshold for MPS.
    """

    def __init__(
        self,
        mode: str = "dense",
        max_bond: int | None = None,
        truncation: float = 1e-10,
    ) -> None:
        if mode not in ("dense", "mps"):
            raise ValueError(f"mode must be 'dense' or 'mps', got {mode!r}")
        self.mode = mode
        self.max_bond = max_bond
        self.truncation = truncation
        self._history: list[QuantumState | MPS] = []

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(
        self,
        state: QuantumState | MPS,
        gate_sequence: GateSchedule | Sequence[GateApplication],
    ) -> QuantumState | MPS:
        """Apply a single step (a gate sequence) to the state.

        Parameters
        ----------
        state : Union[QuantumState, MPS]
            The current state.
        gate_sequence : Union[GateSchedule, Sequence[GateApplication]]
            The gates to apply this step, in order.

        Returns
        -------
        Union[QuantumState, MPS]
            The new state after applying all gates in the sequence.
        """
        if isinstance(gate_sequence, GateSchedule):
            gates = gate_sequence.gates
        else:
            gates = list(gate_sequence)

        result = state
        for gate, qubits in gates:
            result = self._apply_one(result, gate, qubits)
        return result

    def _apply_one(
        self,
        state: QuantumState | MPS,
        gate: NDArray[np.complex128],
        qubits: Sequence[int],
    ) -> QuantumState | MPS:
        """Apply a single gate to a state (dense or MPS)."""
        if self.mode == "mps":
            if not isinstance(state, MPS):
                raise TypeError(
                    f"mode='mps' requires an MPS state, got {type(state).__name__}"
                )
            state.apply_gate(
                gate,
                qubits,
                max_bond=self.max_bond,
                truncation=self.truncation,
            )
            return state

        # Dense mode
        if isinstance(state, MPS):
            state = QuantumState(state.to_vector())
        if not isinstance(state, QuantumState):
            state = QuantumState(state)
        new_vec = apply_gate_to_state(state.vector, gate, qubits)
        return QuantumState(new_vec, normalize=False)

    # ------------------------------------------------------------------
    # Evolve
    # ------------------------------------------------------------------

    def evolve(
        self,
        state: QuantumState | MPS,
        n_steps: int = 1,
        schedule: GateSchedule | Callable[[int], GateSchedule] | None = None,
    ) -> list[QuantumState | MPS]:
        """Evolve the state over multiple steps.

        Parameters
        ----------
        state : Union[QuantumState, MPS]
            Initial state.
        n_steps : int
            Number of steps to evolve.
        schedule : Union[GateSchedule, Callable[[int], GateSchedule], None]
            Either a fixed schedule applied every step, or a callable that
            returns a schedule for each step index.  If ``None``, an empty
            schedule is used (identity evolution).

        Returns
        -------
        List[Union[QuantumState, MPS]]
            List of states after each step (length n_steps).  The initial
            state is not included.
        """
        if n_steps < 0:
            raise ValueError(f"n_steps must be >= 0, got {n_steps}")

        if schedule is None:
            schedule = GateSchedule()

        history: list[QuantumState | MPS] = []
        current = state

        for t in range(n_steps):
            if callable(schedule):
                step_schedule = schedule(t)
            else:
                step_schedule = schedule
            current = self.step(current, step_schedule)
            history.append(current)

        self._history = history
        return history

    @property
    def history(self) -> list[object]:
        """States produced by the most recent evolve() call."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear the stored evolution history."""
        self._history = []

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def apply(
        self,
        state: QuantumState | MPS,
        gate: NDArray[np.complex128],
        qubits: Sequence[int],
    ) -> QuantumState | MPS:
        """Apply a single gate (convenience wrapper around step)."""
        return self.step(state, [(gate, tuple(qubits))])
