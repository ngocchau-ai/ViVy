"""
cautreo_scoring_journal.py — Antigravity Scoring & Journaling Interface for Cautreo Library.

Cung cấp interface chuyên biệt cho Antigravity IDE (Deputy 1 Coordinator / Auditor):
1. Chấm điểm (Scoring): Ghi nhận điểm số tiến độ, chất lượng bộ nhớ, và hiệu suất
   ngữ cảnh vào Cautreo Runtime Score Graph (C-ABI ct_score_graph_update).
2. Ghi nhật ký (Journaling): Lưu trữ nhận xét, quy tắc bất biến mới (constraints),
   và bằng chứng (hard facts) vào Cautreo Native Memory (C-ABI ct_context_memory_put)
   để ViVy có thể đọc trực tiếp từ RAM native 0ms latency.
3. Kích hoạt Dream Engine (Dream Consolidation): Gọi chu trình Dream củng cố nhận
   thức của ViVy mỗi khi ViVy hoàn thành task và chuyển sang trạng thái chờ (Idle/Standby).

Changelog:
    21/09/2026 (Antigravity IDE — HoH Default Agent & Dream Engine): Initial implementation.
"""

from __future__ import annotations

import argparse
import logging
import time

try:
    from engine.dream_engine import (
        DreamCycleResult,
        VivyDreamEngine,
    )
    from integration.cautreo_binding import (
        CautreoContextMemory,
        CautreoScoreGraph,
        CautreoScoreType,
    )
except ImportError:
    from unitary_reasoner.engine.dream_engine import (  # type: ignore[no-redef]
        DreamCycleResult,
        VivyDreamEngine,
    )
    from unitary_reasoner.integration.cautreo_binding import (  # type: ignore[no-redef]
        CautreoContextMemory,
        CautreoScoreGraph,
        CautreoScoreType,
    )

logger = logging.getLogger(__name__)


