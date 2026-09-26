"""Unit tests for EvidencePacket V1 model and canonical serialization.

Covers schema compatibility, lossless round-trips, frozen value objects,
validation of all required fields, reproducibility, and static AST audit
of production modules.
"""

from __future__ import annotations

import ast
import json
import pathlib
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from nps_core.evidence_assimilator import (
    EvidencePacket,
    PacketValidationError,
    Reproducibility,
)

# ---------------------------------------------------------------------------
# Canonical schema path
# ---------------------------------------------------------------------------
_SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "schemas"
    / "evidence_packet.schema.json"
)

# ---------------------------------------------------------------------------
# Canonical EvidencePacket V1 dict (opaque non-empty content_hash)
# ---------------------------------------------------------------------------

_CANONICAL: dict[str, Any] = {
    "evidence_id": "EV-2024.alpha-001",
    "task_id": "TASK-003",
    "executor_id": "executor-alpha",
    "claim": "The sky is blue during clear daytime.",
    "result": "Observed blue sky at solar noon.",
    "method": "Direct visual observation with calibrated instrument.",
    "artifacts": ["photo-001.png", "spectral-log.csv"],
    "confidence": 0.85,
    "limitations": ["Single location only"],
    "failure_modes": ["Cloud cover obscures result"],
    "reproducibility": {
        "command": "python observe.py --location lab",
        "environment": "Ubuntu 22.04, Python 3.11",
        "seed": 42,
    },
    "affected_hypotheses": ["H1-sky-color", "H2-light-scattering"],
    "provenance": ["journal-ref-2024-001"],
    "content_hash": "a]b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1",
}


def _make_packet_dict(**overrides: Any) -> dict[str, Any]:
    """Return a deep copy of the canonical dict with optional overrides."""
    d = json.loads(json.dumps(_CANONICAL))
    d.update(overrides)
    return d


def _load_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Schema validator fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = _load_schema()
    return Draft202012Validator(schema, format_checker=FormatChecker())


# ---------------------------------------------------------------------------
# 1. Schema compatibility
# ---------------------------------------------------------------------------

class TestSchemaCompatibility:
    """Canonical dict and serialized output must pass Draft 2020-12 validation."""

    def test_canonical_dict_validates(self, validator: Draft202012Validator) -> None:
        d = _make_packet_dict()
        errors = list(validator.iter_errors(d))
        assert errors == [], f"Schema errors: {errors}"

    def test_to_dict_validates(self, validator: Draft202012Validator) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        serialized = pkt.to_dict()
        errors = list(validator.iter_errors(serialized))
        assert errors == [], f"Schema errors: {errors}"

    def test_canonical_json_validates(self, validator: Draft202012Validator) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        text = pkt.to_canonical_json()
        data = json.loads(text)
        errors = list(validator.iter_errors(data))
        assert errors == [], f"Schema errors: {errors}"


