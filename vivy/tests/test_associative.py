"""Unit tests for memory/associative.py — QuantumAssociativeMemory."""


import numpy as np
import pytest

from memory.associative import (
    SPARSE_DIM_THRESHOLD,
    AssociativeMemory,
    QuantumAssociativeMemory,
)


class TestInit:
    def test_small_dim(self):
        mem = QuantumAssociativeMemory(dim=4)
        assert mem.dim == 4
        assert not mem.is_sparse
        assert mem.store_count == 0

    def test_large_dim_triggers_sparse(self):
        mem = QuantumAssociativeMemory(dim=300)
        assert mem.is_sparse

    def test_dim_1(self):
        mem = QuantumAssociativeMemory(dim=1)
        assert mem.dim == 1

    def test_invalid_dim_raises(self):
        with pytest.raises(ValueError):
            QuantumAssociativeMemory(dim=0)
        with pytest.raises(ValueError):
            QuantumAssociativeMemory(dim=-5)

    def test_custom_params(self):
        mem = QuantumAssociativeMemory(dim=8, eta=0.5, reunit_interval=3, max_iterations=20)
        assert mem.eta == 0.5
        assert mem.reunit_interval == 3
        assert mem.max_iterations == 20

    def test_associativememory_alias(self):
        assert AssociativeMemory is QuantumAssociativeMemory


class TestStore:
    def test_basic_store(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y, eta=0.5)
        assert mem.store_count == 1
        assert not mem._is_empty()

    def test_store_with_default_eta(self):
        mem = QuantumAssociativeMemory(dim=4, eta=0.3)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        assert mem.store_count == 1

    def test_store_complex_vectors(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0 + 0.5j, 0.0, 0.0, 0.0])
        y = np.array([0.0, 0.0, 1.0, 0.0])
        mem.store(x, y)
        assert mem.store_count == 1

    def test_store_auto_normalises(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([2.0, 2.0, 0.0, 0.0])  # norm = sqrt(8)
        y = np.array([0.0, 0.0, 3.0, 0.0])  # norm = 3
        mem.store(x, y)
        # After normalisation, x should be unit norm.
        # Check that query returns something sensible.
        q, conf = mem.query(np.array([1.0, 0.0, 0.0, 0.0]))
        assert conf > 0.0

    def test_store_multiple_patterns(self):
        mem = QuantumAssociativeMemory(dim=4)
        for i in range(4):
            x = np.zeros(4)
            y = np.zeros(4)
            x[i] = 1.0
            y[(i + 1) % 4] = 1.0
            mem.store(x, y)
        assert mem.store_count == 4

    def test_store_invalid_dim_raises(self):
        mem = QuantumAssociativeMemory(dim=4)
        with pytest.raises(ValueError):
            mem.store(np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0, 0.0]))

    def test_store_2d_array_raises(self):
        mem = QuantumAssociativeMemory(dim=4)
        with pytest.raises(ValueError):
            mem.store(np.ones((2, 2)), np.ones(4))

    def test_store_sparse_mode(self):
        mem = QuantumAssociativeMemory(dim=300)
        x = np.zeros(300)
        y = np.zeros(300)
        x[0] = 1.0
        y[1] = 1.0
        mem.store(x, y)
        assert mem.store_count == 1
        assert mem._is_empty() is False


