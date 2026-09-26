import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parents[2]
wrapper = repo_root / "scripts" / "refresh_codegraph.py"


def test_refresh_codegraph(tmp_path):
    if not shutil.which("git"):
        pytest.skip("Git executable is unavailable")

    sample_dir = tmp_path / "src" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "__init__.py").touch()
    (sample_dir / "module.py").touch()

    subprocess.run(
        ["git", "-C", str(tmp_path), "init"],
        check=True,
        capture_output=True,
        text=True
    )

    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
        text=True
    )

    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
        text=True
    )

    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "."],
        check=True,
        capture_output=True,
        text=True
    )

    subprocess.run(
        ["git", "commit", "-m", "test commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True
    )
    head = subprocess.run(
        ["git", "-C", tmp_path, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True
    ).stdout.strip()

    result = subprocess.run(
        [sys.executable, wrapper, "--root", str(tmp_path), "--output", "graph/codegraph.json", "--summary", "graph/summary.md", "--dependencies", "graph/dependencies.md", "--impact", "graph/impact.md"],
        check=False,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Wrapper failed with stderr: {result.stderr}"

    output_artifacts = [
        "graph/codegraph.json",
        "graph/summary.md",
        "graph/dependencies.md",
        "graph/impact.md"
    ]

    for artifact in output_artifacts:
        assert (tmp_path / artifact).exists(), f"Output artifact {artifact} does not exist"

    with open(tmp_path / "graph/codegraph.json") as f:
        codegraph = json.load(f)

    assert codegraph["status"] == "FRESH"
    assert codegraph["repository_head"] == head
    assert codegraph["codegraph_commit"] == head

    with open(tmp_path / "graph/summary.md") as f:
        summary = f.read()

    assert "Status" in summary
    assert "Repository HEAD" in summary
    assert "Nodes" in summary
    assert "Edges" in summary
    assert "Errors" in summary

    for node in codegraph["nodes"]:
        assert chr(92) not in str(node["path"])
