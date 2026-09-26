"""
Hebbian Recall — ViVy Final V1.0 Sprint 2.

Triển khai HebbianRecall với operator W = YX+ (Moore–Penrose pseudoinverse)
để truy xuất pattern từ CognitiveStateGraph theo ARCHITECTURE_V5.md Mục 6.3.
# [ISOLATED 23/09/2026] prior: "truy xuất O(1) từ CognitiveStateGraph" — complexity: see P5 receipt

Design:
    Mỗi node trong CognitiveStateGraph có embedding vector (từ ElasticNCore
    hidden state). HebbianRecall xây dựng ma trận liên kết:

        W = Y @ pinv(X)     (Moore–Penrose pseudoinverse)

    Trong đó:
        X = [x_1 | x_2 | ... | x_n]  ← input embeddings (keys)
        Y = [y_1 | y_2 | ... | y_n]  ← output embeddings (values)

    Truy xuất: y* = W @ x_query (một phép nhân ma trận, độc lập số node
    sau khi W đã build). Lookup node-id gần nhất là quét O(n).

Complexity (measured — see P5 receipt):
    - Build W: O(n * d^2) — amortised batch update
    - Recall W@x: O(d^2) — independent of graph size n
    - Nearest-node ID scan: O(n) khi truyền graph
    # [ISOLATED 23/09/2026] prior: "Recall: O(d^2) … → O(1) in graph size"

Khác với AssociativeMemory (unitary / Hopfield dynamics), HebbianRecall
dùng W = YX+ trực tiếp — không unitary projection, không Hopfield iter —
phù hợp với bài toán symbolic → embedding recall tốc độ cao.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2 — HOH-VIVY-FINAL-V1): Initial implementation.
    23/09/2026 (Claude Code — P5 Gate 9): Isolate unbenchmarked complexity claims; point at P5 receipt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from memory.cognitive_graph import CognitiveStateGraph, GraphNode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


@dataclass
class RecallResult:
    """Result of a HebbianRecall.recall() query.

    Attributes
    ----------
    query_embedding:
        The input query vector.
    recalled_embedding:
        The retrieved embedding vector (W @ query).
    recalled_node_id:
        ID of the nearest graph node to the recalled embedding (None if empty).
    recalled_node:
        The GraphNode object (None if graph is empty).
    similarity:
        Cosine similarity between recalled_embedding and the matched node's embedding.
    elapsed_ms:
        Wall-clock time of the recall operation.
    w_size:
        Number of key-value pairs contributing to W.
    """

    query_embedding: NDArray[np.float32]
    recalled_embedding: NDArray[np.float32]
    recalled_node_id: str | None
    recalled_node: GraphNode | None
    similarity: float
    elapsed_ms: float
    w_size: int


# ---------------------------------------------------------------------------
# HebbianRecall
# ---------------------------------------------------------------------------


class HebbianRecall:
    """Associative recall via W = Y @ pinv(X) — Moore–Penrose pseudoinverse.
    # [ISOLATED 23/09/2026] prior: "O(1) associative recall" — complexity: see P5 receipt

    HebbianRecall maintains a weight matrix W built from the embeddings of
    all nodes in a CognitiveStateGraph. When new nodes are added/removed,
    W is lazily rebuilt. Once built, recall is a single matrix multiplication
    with cost independent of the number of graph nodes (O(d^2) in embedding
    dimension). Nearest-node ID lookup still scans the graph (O(n)).

    Parameters
    ----------
    dim:
        Embedding dimension. Must match ElasticNCore.hidden_dim.
    rcond:
        Cut-off for small singular values in Moore-Penrose pseudoinverse
        (passed to numpy.linalg.pinv). Default None = machine epsilon.
    """

    def __init__(self, dim: int = 64, rcond: float | None = None) -> None:
        if dim < 1:
            raise ValueError(f"dim must be ≥ 1, got {dim}")
        self.dim = dim
        self._rcond = rcond

        # W = Y @ pinv(X): shape (dim, dim)
        # Built lazily from registered key-value embedding pairs.
        self._W: NDArray[np.float32] | None = None
        self._is_dirty: bool = False

        # Key-value embedding store: {node_id: (x_key, y_value)}
        # x_key = query embedding (from hidden_state)
        # y_value = node embedding (what to recall)
        self._kv: dict[str, tuple[NDArray[np.float32], NDArray[np.float32]]] = {}

        logger.debug("HebbianRecall: initialised dim=%d", dim)

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register(
        self,
        node_id: str,
        key_embedding: NDArray[np.float32] | list[float],
        value_embedding: NDArray[np.float32] | list[float] | None = None,
    ) -> None:
        """Register a node's embedding as a key-value pair.

        Parameters
        ----------
        node_id:
            Unique node identifier (matches CognitiveStateGraph node ID).
        key_embedding:
            Query key vector of shape (dim,). Typically the hidden_state
            from ElasticNCore that produced this node.
        value_embedding:
            Value vector to recall. If None, uses key_embedding (identity
            associative memory — recall the same embedding).
        """
        x = np.asarray(key_embedding, dtype=np.float32).ravel()
        if x.shape[0] != self.dim:
            raise ValueError(f"key_embedding dim mismatch: expected {self.dim}, got {x.shape[0]}")
        y = (
            np.asarray(value_embedding, dtype=np.float32).ravel()
            if value_embedding is not None
            else x.copy()
        )
        if y.shape[0] != self.dim:
            raise ValueError(f"value_embedding dim mismatch: expected {self.dim}, got {y.shape[0]}")
        self._kv[node_id] = (x, y)
        self._is_dirty = True
        logger.debug("HebbianRecall: registered node=%s", node_id)

    def unregister(self, node_id: str) -> bool:
        """Remove a node's embedding pair. Returns True if it existed."""
        if node_id in self._kv:
            del self._kv[node_id]
            self._is_dirty = True
            return True
        return False

    def sync_from_graph(self, graph: CognitiveStateGraph) -> int:
        """Synchronise all embeddings from a CognitiveStateGraph.

        Registers all nodes that have a non-None embedding.
        Returns the number of nodes registered.
        """
        count = 0
        for node in graph.iter_nodes():
            if node.embedding is not None:
                self.register(node.node_id, node.embedding)
                count += 1
        logger.debug("HebbianRecall.sync_from_graph: registered %d nodes", count)
        return count

    # ------------------------------------------------------------------
    # Core Recall
    # ------------------------------------------------------------------

    def recall(
        self,
        query_embedding: NDArray[np.float32] | list[float],
        graph: CognitiveStateGraph | None = None,
    ) -> RecallResult:
        """Recall a pattern embedding via W = Y @ pinv(X) (cost independent of n).
        # [ISOLATED 23/09/2026] prior: "in O(1)" — complexity: see P5 receipt

        Parameters
        ----------
        query_embedding:
            Query vector of shape (dim,). Typically the hidden_state from
            ElasticNCore at time t.
        graph:
            Optional CognitiveStateGraph to look up the nearest node ID
            after recall. If None, recalled_node_id is None.

        Returns
        -------
        RecallResult
            .recalled_embedding = W @ query_embedding (the recalled pattern)
            .recalled_node_id = nearest node in the graph (cosine similarity)
        """
        t0 = time.perf_counter()

        x_q = np.asarray(query_embedding, dtype=np.float32).ravel()
        if x_q.shape[0] != self.dim:
            raise ValueError(f"query_embedding dim mismatch: expected {self.dim}, got {x_q.shape[0]}")

        # Normalise query
        norm = np.linalg.norm(x_q)
        if norm > 1e-8:
            x_q = x_q / norm

        w_size = len(self._kv)

        # Empty memory: return zero embedding
        if w_size == 0:
            empty = np.zeros(self.dim, dtype=np.float32)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return RecallResult(
                query_embedding=x_q,
                recalled_embedding=empty,
                recalled_node_id=None,
                recalled_node=None,
                similarity=0.0,
                elapsed_ms=elapsed_ms,
                w_size=0,
            )

        # Build W lazily (only when dirty)
        if self._W is None or self._is_dirty:
            self._build_W()

        # W@x recall: y* = W @ x_q  (1 matrix multiplication; independent of n)
        # [ISOLATED 23/09/2026] prior: "O(1) recall" — complexity: see P5 receipt
        W = self._W
        assert W is not None
        y_star = W @ x_q  # (dim,)

        # Normalise recalled embedding
        y_norm = np.linalg.norm(y_star)
        if y_norm > 1e-8:
            y_star_normed = y_star / y_norm
        else:
            y_star_normed = y_star

        # Find nearest node by cosine similarity (scan is O(n) but
        # this is only for the "which node ID" lookup — the core recall
        # itself is O(1). In production, an FAISS index handles this.)
        best_node_id: str | None = None
        best_node: GraphNode | None = None
        best_sim = -1.0

        if graph is not None and len(graph) > 0:
            for node in graph.iter_nodes():
                if node.embedding is not None:
                    emb = np.asarray(node.embedding, dtype=np.float32)
                    emb_norm = np.linalg.norm(emb)
                    if emb_norm > 1e-8:
                        emb = emb / emb_norm
                    sim = float(np.dot(y_star_normed, emb))
                    if sim > best_sim:
                        best_sim = sim
                        best_node_id = node.node_id
                        best_node = node

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "HebbianRecall.recall: w_size=%d node=%s sim=%.4f %.3fms",
            w_size,
            best_node_id,
            best_sim,
            elapsed_ms,
        )

        return RecallResult(
            query_embedding=x_q,
            recalled_embedding=y_star,
            recalled_node_id=best_node_id,
            recalled_node=best_node,
            similarity=float(np.clip(best_sim, 0.0, 1.0)),
            elapsed_ms=elapsed_ms,
            w_size=w_size,
        )

    # ------------------------------------------------------------------
    # W matrix management
    # ------------------------------------------------------------------

    def _build_W(self) -> None:
        """Build W = Y @ pinv(X) from all registered key-value pairs.

        X: (dim, n) — each column is a key embedding
        Y: (dim, n) — each column is a value embedding
        W = Y @ pinv(X): (dim, dim)

        This is the Moore–Penrose pseudoinverse formulation:
            W = Y X+ = Y X^T (X X^T)^+ — least-squares optimal operator
            that maps X → Y in a way that minimises ‖WX - Y‖_F.
        """
        items = list(self._kv.values())
        n = len(items)

        # X and Y matrices: shape (dim, n)
        X = np.stack([kv[0] for kv in items], axis=1).astype(np.float32)  # (dim, n)
        Y = np.stack([kv[1] for kv in items], axis=1).astype(np.float32)  # (dim, n)

        # Moore–Penrose pseudoinverse of X: shape (n, dim)
        X_plus = np.linalg.pinv(X, rcond=self._rcond)  # (n, dim)

        # W = Y @ X+: shape (dim, dim)
        self._W = (Y @ X_plus).astype(np.float32)  # (dim, dim)
        self._is_dirty = False
        logger.debug("HebbianRecall._build_W: n=%d W.shape=%s", n, self._W.shape)

    def reset(self) -> None:
        """Clear all registered embeddings and the W matrix."""
        self._kv.clear()
        self._W = None
        self._is_dirty = False

    @property
    def is_built(self) -> bool:
        """True when W is up-to-date (not dirty)."""
        return self._W is not None and not self._is_dirty

    @property
    def size(self) -> int:
        """Number of registered key-value pairs."""
        return len(self._kv)
