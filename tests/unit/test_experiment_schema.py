import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError
from jsonschema import Draft202012Validator

schema_path = Path(__file__).resolve().parents[2] / "schemas/experiment.schema.json"
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = json.load(f)


def validate_experiment(experiment):
    validator = Draft202012Validator(schema)
    validator.validate(instance=experiment)


@pytest.fixture
def valid_experiment():
    return {
        "experiment": {
            "experiment_id": "EXP-12345",
            "objective": "Test Objective",
            "hypotheses_tested": [],
            "discriminating_outcomes": {"outcome1": "Description"},
            "method": "Method Description",
            "executor_requirements": [],
            "cost_budget": {},
            "stop_conditions": [],
            "expected_information_gain": 0.5,
            "acceptance_schema": "Acceptance Schema"
        }
    }


def test_valid_experiment(valid_experiment):
    validate_experiment(valid_experiment)


def add_unknown_key_to_outer_candidate(experiment):
    experiment["unknown_key"] = "value"


def set_bad_experiment_id(experiment):
    experiment["experiment"]["experiment_id"] = "BAD"


def set_expected_information_gain_1_1(experiment):
    experiment["experiment"]["expected_information_gain"] = 1.1


def set_discriminating_outcomes_to_empty_dict(experiment):
    experiment["experiment"]["discriminating_outcomes"] = {}


def set_cost_budget_with_negative_resource(experiment):
    experiment["experiment"]["cost_budget"] = {"resource": -1}


@pytest.mark.parametrize("mutate", [
    add_unknown_key_to_outer_candidate,
    set_bad_experiment_id,
    set_expected_information_gain_1_1,
    set_discriminating_outcomes_to_empty_dict,
    set_cost_budget_with_negative_resource
])
def test_invalid_experiments(mutate, valid_experiment):
    experiment = deepcopy(valid_experiment)
    mutate(experiment)
    with pytest.raises(ValidationError):
        validate_experiment(experiment)
