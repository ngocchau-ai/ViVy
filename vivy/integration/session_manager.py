"""
Session Manager — ViVy Sprint 3.

Isolate CognitiveStateGraph và HebbianRecall per session.
Mỗi session là 1 ngữ cảnh tư duy độc lập, không lẫn lộn state.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from memory.cognitive_graph import CognitiveStateGraph
from memory.hebbian_recall import HebbianRecall
from orchestrator.graph_bridge import GraphBridge

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


@dataclass
class ViVySession:
    """One isolated ViVy reasoning session.

    Attributes
    ----------
    session_id:
        Unique identifier (UUID4 hex).
    graph:
        CognitiveStateGraph for this session.
    recall:
        HebbianRecall W-matrix for this session.
    bridge:
        GraphBridge wiring graph and recall together.
    created_at:
        Unix timestamp of session creation.
    last_active:
        Unix timestamp of last inference call.
    metadata:
        Arbitrary key-value metadata (e.g., user_id, task_context).
    """

    session_id: str
    graph: CognitiveStateGraph
    recall: HebbianRecall
    bridge: GraphBridge
    created_at: float
    last_active: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update last_active timestamp."""
        self.last_active = time.time()

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_active


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


class SessionManager:
    """Create, retrieve, and expire ViVy sessions.

    Each session gets its own CognitiveStateGraph + HebbianRecall,
    ensuring complete cognitive isolation between users/tasks.

    Parameters
    ----------
    hidden_dim:
        Embedding dimension (must match ElasticNCore.hidden_dim). Default 64.
    max_sessions:
        Maximum number of concurrent sessions. LRU eviction when exceeded.
    ttl_seconds:
        Time-to-live for idle sessions. Default 3600 (1 hour).
    graph_max_nodes:
        Max nodes per session graph.
    """

    def __init__(
        self,
        hidden_dim: int = 64,
        max_sessions: int = 32,
        ttl_seconds: float = 3600.0,
        graph_max_nodes: int = 5000,
    ) -> None:
        self._dim = hidden_dim
        self._max = max_sessions
        self._ttl = ttl_seconds
        self._graph_max = graph_max_nodes

        self._sessions: dict[str, ViVySession] = {}
        self._lock = threading.RLock()

        logger.info(
            "SessionManager: dim=%d max=%d ttl=%.0fs",
            hidden_dim, max_sessions, ttl_seconds,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ViVySession:
        """Create a new session with isolated cognitive state.

        Parameters
        ----------
        session_id:
            Optional explicit ID. If None, generates UUID4 hex.
        metadata:
            Optional metadata dict to attach to the session.

        Returns
        -------
        ViVySession
        """
        sid = session_id or uuid.uuid4().hex
        now = time.time()

        session = ViVySession(
            session_id=sid,
            graph=CognitiveStateGraph(max_nodes=self._graph_max),
            recall=HebbianRecall(dim=self._dim),
            bridge=GraphBridge(dampening_noise_floor=0.05, auto_register=True),
            created_at=now,
            last_active=now,
            metadata=metadata or {},
        )

        with self._lock:
            self._evict_if_needed()
            self._sessions[sid] = session

        logger.debug("SessionManager: created session %s", sid[:8])
        return session

    def get_session(self, session_id: str) -> ViVySession | None:
        """Retrieve an existing session by ID.

        Returns None if session not found or has expired (TTL exceeded).
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.idle_seconds > self._ttl:
                logger.info("SessionManager: evicting idle session %s", session_id[:8])
                del self._sessions[session_id]
                return None
            session.touch()
            return session

    def get_or_create(
        self,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> ViVySession:
        """Get existing session or create a new one."""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id=session_id, metadata=metadata)
        return session

    def destroy_session(self, session_id: str) -> bool:
        """Explicitly destroy a session and free its memory."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug("SessionManager: destroyed session %s", session_id[:8])
                return True
            return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions with basic stats."""
        with self._lock:
            result = []
            for sid, s in self._sessions.items():
                result.append({
                    "session_id": sid,
                    "age_seconds": round(s.age_seconds, 1),
                    "idle_seconds": round(s.idle_seconds, 1),
                    "graph_nodes": len(s.graph),
                    "metadata": s.metadata,
                })
            return result

    def prune_expired(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if s.idle_seconds > self._ttl
            ]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                logger.info("SessionManager: pruned %d expired sessions", len(expired))
            return len(expired)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_if_needed(self) -> None:
        """LRU eviction when max_sessions is exceeded. Must be called under lock."""
        if len(self._sessions) < self._max:
            return
        # Sort by last_active ascending (oldest first)
        oldest_sid = min(self._sessions, key=lambda sid: self._sessions[sid].last_active)
        logger.info(
            "SessionManager: LRU evict session %s (idle=%.0fs)",
            oldest_sid[:8],
            self._sessions[oldest_sid].idle_seconds,
        )
        del self._sessions[oldest_sid]