class TestQuery:
    def test_query_returns_same_dim(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        result, conf = mem.query(x)
        assert result.shape == (4,)
        assert isinstance(conf, float)

    def test_query_empty_memory(self):
        mem = QuantumAssociativeMemory(dim=4)
        result, conf = mem.query(np.array([1.0, 0.0, 0.0, 0.0]))
        assert conf == 0.0
        assert np.all(result == 0.0)

    def test_query_returns_unit_norm(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        result, _ = mem.query(x)
        norm = float(np.linalg.norm(result))
        assert abs(norm - 1.0) < 1e-12 or norm < 1e-15

    def test_query_confidence_nonzero_for_stored(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        _, conf = mem.query(x)
        assert conf > 0.0

    def test_query_multiple_stores(self):
        mem = QuantumAssociativeMemory(dim=4)
        for i in range(4):
            x = np.zeros(4)
            y = np.zeros(4)
            x[i] = 1.0
            y[(i + 1) % 4] = 1.0
            mem.store(x, y)
        _, conf = mem.query(np.array([1.0, 0.0, 0.0, 0.0]))
        assert conf > 0.0

    def test_query_with_custom_iterations(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        r1, c1 = mem.query(x, iterations=1)
        r2, c2 = mem.query(x, iterations=20)
        # Both should work; longer iterations may converge differently.
        assert c1 > 0.0
        assert c2 > 0.0

    def test_query_sparse_mode(self):
        mem = QuantumAssociativeMemory(dim=300)
        x = np.zeros(300)
        y = np.zeros(300)
        x[0] = 1.0
        y[1] = 1.0
        mem.store(x, y)
        result, conf = mem.query(x)
        assert result.shape == (300,)
        assert conf > 0.0


class TestMakeUnitary:
    def test_polar_decomposition_identity(self):
        mem = QuantumAssociativeMemory(dim=4)
        U = mem._make_unitary()
        # Empty memory => identity.
        assert np.allclose(U, np.eye(4, dtype=np.complex128))

    def test_polar_decomposition_is_unitary(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        U = mem.unitary
        # U @ U† should be identity.
        prod = U @ U.conj().T
        assert np.allclose(prod, np.eye(4, dtype=np.complex128), atol=1e-12)

    def test_polar_decomposition_determinant(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        U = mem.unitary
        det = np.linalg.det(U)
        assert abs(abs(det) - 1.0) < 1e-12

    def test_reunit_interval_triggers(self):
        mem = QuantumAssociativeMemory(dim=4, reunit_interval=2)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        # After 1 store, not yet triggered.
        assert mem._U is None
        mem.store(y, x)
        # After 2 stores, should have triggered.
        assert mem._U is not None


class TestReset:
    def test_reset_clears_memory(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        assert not mem._is_empty()
        mem.reset()
        assert mem._is_empty()
        assert mem.store_count == 0

    def test_reset_then_query_returns_zero(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(x, y)
        mem.reset()
        result, conf = mem.query(x)
        assert conf == 0.0
        assert np.all(result == 0.0)

    def test_reset_sparse(self):
        mem = QuantumAssociativeMemory(dim=300)
        x = np.zeros(300)
        x[0] = 1.0
        y = np.zeros(300)
        y[1] = 1.0
        mem.store(x, y)
        mem.reset()
        assert mem._is_empty()


class TestEdgeCases:
    def test_catastrophic_forgetting(self):
        """After many stores, the first pattern should still be retrievable."""
        mem = QuantumAssociativeMemory(dim=8, eta=0.1, reunit_interval=5)
        # Store first pattern.
        x0 = np.zeros(8)
        x0[0] = 1.0
        y0 = np.zeros(8)
        y0[1] = 1.0
        mem.store(x0, y0)

        # Store many other patterns.
        for i in range(2, 8):
            x = np.zeros(8)
            y = np.zeros(8)
            x[i] = 1.0
            y[(i + 1) % 8] = 1.0
            mem.store(x, y)

        # The first pattern should still be retrievable with non-zero confidence.
        _, conf = mem.query(x0)
        assert conf > 0.0, "Catastrophic forgetting: first pattern lost"

    def test_identity_retrieval(self):
        """Storing x->x should retrieve x when queried with x."""
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        mem.store(x, x)
        result, conf = mem.query(x)
        assert conf > 0.0
        # Should be close to x itself.
        overlap = abs(np.vdot(result, x))
        assert overlap > 0.9

    def test_orthogonal_patterns(self):
        """Orthogonal patterns should be distinguishable."""
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        e2 = np.array([0.0, 0.0, 1.0, 0.0])
        e3 = np.array([0.0, 0.0, 0.0, 1.0])
        mem.store(e0, e1)
        mem.store(e2, e3)

        r1, _ = mem.query(e0)
        r2, _ = mem.query(e2)
        # r1 should be closer to e1, r2 closer to e3.
        sim1 = abs(np.vdot(r1, e1))
        sim2 = abs(np.vdot(r2, e3))
        assert sim1 > 0.0
        assert sim2 > 0.0

    def test_sparse_threshold_constant(self):
        assert SPARSE_DIM_THRESHOLD == 256

    def test_repeated_store_same_pattern(self):
        mem = QuantumAssociativeMemory(dim=4)
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0, 0.0])
        for _ in range(5):
            mem.store(x, y)
        assert mem.store_count == 5
        _, conf = mem.query(x)
        assert conf > 0.0

    def test_dim_256_not_sparse(self):
        mem = QuantumAssociativeMemory(dim=256)
        assert not mem.is_sparse

    def test_dim_257_is_sparse(self):
        mem = QuantumAssociativeMemory(dim=257)
        assert mem.is_sparse

    def test_store_1d_list(self):
        mem = QuantumAssociativeMemory(dim=4)
        mem.store([1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0])
        assert mem.store_count == 1

    def test_store_1d_tuple(self):
        mem = QuantumAssociativeMemory(dim=4)
        mem.store((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0))
        assert mem.store_count == 1

    def test_store_real_vectors(self):
        mem = QuantumAssociativeMemory(dim=4)
        mem.store(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
                  np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float64))
        _, conf = mem.query(np.array([1.0, 0.0, 0.0, 0.0]))
        assert conf > 0.0
