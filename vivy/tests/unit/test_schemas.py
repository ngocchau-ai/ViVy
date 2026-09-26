import json
from pathlib import Path

import pytest
from jsonschema.validators import Draft202012Validator

# Resolve repository root
repo_root = Path(__file__).resolve().parents[2]
schema_dir = repo_root / 'schemas'

# List of schema filenames to test
SCHEMA_FILES = [
    "thought_state.schema.json",
    "evidence_packet.schema.json",
    "task_contract.schema.json",
    "experiment.schema.json"
]

@pytest.mark.parametrize('schema_file', SCHEMA_FILES)
def test_validate_schemas(schema_file):
    with open(schema_dir / schema_file, encoding='utf-8') as file:
        schema = json.load(file)

    validator = Draft202012Validator.check_schema
    validator(schema)

@pytest.mark.parametrize('schema_file', SCHEMA_FILES)
def test_schema_properties(schema_file):
    with open(schema_dir / schema_file, encoding='utf-8') as file:
        schema = json.load(file)

    assert schema.get('$schema') == 'https://json-schema.org/draft/2020-12/schema'
    assert schema.get('additionalProperties', True) is False
