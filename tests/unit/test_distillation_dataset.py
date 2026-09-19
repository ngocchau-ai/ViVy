"""Unit tests for Stage 6 Distillation Dataset Builder and Splitter."""

from __future__ import annotations

import pytest

from nps_core.distillation_dataset import (
    DatasetBuilder,
    DatasetRecord,
    DatasetSplitter,
    ReplayManifest,
    SplitError,
)
from nps_core.hypothesis_population import (
    VALID_STATES,
    PopulationSnapshot,
    thought_state_from_dict,
)


def _make_thought_dict(thought_id: str) -> dict:
    return {
        "thought_id": thought_id,
        "parent_ids": [],
        "created_at": "2026-07-25T10:00:00Z",
        "interpretation": {"summary": "sum", "scope": "global", "excluded_scope": []},
        "hypothesis": {"claim": "claim", "predicted_observations": ["obs"], "falsification_conditions": ["cond"]},
        "assumptions": [],
        "evidence": {"supporting": [], "opposing": [], "unresolved": []},
        "metrics": {"confidence": 0.5, "novelty": 0.5, "diversity": 0.5, "expected_value": 0.5, "information_need": 0.5, "risk_if_wrong": 0.5, "execution_cost": 0.5},
        "verification_plan": {"questions": [], "required_experiments": [], "acceptable_evidence": [], "rejection_threshold": 0.2},
        "executor_profile": {"skills": ["python"], "tool_requirements": [], "preferred_model_class": "coder", "independence_requirements": []},
        "graph": {"dependencies": [], "contradictions": [], "overlaps": []},
        "status": {"state": "active", "allowed_values": list(VALID_STATES)},
    }


def test_dataset_splitter() -> None:
    records = [
        DatasetRecord(f"REC-{i:03d}", f"THOUGHT-{i:03d}", "transition", "active", "provenance")
        for i in range(20)
    ]

    train, val, test = DatasetSplitter.split(records, train_ratio=0.7, val_ratio=0.15)
    assert len(train) + len(val) + len(test) == 20
    assert len(train) > 0

    with pytest.raises(SplitError, match="Ratios must satisfy"):
        DatasetSplitter.split(records, train_ratio=0.8, val_ratio=0.3)


def test_dataset_builder() -> None:
    t1 = thought_state_from_dict(_make_thought_dict("THOUGHT-001"))
    t2 = thought_state_from_dict(_make_thought_dict("THOUGHT-002"))
    snapshot = PopulationSnapshot(thoughts=(t1, t2))

    manifest = DatasetBuilder.build_manifest("v1.0.0", snapshot)
    assert manifest.version == "v1.0.0"
    assert len(manifest.records) == 2

    # Round trip
    manifest_rt = ReplayManifest.from_dict(manifest.to_dict())
    assert manifest_rt.digest == manifest.digest
