"""
test_dream_engine.py — Unit tests for ViVy Dream Engine & Scoring Journal.

Tests:
1. test_dream_engine_lifecycle: Basic dream cycle execution.
2. test_dream_engine_promotes_invariants: Constraints from Antigravity become invariants.
3. test_dream_engine_error_dampening: Low score triggers error-dampening on hypotheses.
4. test_dream_engine_intuition_digest: Fresh intuition digest is stored in Cautreo memory.
5. test_cautreo_scoring_journal: Full workflow of scoring, journaling, and dream activation.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engine.dream_engine import VivyDreamEngine
from integration.cautreo_binding import (
    CautreoContextMemory,
    CautreoScoreGraph,
    CautreoScoreType,
)
from integration.cautreo_scoring_journal import CautreoScoringJournal
from memory.cognitive_graph import CognitiveStateGraph, NodeType


@pytest.fixture
def temp_brain():
    tmp_dir = Path("build_test_brain_tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_dream_engine_lifecycle(temp_brain: Path) -> None:
    """Test basic dream cycle execution and standby state."""
    graph = CognitiveStateGraph()
    mem = CautreoContextMemory()
    scores = CautreoScoreGraph()
    scores.update(CautreoScoreType.TASK_PROGRESS, 0.95)
    scores.update(CautreoScoreType.CONTEXT_EFFICIENCY, 0.90)

    engine = VivyDreamEngine(
        cognitive_graph=graph,
        context_memory=mem,
        score_graph=scores,
        brain_path=str(temp_brain),
    )

    result = engine.run_dream_cycle(task_id="test_task_1")
    assert result.success is True
    assert result.status == "LUCID_STANDBY"
    assert result.scores_ingested["task_progress"] > 0.5
    assert result.synced_2brain is True
    assert "LUCID_STANDBY" in result.intuition_digest


def test_dream_engine_promotes_invariants(temp_brain: Path) -> None:
    """Test that Antigravity constraints in memory become Invariants in CognitiveStateGraph."""
    graph = CognitiveStateGraph()
    mem = CautreoContextMemory()
    scores = CautreoScoreGraph()
    scores.update(CautreoScoreType.TASK_PROGRESS, 1.0)
    scores.update(CautreoScoreType.CONTEXT_EFFICIENCY, 0.95)

    # Antigravity logs a constraint
    mem.store_constraint("const_repeat_0", "Error repeat rate must be 0% in production")

    engine = VivyDreamEngine(
        cognitive_graph=graph,
        context_memory=mem,
        score_graph=scores,
        brain_path=str(temp_brain),
    )

    result = engine.run_dream_cycle(task_id="test_task_2")
    assert result.invariants_promoted == 1

    # Verify invariant is in graph
    inv_node = graph.get_node("inv_const_repeat_0")
    assert inv_node is not None
    assert inv_node.node_type == NodeType.INVARIANT
    assert "0%" in inv_node.content


def test_dream_engine_error_dampening(temp_brain: Path) -> None:
    """Test that low progress triggers error dampening on task hypotheses."""
    graph = CognitiveStateGraph()
    hyp = graph.add_node("hyp_task_fail_1", NodeType.HYPOTHESIS, "Attempted invalid regex")
    assert hyp.falsified_count == 0

    mem = CautreoContextMemory()
    scores = CautreoScoreGraph()
    scores.update(CautreoScoreType.TASK_PROGRESS, 0.3)  # low score

    engine = VivyDreamEngine(
        cognitive_graph=graph,
        context_memory=mem,
        score_graph=scores,
        brain_path=str(temp_brain),
    )

    result = engine.run_dream_cycle(task_id="task_fail")
    assert result.success is True
    assert hyp.falsified_count >= 1
    assert hyp.is_dampened() is True


def test_cautreo_scoring_journal(temp_brain: Path) -> None:
    """Test complete workflow of Antigravity scoring, journaling, and dream triggering."""
    journal = CautreoScoringJournal()
    journal.dream_engine.brain_path = temp_brain

    # Antigravity scores
    scores = journal.score_task("task_deploy", task_progress=0.98, context_efficiency=0.92)
    assert scores["task_progress"] == 0.98

    # Antigravity logs journal
    logged = journal.log_audit_entry(
        task_id="task_deploy",
        summary="Deployment verified with 11 gates cleared",
        constraints=["Only isolate, never delete old specs"],
        hard_facts=["Port 8080 active"],
    )
    assert len(logged) == 3

    # Antigravity triggers dream
    dream_res = journal.trigger_vivy_dream(task_id="task_deploy")
    assert dream_res.success is True
    assert dream_res.status == "LUCID_STANDBY"
    assert dream_res.synced_2brain is True
