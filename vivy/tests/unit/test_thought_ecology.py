"""Unit tests for thought_ecology: relations, ThoughtEcology, build, and validate_for."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from nps_core.hypothesis_population import (
    PopulationSnapshot,
    ThoughtState,
)
from nps_core.thought_ecology import (
    AmbiguousEvidenceBucketError,
    ConflictingAssumptionError,
    ContradictionEdge,
    DependencyCycleError,
    DependencyEdge,
    EcologyValidationError,
    EvidencePlacement,
    OverlapEdge,
    SelfReferenceError,
    SharedAssumptionLink,
    SnapshotMismatchError,
    ThoughtEcology,
    UnknownThoughtError,
    build,
)

# ---------------------------------------------------------------------------
# Compact factories
# ---------------------------------------------------------------------------

_TS = "2025-01-01T00:00:00Z"
_VALID_STATES = (
    "active", "queued", "testing", "partially_verified",
    "verified", "rejected", "merged", "dormant",
)


def _make_state(
    tid: str,
    *,
    state: str = "active",
    parent_ids: tuple[str, ...] = (),
    deps: tuple[str, ...] = (),
    contras: tuple[str, ...] = (),
    overlaps: tuple[str, ...] = (),
    assumptions: tuple[dict[str, Any], ...] = (),
    supporting: tuple[str, ...] = (),
    opposing: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> ThoughtState:
    return ThoughtState.from_dict({
        "thought_id": tid,
        "parent_ids": list(parent_ids),
        "created_at": _TS,
        "interpretation": {"summary": "s", "scope": "sc", "excluded_scope": []},
        "hypothesis": {
            "claim": "c",
            "predicted_observations": [],
            "falsification_conditions": [],
        },
        "assumptions": list(assumptions),
        "evidence": {
            "supporting": list(supporting),
            "opposing": list(opposing),
            "unresolved": list(unresolved),
        },
        "metrics": {
            "confidence": 0.5,
            "novelty": 0.5,
            "diversity": 0.5,
            "expected_value": 0.5,
            "information_need": 0.5,
            "risk_if_wrong": 0.5,
            "execution_cost": 0.5,
        },
        "verification_plan": {
            "questions": [],
            "required_experiments": [],
            "acceptable_evidence": [],
            "rejection_threshold": 0.5,
        },
        "executor_profile": {
            "skills": [],
            "tool_requirements": [],
            "preferred_model_class": "default",
            "independence_requirements": [],
        },
        "graph": {
            "dependencies": list(deps),
            "contradictions": list(contras),
            "overlaps": list(overlaps),
        },
        "status": {
            "state": state,
            "allowed_values": list(_VALID_STATES),
        },
    })


def _snapshot(*states: ThoughtState) -> PopulationSnapshot:
    return PopulationSnapshot(thoughts=tuple(states), history=())


def _build(*states: ThoughtState) -> ThoughtEcology:
    return build(_snapshot(*states))


# ---------------------------------------------------------------------------
# Relation value objects
# ---------------------------------------------------------------------------


class TestDependencyEdge:
    def test_direct_construction(self) -> None:
        e = DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-b")
        assert e.source_id == "THOUGHT-a"
        assert e.target_id == "THOUGHT-b"

    def test_self_reference_rejected(self) -> None:
        with pytest.raises(SelfReferenceError, match="same thought"):
            DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-a")

    @pytest.mark.parametrize("bad", ["", "not-valid", 123, None])
    def test_invalid_id(self, bad: Any) -> None:
        with pytest.raises(EcologyValidationError):
            DependencyEdge(source_id=bad, target_id="THOUGHT-b")  # type: ignore[arg-type]
        with pytest.raises(EcologyValidationError):
            DependencyEdge(source_id="THOUGHT-a", target_id=bad)  # type: ignore[arg-type]

    def test_to_dict_from_dict_roundtrip(self) -> None:
        e = DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-b")
        d = e.to_dict()
        assert d == {"source_id": "THOUGHT-a", "target_id": "THOUGHT-b"}
        e2 = DependencyEdge.from_dict(d)
        assert e2 == e

    def test_from_dict_extra_key(self) -> None:
        with pytest.raises(EcologyValidationError, match="exactly"):
            DependencyEdge.from_dict({"source_id": "THOUGHT-a", "target_id": "THOUGHT-b", "x": 1})

    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(EcologyValidationError, match="exactly"):
            DependencyEdge.from_dict({"source_id": "THOUGHT-a"})

    def test_from_dict_wrong_type(self) -> None:
        with pytest.raises(EcologyValidationError, match="dict"):
            DependencyEdge.from_dict("bad")  # type: ignore[arg-type]


class TestContradictionEdge:
    def test_canonicalization(self) -> None:
        e = ContradictionEdge(first_id="THOUGHT-z", second_id="THOUGHT-a")
        assert e.first_id == "THOUGHT-a"
        assert e.second_id == "THOUGHT-z"

    def test_self_reference_rejected(self) -> None:
        with pytest.raises(SelfReferenceError):
            ContradictionEdge(first_id="THOUGHT-a", second_id="THOUGHT-a")

    def test_to_dict_from_dict_roundtrip(self) -> None:
        e = ContradictionEdge(first_id="THOUGHT-a", second_id="THOUGHT-b")
        d = e.to_dict()
        e2 = ContradictionEdge.from_dict(d)
        assert e2 == e

    def test_from_dict_extra_key(self) -> None:
        with pytest.raises(EcologyValidationError):
            ContradictionEdge.from_dict({"first_id": "THOUGHT-a", "second_id": "THOUGHT-b", "x": 1})


class TestOverlapEdge:
    def test_canonicalization(self) -> None:
        e = OverlapEdge(first_id="THOUGHT-z", second_id="THOUGHT-a")
        assert e.first_id == "THOUGHT-a"
        assert e.second_id == "THOUGHT-z"

    def test_self_reference_rejected(self) -> None:
        with pytest.raises(SelfReferenceError):
            OverlapEdge(first_id="THOUGHT-a", second_id="THOUGHT-a")

    def test_to_dict_from_dict_roundtrip(self) -> None:
        e = OverlapEdge(first_id="THOUGHT-a", second_id="THOUGHT-b")
        d = e.to_dict()
        e2 = OverlapEdge.from_dict(d)
        assert e2 == e


class TestSharedAssumptionLink:
    def test_canonicalization(self) -> None:
        link = SharedAssumptionLink(
            assumption_id="asm1", first_thought_id="THOUGHT-z", second_thought_id="THOUGHT-a"
        )
        assert link.first_thought_id == "THOUGHT-a"
        assert link.second_thought_id == "THOUGHT-z"

    def test_self_reference_rejected(self) -> None:
        with pytest.raises(SelfReferenceError):
            SharedAssumptionLink(
                assumption_id="asm1", first_thought_id="THOUGHT-a", second_thought_id="THOUGHT-a"
            )

    def test_to_dict_from_dict_roundtrip(self) -> None:
        link = SharedAssumptionLink(
            assumption_id="asm1", first_thought_id="THOUGHT-a", second_thought_id="THOUGHT-b"
        )
        d = link.to_dict()
        link2 = SharedAssumptionLink.from_dict(d)
        assert link2 == link

    def test_from_dict_extra_key(self) -> None:
        with pytest.raises(EcologyValidationError):
            SharedAssumptionLink.from_dict(
                {"assumption_id": "a", "first_thought_id": "THOUGHT-a",
                 "second_thought_id": "THOUGHT-b", "x": 1}
            )


class TestEvidencePlacement:
    @pytest.mark.parametrize("bucket", ["supporting", "opposing", "unresolved"])
    def test_valid_buckets(self, bucket: str) -> None:
        ep = EvidencePlacement(evidence_id="ev1", thought_id="THOUGHT-a", bucket=bucket)
        assert ep.bucket == bucket

    def test_invalid_bucket(self) -> None:
        with pytest.raises(EcologyValidationError, match="bucket"):
            EvidencePlacement(evidence_id="ev1", thought_id="THOUGHT-a", bucket="bad")

    def test_to_dict_from_dict_roundtrip(self) -> None:
        ep = EvidencePlacement(evidence_id="ev1", thought_id="THOUGHT-a", bucket="supporting")
        d = ep.to_dict()
        ep2 = EvidencePlacement.from_dict(d)
        assert ep2 == ep

    def test_from_dict_extra_key(self) -> None:
        with pytest.raises(EcologyValidationError):
            EvidencePlacement.from_dict(
                {"evidence_id": "ev1", "thought_id": "THOUGHT-a", "bucket": "supporting", "x": 1}
            )


# ---------------------------------------------------------------------------
# ThoughtEcology direct construction
# ---------------------------------------------------------------------------


class TestThoughtEcologyConstruction:
    def test_direct_tuple_enforcement(self) -> None:
        with pytest.raises(EcologyValidationError, match="tuple"):
            ThoughtEcology(
                snapshot_digest="a" * 64, thought_ids="bad",  # type: ignore[arg-type]
                dependencies=(), contradictions=(), overlaps=(),
                shared_assumptions=(), evidence_placements=(),
            )

    def test_wrong_relation_type_rejected(self) -> None:
        with pytest.raises(EcologyValidationError, match="DependencyEdge"):
            ThoughtEcology(
                snapshot_digest="a" * 64, thought_ids=("THOUGHT-a", "THOUGHT-b"),
                dependencies=(ContradictionEdge(first_id="THOUGHT-a", second_id="THOUGHT-b"),),  # type: ignore[arg-type]
                contradictions=(), overlaps=(),
                shared_assumptions=(), evidence_placements=(),
            )

    def test_unknown_endpoint_rejected(self) -> None:
        with pytest.raises(EcologyValidationError, match="not in thought_ids"):
            ThoughtEcology(
                snapshot_digest="a" * 64, thought_ids=("THOUGHT-a",),
                dependencies=(DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-b"),),
                contradictions=(), overlaps=(),
                shared_assumptions=(), evidence_placements=(),
            )

    def test_duplicate_dependency_rejected(self) -> None:
        with pytest.raises(EcologyValidationError, match="duplicate dependency"):
            ThoughtEcology(
                snapshot_digest="a" * 64,
                thought_ids=("THOUGHT-a", "THOUGHT-b"),
                dependencies=(
                    DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-b"),
                    DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-b"),
                ),
                contradictions=(), overlaps=(),
                shared_assumptions=(), evidence_placements=(),
            )

    def test_ambiguous_evidence_bucket_rejected(self) -> None:
        with pytest.raises(AmbiguousEvidenceBucketError):
            ThoughtEcology(
                snapshot_digest="a" * 64,
                thought_ids=("THOUGHT-a",),
                dependencies=(), contradictions=(), overlaps=(),
                shared_assumptions=(),
                evidence_placements=(
                    EvidencePlacement(evidence_id="ev1", thought_id="THOUGHT-a", bucket="supporting"),
                    EvidencePlacement(evidence_id="ev1", thought_id="THOUGHT-a", bucket="opposing"),
                ),
            )

    def test_dependency_cycle_rejected(self) -> None:
        with pytest.raises(DependencyCycleError):
            ThoughtEcology(
                snapshot_digest="a" * 64,
                thought_ids=("THOUGHT-a", "THOUGHT-b"),
                dependencies=(
                    DependencyEdge(source_id="THOUGHT-a", target_id="THOUGHT-b"),
                    DependencyEdge(source_id="THOUGHT-b", target_id="THOUGHT-a"),
                ),
                contradictions=(), overlaps=(),
                shared_assumptions=(), evidence_placements=(),
            )

    def test_sorting_canonical_shape(self) -> None:
        eco = ThoughtEcology(
            snapshot_digest="a" * 64,
            thought_ids=("THOUGHT-b", "THOUGHT-a"),
            dependencies=(
                DependencyEdge(source_id="THOUGHT-b", target_id="THOUGHT-a"),
            ),
            contradictions=(), overlaps=(),
            shared_assumptions=(), evidence_placements=(),
        )
        assert eco.thought_ids == ("THOUGHT-a", "THOUGHT-b")
        assert eco.dependencies[0].source_id == "THOUGHT-b"


# ---------------------------------------------------------------------------
# ThoughtEcology from_dict / to_dict / JSON
# ---------------------------------------------------------------------------


class TestThoughtEcologySerialization:
    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(EcologyValidationError, match="missing"):
            ThoughtEcology.from_dict({"snapshot_digest": "a" * 64})

    def test_from_dict_extra_key(self) -> None:
        d = {
            "snapshot_digest": "a" * 64,
            "thought_ids": [],
            "dependencies": [],
            "contradictions": [],
            "overlaps": [],
            "shared_assumptions": [],
            "evidence_placements": [],
            "extra": 1,
        }
        with pytest.raises(EcologyValidationError, match="unexpected"):
            ThoughtEcology.from_dict(d)

    def test_from_dict_requires_lists(self) -> None:
        base: dict[str, Any] = {
            "snapshot_digest": "a" * 64,
            "thought_ids": [],
            "dependencies": [],
            "contradictions": [],
            "overlaps": [],
            "shared_assumptions": [],
            "evidence_placements": [],
        }
        for key in ("thought_ids", "dependencies", "contradictions",
                     "overlaps", "shared_assumptions", "evidence_placements"):
            bad = {**base, key: "not-a-list"}
            with pytest.raises(EcologyValidationError, match="list"):
                ThoughtEcology.from_dict(bad)

    def test_to_dict_from_dict_roundtrip(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b"),
        )
        d = eco.to_dict()
        eco2 = ThoughtEcology.from_dict(d)
        assert eco2.to_canonical_json() == eco.to_canonical_json()

    def test_canonical_json_deterministic(self) -> None:
        eco = _build(_make_state("THOUGHT-a"))
        j1 = eco.to_canonical_json()
        j2 = eco.to_canonical_json()
        assert j1 == j2
        parsed = json.loads(j1)
        assert isinstance(parsed, dict)

    def test_from_canonical_json_roundtrip(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b"),
        )
        j = eco.to_canonical_json()
        eco2 = ThoughtEcology.from_canonical_json(j)
        assert eco2.to_canonical_json() == j

    def test_from_canonical_json_bad_type(self) -> None:
        with pytest.raises(EcologyValidationError, match="string"):
            ThoughtEcology.from_canonical_json(123)  # type: ignore[arg-type]

    def test_from_canonical_json_bad_json(self) -> None:
        with pytest.raises(EcologyValidationError, match="invalid JSON"):
            ThoughtEcology.from_canonical_json("{bad")


# ---------------------------------------------------------------------------
# SHA-256 snapshot digest
# ---------------------------------------------------------------------------


class TestSnapshotDigest:
    def test_digest_is_sha256_of_snapshot(self) -> None:
        snap = _snapshot(_make_state("THOUGHT-a"))
        eco = build(snap)
        expected = hashlib.sha256(snap.to_canonical_json().encode("utf-8")).hexdigest()
        assert eco.snapshot_digest == expected
        assert len(eco.snapshot_digest) == 64

    def test_digest_deterministic(self) -> None:
        snap = _snapshot(_make_state("THOUGHT-a"))
        eco1 = build(snap)
        eco2 = build(snap)
        assert eco1.snapshot_digest == eco2.snapshot_digest


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------


class TestBuild:
    def test_empty_snapshot(self) -> None:
        eco = build(PopulationSnapshot.empty())
        assert eco.thought_ids == ()
        assert eco.dependencies == ()
        assert eco.snapshot_digest == hashlib.sha256(
            PopulationSnapshot.empty().to_canonical_json().encode("utf-8")
        ).hexdigest()

    def test_dependency_direction(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b"),
        )
        assert len(eco.dependencies) == 1
        assert eco.dependencies[0].source_id == "THOUGHT-a"
        assert eco.dependencies[0].target_id == "THOUGHT-b"

    def test_reciprocal_undirected_collapse(self) -> None:
        """Contradictions/overlaps declared from both sides collapse to one edge."""
        eco = _build(
            _make_state("THOUGHT-a", contras=("THOUGHT-b",)),
            _make_state("THOUGHT-b", contras=("THOUGHT-a",)),
        )
        assert len(eco.contradictions) == 1

    def test_shared_assumption_pair_generation(self) -> None:
        asm = {"assumption_id": "asm1", "statement": "s", "confidence": 0.5, "source": "src"}
        eco = _build(
            _make_state("THOUGHT-a", assumptions=(asm,)),
            _make_state("THOUGHT-b", assumptions=(asm,)),
        )
        assert len(eco.shared_assumptions) == 1
        link = eco.shared_assumptions[0]
        assert link.assumption_id == "asm1"
        assert link.first_thought_id == "THOUGHT-a"
        assert link.second_thought_id == "THOUGHT-b"

    def test_shared_assumption_payload_conflict(self) -> None:
        a1 = {"assumption_id": "asm1", "statement": "s1", "confidence": 0.5, "source": "src"}
        a2 = {"assumption_id": "asm1", "statement": "s2", "confidence": 0.5, "source": "src"}
        with pytest.raises(ConflictingAssumptionError, match="asm1"):
            _build(
                _make_state("THOUGHT-a", assumptions=(a1,)),
                _make_state("THOUGHT-b", assumptions=(a2,)),
            )

    def test_evidence_placements(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", supporting=("ev1",), opposing=("ev2",)),
        )
        assert len(eco.evidence_placements) == 2
        buckets = {ep.bucket for ep in eco.evidence_placements}
        assert buckets == {"supporting", "opposing"}

    def test_unknown_dependency_endpoint(self) -> None:
        with pytest.raises(UnknownThoughtError):
            _build(_make_state("THOUGHT-a", deps=("THOUGHT-missing",)))

    def test_self_dependency_rejected(self) -> None:
        with pytest.raises(SelfReferenceError):
            _build(_make_state("THOUGHT-a", deps=("THOUGHT-a",)))

    def test_unknown_contradiction_endpoint(self) -> None:
        with pytest.raises(UnknownThoughtError):
            _build(_make_state("THOUGHT-a", contras=("THOUGHT-missing",)))

    def test_self_contradiction_rejected(self) -> None:
        with pytest.raises(SelfReferenceError):
            _build(_make_state("THOUGHT-a", contras=("THOUGHT-a",)))

    def test_unknown_overlap_endpoint(self) -> None:
        with pytest.raises(UnknownThoughtError):
            _build(_make_state("THOUGHT-a", overlaps=("THOUGHT-missing",)))

    def test_self_overlap_rejected(self) -> None:
        with pytest.raises(SelfReferenceError):
            _build(_make_state("THOUGHT-a", overlaps=("THOUGHT-a",)))

    def test_dependency_cycle_detected(self) -> None:
        with pytest.raises(DependencyCycleError) as exc_info:
            _build(
                _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
                _make_state("THOUGHT-b", deps=("THOUGHT-a",)),
            )
        assert exc_info.value.cycle is not None


    def test_dependency_three_node_cycle_detected(self) -> None:
        with pytest.raises(DependencyCycleError) as exc_info:
            _build(
                _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
                _make_state("THOUGHT-b", deps=("THOUGHT-c",)),
                _make_state("THOUGHT-c", deps=("THOUGHT-a",)),
            )
        assert exc_info.value.cycle == ("THOUGHT-a", "THOUGHT-b", "THOUGHT-c", "THOUGHT-a")


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------


class TestQueryMethods:
    @pytest.fixture()
    def eco(self) -> ThoughtEcology:
        return _build(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",), contras=("THOUGHT-c",)),
            _make_state("THOUGHT-b", overlaps=("THOUGHT-c",)),
            _make_state("THOUGHT-c"),
        )

    def test_dependencies_of(self, eco: ThoughtEcology) -> None:
        deps = eco.dependencies_of("THOUGHT-a")
        assert len(deps) == 1
        assert deps[0].target_id == "THOUGHT-b"

    def test_dependents_of(self, eco: ThoughtEcology) -> None:
        deps = eco.dependents_of("THOUGHT-b")
        assert len(deps) == 1
        assert deps[0].source_id == "THOUGHT-a"

    def test_contradictions_of(self, eco: ThoughtEcology) -> None:
        contras = eco.contradictions_of("THOUGHT-a")
        assert len(contras) == 1

    def test_overlaps_of(self, eco: ThoughtEcology) -> None:
        overlaps = eco.overlaps_of("THOUGHT-b")
        assert len(overlaps) == 1

    def test_evidence_for(self) -> None:
        eco = _build(_make_state("THOUGHT-a", supporting=("ev1",)))
        eps = eco.evidence_for("THOUGHT-a")
        assert len(eps) == 1
        assert eps[0].evidence_id == "ev1"

    def test_unknown_query_id_raises(self, eco: ThoughtEcology) -> None:
        with pytest.raises(UnknownThoughtError, match="unknown thought"):
            eco.dependencies_of("THOUGHT-missing")

    def test_transitive_dependencies(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b", deps=("THOUGHT-c",)),
            _make_state("THOUGHT-c"),
        )
        trans = eco.transitive_dependencies("THOUGHT-a")
        assert set(trans) == {"THOUGHT-b", "THOUGHT-c"}

    def test_transitive_unknown_raises(self, eco: ThoughtEcology) -> None:
        with pytest.raises(UnknownThoughtError):
            eco.transitive_dependencies("THOUGHT-missing")

    def test_topological_order_target_before_source(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b"),
        )
        topo = eco.topological_order()
        assert topo.index("THOUGHT-b") < topo.index("THOUGHT-a")

    def test_topological_order_empty(self) -> None:
        eco = build(PopulationSnapshot.empty())
        assert eco.topological_order() == ()

    def test_neighborhood(self, eco: ThoughtEcology) -> None:
        n = eco.neighborhood("THOUGHT-a")
        assert "THOUGHT-b" in n  # dependency
        assert "THOUGHT-c" in n  # contradiction
        assert "THOUGHT-a" not in n

    def test_neighborhood_unknown_raises(self, eco: ThoughtEcology) -> None:
        with pytest.raises(UnknownThoughtError):
            eco.neighborhood("THOUGHT-missing")

    def test_neighborhood_evidence_sharing(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a", supporting=("ev1",)),
            _make_state("THOUGHT-b", supporting=("ev1",)),
        )
        n = eco.neighborhood("THOUGHT-a")
        assert "THOUGHT-b" in n


# ---------------------------------------------------------------------------
# validate_for
# ---------------------------------------------------------------------------


class TestValidateFor:
    def test_validate_for_exact_snapshot(self) -> None:
        snap = _snapshot(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b"),
        )
        eco = build(snap)
        eco.validate_for(snap)  # should not raise

    def test_validate_for_digest_mismatch(self) -> None:
        snap1 = _snapshot(_make_state("THOUGHT-a"))
        snap2 = _snapshot(_make_state("THOUGHT-b"))
        eco = build(snap1)
        with pytest.raises(SnapshotMismatchError) as exc_info:
            eco.validate_for(snap2)
        assert exc_info.value.expected_digest != exc_info.value.actual_digest

    def test_validate_for_forged_same_digest_missing_relation(self) -> None:
        """Forge an ecology with same digest but missing a relation."""
        snap = _snapshot(
            _make_state("THOUGHT-a", deps=("THOUGHT-b",)),
            _make_state("THOUGHT-b"),
        )
        eco = build(snap)
        # Forge: same digest, but remove the dependency
        forged = ThoughtEcology(
            snapshot_digest=eco.snapshot_digest,
            thought_ids=eco.thought_ids,
            dependencies=(),
            contradictions=eco.contradictions,
            overlaps=eco.overlaps,
            shared_assumptions=eco.shared_assumptions,
            evidence_placements=eco.evidence_placements,
        )
        with pytest.raises(SnapshotMismatchError):
            forged.validate_for(snap)


# ---------------------------------------------------------------------------
# Static import audit
# ---------------------------------------------------------------------------

_ALLOWED_IMPORT_ROOTS = frozenset({"nps_core", "__future__", *sys.stdlib_module_names})


def _collect_imports(filepath: Path) -> list[str]:
    """Return all top-level module names imported in *filepath*."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                names.append(node.module.split(".")[0])
    return names


