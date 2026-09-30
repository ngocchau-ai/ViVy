# Schemas

These are executable Draft 2020-12 schemas.

- `thought_state.schema.json` - ThoughtState lifecycle contract.
- `evidence_packet.schema.json` - executor evidence and provenance contract.
- `task_contract.schema.json` - Codex-to-local TaskContract envelope.
- `experiment.schema.json` - verification experiment contract.

Objects reject unknown fields using `additionalProperties: false`.

## Validation

```sh
uv run pytest tests/unit/test_schemas.py
```