class CautreoScoringJournal:
    """Công cụ chấm điểm và ghi nhật ký của Antigravity IDE vào Cautreo Library."""

    def __init__(
        self,
        context_memory: CautreoContextMemory | None = None,
        score_graph: CautreoScoreGraph | None = None,
    ) -> None:
        self.context_memory = context_memory or CautreoContextMemory()
        self.score_graph = score_graph or CautreoScoreGraph()
        self.dream_engine = VivyDreamEngine(
            context_memory=self.context_memory,
            score_graph=self.score_graph,
        )

    def score_task(
        self,
        task_id: str,
        task_progress: float = 1.0,
        context_efficiency: float = 1.0,
        memory_quality: float = 1.0,
        precision_fit: float = 1.0,
    ) -> dict[str, float]:
        """Chấm điểm hiệu năng thực thi của ViVy vào Cautreo Score Graph.

        Các tham số nằm trong khoảng [0.0, 1.0].
        """
        self.score_graph.update(CautreoScoreType.TASK_PROGRESS, float(task_progress))
        self.score_graph.update(CautreoScoreType.CONTEXT_EFFICIENCY, float(context_efficiency))
        self.score_graph.update(CautreoScoreType.MEMORY_QUALITY, float(memory_quality))
        self.score_graph.update(CautreoScoreType.PRECISION_FIT, float(precision_fit))

        scores = {
            "task_progress": task_progress,
            "context_efficiency": context_efficiency,
            "memory_quality": memory_quality,
            "precision_fit": precision_fit,
        }
        logger.info("[Antigravity Scorer] Đã chấm điểm task '%s': %s", task_id, scores)
        return scores

    def log_audit_entry(
        self,
        task_id: str,
        summary: str,
        constraints: list[str] | None = None,
        hard_facts: list[str] | None = None,
    ) -> list[str]:
        """Ghi nhật ký thẩm định và chỉ thị mới vào Cautreo Native Memory."""
        logged_ids: list[str] = []
        now_ts = int(time.time())

        # 1. Ghi nhận xét / báo cáo tóm tắt
        if summary:
            sum_id = f"eval_{task_id}_{now_ts}"
            self.context_memory.store_summary(sum_id, f"[Antigravity QA] {summary}")
            logged_ids.append(sum_id)

        # 2. Ghi các ràng buộc / bài học để ViVy không lặp lại sai lầm
        if constraints:
            for idx, c in enumerate(constraints):
                cid = f"const_{task_id}_{idx}_{now_ts}"
                self.context_memory.store_constraint(cid, c)
                logged_ids.append(cid)

        # 3. Ghi các bằng chứng thực tế
        if hard_facts:
            for idx, f in enumerate(hard_facts):
                fid = f"fact_{task_id}_{idx}_{now_ts}"
                self.context_memory.store_hard_fact(fid, f)
                logged_ids.append(fid)

        logger.info("[Antigravity Journal] Đã ghi %d mục vào Cautreo Context Memory", len(logged_ids))
        return logged_ids

    def trigger_vivy_dream(
        self,
        task_id: str = "current_session",
        idle_duration_s: float = 0.0,
    ) -> DreamCycleResult:
        """Kích hoạt cơ chế Dream cho ViVy khi rơi vào trạng thái chờ nhiệm vụ mới."""
        logger.info("[Antigravity] Kích hoạt cơ chế Dream cho ViVy (task: %s)...", task_id)
        result = self.dream_engine.run_dream_cycle(
            task_id=task_id,
            idle_duration_s=idle_duration_s,
        )
        return result

    def log_scored_branch(
        self,
        task_id: str,
        status: str,
        score: float,
        rca_reason: str | None = None,
        negative_constraints: list[str] | None = None,
    ) -> list[str]:
        """Log a ScoredTaskNode branch outcome into Cautreo Native Memory.

        Phase 2 integration — PLAN-VIVY-SCORED-MINDMAP-DAG-2026-09-24.
        Stores the branch verdict as a hard fact and its negative
        constraints as durable constraint entries.
        """
        logged_ids: list[str] = []
        now_ts = int(time.time())

        verdict = (
            f"Branch {task_id} → {status} | score={score:.1f}/10"
            + (f" | RCA: {rca_reason}" if rca_reason else "")
        )
        fact_id = f"branch_{task_id}_{now_ts}"
        self.context_memory.store_hard_fact(fact_id, verdict)
        logged_ids.append(fact_id)

        if negative_constraints:
            for idx, c in enumerate(negative_constraints):
                cid = f"negconst_{task_id}_{idx}_{now_ts}"
                self.context_memory.store_constraint(cid, c)
                logged_ids.append(cid)

        logger.info(
            "[Antigravity Journal] Scored branch %s → %s (%.1f/10), %d constraints",
            task_id, status, score, len(negative_constraints or []),
        )
        return logged_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Scoring & Journaling Interface for Cautreo")
    parser.add_argument("--task-id", default="session_latest", help="Mã nhiệm vụ vừa thực thi")
    parser.add_argument("--progress", type=float, default=1.0, help="Điểm tiến độ [0.0 - 1.0]")
    parser.add_argument("--efficiency", type=float, default=1.0, help="Điểm hiệu quả ngữ cảnh [0.0 - 1.0]")
    parser.add_argument("--memory-quality", type=float, default=1.0, help="Điểm chất lượng nhớ [0.0 - 1.0]")
    parser.add_argument("--summary", default="", help="Nhận xét thẩm định của Antigravity")
    parser.add_argument("--constraint", action="append", default=[], help="Ràng buộc/bài học mới cho ViVy")
    parser.add_argument("--hard-fact", action="append", default=[], help="Bằng chứng/fact cần lưu")
    parser.add_argument("--dream", action="store_true", help="Kích hoạt ngay chu trình Dream sau khi ghi")
    args = parser.parse_args()

    journal = CautreoScoringJournal()

    # 1. Chấm điểm
    scores = journal.score_task(
        task_id=args.task_id,
        task_progress=args.progress,
        context_efficiency=args.efficiency,
        memory_quality=args.memory_quality,
    )
    print(f"\n[OK] Antigravity chấm điểm vào Cautreo Score Graph: {scores}")

    # 2. Ghi nhật ký
    logged = journal.log_audit_entry(
        task_id=args.task_id,
        summary=args.summary or "Hoàn thành nhiệm vụ đạt chuẩn chất lượng.",
        constraints=args.constraint,
        hard_facts=args.hard_fact,
    )
    print(f"[OK] Đã ghi nhật ký vào Cautreo Context Memory: {len(logged)} items")

    # 3. Kích hoạt Dream nếu có cờ --dream
    if args.dream:
        print("\n[*] Kích hoạt cơ chế Dream cho ViVy...")
        dream_res = journal.trigger_vivy_dream(task_id=args.task_id)
        print(f"[OK] ViVy Dream Status: {dream_res.status} (Elapsed: {dream_res.elapsed_ms:.1f}ms)")
        print(f"     Reinforced Nodes: {dream_res.nodes_reinforced} | Promoted Invariants: {dream_res.invariants_promoted}")
        print(f"     Intuition Digest: {len(dream_res.intuition_digest)} chars")
        print(f"     2Brain Synced: {dream_res.synced_2brain}")


if __name__ == "__main__":
    main()
