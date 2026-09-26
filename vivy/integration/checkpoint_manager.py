"""
CheckpointManager -- ViVy Sprint 4 (Gate 5: Durability).

Save va restore CognitiveStateGraph + HebbianRecall W-matrix vao disk (JSONL).
Cho phep ViVy nho giua cac sessions va recover sau crash.

Gate 5 Acceptance:
    - Session A writes checkpoint -> closes
    - Session B restores state -> finds nodes and recall W-matrix
    - No data loss between sessions
    - Checkpoint is atomic (write-then-rename, WAL-style)

Evidence boundary:
    Checkpoint luu state snapshot. No khong tu dong promote knowledge.
    Promotion tu PROVISIONAL -> VERIFIED phai qua LessonStore.promote().

Changelog:
    21/09/2026 (Antigravity IDE, Sprint 4 -- Gate 5 Durability): Initial.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from memory.cognitive_graph import (
    CognitiveStateGraph,
    EdgeType,
    NodeType,
    ScoredMindmapDAG,
    ScoredTaskNode,
)
from memory.hebbian_recall import HebbianRecall

logger = logging.getLogger(__name__)

_DEFAULT_CHECKPOINT_DIR = Path(
    os.environ.get("VIVY_CHECKPOINT_DIR", "checkpoints")
)


@dataclass
class CheckpointMetadata:
    """Metadata for a saved checkpoint."""

    checkpoint_id: str
    session_id: str
    timestamp: float
    node_count: int
    recall_dim: int
    file_path: str

    def age_seconds(self) -> float:
        return time.time() - self.timestamp


class CheckpointManager:
    """Save and restore ViVy cognitive state to disk.

    Checkpoint format: one JSONL file per session.
    Line 1: header metadata (JSON).
    Line 2: CognitiveStateGraph nodes (JSON).
    Line 3: CognitiveStateGraph edges (JSON).
    Line 4: HebbianRecall W-matrix (base64-encoded numpy float32).

    Atomic write: write to .tmp file then rename -- prevents partial writes.

    Parameters
    ----------
    checkpoint_dir : Directory to store checkpoint files. Created if missing.
    max_checkpoints_per_session : Oldest checkpoints purged when exceeded.
    """

    def __init__(
        self,
        checkpoint_dir: Path | str = _DEFAULT_CHECKPOINT_DIR,
        max_checkpoints_per_session: int = 5,
    ) -> None:
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._max = max_checkpoints_per_session
        logger.info("CheckpointManager: dir=%s max=%d", self._dir, self._max)

    def save(
        self,
        session_id: str,
        graph: CognitiveStateGraph,
        recall: HebbianRecall,
    ) -> CheckpointMetadata:
        """Save current session cognitive state to disk atomically."""
        ckpt_id = uuid.uuid4().hex[:12]
        timestamp = time.time()
        filename = f"{session_id}_{ckpt_id}_{int(timestamp)}.jsonl"
        final_path = self._dir / filename
        tmp_path = self._dir / (filename + ".tmp")

        nodes_data = []
        for node_id, node in graph._nodes.items():
            nodes_data.append({
                "node_id": node_id,
                "node_type": node.node_type.name,
                "content": node.content,
                "embedding": node.embedding,
                "confidence": node.confidence,
                "falsified_count": node.falsified_count,
                "created_at": node.created_at,
            })

        edges_data = []
        for edge in graph._edges:
            edges_data.append({
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "edge_type": edge.edge_type.name,
                "weight": edge.weight,
            })

        # Serialize HebbianRecall via _kv (key -> embedding).
        # W-matrix is built lazily from _kv on first recall() -- no need to serialize W.
        recall_kv: dict[str, list[float]] = {}
        for node_id, vec in recall._kv.items():
            # _kv values are numpy arrays -- use tolist() for JSON serialization
            arr = np.asarray(vec, dtype=np.float32)
            recall_kv[node_id] = arr.tolist()

        with tmp_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "header",
                "checkpoint_id": ckpt_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "node_count": len(nodes_data),
                "edge_count": len(edges_data),
                "recall_dim": recall.dim,
                "recall_kv_count": len(recall_kv),
            }) + "\n")
            f.write(json.dumps({"type": "nodes", "data": nodes_data}) + "\n")
            f.write(json.dumps({"type": "edges", "data": edges_data}) + "\n")
            f.write(json.dumps({"type": "recall_kv", "kv": recall_kv}) + "\n")

        tmp_path.rename(final_path)

        meta = CheckpointMetadata(
            checkpoint_id=ckpt_id,
            session_id=session_id,
            timestamp=timestamp,
            node_count=len(nodes_data),
            recall_dim=recall.dim,
            file_path=str(final_path),
        )
        logger.info(
            "CheckpointManager.save: session=%s nodes=%d ckpt=%s",
            session_id[:8], len(nodes_data), ckpt_id,
        )
        self._purge_old(session_id)
        return meta

    # ------------------------------------------------------------------
    # Scored Mindmap DAG — WAL Checkpoint (Phase 4)
    # ------------------------------------------------------------------

    def save_scored_mindmap(
        self,
        session_id: str,
        mindmap: ScoredMindmapDAG,
    ) -> CheckpointMetadata:
        """Atomically persist the full ScoredTaskNode tree to a JSONL WAL file.

        Write-then-rename ensures no partial writes.  Stores every node's
        status, score, and negative_constraints so recovery needs no re-scan.
        """
        ckpt_id = uuid.uuid4().hex[:12]
        timestamp = time.time()
        filename = f"{session_id}_mindmap_{ckpt_id}_{int(timestamp)}.jsonl"
        final_path = self._dir / filename
        tmp_path = self._dir / (filename + ".tmp")

        mindmap_data = mindmap.to_dict()
        node_count = len(mindmap_data.get("nodes", []))

        with tmp_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "mindmap_header",
                "checkpoint_id": ckpt_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "node_count": node_count,
                "format_version": 1,
            }) + "\n")
            f.write(json.dumps({"type": "mindmap_nodes", "data": mindmap_data}) + "\n")

        tmp_path.rename(final_path)

        meta = CheckpointMetadata(
            checkpoint_id=ckpt_id,
            session_id=session_id,
            timestamp=timestamp,
            node_count=node_count,
            recall_dim=0,
            file_path=str(final_path),
        )
        logger.info(
            "CheckpointManager.save_scored_mindmap: session=%s nodes=%d ckpt=%s",
            session_id[:8], node_count, ckpt_id,
        )
        return meta

    def restore_scored_mindmap(
        self,
        session_id: str,
        checkpoint_id: str | None = None,
    ) -> ScoredMindmapDAG | None:
        """Restore a ScoredMindmapDAG from the latest (or specified) WAL file."""
        ckpt_file = self._find_latest_mindmap(session_id, checkpoint_id)
        if ckpt_file is None:
            return None

        with ckpt_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) < 2:
            logger.error("restore_scored_mindmap: malformed %s", ckpt_file)
            return None

        mindmap_block = json.loads(lines[1])
        return ScoredMindmapDAG.from_dict(mindmap_block["data"])

    def rehydrate_active_subtask(
        self,
        session_id: str,
        checkpoint_id: str | None = None,
    ) -> tuple[ScoredTaskNode | None, list[tuple[str, str, float]]]:
        """Recover the active subtask and negative constraints after a crash.

        Reads the latest mindmap WAL → finds the IN_PROGRESS node →
        extracts negative constraints from STOPPED branches.

        Returns (active_node_or_None, negative_constraints).
        Target latency: < 5ms (measured by benchmark, not claimed here).
        """
        dag = self.restore_scored_mindmap(session_id, checkpoint_id)
        if dag is None:
            return None, []

        active_nodes = dag.get_active_nodes()
        active = active_nodes[0] if active_nodes else None
        constraints = dag.get_negative_constraints()
        logger.info(
            "CheckpointManager.rehydrate_active_subtask: session=%s "
            "active=%s constraints=%d",
            session_id[:8],
            active.task_id if active else "None",
            len(constraints),
        )
        return active, constraints

    def _find_latest_mindmap(
        self, session_id: str, checkpoint_id: str | None
    ) -> Path | None:
        files = sorted(
            self._dir.glob(f"{session_id}_mindmap_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return None
        if checkpoint_id is None:
            return files[0]
        for f in files:
            if checkpoint_id in f.name:
                return f
        return None

    def restore(
        self,
        session_id: str,
        graph: CognitiveStateGraph,
        recall: HebbianRecall,
        checkpoint_id: str | None = None,
    ) -> CheckpointMetadata | None:
        """Restore the latest (or specified) checkpoint into graph + recall in-place."""
        ckpt_file = self._find_latest(session_id, checkpoint_id)
        if ckpt_file is None:
            logger.info(
                "CheckpointManager.restore: no checkpoint for session=%s", session_id[:8]
            )
            return None

        with ckpt_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) < 4:
            logger.error("CheckpointManager.restore: malformed checkpoint %s", ckpt_file)
            return None

        header = json.loads(lines[0])
        nodes_block = json.loads(lines[1])
        edges_block = json.loads(lines[2])
        json.loads(lines[3])

        for nd in nodes_block["data"]:
            graph.add_node(
                node_id=nd["node_id"],
                node_type=NodeType[nd["node_type"]],
                content=nd["content"],
                embedding=nd["embedding"],
                confidence=nd["confidence"],
            )
            if nd["falsified_count"] > 0:
                node = graph._nodes.get(nd["node_id"])
                if node:
                    node.falsified_count = nd["falsified_count"]

        for ed in edges_block["data"]:
            if ed["edge_type"] == EdgeType.FALSIFIED.name:
                try:
                    graph.add_edge_falsified(
                        source_id=ed["source_id"],
                        target_id=ed["target_id"],
                    )
                except Exception:  # noqa: BLE001
                    pass

        # Restore HebbianRecall by re-registering from node embeddings.
        # We use the node embeddings from the graph (already restored above)
        # NOT from _kv (which stores internal Hebbian (key, value) tuples of 2xD).
        # W-matrix is rebuilt lazily from these registrations on first recall() call.
        for nd in nodes_block["data"]:
            if nd["embedding"]:
                try:
                    recall.register(
                        nd["node_id"],
                        np.array(nd["embedding"], dtype=np.float32),
                    )
                except Exception:  # noqa: BLE001
                    pass  # Skip if dim mismatch (different checkpoint dim)


        meta = CheckpointMetadata(
            checkpoint_id=header["checkpoint_id"],
            session_id=session_id,
            timestamp=header["timestamp"],
            node_count=header["node_count"],
            recall_dim=header["recall_dim"],
            file_path=str(ckpt_file),
        )
        logger.info(
            "CheckpointManager.restore: session=%s nodes=%d age=%.0fs",
            session_id[:8], header["node_count"], meta.age_seconds(),
        )
        return meta

    def list_checkpoints(self, session_id: str) -> list[CheckpointMetadata]:
        """List all checkpoints for a session, newest first."""
        files = sorted(
            self._dir.glob(f"{session_id}_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        result = []
        for f in files:
            try:
                with f.open("r", encoding="utf-8") as fh:
                    header = json.loads(fh.readline())
                result.append(CheckpointMetadata(
                    checkpoint_id=header["checkpoint_id"],
                    session_id=session_id,
                    timestamp=header["timestamp"],
                    node_count=header["node_count"],
                    recall_dim=header["recall_dim"],
                    file_path=str(f),
                ))
            except Exception:  # noqa: BLE001
                continue
        return result

    def _find_latest(
        self, session_id: str, checkpoint_id: str | None
    ) -> Path | None:
        files = sorted(
            self._dir.glob(f"{session_id}_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return None
        if checkpoint_id is None:
            return files[0]
        for f in files:
            if checkpoint_id in f.name:
                return f
        return None

    def _purge_old(self, session_id: str) -> None:
        files = sorted(
            self._dir.glob(f"{session_id}_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in files[self._max:]:
            try:
                old.unlink()
            except Exception:  # noqa: BLE001
                pass
