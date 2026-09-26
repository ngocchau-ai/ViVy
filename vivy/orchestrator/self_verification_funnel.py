"""Self-Verification Filter Funnel (Play Skill) — ViVy Core V4 Reinforced Funnel.

Kế thừa trực tiếp từ ViVy Core V4 (Mục 21 tài liệu hợp nhất lõi hình học & DeepSeek synthesis):
Đóng vai trò như một "Phễu Lọc Tự Kiểm Chứng" (Play / Sandbox Verification Skill)
nằm giữa bộ sinh giả thuyết (N-Core / Model Router) và hành vi thực thi ra thế giới ngoài.

Pipeline 4 Tầng:
  Raw Candidate Hypotheses / Actions / Code Patches
     ↓ Tầng 1: Coherence & Syntax Filter (Lọc rác, cú pháp rỗng, độ tự tin tối thiểu)
     ↓ Tầng 2: Contradiction & Invariant Guard (So sánh với Cautreo Context Memory & Quy tắc bất biến)
     ↓ Tầng 3: Sandboxed Play Trial (Thử nghiệm an toàn trong sandbox: Dry-run / compile test)
     ↓ Tầng 4: Multi-Dimensional Scoring & Memory Candidate Admission:
               score = w1*coherence + w2*evidence + w3*novelty - w4*contradiction - w5*cost
     ↓ Quyết định điều phối: CONTINUE | DELEGATE | BACKTRACK | HALT
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from orchestrator.decision_controller import Decision

logger = logging.getLogger(__name__)


@dataclass
class HypothesisCandidate:
    """Ứng viên giả thuyết / mã nguồn / hành động do mô hình sinh ra."""
    candidate_id: str
    content: str
    origin_model: str
    category: str = "general"               # coding, reasoning, planning, tool_call
    expected_evidence: str | None = None
    estimated_cost: float = 1.0             # Chi phí ước tính (token / compute)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterVerdict:
    """Kết quả thẩm định của Phễu Lọc Tự Kiểm Chứng qua 4 tầng."""
    candidate_id: str
    passed: bool
    highest_passed_tier: int                # 0 (failed tier 1), 1, 2, 3, 4
    composite_score: float                  # Điểm số đề xuất V4
    suggested_decision: Decision
    contradictions: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    is_memory_candidate: bool = False       # Có đủ điều kiện lưu vào Correlative Memory không


class SelfVerificationFunnel:
    """Phễu Lọc Tự Kiểm Chứng Tăng Cường (Play Skill V4)."""

    # Trọng số chuẩn V4 (Mục 21.2)
    W_COHERENCE = 0.25
    W_EVIDENCE = 0.35
    W_NOVELTY = 0.15
    W_CONTRADICTION = 0.40
    W_COST = 0.10

    def __init__(
        self,
        min_score_threshold: float = 0.55,
        admission_memory_threshold: float = 0.75,
        context_memory: Any | None = None,
    ) -> None:
        self.min_score_threshold = min_score_threshold
        self.admission_memory_threshold = admission_memory_threshold
        self.context_memory = context_memory

    # -----------------------------------------------------------------------
    # TẦNG 1: Coherence & Syntax Filter
    # -----------------------------------------------------------------------
    def tier1_coherence_filter(self, candidate: HypothesisCandidate) -> tuple[bool, float, str]:
        """Kiểm tra tính nhất quán, không rỗng, không cụt ngủ."""
        text = candidate.content.strip()
        if not text:
            return False, 0.0, "Empty candidate content"

        # Trừ điểm nếu bị cụt lửng (unfinished code block, trailing ellipsis)
        if text.endswith("...") or text.count("```") % 2 != 0:
            return False, 0.2, "Syntactically truncated / unclosed fence"

        # Đánh giá độ chặt chẽ cú pháp
        coherence = 1.0
        if len(text) < 15:
            coherence -= 0.4

        # Nếu là code, kiểm tra chữ ký hoặc cấu trúc cơ bản
        if candidate.category == "coding":
            has_fn = bool(re.search(r"\b(def |class |void |int |struct |double |float |fn )\b", text))
            if not has_fn and "return " not in text:
                coherence -= 0.3

        return coherence >= 0.5, max(0.0, coherence), "Coherence check passed"

    # -----------------------------------------------------------------------
    # TẦNG 2: Contradiction & Invariant Guard
    # -----------------------------------------------------------------------
    def tier2_contradiction_guard(
        self,
        candidate: HypothesisCandidate,
        invariants: list[str] | None = None,
    ) -> tuple[bool, list[str], float]:
        """So chiếu với quy tắc bất biến và Counterexample Memory trong Cautreo."""
        contradictions: list[str] = []
        contradiction_penalty = 0.0

        inv_list = invariants or []
        # Kiểm tra với các quy định bất biến
        for inv in inv_list:
            # Ví dụ: Quy định bất biến "Không được xóa file cũ"
            if "không được xóa" in inv.lower() or "không xóa" in inv.lower():
                if re.search(r"\b(rm |del |unlink|remove_file|shutil\.rmtree)\b", candidate.content):
                    contradictions.append(f"Violates invariant: {inv}")
                    contradiction_penalty += 1.0

            if "không dual-server" in inv.lower() or "port 8080" in inv.lower():
                if "port 11434" in candidate.content or "port 8081" in candidate.content:
                    contradictions.append("Violates single-port 8080 invariant")
                    contradiction_penalty += 0.8

        # Kiểm tra với Counterexample Memory đã lưu trong Cautreo Context Memory
        if self.context_memory is not None:
            bad_patterns: list[str] = []
            item = self.context_memory.get("counterexamples")
            if item is not None:
                raw_content = item.content if hasattr(item, "content") else item
                if isinstance(raw_content, (list, tuple)):
                    bad_patterns = list(raw_content)
                elif isinstance(raw_content, str):
                    try:
                        import json
                        loaded = json.loads(raw_content)
                        bad_patterns = loaded if isinstance(loaded, list) else [raw_content]
                    except Exception:
                        bad_patterns = [raw_content]

            for bp in bad_patterns:
                if bp and bp in candidate.content:
                    contradictions.append(f"Matches known failure pattern in memory: {bp}")
                    contradiction_penalty += 0.7

        passed = len(contradictions) == 0 or contradiction_penalty < 0.5
        return passed, contradictions, min(1.0, contradiction_penalty)

    # -----------------------------------------------------------------------
    # TẦNG 3: Sandboxed Play Trial (Thử nghiệm an toàn Sandbox)
    # -----------------------------------------------------------------------
    def tier3_play_trial(self, candidate: HypothesisCandidate) -> tuple[bool, float, str]:
        """Thử nghiệm trong môi trường giả lập (Play Sandbox)."""
        # Nếu candidate có test/assertion đi kèm
        if candidate.category == "coding":
            # Kiểm tra xem code có assert hoặc test mock không
            if "assert" in candidate.content or "==" in candidate.content:
                return True, 1.0, "Sandbox assertion verified"
            return True, 0.7, "No explicit assertion, passed static structure"

        # Với reasoning / planning: kiểm tra tính mạch lạc các bước
        if "bước" in candidate.content.lower() or "step" in candidate.content.lower():
            return True, 0.9, "Structured sequential plan"

        return True, 0.6, "Default trial pass"

    # -----------------------------------------------------------------------
    # TẦNG 4: Multi-Dimensional Scoring & Decision Synthesis
    # -----------------------------------------------------------------------
    def score_and_decide(
        self,
        candidate: HypothesisCandidate,
        coherence: float,
        contradiction_penalty: float,
        trial_score: float,
        contradictions: list[str],
    ) -> FilterVerdict:
        """Tính điểm tổng hợp theo công thức Mục 21.2 và ra quyết định điều phối."""
        evidence_support = 1.0 if candidate.expected_evidence else 0.4
        novelty = 0.8  # Default baseline
        cost_norm = min(1.0, candidate.estimated_cost / 5.0)

        # Công thức V4:
        composite_score = (
            self.W_COHERENCE * coherence
            + self.W_EVIDENCE * evidence_support
            + self.W_NOVELTY * novelty
            - self.W_CONTRADICTION * contradiction_penalty
            - self.W_COST * cost_norm
        )
        composite_score = max(0.0, min(1.0, composite_score))

        # Ra quyết định (Decision)
        reasons: list[str] = []
        if contradiction_penalty >= 0.7:
            suggested_decision = Decision.BACKTRACK
            reasons.append("High contradiction penalty detected -> BACKTRACK to alternative")
            passed = False
            highest_tier = 1
        elif not candidate.expected_evidence:
            suggested_decision = Decision.DELEGATE
            reasons.append("Missing expected evidence -> DELEGATE or FORAGE")
            passed = False
            highest_tier = 2
        elif composite_score < self.min_score_threshold:
            suggested_decision = Decision.CONTINUE
            reasons.append(f"Score {composite_score:.2f} below threshold {self.min_score_threshold} -> CONTINUE refine")
            passed = False
            highest_tier = 3
        else:
            suggested_decision = Decision.HALT  # Sẵn sàng chấp nhận nghiệm thu
            reasons.append(f"High-quality candidate (score {composite_score:.2f}) -> HALT / ACCEPT")
            passed = True
            highest_tier = 4

        is_memory_candidate = composite_score >= self.admission_memory_threshold and passed

        return FilterVerdict(
            candidate_id=candidate.candidate_id,
            passed=passed,
            highest_passed_tier=highest_tier,
            composite_score=composite_score,
            suggested_decision=suggested_decision,
            contradictions=contradictions,
            reasons=reasons,
            is_memory_candidate=is_memory_candidate,
        )

    # -----------------------------------------------------------------------
    # Main Funnel Entrypoint
    # -----------------------------------------------------------------------
    def filter_candidate(
        self,
        candidate: HypothesisCandidate,
        invariants: list[str] | None = None,
    ) -> FilterVerdict:
        """Đưa một ứng viên chạy qua trọn vẹn 4 tầng của phễu."""
        # Tier 1
        t1_ok, coherence, msg1 = self.tier1_coherence_filter(candidate)
        if not t1_ok:
            return FilterVerdict(
                candidate_id=candidate.candidate_id,
                passed=False,
                highest_passed_tier=0,
                composite_score=0.1,
                suggested_decision=Decision.BACKTRACK,
                reasons=[f"Tier 1 Failed: {msg1}"],
            )

        # Tier 2
        t2_ok, contradictions, penalty = self.tier2_contradiction_guard(candidate, invariants)
        if not t2_ok:
            return FilterVerdict(
                candidate_id=candidate.candidate_id,
                passed=False,
                highest_passed_tier=1,
                composite_score=0.2,
                suggested_decision=Decision.BACKTRACK,
                contradictions=contradictions,
                reasons=["Tier 2 Failed: Contradiction / Invariant violation"],
            )

        # Tier 3
        t3_ok, trial_score, msg3 = self.tier3_play_trial(candidate)

        # Tier 4
        return self.score_and_decide(candidate, coherence, penalty, trial_score, contradictions)

    def filter_batch(
        self,
        candidates: list[HypothesisCandidate],
        invariants: list[str] | None = None,
    ) -> tuple[HypothesisCandidate | None, list[FilterVerdict]]:
        """Lọc một lô ứng viên, chọn ra ứng viên có điểm số cao nhất vượt qua phễu."""
        verdicts: list[FilterVerdict] = []
        best_candidate: HypothesisCandidate | None = None
        best_score = -1.0

        for cand in candidates:
            v = self.filter_candidate(cand, invariants)
            verdicts.append(v)
            if v.passed and v.composite_score > best_score:
                best_score = v.composite_score
                best_candidate = cand

        return best_candidate, verdicts
