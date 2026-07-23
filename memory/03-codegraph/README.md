# memory/03-codegraph/README.md

## Purpose
The codegraph is a deterministic repository map designed for task-scoped retrieval and impact analysis. It captures the structure of Python projects, including module dependencies and syntax errors, ensuring consistency across different environments.

## JSON Top-Level Fields
- `schema_version`: Version of the schema used.
- `status`: Current status of the codegraph (e.g., "up-to-date", "out-of-date").
- `repository_head`: Git commit hash representing the current HEAD of the repository.
- `codegraph_commit`: Commit hash of the codegraph itself, ensuring it matches the repository's HEAD.
- `nodes`: List of nodes representing modules and symbols.
- `edges`: List of edges representing dependencies between nodes.
- `errors`: List of syntax errors encountered during indexing.

## Freshness Invariant
The `codegraph_commit` must always match the current Git HEAD to ensure the codegraph is up-to-date with the repository's state.

## Node Fields
- `id`: Unique identifier for each node.
- `kind`: Type of node (e.g., "module", "class", "function").
- `name`: Name of the node.
- `qualified_name`: Fully qualified name of the node.
- `path`: File path where the node is located.
- `line`: Line number within the file.

## Edge Fields
- `source`: ID of the source node.
- `target`: ID of the target node.
- `kind`: Type of edge (e.g., "contains", "imports").

## Imported Targets
Imported targets are represented using the format `import:<module_name>`, and they do not require a corresponding node in the graph.

## Ordering
Nodes are ordered by their `id`. Edges are ordered first by `kind`, then by `source`, and finally by `target`. Errors are sorted alphabetically.

## Indexing
The codegraph is generated using Python's Abstract Syntax Tree (AST) only. It does not import or execute source code, records syntax errors, and excludes directories such as Git, virtualenvs, caches, node_modules, and symlink directories.

## Generated Artifacts
- `codegraph.json`: The primary JSON representation of the codegraph.
- `codegraph-summary.md`: A summary of the codegraph's contents.
- `module-dependencies.md`: Detailed module dependency information.
- `change-impact.md`: Impact analysis based on changes to the codebase.

## Refresh Command
To refresh the codegraph, run:
```sh
uv run python scripts/refresh_codegraph.py
```

## Closure Rule
The codegraph should only be refreshed after the final task commit. A task cannot be closed if the recorded commit differs from the current HEAD.

## Limitations
- Python-only AST baseline.
- Imports are syntactic; no call graph.
- No incremental diff indexing in TASK-001.
