"""Unit tests for Quantum-Inspired Associative Memory."""

import pytest

from nps_core.memory import PatternMatchResult, QuantumAssociativeMemory


def test_associative_memory_store_and_query():
    memory = QuantumAssociativeMemory(dim_input=2, dim_output=2, use_unitary=True)

    input_pattern = [1.0, 0.0]
    output_pattern = [0.0, 1.0]

    memory.store(input_pattern, output_pattern, learning_rate=0.5)

    assert memory.pattern_count == 1

    # Query bằng vector gần giống input_pattern
    query_vec = [0.99, 0.01]
    res = memory.query(query_vec)

    assert isinstance(res, PatternMatchResult)
    assert res.confidence > 0.8
    assert res.matched_pattern_index == 0
    assert len(res.suggested_output) == 2


def test_associative_memory_multiple_patterns():
    memory = QuantumAssociativeMemory(dim_input=2, dim_output=2, use_unitary=True)

    p1_in, p1_out = [1.0, 0.0], [0.0, 1.0]
    p2_in, p2_out = [0.0, 1.0], [1.0, 0.0]

    memory.store(p1_in, p1_out)
    memory.store(p2_in, p2_out)

    assert memory.pattern_count == 2

    res1 = memory.query([1.0, 0.0])
    assert res1.matched_pattern_index == 0

    res2 = memory.query([0.0, 1.0])
    assert res2.matched_pattern_index == 1


def test_associative_memory_empty_query():
    memory = QuantumAssociativeMemory(dim_input=2, dim_output=2)
    res = memory.query([1.0, 0.0])

    assert res.confidence == 0.0
    assert res.matched_pattern_index is None
