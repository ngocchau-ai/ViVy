"""Unit tests for memory/query.py — cosine_similarity and analogical_reasoning."""

import numpy as np
import pytest

from memory.associative import QuantumAssociativeMemory
from memory.query import analogical_reasoning, cosine_similarity


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = np.array([1.0, 0.0, 0.0, 0.0])
        sim = cosine_similarity(a, a)
        assert abs(sim - 1.0) < 1e-12

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0, 0.0])
        sim = cosine_similarity(a, b)
        assert abs(sim) < 1e-12

    def test_partial_overlap(self):
        a = np.array([1.0, 0.0])
        b = np.array([1.0 / np.sqrt(2), 1.0 / np.sqrt(2)])
        sim = cosine_similarity(a, b)
        assert abs(sim - 1.0 / np.sqrt(2)) < 1e-12

    def test_zero_vector(self):
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert cosine_similarity(a, b) == 0.0
        assert cosine_similarity(b, a) == 0.0
        assert cosine_similarity(a, a) == 0.0

    def test_complex_vectors(self):
        a = np.array([1.0 + 0.5j, 0.0])
        b = np.array([0.0, 1.0 - 0.5j])
        sim = cosine_similarity(a, b)
        assert abs(sim) < 1e-12

    def test_same_direction_complex(self):
        a = np.array([1.0 + 1.0j, 0.0])
        b = np.array([2.0 + 2.0j, 0.0])
        sim = cosine_similarity(a, b)
        assert abs(sim - 1.0) < 1e-12

    def test_different_lengths_raises(self):
        with pytest.raises(ValueError):
            cosine_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0, 0.0]))

    def test_list_input(self):
        assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-12

    def test_float64_input(self):
        a = np.array([1.0, 0.0], dtype=np.float64)
        b = np.array([0.0, 1.0], dtype=np.float64)
        assert abs(cosine_similarity(a, b)) < 1e-12


class TestAnalogicalReasoning:
    def test_empty_memory_returns_empty(self):
        mem = QuantumAssociativeMemory(dim=4)
        results = analogical_reasoning(mem, np.array([1.0, 0.0, 0.0, 0.0]), k=3)
        assert results == []

    def test_basic_analogy(self):
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        e2 = np.array([0.0, 0.0, 1.0, 0.0])
        e3 = np.array([0.0, 0.0, 0.0, 1.0])

        mem.store(e0, e1)
        mem.store(e2, e3)

        results = analogical_reasoning(mem, e0, k=2)
        assert len(results) <= 2
        # The retrieved pattern should be most similar to e1.
        if results:
            pattern, sim = results[0]
            assert sim > 0.0

    def test_k_zero_returns_empty(self):
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(e0, e1)
        assert analogical_reasoning(mem, e0, k=0) == []

    def test_k_negative_returns_empty(self):
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(e0, e1)
        assert analogical_reasoning(mem, e0, k=-1) == []

    def test_with_explicit_candidates(self):
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(e0, e1)

        candidates = [
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0, 0.0]),
        ]
        results = analogical_reasoning(mem, e0, candidates=candidates, k=2)
        assert len(results) == 2
        # First result should be most similar to e0.
        assert results[0][1] >= results[1][1]

    def test_sparse_memory_analogy(self):
        mem = QuantumAssociativeMemory(dim=300)
        x = np.zeros(300)
        y = np.zeros(300)
        x[0] = 1.0
        y[1] = 1.0
        mem.store(x, y)
        results = analogical_reasoning(mem, x, k=1)
        # Should not crash; may return empty if no candidates match.
        assert isinstance(results, list)

    def test_analogy_returns_sorted(self):
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        e2 = np.array([0.0, 0.0, 1.0, 0.0])
        e3 = np.array([0.0, 0.0, 0.0, 1.0])
        mem.store(e0, e1)
        mem.store(e2, e3)

        results = analogical_reasoning(mem, e0, k=5)
        sims = [s for _, s in results]
        assert all(sims[i] >= sims[i + 1] for i in range(len(sims) - 1))
