"""Unit tests for SelfVerificationFunnel (Play Skill V4 Reinforced Funnel)."""

from __future__ import annotations

from orchestrator.decision_controller import Decision
from orchestrator.self_verification_funnel import (
    HypothesisCandidate,
    SelfVerificationFunnel,
)


class MockContextMemory:
    def __init__(self, data: dict | None = None) -> None:
        self.data = data or {}

    def get(self, key: str, default=None):
        return self.data.get(key, default)


def test_tier1_rejects_empty_and_truncated():
    funnel = SelfVerificationFunnel()

    empty_cand = HypothesisCandidate(candidate_id="c1", content="", origin_model="test")
    v1 = funnel.filter_candidate(empty_cand)
    assert not v1.passed
    assert v1.highest_passed_tier == 0
    assert v1.suggested_decision == Decision.BACKTRACK

    trunc_cand = HypothesisCandidate(
        candidate_id="c2",
        content="```python\ndef test():\n    return 1\n", # Thiếu unclosed fence
        origin_model="test",
    )
    v2 = funnel.filter_candidate(trunc_cand)
    assert not v2.passed
    assert v2.highest_passed_tier == 0


def test_tier2_catches_invariants_and_memory_counterexamples():
    mem = MockContextMemory({"counterexamples": ["bad_kernel_call", "deadlock_mutex"]})
    funnel = SelfVerificationFunnel(context_memory=mem)

    # Vi phạm quy tắc bất biến "Không được xóa file cũ"
    del_cand = HypothesisCandidate(
        candidate_id="c3",
        content="def cleanup():\n    shutil.rmtree('/data/old_files')\n    return True\n",
        origin_model="test",
        category="coding",
        expected_evidence="files_deleted",
    )
    v_del = funnel.filter_candidate(del_cand, invariants=["QUY ĐỊNH: Không được xóa file cũ"])
    assert not v_del.passed
    assert any("Violates invariant" in c for c in v_del.contradictions)
    assert v_del.suggested_decision == Decision.BACKTRACK

    # Khớp với Counterexample Memory
    bad_cand = HypothesisCandidate(
        candidate_id="c4",
        content="void execute() { bad_kernel_call(); }",
        origin_model="test",
        category="coding",
        expected_evidence="kernel_ok",
    )
    v_bad = funnel.filter_candidate(bad_cand)
    assert not v_bad.passed
    assert any("known failure pattern" in c for c in v_bad.contradictions)


def test_tier3_and_tier4_scoring_and_admission():
    funnel = SelfVerificationFunnel(min_score_threshold=0.6, admission_memory_threshold=0.7)

    # Ứng viên chất lượng cao có assertion
    good_cand = HypothesisCandidate(
        candidate_id="c5",
        content="int add(int a, int b) {\n    return a + b;\n}\n// assert(add(2, 3) == 5)\n",
        origin_model="qwen2.5-coder",
        category="coding",
        expected_evidence="assert(add(2,3)==5) == true",
        estimated_cost=0.5,
    )
    v_good = funnel.filter_candidate(good_cand)
    assert v_good.passed
    assert v_good.highest_passed_tier == 4
    assert v_good.composite_score >= 0.7
    assert v_good.suggested_decision == Decision.HALT
    assert v_good.is_memory_candidate


def test_filter_batch_selects_best():
    funnel = SelfVerificationFunnel()

    cand1 = HypothesisCandidate(
        candidate_id="c_weak",
        content="int add(int a, int b) { return a + b; }",
        origin_model="model_a",
        category="coding",
        expected_evidence=None, # Missing evidence -> DELEGATE
    )
    cand2 = HypothesisCandidate(
        candidate_id="c_strong",
        content="int add(int a, int b) {\n    return a + b;\n}\n// assert(add(2, 3) == 5)",
        origin_model="qwen2.5-coder",
        category="coding",
        expected_evidence="test passes",
    )

    best, verdicts = funnel.filter_batch([cand1, cand2])
    assert best is not None
    assert best.candidate_id == "c_strong"
    assert len(verdicts) == 2
