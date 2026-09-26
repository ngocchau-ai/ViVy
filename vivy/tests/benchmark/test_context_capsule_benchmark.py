"""Benchmark test for Stage 3 Context Capsule token reduction."""

from __future__ import annotations

import time

from nps_core.codegraph import ContextRetriever


def test_context_capsule_token_reduction_benchmark() -> None:
    # Generate 500 symbol nodes representing a large codebase AST
    large_ast_nodes = [
        {
            "id": f"symbol:mod_{i}:Class_{i}",
            "kind": "class",
            "name": f"Class_{i}",
            "qualified_name": f"nps_core.module_{i % 10}.Class_{i}",
            "path": f"src/nps_core/module_{i % 10}/file_{i}.py",
            "line": 10 + i,
            "docstring": f"Detailed documentation string for Class_{i} containing extensive type signatures.",
        }
        for i in range(500)
    ]

    start_time = time.perf_counter()

    # Full context token count estimate
    full_tokens = sum(len(str(n)) // 4 for n in large_ast_nodes)

    # Budgeted capsule retrieval (budget = 250 tokens)
    budget = 250
    capsule = ContextRetriever.build_capsule(large_ast_nodes, query="Class_42 Class_100", max_token_budget=budget)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert capsule.estimated_tokens <= budget
    assert capsule.estimated_tokens < full_tokens
    assert elapsed_ms < 50.0, f"Context retrieval capsule benchmark took {elapsed_ms:.2f}ms (>50ms threshold)"
