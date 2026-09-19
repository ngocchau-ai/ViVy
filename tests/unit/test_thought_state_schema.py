import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

schema_path = Path(__file__).resolve().parents[2] / "schemas/thought_state.schema.json"
with open(schema_path, 'r', encoding='utf-8') as f:
    thought_state_schema = json.load(f)

canonical_thought_state = {
    "thought_id": "THOUGHT-12345",
    "parent_ids": [],
    "created_at": "2026-07-23T00:00:00Z",
    "interpretation": {
        "summary": "Summary of the thought",
        "scope": "Scope of the thought",
        "excluded_scope": []
    },
    "hypothesis": {
        "claim": "Claim of the hypothesis",
        "predicted_observations": [],
        "falsification_conditions": []
    },
    "assumptions": [
        {
            "assumption_id": "ASSUMPTION-1",
            "statement": "Assumption statement 1",
            "confidence": 0.8,
            "source": "Source of assumption 1"
        }
    ],
    "evidence": {
        "supporting": [],
        "opposing": [],
        "unresolved": []
    },
    "metrics": {
        "confidence": 0.9,
        "novelty": 0.7,
        "diversity": 0.6,
        "expected_value": 0.5,
        "information_need": 0.4,
        "risk_if_wrong": 0.3,
        "execution_cost": 0.2
    },
    "verification_plan": {
        "questions": [],
        "required_experiments": [],
        "acceptable_evidence": [],
        "rejection_threshold": 0.1
    },
    "executor_profile": {
        "skills": ["Skill 1", "Skill 2"],
        "tool_requirements": ["Tool 1", "Tool 2"],
        "preferred_model_class": "ModelClass",
        "independence_requirements": []
    },
    "graph": {
        "dependencies": [],
        "contradictions": [],
        "overlaps": []
    },
    "status": {
        "state": "active",
        "allowed_values": ["active", "queued", "testing", "partially_verified", "verified", "rejected", "merged", "dormant"]
    }
}


def test_canonical_thought_state():
    validator = Draft202012Validator(thought_state_schema)
    assert validator.validate(canonical_thought_state) is None


def mutate_unknown_root_key(obj):
    obj['unknown_key'] = 'value'


def mutate_invalid_thought_id(obj):
    obj['thought_id'] = "INVALID-THOUGHT-ID"


def mutate_confidence_1_1(obj):
    obj['metrics']['confidence'] = 1.1


def mutate_missing_required_interpretation_scope(obj):
    del obj['interpretation']['scope']


def mutate_unknown_nested_metric(obj):
    obj['metrics']['unknown_metric'] = 0.5


@pytest.mark.parametrize("mutator", [
    mutate_unknown_root_key,
    mutate_invalid_thought_id,
    mutate_confidence_1_1,
    mutate_missing_required_interpretation_scope,
    mutate_unknown_nested_metric
])
def test_invalid_thought_state(mutator):
    validator = Draft202012Validator(thought_state_schema)
    mutated_state = deepcopy(canonical_thought_state)
    mutator(mutated_state)
    with pytest.raises(ValidationError):
        validator.validate(mutated_state)
