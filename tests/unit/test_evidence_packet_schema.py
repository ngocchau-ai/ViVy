import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError
from jsonschema import Draft202012Validator

schema_path = Path(__file__).resolve().parents[2] / "schemas/evidence_packet.schema.json"
with open(schema_path, 'r', encoding='utf-8') as file:
    schema = json.load(file)

canonical_instance = {
    "evidence_id": "EV-12345",
    "task_id": "TASK-67890",
    "executor_id": "EXEC-ABCDE",
    "claim": "This is a claim",
    "result": "This is a result",
    "method": "This is a method",
    "artifacts": [],
    "confidence": 0.8,
    "limitations": [],
    "failure_modes": [],
    "reproducibility": {
        "command": "echo 'Hello, World!'",
        "environment": "Linux",
        "seed": None
    },
    "affected_hypotheses": [],
    "provenance": [],
    "content_hash": "abc123"
}


def test_valid_canonical_instance():
    validator = Draft202012Validator(schema)
    validator.validate(canonical_instance)


def add_unknown_root_key(instance):
    instance['unknown_root'] = 'value'
    return instance


def set_evidence_id_to_bad(instance):
    instance['evidence_id'] = 'BAD'
    return instance


def confidence_minus_0_1(instance):
    instance['confidence'] = -0.1
    return instance


def delete_reproducibility_seed(instance):
    del instance['reproducibility']['seed']
    return instance


def add_unknown_field_inside_reproducibility(instance):
    instance['reproducibility']['unknown_field'] = 'value'
    return instance


@pytest.mark.parametrize("mutate", [
    add_unknown_root_key,
    set_evidence_id_to_bad,
    confidence_minus_0_1,
    delete_reproducibility_seed,
    add_unknown_field_inside_reproducibility
])
def test_invalid_mutations(mutate):
    instance = deepcopy(canonical_instance)
    mutated_instance = mutate(instance)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(mutated_instance)
