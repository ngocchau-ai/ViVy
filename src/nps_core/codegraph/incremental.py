"""Incremental AST Codegraph Indexer for Stage 3.

Updates existing codegraph nodes and edges for modified files without full repository scan.
Standard-library only.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Sequence

from nps_core.codegraph.indexer import _DefinitionVisitor, _module_name

__all__ = [
    "IncrementalIndexer",
]


class IncrementalIndexer:
    """Incremental indexer that selectively re-indexes changed Python source files."""

    @staticmethod
    def update_file(
        root: Path,
        file_path: Path,
        existing_nodes: Sequence[dict[str, Any]],
        existing_edges: Sequence[dict[str, Any]],
    ) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        """Re-index a single modified file and merge into existing nodes and edges."""
        rel_path_str = str(file_path.resolve().relative_to(root.resolve()))
        module = _module_name(root, file_path)

        # Remove existing nodes and edges belonging to this file
        retained_nodes = [n for n in existing_nodes if n.get("path") != rel_path_str]
        retained_edges = [
            e for e in existing_edges
            if not (isinstance(e.get("source"), str) and e["source"].startswith(f"module:{module}"))
        ]

        if not file_path.exists():
            return tuple(retained_nodes), tuple(retained_edges)

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=rel_path_str)
        except (SyntaxError, UnicodeDecodeError):
            return tuple(retained_nodes), tuple(retained_edges)

        visitor = _DefinitionVisitor(module, rel_path_str)
        visitor.visit(tree)

        new_nodes = list(retained_nodes) + visitor.nodes
        new_edges = list(retained_edges) + visitor.edges

        return tuple(new_nodes), tuple(new_edges)
