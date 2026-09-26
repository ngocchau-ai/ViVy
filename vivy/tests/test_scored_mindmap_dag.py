"""
Tests — Stateful & Scored Cognitive Mindmap DAG.

PLAN-VIVY-SCORED-MINDMAP-DAG-2026-09-24, Phase 5.
Covers: create+score, stop+falsify, pivot inheritance, sliding aperture
token budget, and WAL checkpoint atomic recovery.
"""

from __future__ import annotations

from integration.preflight_steering import build_active_context, estimate_token_count
from memory.cognitive_graph import (
    CognitiveStateGraph,
    EdgeType,
    ScoredMindmapDAG,
    TaskBranchStatus,
)

# ---------------------------------------------------------------------------
# 1. Create & score → VERIFIED_PASS
# ---------------------------------------------------------------------------


def test_create_and_score_branch() -> None:
    dag = ScoredMindmapDAG()
    node = dag.create_node("subtask-150", intent="Fix parser bug in tokenizer")
    assert node.status == TaskBranchStatus.PENDING

    dag.mark_in_progress("subtask-150")
    scored = dag.score_and_verify("subtask-150", score=10.0, evidence_receipt="receipt-001")
    assert scored.status == TaskBranchStatus.VERIFIED_PASS
    assert scored.score == 10.0
    assert scored.evidence_receipt == "receipt-001"
    assert scored.score_metrics.composite_score > 0.0


# ---------------------------------------------------------------------------
# 2. Stop & falsify → STOPPED + FALSIFIED edge
# ---------------------------------------------------------------------------


def test_stop_and_falsify_branch() -> None:
    graph = CognitiveStateGraph()
    dag = ScoredMindmapDAG(graph=graph)
    dag.create_node("subtask-150", intent="Parse JSON with stdlib")
    dag.mark_in_progress("subtask-150")

    stopped = dag.stop_and_score(
        "subtask-150",
        score=3.0,
        rca_reason="stdlib json cannot handle NaN tokens",
        negative_constraint="Do not use stdlib json for NaN-bearing payloads",
    )

    assert stopped.status == TaskBranchStatus.STOPPED
    assert stopped.score == 3.0
    assert stopped.rca_reason is not None
    assert "NaN" in stopped.negative_constraints[0]

    # FALSIFIED edge must exist in the CognitiveStateGraph
    falsified_edges = [
        e for e in graph.iter_edges(EdgeType.FALSIFIED) if e.source_id == "subtask-150"
    ]
    assert len(falsified_edges) == 1


# ---------------------------------------------------------------------------
# 3. Pivot → inherit negative constraints
# ---------------------------------------------------------------------------


def test_pivot_alternative_inheritance() -> None:
    dag = ScoredMindmapDAG()
    dag.create_node("subtask-150", intent="Parse JSON with stdlib")
    dag.mark_in_progress("subtask-150")
    dag.stop_and_score(
        "subtask-150",
        score=3.0,
        rca_reason="stdlib json cannot handle NaN tokens",
        negative_constraint="Do not use stdlib json for NaN-bearing payloads",
    )

    alt = dag.pivot_alternative(
        failed_task_id="subtask-150",
        new_task_id="subtask-150-alt",
        new_intent="Parse JSON with orjson after NaN preprocessing",
    )

    # New node is IN_PROGRESS and inherits constraints
    assert alt.status == TaskBranchStatus.IN_PROGRESS
    assert alt.task_id == "subtask-150-alt"
    assert len(alt.negative_constraints) == 1
    assert "NaN" in alt.negative_constraints[0]

    # Failed node is PIVOTED and points to the alternative
    failed = dag.get_node("subtask-150")
    assert failed is not None
    assert failed.status == TaskBranchStatus.PIVOTED
    assert failed.alternative_id == "subtask-150-alt"

    # DERIVED_FROM edge exists: new → failed
    derived = [
        e for e in dag.graph.iter_edges(EdgeType.DERIVED_FROM)
        if e.source_id == "subtask-150-alt"
    ]
    assert len(derived) == 1


# ---------------------------------------------------------------------------
# 4. Sliding aperture — prompt < 300 tokens
# ---------------------------------------------------------------------------


def test_context_budget_aperture() -> None:
    dag = ScoredMindmapDAG()
    dag.create_node("subtask-150", intent="Parse JSON with stdlib")
    dag.mark_in_progress("subtask-150")
    dag.stop_and_score(
        "subtask-150",
        score=3.0,
        rca_reason="stdlib json cannot handle NaN tokens",
        negative_constraint="Do not use stdlib json for NaN-bearing payloads",
    )
    alt = dag.pivot_alternative(
        "subtask-150",
        "subtask-150-alt",
        "Parse JSON with orjson after NaN preprocessing",
    )

    prompt = build_active_context(
        current_node=alt,
        parent_node=dag.get_node("subtask-150"),
        negative_constraints=dag.get_negative_constraints(),
        expected_evidence="Valid parsed dict with zero NaN leakage",
    )

    tokens = estimate_token_count(prompt)
    assert tokens < 300, f"Aperture prompt {tokens} tokens exceeds 300 ceiling"
    # Must contain the four required sections
    assert "ACTIVE SUBTASK" in prompt
    assert "NEGATIVE CONSTRAINTS" in prompt or "CẤM ĐOÁN" in prompt
    assert "EVIDENCE CONTRACT" in prompt or "NGHIỆM THU" in prompt


# ---------------------------------------------------------------------------
# 5. WAL checkpoint — atomic save + rehydrate
# ---------------------------------------------------------------------------


def test_checkpoint_atomic_recovery(tmp_path) -> None:
    from integration.checkpoint_manager import CheckpointManager

    dag = ScoredMindmapDAG()
    dag.create_node("subtask-150", intent="Parse JSON with stdlib")
    dag.mark_in_progress("subtask-150")
    dag.stop_and_score(
        "subtask-150",
        score=3.0,
        rca_reason="stdlib json cannot handle NaN tokens",
        negative_constraint="Do not use stdlib json for NaN-bearing payloads",
    )
    dag.pivot_alternative(
        "subtask-150",
        "subtask-150-alt",
        "Parse JSON with orjson after NaN preprocessing",
    )

    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    mgr.save_scored_mindmap("session-recovery", dag)

    # Simulate crash: clear in-RAM state
    del dag

    # Rehydrate from WAL
    active, constraints = mgr.rehydrate_active_subtask("session-recovery")
    assert active is not None
    assert active.task_id == "subtask-150-alt"
    assert active.status == TaskBranchStatus.IN_PROGRESS

    # Failed branch (now PIVOTED) with 3/10 score must be intact
    restored = mgr.restore_scored_mindmap("session-recovery")
    assert restored is not None
    failed = restored.get_node("subtask-150")
    assert failed is not None
    assert failed.status == TaskBranchStatus.PIVOTED
    assert failed.score == 3.0

    # Negative constraints survived
    assert len(constraints) >= 1
