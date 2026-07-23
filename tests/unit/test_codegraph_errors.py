import pytest
from nps_core.codegraph.indexer import build_codegraph


def test_syntax_error(tmp_path):
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)

    with open(pkg / "good.py", "w", encoding="utf-8") as f:
        f.write("def good():\n    pass\n")

    with open(pkg / "bad.py", "w", encoding="utf-8") as f:
        f.write("def broken(:\n")

    graph = build_codegraph(tmp_path)
    ids = {node["id"] for node in graph["nodes"]}
    assert "module:pkg.good" in ids
    assert len(graph["errors"]) == 1
    error = graph["errors"][0]
    assert error["path"] == "src/pkg/bad.py"
    assert error["line"] == 1
    assert error["message"]


def test_excluded_directories(tmp_path):
    excluded = (".venv", "__pycache__", ".pytest_cache", "node_modules")
    for name in excluded:
        (tmp_path / name).mkdir()
        (tmp_path / name / "hidden.py").write_text("x = 1\n", encoding="utf-8")

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "kept.py").write_text("x = 1\n", encoding="utf-8")

    graph = build_codegraph(tmp_path)
    ids = {node["id"] for node in graph["nodes"]}
    assert "module:kept" in ids

    paths = [str(node["path"]) for node in graph["nodes"]]
    for name in excluded:
        assert all(name not in path for path in paths)


def test_symlink_directory(tmp_path_factory):
    root = tmp_path_factory.mktemp("root")
    external = tmp_path_factory.mktemp("external")

    (external / "hidden.py").write_text("x = 1\n", encoding="utf-8")

    linked = root / "linked"
    try:
        linked.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip()

    graph = build_codegraph(root)

    for node in graph["nodes"]:
        assert "linked" not in str(node["path"]) and "hidden" not in str(node["id"])
