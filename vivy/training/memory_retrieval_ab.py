"""C10 — memory retrieval quality + memory-on/off A/B on held-out tasks.

Acceptance-plan C10.4–C10.5: retrieve relevant/contradictory/stale memory;
compare memory-on/off with the same backend; report gain/harm with
denominators; no cross-session leak; no physical-zero latency claim.

Changelog:
    2026-09-24 (Claude Code — P5 C10): Initial.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Sequence

LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"
STATUS_LABEL = "PROVISIONAL_RESULT"
BACKEND_ID = "lexical-overlap-v1"


@dataclass(frozen=True)
class MemoryCase:
    memory_id: str
    content: str
    tags: frozenset[str] | set[str]
    session_id: str
    created_at_ms: int
    expires_at_ms: int
    contradicts: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", frozenset(self.tags))


@dataclass(frozen=True)
class RetrievalTask:
    task_id: str
    query: str
    gold_memory_id: str | None
    candidates: tuple[str, ...]


def _alive(m: MemoryCase, now_ms: int) -> bool:
    return m.expires_at_ms == 0 or now_ms < m.expires_at_ms


def retrieve_memories(
    query: str,
    store: Sequence[MemoryCase],
    *,
    now_ms: int,
    session_id: str,
) -> dict:
    """Return active / stale / contradiction partitions for one session.

    Cross-session items are never returned. Expired items land in
    `stale_ids`, not `active`. Items whose `contradicts` points at another
    retrieved item are listed in `contradiction_ids`.
    """
    q_tokens = set(query.lower().split())
    active: list[MemoryCase] = []
    stale_ids: list[str] = []
    skipped_sessions: list[str] = []

    for m in store:
        if m.session_id != session_id:
            skipped_sessions.append(m.memory_id)
            continue
        if not _alive(m, now_ms):
            stale_ids.append(m.memory_id)
            continue
        tokens = set(m.content.lower().split())
        if q_tokens & tokens or m.tags & {"relevant", "contradictory"}:
            active.append(m)

    active_ids = {m.memory_id for m in active}
    contradiction_ids = [
        m.memory_id for m in active if m.contradicts and m.contradicts in active_ids
    ]
    # also surface pre-flagged contradictory tags that are active
    for m in active:
        if "contradictory" in m.tags and m.memory_id not in contradiction_ids:
            contradiction_ids.append(m.memory_id)

    return {
        "active": active,
        "stale_ids": stale_ids,
        "contradiction_ids": contradiction_ids,
        "cross_session_skipped": skipped_sessions,
    }


@dataclass
class RetrievalScoreboard:
    correct: int = 0
    wrong: int = 0
    abstain: int = 0
    latency_ms: list[float] = field(default_factory=list)

    @property
    def denominator(self) -> int:
        return self.correct + self.wrong + self.abstain

    def as_dict(self) -> dict:
        n = self.denominator
        return {
            "correct": self.correct,
            "wrong": self.wrong,
            "abstain": self.abstain,
            "denominator": n,
            "accuracy": (self.correct / n) if n else None,
            "latency_ms_median": (
                sorted(self.latency_ms)[len(self.latency_ms) // 2] if self.latency_ms else None
            ),
        }


def _predict(
    task: RetrievalTask,
    visible: Sequence[MemoryCase],
) -> str | None:
    """Same backend for both arms. With no visible memory → abstain.

    Picks the candidate whose id matches the highest-overlap visible memory.
    """
    if not visible:
        return None
    q_tokens = set(task.query.lower().split())
    best_id = None
    best_score = -1
    for m in visible:
        if m.memory_id not in task.candidates:
            continue
        score = len(q_tokens & set(m.content.lower().split()))
        if score > best_score:
            best_score = score
            best_id = m.memory_id
    if best_score <= 0:
        return None
    return best_id


def run_memory_on_off(
    tasks: Sequence[RetrievalTask],
    store: Sequence[MemoryCase],
    *,
    session_id: str,
    seed: int = 0,
    now_ms: int | None = None,
) -> dict:
    """Paired memory-on / memory-off comparison on the same backend.

    Arm ON retrieves session-scoped memory; arm OFF sees an empty store.
    Gain/harm/tie are counted per task against the gold memory id.
    """
    del seed  # deterministic backend; kept for protocol symmetry
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    on = RetrievalScoreboard()
    off = RetrievalScoreboard()
    gain = harm = tie = 0

    for task in tasks:
        retrieved = retrieve_memories(task.query, store, now_ms=now, session_id=session_id)
        visible_on = retrieved["active"]
        visible_off: list[MemoryCase] = []

        t0 = time.perf_counter()
        pred_on = _predict(task, visible_on)
        on.latency_ms.append((time.perf_counter() - t0) * 1000.0)

        t1 = time.perf_counter()
        pred_off = _predict(task, visible_off)
        off.latency_ms.append((time.perf_counter() - t1) * 1000.0)

        def score(sb: RetrievalScoreboard, pred: str | None) -> bool:
            if pred is None:
                sb.abstain += 1
                return False
            if task.gold_memory_id is None:
                sb.abstain += 1
                return False
            if pred == task.gold_memory_id:
                sb.correct += 1
                return True
            sb.wrong += 1
            return False

        on_ok = score(on, pred_on)
        off_ok = score(off, pred_off)
        if on_ok and not off_ok:
            gain += 1
        elif off_ok and not on_ok:
            harm += 1
        else:
            tie += 1

    on_d = on.as_dict()
    off_d = off.as_dict()
    on_d["memory_visible"] = True
    off_d["memory_visible"] = False

    return {
        "backend_id": BACKEND_ID,
        "backend_id_on": BACKEND_ID,
        "backend_id_off": BACKEND_ID,
        "session_id": session_id,
        "n_tasks": len(tasks),
        "arm_on": on_d,
        "arm_off": off_d,
        "gain": gain,
        "harm": harm,
        "tie": tie,
        "latency_claim": LATENCY_CLAIM,
        "status_label": STATUS_LABEL,
        "note": (
            "paired A/B on one backend; denominators are task counts; "
            "latency is wall-clock observation, not a physical-zero claim"
        ),
    }
