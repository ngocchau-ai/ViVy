"""Tests for core.evolution — UnitaryEvolution and GateSchedule."""

import numpy as np
import pytest

from core.evolution import GateSchedule, UnitaryEvolution
from core.gates import cnot, hadamard, pauli_x
from core.mps import MPS
from core.state import QuantumState


class TestGateSchedule:
    def test_empty(self):
        sched = GateSchedule()
        assert len(sched) == 0

    def test_add(self):
        sched = GateSchedule(label="test")
        sched.add(pauli_x(), [0]).add(hadamard(), [1])
        assert len(sched) == 2

    def test_iter(self):
        sched = GateSchedule()
        sched.add(pauli_x(), [0])
        gates = list(sched)
        assert len(gates) == 1
        assert np.allclose(gates[0][0], pauli_x())
        assert gates[0][1] == (0,)


class TestUnitaryEvolutionDense:
    def test_init(self):
        evo = UnitaryEvolution(mode="dense")
        assert evo.mode == "dense"

    def test_init_invalid_mode(self):
        with pytest.raises(ValueError):
            UnitaryEvolution(mode="invalid")

    def test_apply_single_gate(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        result = evo.apply(state, pauli_x(), [0])
        assert isinstance(result, QuantumState)
        assert np.allclose(result.vector, [0, 1, 0, 0])

    def test_step(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0, 0, 0], dtype=np.complex128))
        sched = GateSchedule().add(pauli_x(), [0]).add(pauli_x(), [0])
        result = evo.step(state, sched)
        # X² = I, so back to |00⟩
        assert np.allclose(result.vector, [1, 0, 0, 0])

    def test_evolve_fixed_schedule(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0], dtype=np.complex128))
        sched = GateSchedule().add(hadamard(), [0])
        history = evo.evolve(state, 3, sched)
        assert len(history) == 3
        # H|0⟩ = (|0⟩+|1⟩)/√2, H² = I, H³ = H
        expected = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
        assert np.allclose(history[0].vector, expected)
        assert np.allclose(history[1].vector, [1, 0])
        assert np.allclose(history[2].vector, expected)

    def test_evolve_callable_schedule(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0], dtype=np.complex128))

        def schedule(t: int):
            if t % 2 == 0:
                return GateSchedule().add(hadamard(), [0])
            return GateSchedule().add(pauli_x(), [0])

        history = evo.evolve(state, 2, schedule)
        assert len(history) == 2

    def test_evolve_negative_steps(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0], dtype=np.complex128))
        sched = GateSchedule()
        with pytest.raises(ValueError):
            evo.evolve(state, -1, sched)

    def test_history(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0], dtype=np.complex128))
        sched = GateSchedule().add(hadamard(), [0])
        evo.evolve(state, 2, sched)
        assert len(evo.history) == 2

    def test_clear_history(self):
        evo = UnitaryEvolution()
        state = QuantumState(np.array([1, 0], dtype=np.complex128))
        sched = GateSchedule().add(hadamard(), [0])
        evo.evolve(state, 2, sched)
        evo.clear_history()
        assert len(evo.history) == 0


class TestUnitaryEvolutionMPS:
    def test_apply_single_gate(self):
        evo = UnitaryEvolution(mode="mps")
        # Create MPS for |00⟩
        t0 = np.zeros((1, 2, 1), dtype=np.complex128)
        t0[0, 0, 0] = 1.0
        t1 = np.zeros((1, 2, 1), dtype=np.complex128)
        t1[0, 0, 0] = 1.0
        mps = MPS([t0, t1], canonicalize=False)

        result = evo.apply(mps, pauli_x(), [0])
        assert isinstance(result, MPS)
        vec = result.to_vector()
        assert np.allclose(vec, [0, 1, 0, 0])

    def test_step_with_schedule(self):
        evo = UnitaryEvolution(mode="mps")
        t0 = np.zeros((1, 2, 1), dtype=np.complex128)
        t0[0, 0, 0] = 1.0
        t1 = np.zeros((1, 2, 1), dtype=np.complex128)
        t1[0, 0, 0] = 1.0
        mps = MPS([t0, t1], canonicalize=False)

        sched = GateSchedule().add(hadamard(), [0]).add(cnot(), [0, 1])
        result = evo.step(mps, sched)
        # H on q0: (|00⟩ + |01⟩)/√2, then CNOT: (|00⟩ + |11⟩)/√2
        vec = result.to_vector()
        expected = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        assert np.allclose(vec, expected)

    def test_evolve(self):
        evo = UnitaryEvolution(mode="mps")
        t0 = np.zeros((1, 2, 1), dtype=np.complex128)
        t0[0, 0, 0] = 1.0
        t1 = np.zeros((1, 2, 1), dtype=np.complex128)
        t1[0, 0, 0] = 1.0
        mps = MPS([t0, t1], canonicalize=False)

        sched = GateSchedule().add(hadamard(), [0])
        history = evo.evolve(mps, 2, sched)
        assert len(history) == 2
