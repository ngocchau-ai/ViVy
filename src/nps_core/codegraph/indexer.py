from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Sequence

DEFAULT_EXCLUDED_DIRS = frozenset(
    (".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules")
)

_GIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


def _resolved_root(root: Path) -> Path:
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ValueError("Provided path is not a directory")
    return resolved


def _safe_output(root: Path, path: Path) -> Path:
    resolved_root = _resolved_root(root)
    candidate = (path if path.is_absolute() else resolved_root / path).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("Path is outside the allowed directory")
    return candidate


def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            shell=False
        )
        if result.returncode == 0 and _GIT_HASH_RE.fullmatch(result.stdout.strip()):
            return result.stdout.strip()
    except OSError:
        pass
    return None


def _module_name(root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(_resolved_root(root)).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or "__root__"


class _DefinitionVisitor(ast.NodeVisitor):
    def __init__(self, module_name: str, path: str) -> None:
        self.module_name = module_name
        self.path = path
        self.nodes: list[dict[str, object]] = []
        self.edges: list[dict[str, str]] = []
        self._stack: list[str] = []

    def _record(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        symbol_name = '.'.join(self._stack + [node.name])
        qualified_name = f"{self.module_name}.{symbol_name}"
        symbol_id = f"symbol:{self.module_name}:{symbol_name}"
        self.nodes.append({
            "id": symbol_id,
            "kind": kind,
            "name": node.name,
            "qualified_name": qualified_name,
            "path": self.path,
            "line": node.lineno
        })
        self.edges.append({
            "source": f"module:{self.module_name}",
            "target": symbol_id,
            "kind": "contains"
        })

    def _visit_definition(self, node: ast.AST, kind: str) -> None:
        self._record(node, kind)
        self._stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_definition(node, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition(node, "async_function")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.edges.append({
                "source": f"module:{self.module_name}",
                "target": f"import:{alias.name}",
                "kind": "imports"
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        target = "." * node.level + (node.module or "")
        if not target:
            target = "."
        self.edges.append({
            "source": f"module:{self.module_name}",
            "target": f"import:{target}",
            "kind": "imports"
        })
        self.generic_visit(node)


def _index_python_file(root: Path, path: Path) -> tuple[list[dict[str, object]], list[dict[str, str]], dict[str, object] | None]:
    root = _resolved_root(root)
    relative_path = path.resolve().relative_to(root).as_posix()
    module_name = _module_name(root, path)

    try:
        with open(path, 'r', encoding='utf-8') as file:
            tree = ast.parse(file.read(), filename=relative_path)
    except SyntaxError as error:
        return [], [], {'path': relative_path, 'line': error.lineno or 0, 'message': error.msg}
    except (OSError, UnicodeError) as error:
        return [], [], {'path': relative_path, 'line': 0, 'message': str(error)}

    module_node = {
        'id': f'module:{module_name}',
        'kind': 'module',
        'name': module_name.split('.')[-1],
        'qualified_name': module_name,
        'path': relative_path,
        'line': 1
    }

    visitor = _DefinitionVisitor(module_name, relative_path)
    visitor.visit(tree)

    return [module_node, *visitor.nodes], visitor.edges, None


def build_codegraph(root: Path) -> dict[str, object]:
    root = _resolved_root(root)
    node_list = []
    edge_list = []
    error_list = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in DEFAULT_EXCLUDED_DIRS and not (Path(dirpath) / name).is_symlink())
        for filename in sorted(filenames):
            if filename.endswith('.py'):
                file_nodes, file_edges, error = _index_python_file(root, Path(dirpath) / filename)
                node_list.extend(file_nodes)
                edge_list.extend(file_edges)
                if error is not None:
                    error_list.append(error)

    nodes_by_id = {str(node["id"]): node for node in node_list}
    edges_by_key = {(str(edge["source"]), str(edge["target"]), str(edge["kind"])): edge for edge in edge_list}

    sorted_nodes = sorted(nodes_by_id.values(), key=lambda n: n["id"])
    sorted_edges = sorted(edges_by_key.values(), key=lambda e: (e["kind"], e["source"], e["target"]))
    sorted_errors = sorted(error_list, key=lambda e: (str(e["path"]), int(e["line"]), str(e["message"])))

    head = _git_head(root)
    status = "FRESH" if head is not None else "UNVERSIONED"

    return {
        "schema_version": "0.1",
        "status": status,
        "repository_head": head,
        "codegraph_commit": head,
        "nodes": sorted_nodes,
        "edges": sorted_edges,
        "errors": sorted_errors
    }


def write_codegraph(root: Path, output: Path) -> dict[str, object]:
    root = _resolved_root(root)
    target = _safe_output(root, output)
    target.parent.mkdir(parents=True, exist_ok=True)
    graph = build_codegraph(root)
    serialized = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    target.write_text(serialized, encoding="utf-8")
    return graph


def write_markdown_reports(root: Path, graph: dict[str, object], summary: Path, dependencies: Path, impact: Path) -> None:
    root = _resolved_root(root)
    head = graph["repository_head"] or "UNVERSIONED"

    summary_lines = [
        "# Codegraph Summary",
        "",
        f"Status: {graph['status']}",
        f"Repository HEAD: {head}",
        f"Nodes: {len(graph['nodes'])}",
        f"Edges: {len(graph['edges'])}",
        f"Errors: {len(graph['errors'])}",
        ""
    ]

    summary_text = "\n".join(summary_lines)

    import_edges = [edge for edge in graph["edges"] if edge["kind"] == "imports"]
    dependency_entries = ["- {} -> {}".format(edge["source"], edge["target"]) for edge in import_edges]
    if not dependency_entries:
        dependency_entries = ["- None."]
    dependency_lines = ["# Module Dependencies", "", *dependency_entries, ""]
    dependencies_text = "\n".join(dependency_lines)

    module_paths = [str(node["path"]) for node in graph["nodes"] if node["kind"] == "module"]
    impact_entries = ["- {}".format(path) for path in module_paths] or ["- None."]
    impact_lines = [
        "# Change Impact",
        "",
        "Generated baseline for indexed modules.",
        "",
        "## Indexed Module Paths",
        *impact_entries,
        ""
    ]
    impact_text = "\n".join(impact_lines)

    for report_path, report_text in (
        (summary, summary_text),
        (dependencies, dependencies_text),
        (impact, impact_text),
    ):
        target = _safe_output(root, report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report_text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the NPS Core codegraph.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Root directory for the codebase")
    parser.add_argument("--output", type=Path, default=Path("memory/03-codegraph/codegraph.json"), help="Output file for the codegraph")
    parser.add_argument("--summary", type=Path, default=Path("memory/03-codegraph/codegraph-summary.md"), help="Output file for the summary report")
    parser.add_argument("--dependencies", type=Path, default=Path("memory/03-codegraph/module-dependencies.md"), help="Output file for the dependencies report")
    parser.add_argument("--impact", type=Path, default=Path("memory/03-codegraph/change-impact.md"), help="Output file for the impact report")
    args = parser.parse_args(argv)

    graph = write_codegraph(args.root, args.output)
    write_markdown_reports(args.root, graph, args.summary, args.dependencies, args.impact)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
