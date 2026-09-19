"""Unit tests for atomic state update: EvidenceUpdateRecord and apply_evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from nps_core.evidence_assimilator.errors import PlanValidationError
from nps_core.evidence_assimilator.impact import AssimilationPlan, EvidenceImpact
from nps_core.evidence_assimilator.packet import EvidencePacket, Reproducibility
from nps_core.hypothesis_population.lifecycle import PopulationSnapshot
from nps_core.hypothesis_population.thought_state import ThoughtState
from nps_core.state_update import (
    EvidenceUpdateRecord,
    InvalidRecordError,
    ReplacementValidationError,
    TargetMismatchError,
    apply_evidence,
)


# ---------------------------------------------------------------------------
# Local helpers Ã¢Â€Â“ never import from tests
# ---------------------------------------------------------------------------

VALID_TS = "2025-06-01T12:00:00Z"
VALID_RECORD_ID = "REC-001"
VALID_ACTOR = "tester"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _snapshot_digest(snap: PopulationSnapshot) -> str:
    return _sha256(_canonical_json_bytes(snap.to_dict()))


def _make_evidence(
    *,
    supporting: tuple[str, ...] = (),
    opposing: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> Any:
    """Return an Evidence-like namespace with the three bucket tuples."""
    from types import SimpleNamespace

    return SimpleNamespace(
        supporting=supporting,
        opposing=opposing,
        unresolved=unresolved,
    )


def _make_status(state: str = "active") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(state=state)


def _make_ts(
    thought_id: str,
    *,
    parents: tuple[str, ...] = (),
    status: str = "active",
    claim: str = "claim",
    confidence: float = 0.5,
    evidence: Any | None = None,
) -> ThoughtState:
    """Build a ThoughtState via from_dict with sensible defaults."""
    if evidence is None:
        ev_dict: dict[str, Any] = {
            "supporting": [],
            "opposing": [],
            "unresolved": [],
        }
    else:
        ev_dict = {
            "supporting": list(evidence.supporting),
            "opposing": list(evidence.opposing),
            "unresolved": list(evidence.unresolved),
        }
    return ThoughtState.from_dict(
        {
            "thought_id": thought_id,
            "parent_ids": list(parents),
            "created_at": "2025-01-01T00:00:00Z",
            "interpretation": {
                "summary": "s",
                "scope": "sc",
                "excluded_scope": [],
            },
            "hypothesis": {
                "claim": claim,
                "predicted_observations": [],
                "falsification_conditions": [],
            },
            "assumptions": [],
            "evidence": ev_dict,
            "metrics": {
                "confidence": confidence,
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
            "graph": {"dependencies": [], "contradictions": [], "overlaps": []},
            "status": {
                "state": status,
                "allowed_values": [
                    "active",
                    "queued",
                    "testing",
                    "partially_verified",
                    "verified",
                    "rejected",
                    "merged",
                    "dormant",
                ],
            },
        }
    )


def _make_packet(
    *,
    evidence_id: str = "EV-001",
    affected: tuple[str, ...] = ("THOUGHT-A",),
    content_hash: str = "abc123",
) -> EvidencePacket:
    return EvidencePacket(
        evidence_id=evidence_id,
        task_id="TASK-001",
        executor_id="exec-1",
        claim="c",
        result="r",
        method="m",
        artifacts=("a1",),
        confidence=0.8,
        limitations=("lim1",),
        failure_modes=("fm1",),
        reproducibility=Reproducibility(
            command="cmd",
            environment="env",
            seed=42,
        ),
        affected_hypotheses=affected,
        provenance=("prov1",),
        content_hash=content_hash,
    )


def _make_plan(
    *,
    packet: EvidencePacket | None = None,
    classifications: dict[str, str] | None = None,
    snapshot: PopulationSnapshot | None = None,
) -> AssimilationPlan:
    """Build an AssimilationPlan validated against *snapshot*."""
    if packet is None:
        affected = tuple(classifications.keys()) if classifications else ("THOUGHT-A",)
        packet = _make_packet(affected=affected)
    if classifications is None:
        classifications = {packet.affected_hypotheses[0]: "supporting"}
    impacts = tuple(
        EvidenceImpact(target_thought_id=tid, classification=cls)
        for tid, cls in classifications.items()
    )
    if snapshot is not None:
        return AssimilationPlan.create(packet, impacts, snapshot)
    return AssimilationPlan(packet=packet, impacts=impacts)


def _make_snapshot(
    thoughts: tuple[ThoughtState, ...],
    history: tuple = (),
) -> PopulationSnapshot:
    return PopulationSnapshot(thoughts=thoughts, history=history)


def _record_dict(**overrides: Any) -> dict[str, Any]:
    """Return a valid record dict, optionally overriding fields."""
    base = {
        "record_id": VALID_RECORD_ID,
        "timestamp": VALID_TS,
        "actor": VALID_ACTOR,
        "evidence_id": "EV-001",
        "content_hash": "some_hash",
        "sorted_target_ids": ["THOUGHT-A"],
        "prior_state_digest": "a" * 64,
        "result_state_digest": "b" * 64,
    }
    base.update(overrides)
    return base


def _record(**overrides: Any) -> EvidenceUpdateRecord:
    d = dict(_record_dict(**overrides))
    d["sorted_target_ids"] = tuple(d["sorted_target_ids"])
    return EvidenceUpdateRecord(**d)


# ===========================================================================
# 1. EvidenceUpdateRecord validation
# ===========================================================================


class TestEvidenceUpdateRecordFrozen:
    def test_frozen_rejects_mutation(self):
        rec = _record()
        with pytest.raises(AttributeError):
            rec.record_id = "other"  # type: ignore[misc]


class TestEvidenceUpdateRecordConstructorRejects:
    @pytest.mark.parametrize(
        "field,bad_val",
        [
            ("record_id", ""),
            ("record_id", 123),
            ("actor", ""),
            ("actor", True),
            ("evidence_id", ""),
            ("evidence_id", "BAD-FORMAT"),
            ("content_hash", ""),
            ("content_hash", 123),
            ("prior_state_digest", ""),
            ("prior_state_digest", "not-hex-64"),
            ("result_state_digest", ""),
            ("result_state_digest", "zz" * 32),
        ],
    )
    def test_bad_field(self, field: str, bad_val: Any):
        kwargs = _record_dict()
        kwargs[field] = bad_val
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

    def test_list_for_tuple_typed_sorted_target_ids_rejected(self):
        kwargs = _record_dict()
        kwargs["sorted_target_ids"] = ["THOUGHT-A"]  # list, not tuple
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

    def test_empty_sorted_target_ids_rejected(self):
        kwargs = _record_dict()
        kwargs["sorted_target_ids"] = ()
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

    def test_duplicate_sorted_target_ids_rejected(self):
        kwargs = _record_dict()
        kwargs["sorted_target_ids"] = ("THOUGHT-A", "THOUGHT-A")
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

    def test_bad_target_pattern_rejected(self):
        kwargs = _record_dict()
        kwargs["sorted_target_ids"] = ("BAD-ID",)
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

    def test_non_string_target_rejected(self):
        kwargs = _record_dict()
        kwargs["sorted_target_ids"] = (123,)
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

    @pytest.mark.parametrize(
        "ts",
        [
            "not-a-timestamp",
            "2025-01-01",
            "2025-01-01T00:00:00",
            "2025-13-01T00:00:00Z",
        ],
        ids=["garbage", "date_only", "naive", "bad_month"],
    )
    def test_bad_timestamp_rejected(self, ts: str):
        kwargs = _record_dict()
        kwargs["timestamp"] = ts
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord(**kwargs)

class TestEvidenceUpdateRecordNormalizesTargets:
    def test_unsorted_targets_normalized(self):
        rec = _record(sorted_target_ids=("THOUGHT-B", "THOUGHT-A"))
        assert rec.sorted_target_ids == ("THOUGHT-A", "THOUGHT-B")

    def test_already_sorted_unchanged(self):
        rec = _record(sorted_target_ids=("THOUGHT-A", "THOUGHT-B"))
        assert rec.sorted_target_ids == ("THOUGHT-A", "THOUGHT-B")


class TestEvidenceUpdateRecordFromDict:
    def test_exact_keys_required(self):
        d = _record_dict()
        rec = EvidenceUpdateRecord.from_dict(d)
        assert rec.record_id == VALID_RECORD_ID

    def test_extra_key_rejected(self):
        d = _record_dict()
        d["extra"] = 1
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord.from_dict(d)

    def test_missing_key_rejected(self):
        d = _record_dict()
        del d["record_id"]
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord.from_dict(d)

    def test_sorted_target_ids_must_be_json_list(self):
        d = _record_dict()
        d["sorted_target_ids"] = ("THOUGHT-A",)  # tuple, not list
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord.from_dict(d)

    def test_non_dict_rejected(self):
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord.from_dict("not a dict")


class TestEvidenceUpdateRecordCanonicalRoundTrip:
    def test_to_canonical_json_from_canonical_json(self):
        rec = _record()
        j = rec.to_canonical_json()
        rec2 = EvidenceUpdateRecord.from_canonical_json(j)
        assert rec2 == rec
        assert rec2.to_canonical_json() == j

    def test_deterministic(self):
        rec = _record()
        assert rec.to_canonical_json() == rec.to_canonical_json()

    def test_from_canonical_json_non_string_rejected(self):
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord.from_canonical_json(123)

    def test_from_canonical_json_bad_json_rejected(self):
        with pytest.raises(InvalidRecordError):
            EvidenceUpdateRecord.from_canonical_json("{bad")


class TestEvidenceUpdateRecordToDict:
    def test_to_dict_returns_list_for_targets(self):
        rec = _record()
        d = rec.to_dict()
        assert isinstance(d["sorted_target_ids"], list)
        assert d["sorted_target_ids"] == ["THOUGHT-A"]


# ===========================================================================
# 2. apply_evidence two-target success
# ===========================================================================


class TestApplyEvidenceTwoTargetSuccess:
    def _build_scenario(self):
        """Build a two-target scenario with different classifications."""
        t_a = _make_ts("THOUGHT-A", claim="claim-a")
        t_b = _make_ts("THOUGHT-B", claim="claim-b")
        snap = _make_snapshot((t_a, t_b))

        classifications = {"THOUGHT-A": "supporting", "THOUGHT-B": "opposing"}
        packet = _make_packet(
            evidence_id="EV-TEST",
            affected=("THOUGHT-A", "THOUGHT-B"),
            content_hash="ch-123",
        )
        plan = _make_plan(
            packet=packet,
            classifications=classifications,
            snapshot=snap,
        )

        # Build replacements: each gets evidence appended to the right bucket
        rep_a = _make_ts(
            "THOUGHT-A",
            claim="claim-a",
            evidence=_make_evidence(supporting=("EV-TEST",)),
        )
        rep_b = _make_ts(
            "THOUGHT-B",
            claim="claim-b",
            evidence=_make_evidence(opposing=("EV-TEST",)),
        )
        replacements = {"THOUGHT-A": rep_a, "THOUGHT-B": rep_b}
        return snap, plan, replacements

    def test_success_returns_new_snapshot_and_record(self):
        snap, plan, reps = self._build_scenario()
        new_snap, rec = apply_evidence(
            snap,
            plan,
            reps,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        assert isinstance(new_snap, PopulationSnapshot)
        assert isinstance(rec, EvidenceUpdateRecord)

    def test_exact_bucket_append(self):
        snap, plan, reps = self._build_scenario()
        new_snap, _ = apply_evidence(
            snap,
            plan,
            reps,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        new_a = new_snap.get("THOUGHT-A")
        new_b = new_snap.get("THOUGHT-B")
        assert new_a is not None and new_b is not None
        assert new_a.evidence.supporting == ("EV-TEST",)
        assert new_a.evidence.opposing == ()
        assert new_a.evidence.unresolved == ()
        assert new_b.evidence.opposing == ("EV-TEST",)
        assert new_b.evidence.supporting == ()
        assert new_b.evidence.unresolved == ()

    def test_caller_changes_metrics_verification_status(self):
        snap, plan, reps = self._build_scenario()
        # Modify metrics/verification/status on replacement A
        rep_a_mod = _make_ts(
            "THOUGHT-A",
            claim="claim-a",
            confidence=0.99,
            evidence=_make_evidence(supporting=("EV-TEST",)),
        )
        reps_mod = {"THOUGHT-A": rep_a_mod, "THOUGHT-B": reps["THOUGHT-B"]}
        new_snap, _ = apply_evidence(
            snap,
            plan,
            reps_mod,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        assert new_snap.get("THOUGHT-A").metrics.confidence == 0.99

    def test_sorted_record_targets(self):
        snap, plan, reps = self._build_scenario()
        _, rec = apply_evidence(
            snap,
            plan,
            reps,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        assert rec.sorted_target_ids == ("THOUGHT-A", "THOUGHT-B")

    def test_explicit_sha256_digests(self):
        snap, plan, reps = self._build_scenario()
        new_snap, rec = apply_evidence(
            snap,
            plan,
            reps,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        expected_prior = _snapshot_digest(snap)
        assert rec.prior_state_digest == expected_prior
        assert rec.result_state_digest == _snapshot_digest(new_snap)
        # result digest must be a valid SHA-256 hex
        assert len(rec.result_state_digest) == 64
        assert all(c in "0123456789abcdef" for c in rec.result_state_digest)

    def test_prior_canonical_bytes_unchanged(self):
        snap, plan, reps = self._build_scenario()
        before = snap.to_canonical_json()
        apply_evidence(
            snap,
            plan,
            reps,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        assert snap.to_canonical_json() == before

    def test_prior_history_unchanged(self):
        snap, plan, reps = self._build_scenario()
        apply_evidence(
            snap,
            plan,
            reps,
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        # snap.history should be empty tuple still
        assert snap.history == ()

    def test_non_target_thought_state_same_object(self):
        """Non-target ThoughtState is the same object in result."""
        t_a = _make_ts("THOUGHT-A")
        t_b = _make_ts("THOUGHT-B")
        t_c = _make_ts("THOUGHT-C")
        snap = _make_snapshot((t_a, t_b, t_c))

        classifications = {"THOUGHT-A": "supporting"}
        packet = _make_packet(evidence_id="EV-X", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications=classifications,
            snapshot=snap,
        )
        rep_a = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-X",)),
        )
        new_snap, _ = apply_evidence(
            snap,
            plan,
            {"THOUGHT-A": rep_a},
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        # THOUGHT-C should be the exact same object
        assert new_snap.get("THOUGHT-C") is t_c


# ===========================================================================
# 3. Replacement key validation
# ===========================================================================


class TestReplacementKeyValidation:
    def _base_snap_and_plan(self):
        t_a = _make_ts("THOUGHT-A")
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-K", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )
        return snap, plan

    @pytest.mark.parametrize(
        "replacements",
        [
            pytest.param({}, id="missing_key"),
            pytest.param(
                {"THOUGHT-A": _make_ts("THOUGHT-A"), "THOUGHT-EXTRA": _make_ts("THOUGHT-EXTRA")},
                id="extra_key",
            ),
        ],
    )
    def test_missing_extra_key(self, replacements):
        snap, plan = self._base_snap_and_plan()
        with pytest.raises(TargetMismatchError):
            apply_evidence(
                snap,
                plan,
                replacements,
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_non_string_key_rejected(self):
        snap, plan = self._base_snap_and_plan()
        with pytest.raises(TargetMismatchError):
            apply_evidence(
                snap,
                plan,
                {123: _make_ts("THOUGHT-A")},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_bad_pattern_key_rejected(self):
        snap, plan = self._base_snap_and_plan()
        with pytest.raises(TargetMismatchError):
            apply_evidence(
                snap,
                plan,
                {"BAD-KEY": _make_ts("THOUGHT-A")},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_non_thought_state_value_rejected(self):
        snap, plan = self._base_snap_and_plan()
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": "not a ThoughtState"},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_replacement_thought_id_mismatch_rejected(self):
        snap, plan = self._base_snap_and_plan()
        # Replacement has wrong thought_id
        wrong = _make_ts("THOUGHT-WRONG")
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": wrong},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )


# ===========================================================================
# 4. Preserved field violations
# ===========================================================================


class TestPreservedFieldViolations:
    def _base(self):
        t_a = _make_ts("THOUGHT-A", parents=("THOUGHT-P",), claim="orig")
        t_p = _make_ts("THOUGHT-P")
        snap = _make_snapshot((t_a, t_p))
        packet = _make_packet(evidence_id="EV-P", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )
        return snap, plan

    @pytest.mark.parametrize(
        "make_replacement",
        [
            pytest.param(
                lambda: _make_ts("THOUGHT-WRONG", evidence=_make_evidence(supporting=("EV-P",))),
                id="thought_id",
            ),
            pytest.param(
                lambda: _make_ts("THOUGHT-A", parents=(), evidence=_make_evidence(supporting=("EV-P",))),
                id="parent_ids",
            ),
        ],
    )
    def test_preserved_field_violation(self, make_replacement):
        snap, plan = self._base()
        rep = make_replacement()
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_created_at_violation(self):
        snap, plan = self._base()
        d = _make_ts("THOUGHT-A", evidence=_make_evidence(supporting=("EV-P",))).to_dict()
        d["created_at"] = "2099-12-31T23:59:59Z"
        rep = ThoughtState.from_dict(d)
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_interpretation_violation(self):
        snap, plan = self._base()
        d = _make_ts("THOUGHT-A", evidence=_make_evidence(supporting=("EV-P",))).to_dict()
        d["interpretation"]["summary"] = "CHANGED"
        rep = ThoughtState.from_dict(d)
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_hypothesis_violation(self):
        snap, plan = self._base()
        d = _make_ts("THOUGHT-A", evidence=_make_evidence(supporting=("EV-P",))).to_dict()
        d["hypothesis"]["claim"] = "CHANGED"
        rep = ThoughtState.from_dict(d)
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_assumptions_violation(self):
        snap, plan = self._base()
        d = _make_ts("THOUGHT-A", evidence=_make_evidence(supporting=("EV-P",))).to_dict()
        d["assumptions"] = [{"statement": "new", "confidence": 0.5, "source": "s", "assumption_id": "ASSUMP-new"}]
        rep = ThoughtState.from_dict(d)
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_executor_profile_violation(self):
        snap, plan = self._base()
        d = _make_ts("THOUGHT-A", evidence=_make_evidence(supporting=("EV-P",))).to_dict()
        d["executor_profile"]["preferred_model_class"] = "CHANGED"
        rep = ThoughtState.from_dict(d)
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_graph_violation(self):
        snap, plan = self._base()
        d = _make_ts("THOUGHT-A", evidence=_make_evidence(supporting=("EV-P",))).to_dict()
        d["graph"]["dependencies"] = ["THOUGHT-Z"]
        rep = ThoughtState.from_dict(d)
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )


# ===========================================================================
# 5. Exact bucket violations
# ===========================================================================


class TestBucketViolations:
    def _base(self):
        t_a = _make_ts("THOUGHT-A")
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-B", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )
        return snap, plan

    def test_missing_append(self):
        """Replacement has empty supporting bucket Ã¢Â€Â“ missing the append."""
        snap, plan = self._base()
        rep = _make_ts("THOUGHT-A")  # no evidence appended
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_extra_selected_bucket_item(self):
        """Replacement has an extra selected-bucket item."""
        snap, plan = self._base()
        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-B", "EV-EXTRA")),
        )
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_removed_prior_entry(self):
        """Prior had evidence in a bucket; replacement removes it."""
        t_a = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(opposing=("EV-OLD",)),
        )
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-B", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )
        # Replacement has supporting appended but opposing is empty (removed EV-OLD)
        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-B",)),
        )
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_reordered_prior_entry(self):
        """Prior had evidence; replacement reorders it."""
        t_a = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-OLD",)),
        )
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-B", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )
        # Reorder: new evidence first, then old
        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-B", "EV-OLD")),
        )
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_evidence_in_wrong_bucket(self):
        """Evidence placed in wrong bucket."""
        snap, plan = self._base()
        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(opposing=("EV-B",)),  # wrong bucket
        )
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_evidence_in_other_bucket(self):
        """Evidence placed in a non-target bucket that should be unchanged."""
        snap, plan = self._base()
        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(
                supporting=("EV-B",),
                unresolved=("EV-SPURIOUS",),
            ),
        )
        with pytest.raises(ReplacementValidationError):
            apply_evidence(
                snap,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )


# ===========================================================================
# 6. Invalid batches Ã¢Â€Â“ prior snapshot unchanged, no result
# ===========================================================================


class TestInvalidBatchPriorUnchanged:
    @pytest.mark.parametrize(
        "build_replacements,expected_error",
        [
            pytest.param(lambda: {}, TargetMismatchError, id="empty_replacements"),
            pytest.param(
                lambda: {"THOUGHT-A": "not-a-thought-state"},
                ReplacementValidationError,
                id="non_thought_state",
            ),
            pytest.param(
                lambda: {"THOUGHT-A": _make_ts("THOUGHT-WRONG")},
                ReplacementValidationError,
                id="id_mismatch",
            ),
            pytest.param(
                lambda: {"THOUGHT-A": _make_ts("THOUGHT-A")},  # no evidence append
                ReplacementValidationError,
                id="missing_bucket_append",
            ),
        ],
    )
    def test_prior_snapshot_canonical_json_unchanged(self, build_replacements, expected_error):
        t_a = _make_ts("THOUGHT-A")
        snap = _make_snapshot((t_a,))
        before_json = snap.to_canonical_json()
        before_history = snap.history

        packet = _make_packet(evidence_id="EV-Z", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )
        reps = build_replacements()

        with pytest.raises(expected_error):
            apply_evidence(
                snap,
                plan,
                reps,
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

        assert snap.to_canonical_json() == before_json
        assert snap.history == before_history


# ===========================================================================
# 7. Stale/deserialized plan revalidation
# ===========================================================================


class TestStalePlanRevalidation:
    def test_terminal_target_fails_revalidation(self):
        t_a = _make_ts("THOUGHT-A", status="active")
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-S", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )

        # Now make target terminal
        t_a_term = _make_ts("THOUGHT-A", status="rejected")
        snap_term = _make_snapshot((t_a_term,))

        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-S",)),
        )
        with pytest.raises(PlanValidationError):
            apply_evidence(
                snap_term,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_evidence_already_present_fails_revalidation(self):
        t_a = _make_ts("THOUGHT-A", status="active")
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-S", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )

        # Now evidence already present
        t_a_ev = _make_ts(
            "THOUGHT-A",
            status="active",
            evidence=_make_evidence(supporting=("EV-S",)),
        )
        snap_ev = _make_snapshot((t_a_ev,))

        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-S",)),
        )
        with pytest.raises(PlanValidationError):
            apply_evidence(
                snap_ev,
                plan,
                {"THOUGHT-A": rep},
                record_id=VALID_RECORD_ID,
                timestamp=VALID_TS,
                actor=VALID_ACTOR,
            )

    def test_deserialized_plan_revalidation(self):
        """A plan round-tripped through canonical JSON still validates."""
        t_a = _make_ts("THOUGHT-A")
        snap = _make_snapshot((t_a,))
        packet = _make_packet(evidence_id="EV-D", affected=("THOUGHT-A",))
        plan = _make_plan(
            packet=packet,
            classifications={"THOUGHT-A": "supporting"},
            snapshot=snap,
        )

        # Round-trip
        j = plan.to_canonical_json()
        plan2 = AssimilationPlan.from_canonical_json(j)

        before = snap.to_canonical_json()
        rep = _make_ts(
            "THOUGHT-A",
            evidence=_make_evidence(supporting=("EV-D",)),
        )
        new_snap, rec = apply_evidence(
            snap,
            plan2,
            {"THOUGHT-A": rep},
            record_id=VALID_RECORD_ID,
            timestamp=VALID_TS,
            actor=VALID_ACTOR,
        )
        assert rec.evidence_id == "EV-D"
        assert new_snap.get("THOUGHT-A").evidence.supporting == ("EV-D",)
        assert rec.prior_state_digest == _snapshot_digest(snap)
        assert rec.result_state_digest == _snapshot_digest(new_snap)
        assert snap.to_canonical_json() == before
        assert new_snap.history == snap.history


@pytest.mark.parametrize(
    "record_id, timestamp, actor",
    [
        ("", VALID_TS, VALID_ACTOR),
        (123, VALID_TS, VALID_ACTOR),
        (VALID_RECORD_ID, "not-a-datetime", VALID_ACTOR),
        (VALID_RECORD_ID, "2025-01-01T00:00:00", VALID_ACTOR),
        (VALID_RECORD_ID, VALID_TS, ""),
        (VALID_RECORD_ID, VALID_TS, 456),
    ],
)
def test_apply_evidence_rejects_invalid_record_metadata(
    record_id: Any, timestamp: Any, actor: Any
) -> None:
    t_a = _make_ts("THOUGHT-A")
    snap = _make_snapshot((t_a,))
    packet = _make_packet(evidence_id="EV-M", affected=("THOUGHT-A",))
    plan = _make_plan(
        packet=packet,
        classifications={"THOUGHT-A": "supporting"},
        snapshot=snap,
    )
    replacement = _make_ts(
        "THOUGHT-A",
        evidence=_make_evidence(supporting=("EV-M",)),
    )

    before = snap.to_canonical_json()
    history = snap.history

    with pytest.raises(InvalidRecordError):
        apply_evidence(
            snap,
            plan,
            {"THOUGHT-A": replacement},
            record_id=record_id,
            timestamp=timestamp,
            actor=actor,
        )

    assert snap.to_canonical_json() == before
    assert snap.history == history
