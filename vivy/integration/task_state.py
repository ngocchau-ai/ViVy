"""Evidence-bound task state passed into the cognitive core."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memory.cognitive_graph import ScoredTaskNode


@dataclass(frozen=True)
class TaskState:
    """Minimal grounded state; product paths must not invent this state."""

    task_id: str
    goal: str
    observation: str
    constraints: tuple[str, ...] = ()
    recalled_lessons: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    prior_failures: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def state_hash(self) -> str:
        payload = {"task_id": self.task_id, "goal": self.goal,
                   "observation": self.observation, "constraints": self.constraints,
                   "recalled_lessons": self.recalled_lessons,
                   "evidence_ids": self.evidence_ids,
                   "prior_failures": self.prior_failures}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def to_text(self) -> str:
        return "\n".join((f"Goal: {self.goal}", f"Observation: {self.observation}",
                           f"Constraints: {', '.join(self.constraints) or 'NONE'}",
                           f"Lessons: {', '.join(self.recalled_lessons) or 'NONE'}",
                           f"Evidence: {', '.join(self.evidence_ids) or 'NONE'}",
                           f"Prior failures: {', '.join(self.prior_failures) or 'NONE'}"))

    def to_scored_node(self) -> ScoredTaskNode:
        """Convert this TaskState into a ScoredTaskNode (Phase 1 — Mindmap DAG)."""
        from memory.cognitive_graph import ScoredTaskNode, TaskBranchStatus

        return ScoredTaskNode(
            task_id=self.task_id,
            intent=self.goal,
            parent_id=None,
            status=TaskBranchStatus.PENDING,
            negative_constraints=list(self.prior_failures),
        )
