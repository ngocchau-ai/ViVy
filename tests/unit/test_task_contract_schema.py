import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

with open(Path(__file__).resolve().parents[2] / "schemas" / "task_contract.schema.json", 'r', encoding='utf-8') as f:
    schema = json.load(f)

canonical_task_contract = {
    "task_contract": {
        "task_id": "TASK-12345",
        "title": "Sample Task",
        "objective": {
            "problem": "Fix bug in login functionality",
            "expected_outcome": "User can successfully log in",
            "non_goals": ["No additional features"]
        },
        "context": {
            "architecture_refs": ["arch1", "arch2"],
            "codegraph_nodes": ["node1", "node2"],
            "relevant_files": ["file1.py", "file2.py"],
            "prior_decisions": ["decision1", "decision2"]
        },
        "constraints": {
            "language": "Python",
            "dependencies_allowed": ["numpy", "pandas"],
            "dependencies_forbidden": [],
            "performance_budget": {"seconds": 5, "mode": "strict", "cached": True},
            "security_requirements": ["no hard-coded passwords"],
            "compatibility_requirements": ["Linux"]
        },
        "implementation": {
            "assigned_role": "Developer",
            "allowed_files": ["file1.py", "file2.py"],
            "forbidden_files": [],
            "expected_artifacts": ["fixed_login_functionality.py"]
        },
        "validation": {
            "acceptance_criteria": ["User can log in with valid credentials"],
            "required_tests": ["unit_test_login.py", "integration_test_login.py"],
            "regression_checks": ["existing_regression_tests.py"],
            "evidence_schema": "evidence_schema.json"
        },
        "token_budget": {
            "max_context_tokens": 4096,
            "max_output_tokens": 2048,
            "required_summary_mode": "condensed"
        },
        "completion": {
            "status": "active",
            "reviewer": "QA Engineer",
            "codegraph_refresh_required": False,
            "memory_update_required": True
        }
    }
}


def test_valid_task_contract():
    validator = Draft202012Validator(schema)
    validator.validate(canonical_task_contract)


def add_unknown_root(candidate):
    candidate["unknown"] = True


def set_bad_task_id(candidate):
    candidate["task_contract"]["task_id"] = "BAD"


def set_zero_tokens(candidate):
    candidate["task_contract"]["token_budget"]["max_context_tokens"] = 0


def add_unknown_constraint(candidate):
    candidate["task_contract"]["constraints"]["unknown"] = True


def set_negative_budget(candidate):
    candidate["task_contract"]["constraints"]["performance_budget"]["seconds"] = -1


@pytest.mark.parametrize("mutator", [
    add_unknown_root,
    set_bad_task_id,
    set_zero_tokens,
    add_unknown_constraint,
    set_negative_budget
])
def test_invalid_task_contract(mutator):
    validator = Draft202012Validator(schema)
    candidate = deepcopy(canonical_task_contract)
    mutator(candidate)
    with pytest.raises(ValidationError):
        validator.validate(candidate)