# ---------------------------------------------------------------------------
# 2. Lossless from_dict / to_dict round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """from_dict â to_dict must be lossless and produce identical dicts."""

    def test_lossless_round_trip(self) -> None:
        original = _make_packet_dict()
        pkt = EvidencePacket.from_dict(original)
        result = pkt.to_dict()
        assert result == original

    def test_canonical_json_round_trip(self) -> None:
        original = _make_packet_dict()
        pkt = EvidencePacket.from_dict(original)
        text = pkt.to_canonical_json()
        pkt2 = EvidencePacket.from_canonical_json(text)
        assert pkt == pkt2
        assert pkt2.to_dict() == original

    def test_canonical_json_deterministic(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        j1 = pkt.to_canonical_json()
        j2 = pkt.to_canonical_json()
        assert j1 == j2

    def test_canonical_json_sorted_keys(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        text = pkt.to_canonical_json()
        data = json.loads(text)
        assert list(data.keys()) == sorted(data.keys())

    def test_canonical_json_compact_separators(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        text = pkt.to_canonical_json()
        expected = json.dumps(
            pkt.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        assert text == expected


# ---------------------------------------------------------------------------
# 3. Equality and frozen value objects
# ---------------------------------------------------------------------------

class TestEqualityAndFrozen:
    """EvidencePacket and Reproducibility must be equal-value and frozen."""

    def test_equality(self) -> None:
        p1 = EvidencePacket.from_dict(_make_packet_dict())
        p2 = EvidencePacket.from_dict(_make_packet_dict())
        assert p1 == p2
        assert hash(p1) == hash(p2)

    def test_inequality(self) -> None:
        p1 = EvidencePacket.from_dict(_make_packet_dict())
        p2 = EvidencePacket.from_dict(_make_packet_dict(confidence=0.5))
        assert p1 != p2

    def test_frozen_packet(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        with pytest.raises(AttributeError):
            pkt.confidence = 0.9  # type: ignore[misc]

    def test_frozen_reproducibility(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        with pytest.raises(AttributeError):
            pkt.reproducibility.seed = 99  # type: ignore[misc]

    def test_tuple_storage(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        assert isinstance(pkt.artifacts, tuple)
        assert isinstance(pkt.limitations, tuple)
        assert isinstance(pkt.failure_modes, tuple)
        assert isinstance(pkt.affected_hypotheses, tuple)
        assert isinstance(pkt.provenance, tuple)


# ---------------------------------------------------------------------------
# 4. Unicode and byte-identical canonical JSON
# ---------------------------------------------------------------------------

class TestUnicode:
    """Unicode content must survive round-trips byte-identically."""

    def test_unicode_fields(self) -> None:
        d = _make_packet_dict(
            claim="ÃnÃ¯cÃ¶dÃ© claim: æ¥æ¬èªãã¹ã",
            result="RÃ©sultat en franÃ§ais 🎉",
            content_hash="cafÃ©0123456789abcdef0123456789abcdef0123456789abcdef0123456789ab",
        )
        pkt = EvidencePacket.from_dict(d)
        text = pkt.to_canonical_json()
        pkt2 = EvidencePacket.from_canonical_json(text)
        assert pkt == pkt2
        assert pkt2.claim == "ÃnÃ¯cÃ¶dÃ© claim: æ¥æ¬èªãã¹ã"

    def test_byte_identical_json(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict())
        b1 = pkt.to_canonical_json().encode("utf-8")
        b2 = pkt.to_canonical_json().encode("utf-8")
        assert b1 == b2


# ---------------------------------------------------------------------------
# 5. Missing / extra root keys
# ---------------------------------------------------------------------------

class TestKeyValidation:
    """Missing or extra root keys must raise PacketValidationError."""

    def test_extra_root_key(self) -> None:
        d = _make_packet_dict(extra_field="bad")
        with pytest.raises(PacketValidationError, match="unexpected keys"):
            EvidencePacket.from_dict(d)

    def test_missing_root_key(self) -> None:
        d = _make_packet_dict()
        del d["claim"]
        with pytest.raises(PacketValidationError, match="missing keys"):
            EvidencePacket.from_dict(d)

    def test_extra_reproducibility_key(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"] = {
            **d["reproducibility"],
            "extra": "bad",
        }
        with pytest.raises(PacketValidationError, match="unexpected keys"):
            EvidencePacket.from_dict(d)

    def test_missing_reproducibility_key(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"] = {
            "command": "cmd",
            "environment": "env",
        }
        with pytest.raises(PacketValidationError, match="missing keys"):
            EvidencePacket.from_dict(d)


# ---------------------------------------------------------------------------
# 6. Invalid evidence_id / task_id patterns
# ---------------------------------------------------------------------------

class TestIdPatterns:
    """Invalid ID patterns must raise PacketValidationError."""

    def test_invalid_evidence_id(self) -> None:
        d = _make_packet_dict(evidence_id="INVALID-123")
        with pytest.raises(PacketValidationError, match="evidence_id"):
            EvidencePacket.from_dict(d)

    def test_invalid_task_id(self) -> None:
        d = _make_packet_dict(task_id="BAD_TASK")
        with pytest.raises(PacketValidationError, match="task_id"):
            EvidencePacket.from_dict(d)

    def test_valid_evidence_id_variants(self) -> None:
        for eid in ["EV-abc", "EV-123", "EV-a.b_c-d"]:
            d = _make_packet_dict(evidence_id=eid)
            pkt = EvidencePacket.from_dict(d)
            assert pkt.evidence_id == eid


# ---------------------------------------------------------------------------
# 7. Whitespace-only required strings
# ---------------------------------------------------------------------------

class TestWhitespaceStrings:
    """Whitespace-only strings must be rejected for all required fields."""

    @pytest.mark.parametrize(
        "field",
        [
            "executor_id",
            "claim",
            "result",
            "method",
            "content_hash",
        ],
    )
    def test_whitespace_only_string(self, field: str) -> None:
        d = _make_packet_dict(**{field: "   "})
        with pytest.raises(PacketValidationError, match="non-empty"):
            EvidencePacket.from_dict(d)

    def test_whitespace_only_array_entry(self) -> None:
        d = _make_packet_dict(artifacts=["  ", "valid.png"])
        with pytest.raises(PacketValidationError, match="non-empty"):
            EvidencePacket.from_dict(d)

    def test_empty_string_array_entry(self) -> None:
        d = _make_packet_dict(provenance=[""])
        with pytest.raises(PacketValidationError, match="non-empty"):
            EvidencePacket.from_dict(d)


# ---------------------------------------------------------------------------
# 8. Wrong container / primitive types
# ---------------------------------------------------------------------------

class TestWrongTypes:
    """Wrong types for arrays, strings, and reproducibility must be rejected."""

    def test_tuple_rejected_at_from_dict(self) -> None:
        d = _make_packet_dict()
        d["artifacts"] = ("a.png", "b.png")
        with pytest.raises(PacketValidationError, match="JSON list"):
            EvidencePacket.from_dict(d)

    def test_string_for_array(self) -> None:
        d = _make_packet_dict()
        d["limitations"] = "not a list"
        with pytest.raises(PacketValidationError, match="JSON list"):
            EvidencePacket.from_dict(d)

    def test_int_for_string(self) -> None:
        d = _make_packet_dict()
        d["claim"] = 42
        with pytest.raises(PacketValidationError, match="expected str"):
            EvidencePacket.from_dict(d)

    def test_list_for_string(self) -> None:
        d = _make_packet_dict()
        d["executor_id"] = ["a", "b"]
        with pytest.raises(PacketValidationError, match="expected str"):
            EvidencePacket.from_dict(d)

    def test_non_dict_reproducibility(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"] = "not a dict"
        with pytest.raises(PacketValidationError, match="expected dict"):
            EvidencePacket.from_dict(d)

    def test_non_dict_root(self) -> None:
        with pytest.raises(PacketValidationError, match="expected dict"):
            EvidencePacket.from_dict("not a dict")

    def test_list_root(self) -> None:
        with pytest.raises(PacketValidationError, match="expected dict"):
            EvidencePacket.from_dict([1, 2, 3])


# ---------------------------------------------------------------------------
# 9. Confidence validation
# ---------------------------------------------------------------------------

class TestConfidence:
    """Confidence must be a finite number in [0, 1]; bools rejected."""

    def test_valid_confidence_zero(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict(confidence=0))
        assert pkt.confidence == 0.0

    def test_valid_confidence_one(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict(confidence=1))
        assert pkt.confidence == 1.0

    def test_valid_confidence_float(self) -> None:
        pkt = EvidencePacket.from_dict(_make_packet_dict(confidence=0.75))
        assert pkt.confidence == 0.75

    def test_bool_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=True)
        with pytest.raises(PacketValidationError, match="bool"):
            EvidencePacket.from_dict(d)

    def test_string_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence="0.5")
        with pytest.raises(PacketValidationError, match="expected number"):
            EvidencePacket.from_dict(d)

    def test_negative_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=-0.1)
        with pytest.raises(PacketValidationError, match=r"\[0, 1\]"):
            EvidencePacket.from_dict(d)

    def test_above_one_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=1.1)
        with pytest.raises(PacketValidationError, match=r"\[0, 1\]"):
            EvidencePacket.from_dict(d)

    def test_nan_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=float("nan"))
        with pytest.raises(PacketValidationError, match="finite"):
            EvidencePacket.from_dict(d)

    def test_inf_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=float("inf"))
        with pytest.raises(PacketValidationError, match="finite"):
            EvidencePacket.from_dict(d)

    def test_neg_inf_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=float("-inf"))
        with pytest.raises(PacketValidationError, match="finite"):
            EvidencePacket.from_dict(d)

    def test_huge_int_confidence_rejected(self) -> None:
        d = _make_packet_dict(confidence=10**100)
        with pytest.raises(PacketValidationError, match=r"\[0, 1\]"):
            EvidencePacket.from_dict(d)


# ---------------------------------------------------------------------------
# 10. Seed validation (int/None success, bool/string/float rejection)
# ---------------------------------------------------------------------------

class TestSeed:
    """Seed must be int or None; bool, string, float rejected."""

    def test_seed_int(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"]["seed"] = 123
        pkt = EvidencePacket.from_dict(d)
        assert pkt.reproducibility.seed == 123

    def test_seed_none(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"]["seed"] = None
        pkt = EvidencePacket.from_dict(d)
        assert pkt.reproducibility.seed is None

    def test_seed_bool_rejected_from_dict(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"]["seed"] = True
        with pytest.raises(PacketValidationError, match="bool"):
            EvidencePacket.from_dict(d)

    def test_seed_string_rejected_from_dict(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"]["seed"] = "42"
        with pytest.raises(PacketValidationError, match="expected int or null"):
            EvidencePacket.from_dict(d)

    def test_seed_float_rejected_from_dict(self) -> None:
        d = _make_packet_dict()
        d["reproducibility"]["seed"] = 3.14
        with pytest.raises(PacketValidationError, match="expected int or null"):
            EvidencePacket.from_dict(d)

    def test_seed_bool_rejected_direct(self) -> None:
        with pytest.raises(PacketValidationError, match="bool"):
            Reproducibility(command="cmd", environment="env", seed=True)  # type: ignore[arg-type]

    def test_seed_string_rejected_direct(self) -> None:
        with pytest.raises(PacketValidationError, match="expected int or null"):
            Reproducibility(command="cmd", environment="env", seed="42")  # type: ignore[arg-type]

    def test_seed_float_rejected_direct(self) -> None:
        with pytest.raises(PacketValidationError, match="expected int or null"):
            Reproducibility(command="cmd", environment="env", seed=3.14)  # type: ignore[arg-type]

    def test_seed_int_direct(self) -> None:
        r = Reproducibility(command="cmd", environment="env", seed=7)
        assert r.seed == 7

    def test_seed_none_direct(self) -> None:
        r = Reproducibility(command="cmd", environment="env", seed=None)
        assert r.seed is None


# ---------------------------------------------------------------------------
# 11. Non-empty provenance / affected_hypotheses
# ---------------------------------------------------------------------------

class TestNonEmptyCollections:
    """provenance and affected_hypotheses must be non-empty."""

    def test_empty_provenance_rejected(self) -> None:
        d = _make_packet_dict(provenance=[])
        with pytest.raises(PacketValidationError, match="provenance must be non-empty"):
            EvidencePacket.from_dict(d)

    def test_empty_affected_hypotheses_rejected(self) -> None:
        d = _make_packet_dict(affected_hypotheses=[])
        with pytest.raises(PacketValidationError, match="affected_hypotheses must be non-empty"):
            EvidencePacket.from_dict(d)

    def test_empty_artifacts_valid(self) -> None:
        d = _make_packet_dict(artifacts=[])
        pkt = EvidencePacket.from_dict(d)
        assert pkt.artifacts == ()

    def test_empty_limitations_valid(self) -> None:
        d = _make_packet_dict(limitations=[])
        pkt = EvidencePacket.from_dict(d)
        assert pkt.limitations == ()

    def test_empty_failure_modes_valid(self) -> None:
        d = _make_packet_dict(failure_modes=[])
        pkt = EvidencePacket.from_dict(d)
        assert pkt.failure_modes == ()


# ---------------------------------------------------------------------------
# 12. Duplicate entries in arrays
# ---------------------------------------------------------------------------

class TestDuplicates:
    """Duplicate entries in affected_hypotheses, artifacts, provenance rejected."""

    def test_duplicate_affected_hypotheses(self) -> None:
        d = _make_packet_dict(affected_hypotheses=["H1", "H1"])
        with pytest.raises(PacketValidationError, match="duplicate"):
            EvidencePacket.from_dict(d)

    def test_duplicate_artifacts(self) -> None:
        d = _make_packet_dict(artifacts=["a.png", "a.png"])
        with pytest.raises(PacketValidationError, match="duplicate"):
            EvidencePacket.from_dict(d)

    def test_duplicate_provenance(self) -> None:
        d = _make_packet_dict(provenance=["ref-1", "ref-1"])
        with pytest.raises(PacketValidationError, match="duplicate"):
            EvidencePacket.from_dict(d)

    def test_unique_entries_accepted(self) -> None:
        d = _make_packet_dict(
            affected_hypotheses=["H1", "H2"],
            artifacts=["a.png", "b.png"],
            provenance=["ref-1", "ref-2"],
        )
        pkt = EvidencePacket.from_dict(d)
        assert len(pkt.affected_hypotheses) == 2
        assert len(pkt.artifacts) == 2
        assert len(pkt.provenance) == 2


# ---------------------------------------------------------------------------
# 13. Malformed / non-string / non-object JSON errors
# ---------------------------------------------------------------------------

class TestJsonErrors:
    """Malformed JSON, non-string input, non-object root must raise errors."""

    def test_malformed_json(self) -> None:
        with pytest.raises(PacketValidationError, match="invalid JSON"):
            EvidencePacket.from_canonical_json("{bad json")

    def test_non_string_json(self) -> None:
        with pytest.raises(PacketValidationError, match="expected str"):
            EvidencePacket.from_canonical_json(123)  # type: ignore[arg-type]

    def test_non_object_json_root(self) -> None:
        with pytest.raises(PacketValidationError, match="expected JSON object"):
            EvidencePacket.from_canonical_json('"just a string"')

    def test_array_json_root(self) -> None:
        with pytest.raises(PacketValidationError, match="expected JSON object"):
            EvidencePacket.from_canonical_json("[1, 2, 3]")

    def test_null_json_root(self) -> None:
        with pytest.raises(PacketValidationError, match="expected JSON object"):
            EvidencePacket.from_canonical_json("null")


# ---------------------------------------------------------------------------
# 14. Reproducibility value object
# ---------------------------------------------------------------------------

class TestReproducibility:
    """Reproducibility must be a frozen value object with strict validation."""

    def test_frozen(self) -> None:
        r = Reproducibility(command="cmd", environment="env", seed=1)
        with pytest.raises(AttributeError):
            r.command = "new"  # type: ignore[misc]

    def test_equality(self) -> None:
        r1 = Reproducibility(command="cmd", environment="env", seed=1)
        r2 = Reproducibility(command="cmd", environment="env", seed=1)
        assert r1 == r2

    def test_inequality(self) -> None:
        r1 = Reproducibility(command="cmd", environment="env", seed=1)
        r2 = Reproducibility(command="cmd", environment="env", seed=2)
        assert r1 != r2

    def test_to_dict(self) -> None:
        r = Reproducibility(command="cmd", environment="env", seed=1)
        assert r.to_dict() == {"command": "cmd", "environment": "env", "seed": 1}

    def test_from_dict_round_trip(self) -> None:
        d = {"command": "cmd", "environment": "env", "seed": 1}
        r = Reproducibility.from_dict(d)
        assert r.to_dict() == d

    def test_whitespace_command_rejected(self) -> None:
        with pytest.raises(PacketValidationError, match="non-empty"):
            Reproducibility(command="  ", environment="env", seed=None)

    def test_whitespace_environment_rejected(self) -> None:
        with pytest.raises(PacketValidationError, match="non-empty"):
            Reproducibility(command="cmd", environment="  ", seed=None)


# ---------------------------------------------------------------------------
# 15. Non-string items in arrays
# ---------------------------------------------------------------------------

class TestArrayItemTypes:
    """Non-string items in arrays must be rejected."""

    def test_int_in_artifacts(self) -> None:
        d = _make_packet_dict(artifacts=[123])
        with pytest.raises(PacketValidationError, match="expected str"):
            EvidencePacket.from_dict(d)

    def test_none_in_provenance(self) -> None:
        d = _make_packet_dict(provenance=[None])
        with pytest.raises(PacketValidationError, match="expected str"):
            EvidencePacket.from_dict(d)

    def test_dict_in_limitations(self) -> None:
        d = _make_packet_dict(limitations=[{"key": "val"}])
        with pytest.raises(PacketValidationError, match="expected str"):
            EvidencePacket.from_dict(d)


# ---------------------------------------------------------------------------
# 16. Static AST audit of production modules
# ---------------------------------------------------------------------------

_PROD_ROOTS = {
    "nps_core",
    "__future__",
    # stdlib modules used in production code
    "json",
    "re",
    "dataclasses",
    "typing",
    "hashlib",
    "datetime",
    "pathlib",
}

_PROD_DIRS = [
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "nps_core"
    / "evidence_assimilator",
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "nps_core"
    / "state_update",
]


def _collect_imports(filepath: pathlib.Path) -> set[str]:
    """Return the set of top-level module names imported in a Python file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                roots.add(node.module.split(".")[0])
    return roots


class TestStaticAstAudit:
    """Every .py file under evidence_assimilator and state_update must only
    import from stdlib roots, __future__, and nps_core."""

    @pytest.mark.parametrize(
        "filepath",
        [
            p
            for d in _PROD_DIRS
            if d.exists()
            for p in sorted(d.glob("*.py"))
        ],
        ids=lambda p: str(p.relative_to(p.parents[3])),
    )
    def test_imports_allowed(self, filepath: pathlib.Path) -> None:
        imports = _collect_imports(filepath)
        # Remove 'nps_core' sub-imports (they start with nps_core)
        disallowed = set()
        for imp in imports:
            if imp in _PROD_ROOTS:
                continue
            # nps_core subpackages are allowed
            if imp.startswith("nps_core") or imp == "nps_core":
                continue
            disallowed.add(imp)
        assert disallowed == set(), (
            f"{filepath.name} imports disallowed modules: {sorted(disallowed)}"
        )
