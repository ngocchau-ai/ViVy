import json
from pathlib import Path

import pytest
from nps_core.codegraph.indexer import write_codegraph, write_markdown_reports


def test_write_codegraph(tmp_path):
    src = tmp_path / "src"
    src.mkdir(parents=True)
    (src / "sample.py").write_text("x = 1\n", encoding="utf-8")
    relative = Path("out/graph.json")
    graph = write_codegraph(tmp_path, relative)
    actual = tmp_path / relative
    assert actual.exists()
    text = actual.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == graph
    with pytest.raises(ValueError):
        write_codegraph(tmp_path, tmp_path.parent / "escape.json")


def test_write_markdown_reports(tmp_path):
    src = tmp_path / "src"
    src.mkdir(parents=True)
    (src / "sample.py").write_text("x = 1\n", encoding="utf-8")
    graph = write_codegraph(tmp_path, Path("graph/codegraph.json"))
    summary = Path("graph/summary.md")
    dependencies = Path("graph/dependencies.md")
    impact = Path("graph/impact.md")
    write_markdown_reports(tmp_path, graph, summary, dependencies, impact)
    assert all((tmp_path / path).exists() for path in (summary, dependencies, impact))
    summary_text = (tmp_path / summary).read_text(encoding="utf-8")
    dependencies_text = (tmp_path / dependencies).read_text(encoding="utf-8")
    impact_text = (tmp_path / impact).read_text(encoding="utf-8")
    for label in ("Status", "Repository HEAD", "Nodes", "Edges", "Errors"):
        assert label in summary_text
    for key in ("nodes", "edges", "errors"):
        assert str(len(graph[key])) in summary_text
    assert dependencies_text.startswith("# Module Dependencies")
    assert "src/sample.py" in impact_text
    with pytest.raises(ValueError):
        write_markdown_reports(
            tmp_path,
            graph,
            tmp_path.parent / "outside.md",
            dependencies,
            impact,
        )
