"""Unit tests for incremental codegraph indexer, retrieval capsule, and cache."""

from __future__ import annotations

from pathlib import Path

from nps_core.codegraph import (
    ContextCache,
    ContextCapsule,
    ContextRetriever,
    IncrementalIndexer,
)


def test_context_retriever_budget_trimming() -> None:
    nodes = [
        {"id": "s1", "name": "ThoughtState", "qualified_name": "nps_core.hypothesis_population.ThoughtState", "path": "src/t.py", "line": 10},
        {"id": "s2", "name": "PopulationSnapshot", "qualified_name": "nps_core.hypothesis_population.PopulationSnapshot", "path": "src/p.py", "line": 20},
        {"id": "s3", "name": "ThoughtEcology", "qualified_name": "nps_core.thought_ecology.ThoughtEcology", "path": "src/e.py", "line": 30},
    ]

    # Large budget -> retrieves all matching symbols
    capsule_full = ContextRetriever.build_capsule(nodes, query="ThoughtState", max_token_budget=1000)
    assert len(capsule_full.symbols) >= 1
    assert capsule_full.estimated_tokens <= 1000

    # Small budget -> trims symbols
    capsule_small = ContextRetriever.build_capsule(nodes, query="ThoughtState", max_token_budget=20)
    assert len(capsule_small.symbols) <= len(capsule_full.symbols)
    assert capsule_small.estimated_tokens <= 20


def test_context_cache() -> None:
    cache = ContextCache()
    capsule = ContextCapsule(query="test", symbols=(), estimated_tokens=10, max_token_budget=100)

    git_commit = "a" * 40
    assert cache.get("test", 100, git_commit) is None

    cache.put("test", 100, git_commit, capsule)
    retrieved = cache.get("test", 100, git_commit)
    assert retrieved is not None
    assert retrieved.digest == capsule.digest


def test_incremental_indexer(tmp_path: Path) -> None:
    file1 = tmp_path / "src" / "sample.py"
    file1.parent.mkdir(parents=True, exist_ok=True)
    file1.write_text("class Foo:\n    def bar(self):\n        pass\n", encoding="utf-8")

    nodes, edges = IncrementalIndexer.update_file(tmp_path, file1, [], [])
    assert len(nodes) == 2
    assert any(n["name"] == "Foo" for n in nodes)
    assert any(n["name"] == "bar" for n in nodes)