class TestStaticImportAudit:
    """Every .py directly under src/nps_core/thought_ecology must only import
    from nps_core, __future__, or the stdlib."""

    def test_no_disallowed_imports(self) -> None:
        prod_dir = Path(__file__).resolve().parents[2] / "src" / "nps_core" / "thought_ecology"
        assert prod_dir.is_dir(), f"production directory not found: {prod_dir}"
        disallowed: list[tuple[str, str]] = []
        for py_file in sorted(prod_dir.glob("*.py")):
            for root in _collect_imports(py_file):
                if root not in _ALLOWED_IMPORT_ROOTS:
                    disallowed.append((py_file.name, root))
        assert disallowed == [], f"disallowed imports: {disallowed}"


# ---------------------------------------------------------------------------
# shared_assumptions_of with absent thought ID
# ---------------------------------------------------------------------------


class TestSharedAssumptionsOfUnknown:
    def test_valid_format_absent_id_raises(self) -> None:
        eco = _build(
            _make_state("THOUGHT-a"),
            _make_state("THOUGHT-b"),
        )
        with pytest.raises(UnknownThoughtError, match="unknown thought"):
            eco.shared_assumptions_of("THOUGHT-absent")


# ---------------------------------------------------------------------------
# from_dict rejects non-string snapshot_digest
# ---------------------------------------------------------------------------


class TestFromDictSnapshotDigest:
    def test_non_string_rejected(self) -> None:
        data = {
            "snapshot_digest": 12345,
            "thought_ids": [],
            "dependencies": [],
            "contradictions": [],
            "overlaps": [],
            "shared_assumptions": [],
            "evidence_placements": [],
        }
        with pytest.raises(EcologyValidationError, match="snapshot_digest"):
            ThoughtEcology.from_dict(data)
