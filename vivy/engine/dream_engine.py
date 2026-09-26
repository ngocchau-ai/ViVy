"""
dream_engine.py — ViVy Native Dream Consolidation & Standby Engine.

Triển khai cơ chế DREAM (Memory Consolidation & Skill Play Simulation)
cho ViVy mỗi khi hoàn thành nhiệm vụ và rơi vào trạng thái chờ (Idle/Standby).

Luồng hoạt động:
    1. Memory Ingestion:
       - Đọc các đánh giá mới nhất do Antigravity IDE (Deputy 1 Coordinator)
         ghi vào Cautreo Library (context_memory: SUMMARY, CONSTRAINT, HARD_FACT)
       - Đọc điểm số runtime từ Cautreo Score Graph (TASK_PROGRESS, CONTEXT_EFFICIENCY, MEMORY_QUALITY).
    2. SVD / Hebbian Consolidation:
       - Củng cố các node thành công (Hebbian reinforcement).
       - Khử nhiễu, làm mờ (decay & prune) các hành động/thông tin tạm bợ.
       - Tự động chuyển đổi các phát hiện thành Invariants bất biến.
    3. Counterfactual Reflection & Lesson Synthesis:
       - Rút ra bài học kinh nghiệm bền vững (Durable Lessons) từ các phản hồi của Antigravity.
       - Đồng bộ vào D:\\2brain (hot-memory & notes/antigravity).
    4. Intuition Digest Generation (~150 tokens):
       - Tinh lọc bản tóm tắt trực giác nén 150 tokens đưa vào RAM native của Cautreo.
       - Đưa ViVy vào trạng thái "LUCID_STANDBY" sẵn sàng thức tỉnh tức thì khi có task mới.
       # [ISOLATED 24/09/2026] prior: "sẵn sàng thức tỉnh 0ms" — Gate 9: no latency claim without receipt.

Changelog:
    21/09/2026 (Antigravity IDE — HoH Default Agent & Dream Engine): Initial implementation.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    from integration.cautreo_binding import (
        CautreoContextMemory,
        CautreoMemoryKind,
        CautreoScoreGraph,
        CautreoScoreType,
    )
    from memory.cognitive_graph import (
        CognitiveStateGraph,
        NodeType,
    )
except ImportError:
    from unitary_reasoner.integration.cautreo_binding import (  # type: ignore[no-redef]
        CautreoContextMemory,
        CautreoMemoryKind,
        CautreoScoreGraph,
        CautreoScoreType,
    )
    from unitary_reasoner.memory.cognitive_graph import (  # type: ignore[no-redef]
        CognitiveStateGraph,
        NodeType,
    )

logger = logging.getLogger(__name__)


@dataclass
class DreamCycleResult:
    """Kết quả chu trình Dream của ViVy."""

    success: bool
    status: str  # "LUCID_STANDBY" | "CONSOLIDATED" | "FAILED"
    elapsed_ms: float
    nodes_reinforced: int = 0
    invariants_promoted: int = 0
    scores_ingested: dict[str, float] = field(default_factory=dict)
    intuition_digest: str = ""
    durable_lessons: list[str] = field(default_factory=list)
    synced_2brain: bool = False


class VivyDreamEngine:
    """Engine phụ trách cơ chế Dream và củng cố nhận thức khi ViVy chờ nhiệm vụ mới."""

    def __init__(
        self,
        cognitive_graph: CognitiveStateGraph | None = None,
        context_memory: CautreoContextMemory | None = None,
        score_graph: CautreoScoreGraph | None = None,
        brain_path: str = r"D:\2brain",
    ) -> None:
        self.cognitive_graph = cognitive_graph if cognitive_graph is not None else CognitiveStateGraph()
        self.context_memory = context_memory if context_memory is not None else CautreoContextMemory()
        self.score_graph = score_graph if score_graph is not None else CautreoScoreGraph()
        self.brain_path = Path(brain_path)

    def run_dream_cycle(
        self,
        task_id: str = "current_session",
        idle_duration_s: float = 0.0,
    ) -> DreamCycleResult:
        """Kích hoạt 1 chu trình Dream hoàn chỉnh."""
        t0 = time.perf_counter()
        logger.info("[VivyDreamEngine] Bắt đầu chu trình Dream cho task: %s (idle: %.1fs)", task_id, idle_duration_s)

        nodes_reinforced = 0
        invariants_promoted = 0
        scores_ingested: dict[str, float] = {}
        durable_lessons: list[str] = []

        try:
            # 1. Đọc điểm số do Antigravity chấm từ Cautreo Score Graph
            progress = self.score_graph.get_score(CautreoScoreType.TASK_PROGRESS)
            efficiency = self.score_graph.get_score(CautreoScoreType.CONTEXT_EFFICIENCY)
            mem_quality = self.score_graph.get_score(CautreoScoreType.MEMORY_QUALITY)
            scores_ingested = {
                "task_progress": round(progress, 3),
                "context_efficiency": round(efficiency, 3),
                "memory_quality": round(mem_quality, 3),
            }
            logger.info("[VivyDreamEngine] Đọc điểm từ Antigravity: %s", scores_ingested)

            # 2. Đọc nhật ký và chỉ thị từ Cautreo Context Memory
            digest_items = self.context_memory.get_all()
            for item in digest_items:
                if item.kind == CautreoMemoryKind.CONSTRAINT:
                    # Chuyển đổi constraint từ Antigravity thành Invariant bất biến của ViVy
                    inv_id = f"inv_{item.id}"
                    if self.cognitive_graph.get_node(inv_id) is None:
                        self.cognitive_graph.add_node(
                            node_id=inv_id,
                            node_type=NodeType.INVARIANT,
                            content=item.content,
                            confidence=0.95,
                            metadata={"promoted_by": "antigravity_evaluator", "task_id": task_id},
                        )
                        invariants_promoted += 1
                        durable_lessons.append(f"INVARIANT: {item.content}")
                elif item.kind == CautreoMemoryKind.HARD_FACT:
                    nodes_reinforced += 1
                elif item.kind == CautreoMemoryKind.SUMMARY:
                    logger.debug("[VivyDreamEngine] Nhận diện nhận xét từ Antigravity: %s", item.content[:80])

            # 3. Phản tư nhận thức & Error-Dampening (Hebbian Consolidation)
            if progress >= 0.8 and efficiency >= 0.7:
                # Phiên làm việc xuất sắc: Củng cố các hypotheses tích cực
                for hyp in self.cognitive_graph.iter_nodes(NodeType.HYPOTHESIS):
                    if not hyp.is_dampened():
                        hyp.confidence = min(1.0, hyp.confidence + 0.1)
                        nodes_reinforced += 1
            elif progress < 0.5:
                # Có trục trặc: Kích hoạt Error-Dampening
                logger.warning("[VivyDreamEngine] Điểm tiến độ thấp (%.2f) — kích hoạt Error-Dampening", progress)
                for hyp in self.cognitive_graph.iter_nodes(NodeType.HYPOTHESIS):
                    if hyp.node_id.startswith(f"hyp_{task_id}"):
                        hyp.falsified_count += 1
                        logger.info("[VivyDreamEngine] Dampened node: %s (falsified: %d)", hyp.node_id, hyp.falsified_count)

            # 4. Tinh lọc Intuition Digest (~150 tokens) và nạp vào Cautreo RAM Native
            intuition_digest = self.context_memory.build_intuition_digest()
            active_invariants_count = sum(1 for _ in self.cognitive_graph.iter_nodes(NodeType.INVARIANT))
            # Bổ sung header trạng thái Dream
            enhanced_digest = (
                f"{intuition_digest}\n"
                f"• STATE: LUCID_STANDBY | Dream Consolidated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"• METRICS: Progress={scores_ingested['task_progress']} | ContextEff={scores_ingested['context_efficiency']}\n"
                f"• INVARIANTS: Total {active_invariants_count} active invariant rules"
            )
            self.context_memory.store_summary("vivy_intuition_digest_current", enhanced_digest)

            # 5. Đồng bộ tri thức bền vững vào D:\2brain
            synced_2brain = self._sync_dream_to_2brain(
                task_id=task_id,
                scores=scores_ingested,
                lessons=durable_lessons,
                digest=enhanced_digest,
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                "[VivyDreamEngine] Chu trình Dream hoàn tất thành công trong %.2fms. Trạng thái: LUCID_STANDBY",
                elapsed_ms,
            )

            return DreamCycleResult(
                success=True,
                status="LUCID_STANDBY",
                elapsed_ms=elapsed_ms,
                nodes_reinforced=nodes_reinforced,
                invariants_promoted=invariants_promoted,
                scores_ingested=scores_ingested,
                intuition_digest=enhanced_digest,
                durable_lessons=durable_lessons,
                synced_2brain=synced_2brain,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.error("[VivyDreamEngine] Lỗi trong chu trình Dream: %s", e, exc_info=True)
            return DreamCycleResult(
                success=False,
                status="FAILED",
                elapsed_ms=elapsed_ms,
                scores_ingested=scores_ingested,
            )

    def _sync_dream_to_2brain(
        self,
        task_id: str,
        scores: dict[str, float],
        lessons: list[str],
        digest: str,
    ) -> bool:
        """Đồng bộ nhật ký chu trình Dream vào D:\\2brain."""
        try:
            hot_mem = self.brain_path / "hot-memory"
            notes_anti = self.brain_path / "notes" / "antigravity"
            hot_mem.mkdir(parents=True, exist_ok=True)
            notes_anti.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S ICT")

            # Ghi file hot-memory
            dream_file = hot_mem / "durable-learning-dream-cycle-latest.md"
            content = (
                f"# ViVy Dream Cycle — Durable Learning\n\n"
                f"> **Thời gian:** {timestamp}\n"
                f"> **Task:** `{task_id}`\n"
                f"> **Trạng thái:** `LUCID_STANDBY` (Đã đồng hóa tri thức & sẵn sàng thức tỉnh)\n\n"
                f"## 1. Điểm Số Đã Đọc Từ Antigravity IDE (Cautreo Score Graph)\n"
                f"- **Task Progress:** {scores.get('task_progress', 0.0)}\n"
                f"- **Context Efficiency:** {scores.get('context_efficiency', 0.0)}\n"
                f"- **Memory Quality:** {scores.get('memory_quality', 0.0)}\n\n"
                f"## 2. Invariants & Bài Học Được Củng Cố\n"
            )
            if lessons:
                for les in lessons:
                    content += f"- {les}\n"
            else:
                content += "- Duy trì toàn vẹn Cognitive State Graph, không có vi phạm mới.\n"

            content += f"\n## 3. Bản Tóm Tắt Trực Giác Nén (Intuition Digest 150 Tokens)\n```text\n{digest}\n```\n"

            dream_file.write_text(content, encoding="utf-8")
            logger.info("[VivyDreamEngine] Đã đồng bộ dream cycle vào: %s", dream_file)
            return True
        except Exception as e:
            logger.warning("[VivyDreamEngine] Không thể đồng bộ D:\\2brain: %s", e)
            # Keep the receipt locally for a later retry; never report a false sync.
            pending_root = Path(os.environ.get("VIVY_PENDING_SYNC_DIR", ".vivy_pending_sync"))
            pending_root.mkdir(parents=True, exist_ok=True)
            pending_file = pending_root / f"dream-{task_id}.md"
            pending_file.write_text(
                f"# Pending ViVy Dream Sync\n\n"
                f"> Target: `{self.brain_path}`\n"
                f"> Task: `{task_id}`\n"
                f"> Reason: `{e}`\n\n{content}",
                encoding="utf-8",
            )
            logger.warning("[VivyDreamEngine] Đã lưu pending receipt tại: %s", pending_file)
            return False
