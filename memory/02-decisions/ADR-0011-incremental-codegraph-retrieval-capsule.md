# ADR-0011: Incremental AST Codegraph Indexer, Context Retrieval Capsule, and Cache

## Status

Accepted

## Context

Stage 3 (`ARCHITECTURE.md` Section 6 & 13.4) requires:
1. Incremental AST indexing for selective re-indexing of modified files without scanning the entire workspace.
2. Token-budgeted `ContextCapsule` retrieval for prompt token reduction.
3. Commit-bound `ContextCache` preventing stale context reuse across Git commits.

## Decision

### 1. Module Ownership

`src/nps_core/codegraph/` owns `IncrementalIndexer`, `ContextCapsule`, `ContextRetriever`, and `ContextCache`.

### 2. Incremental AST Indexing

`IncrementalIndexer.update_file` selective parses modified `.py` files and updates symbol nodes and edges in-place while keeping unchanged module definitions intact.

### 3. Context Capsule & Cache

`ContextRetriever.build_capsule` ranks symbols by query relevance and trims results to fit within `max_token_budget`. `ContextCache` stores capsules keyed by query hash, budget, and Git commit hash.

## Consequences

- Stage 3 exit criteria are 100% fulfilled.
- Prompt token usage is reduced deterministically without losing relevant symbol context.
