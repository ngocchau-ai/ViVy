"""Atomic multi-thought state update engine for evidence assimilation.

Provides ``EvidenceUpdateRecord`` and ``apply_evidence`` for deterministic,
replayable, atomic replacement of affected ThoughtStates within a
PopulationSnapshot.  Standard-library only; no I/O, no ID/timestamp generation,
no confidence arithmetic.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from nps_core.evidence_assimilator.errors import PlanValidationError
from nps_core.evidence_assimilator.impact import AssimilationPlan
from nps_core.hypothesis_population.lifecycle import PopulationSnapshot
from nps_core.hypothesis_population.thought_state import ThoughtState
from nps_core.state_update.errors import (
    InvalidRecordError,
    ReplacementValidationError,
    TargetMismatchError,
)

__all__ = [
    "EvidenceUpdateRecord",
    "apply_evidence",
]

# ---------------------------------------------------------------------------
# Constants / patterns
# ---------------------------------------------------------------------------

_EVIDENCE_ID_RE = re.compile(r"^EV-[A-Za-z0-9._-]+$")
_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")
_ISO_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_EVIDENCE_BUCKETS = ("supporting", "opposing", "unresolved")

_RECORD_KEYS = frozenset({
    "record_id",
    "timestamp",
    "actor",
    "evidence_id",
    "content_hash",
    "sorted_target_ids",
    "prior_state_digest",
    "result_state_digest",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_err(msg: str, **kwargs: Any) -> InvalidRecordError:
    return InvalidRecordError(msg, **kwargs)


def _replacement_err(
    msg: str, *, thought_id: str | None = None, **kwargs: Any
) -> ReplacementValidationError:
    return ReplacementValidationError(msg, thought_id=thought_id, **kwargs)


def _target_err(msg: str, *, thought_id: str | None = None) -> TargetMismatchError:
    return TargetMismatchError(msg, thought_id=thought_id)


def _plan_err(msg: str, **kwargs: Any) -> PlanValidationError:
    return PlanValidationError(msg, **kwargs)


def _validate_non_empty_str(value: Any, name: str) -> str:
    if isinstance(value, bool):
        raise _record_err(f"{name} must be a string, not bool", path=name)
    if not isinstance(value, str) or not value.strip():
        raise _record_err(f"{name} must be a non-empty string", path=name)
    return value


def _validate_timestamp(value: Any, name: str) -> str:
    _validate_non_empty_str(value, name)
    if not _ISO_Z_RE.match(value):
        raise _record_err(
            f"{name} must be RFC3339/ISO-8601 timezone-aware", path=name
        )
    raw = value
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise _record_err(
            f"{name} is not a valid ISO-8601 datetime: {exc}", path=name
        ) from exc
    if dt.tzinfo is None:
        raise _record_err(f"{name} must be timezone-aware", path=name)
    return value


def _validate_digest(value: Any, name: str) -> str:
    _validate_non_empty_str(value, name)
    if not _SHA256_RE.match(value):
        raise _record_err(
            f"{name} must be a lowercase 64-hex SHA-256 digest, got {value!r}",
            path=name,
        )
    return value


def _validate_content_hash(value: Any) -> str:
    """Validate content_hash as opaque non-empty string per schema and ADR-0006."""
    return _validate_non_empty_str(value, "content_hash")


def _canonical_json_bytes(obj: Any) -> bytes:
    """Produce deterministic canonical JSON bytes."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot_digest(snapshot: PopulationSnapshot) -> str:
    """SHA-256 hex digest of the snapshot's canonical JSON."""
    return _sha256_hex(_canonical_json_bytes(snapshot.to_dict()))


def _normalize_sorted_target_ids(raw: Any) -> tuple[str, ...]:
    """Normalize and validate sorted_target_ids.

    Direct construction requires ``raw`` to be a ``tuple``.  ``from_dict``
    converts the JSON list to a tuple before calling this function, so
    dict/JSON round trips remain unchanged.

    Validates each entry is a string matching the Thought ID pattern,
    ensures uniqueness, and returns a lexicographically sorted tuple.
    """
    if not isinstance(raw, tuple):
        raise _record_err(
            f"sorted_target_ids must be a tuple, got {type(raw).__name__}",
            path="sorted_target_ids",
        )
    if len(raw) == 0:
        raise _record_err(
            "sorted_target_ids must be non-empty",
            path="sorted_target_ids",
        )
    seen: set[str] = set()
    validated: list[str] = []
    for i, tid in enumerate(raw):
        if not isinstance(tid, str):
            raise _record_err(
                f"sorted_target_ids[{i}] must be a string, got {type(tid).__name__}",
                path=f"sorted_target_ids[{i}]",
            )
        if not _THOUGHT_ID_RE.match(tid):
            raise _record_err(
                (
                    "sorted_target_ids entries must match "
                    "^THOUGHT-[A-Za-z0-9._-]+$, "
                    f"got {tid!r}"
                ),
                path=f"sorted_target_ids[{i}]",
            )
        if tid in seen:
            raise _record_err(
                f"duplicate target in sorted_target_ids: {tid!r}",
                path="sorted_target_ids",
            )
        seen.add(tid)
        validated.append(tid)
    return tuple(sorted(validated))


# ---------------------------------------------------------------------------
# EvidenceUpdateRecord
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvidenceUpdateRecord:
    """Immutable provenance record for an atomic evidence update.

    All fields are caller-supplied or derived deterministically from the
    update operation.  No nondeterministic data is generated.
    """

    record_id: str
    timestamp: str
    actor: str
    evidence_id: str
    content_hash: str
    sorted_target_ids: tuple[str, ...]
    prior_state_digest: str
    result_state_digest: str

    def __post_init__(self) -> None:
        # record_id
        _validate_non_empty_str(self.record_id, "record_id")
        # timestamp â RFC3339 timezone-aware
        _validate_timestamp(self.timestamp, "timestamp")
        # actor
        _validate_non_empty_str(self.actor, "actor")
        # evidence_id â EV- pattern
        _validate_non_empty_str(self.evidence_id, "evidence_id")
        if not _EVIDENCE_ID_RE.match(self.evidence_id):
            raise _record_err(
                (
                    "evidence_id must match "
                    "^EV-[A-Za-z0-9._-]+$, "
                    f"got {self.evidence_id!r}"
                ),
                path="evidence_id",
            )
        # content_hash â opaque non-empty string per schema and ADR-0006
        _validate_content_hash(self.content_hash)
        # sorted_target_ids â normalize: validate, deduplicate, sort
        normalized = _normalize_sorted_target_ids(self.sorted_target_ids)
        # Use object.__setattr__ to set the normalized value on frozen dataclass
        object.__setattr__(self, "sorted_target_ids", normalized)
        # prior_state_digest
        _validate_digest(self.prior_state_digest, "prior_state_digest")
        # result_state_digest
        _validate_digest(self.result_state_digest, "result_state_digest")

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "evidence_id": self.evidence_id,
            "content_hash": self.content_hash,
            "sorted_target_ids": list(self.sorted_target_ids),
            "prior_state_digest": self.prior_state_digest,
            "result_state_digest": self.result_state_digest,
        }

    @classmethod
    def from_dict(cls, data: Any) -> EvidenceUpdateRecord:
        """Strict construction from a plain dict.

        Requires exact keys and JSON list for ``sorted_target_ids``.
        """
        if not isinstance(data, dict):
            raise _record_err(
                f"expected dict, got {type(data).__name__}",
                path="root",
            )
        extra = set(data.keys()) - _RECORD_KEYS
        if extra:
            raise _record_err(
                f"unexpected keys: {sorted(extra)}",
                path="root",
            )
        missing = _RECORD_KEYS - set(data.keys())
        if missing:
            raise _record_err(
                f"missing keys: {sorted(missing)}",
                path="root",
            )
        # sorted_target_ids must be a JSON list
        raw_targets = data["sorted_target_ids"]
        if not isinstance(raw_targets, list):
            raise _record_err(
                f"sorted_target_ids must be a JSON list, got {type(raw_targets).__name__}",
                path="sorted_target_ids",
            )
        return cls(
            record_id=data["record_id"],
            timestamp=data["timestamp"],
            actor=data["actor"],
            evidence_id=data["evidence_id"],
            content_hash=data["content_hash"],
            sorted_target_ids=tuple(raw_targets),
            prior_state_digest=data["prior_state_digest"],
            result_state_digest=data["result_state_digest"],
        )

    def to_canonical_json(self) -> str:
        """Serialize to deterministic canonical JSON string."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_canonical_json(cls, text: str) -> EvidenceUpdateRecord:
        """Deserialize from a canonical JSON string."""
        if not isinstance(text, str):
            raise _record_err(
                f"expected str, got {type(text).__name__}",
                path="root",
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _record_err(
                f"invalid JSON: {exc}",
                path="root",
            ) from exc
        if not isinstance(data, dict):
            raise _record_err(
                f"expected JSON object at root, got {type(data).__name__}",
                path="root",
            )
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# apply_evidence
# ---------------------------------------------------------------------------

def apply_evidence(
    snapshot: PopulationSnapshot,
    plan: AssimilationPlan,
    replacements: dict[str, ThoughtState],
    *,
    record_id: str,
    timestamp: str,
    actor: str,
) -> tuple[PopulationSnapshot, EvidenceUpdateRecord]:
    """Atomically apply an evidence update to all affected ThoughtStates.

    Validates the complete update batch before constructing a new snapshot.
    On any validation failure the prior snapshot is returned byte-identical
    and no record is produced.

    Parameters
    ----------
    snapshot:
        The current immutable population snapshot.
    plan:
        A validated assimilation plan mapping one evidence packet to
        per-hypothesis impacts.
    replacements:
        Mapping from target thought ID to the caller-supplied complete
        replacement ThoughtState.
    record_id:
        Caller-supplied unique record identifier.
    timestamp:
        Caller-supplied RFC3339 timezone-aware timestamp.
    actor:
        Caller-supplied non-empty actor string.

    Returns
    -------
    tuple[PopulationSnapshot, EvidenceUpdateRecord]
        The new snapshot with all replacements applied and the provenance
        record.

    Raises
    ------
    InvalidRecordError
        If record_id, timestamp, or actor is missing or malformed.
    PlanValidationError
        If the plan fails validation against the snapshot.
    TargetMismatchError
        If the replacement key set does not match the plan targets.
    ReplacementValidationError
        If any replacement fails boundary validation.
    """

    # ------------------------------------------------------------------
    # 1. Validate caller record metadata
    # ------------------------------------------------------------------
    _validate_non_empty_str(record_id, "record_id")
    _validate_timestamp(timestamp, "timestamp")
    _validate_non_empty_str(actor, "actor")

    # ------------------------------------------------------------------
    # 2. Validate input types
    # ------------------------------------------------------------------
    if not isinstance(snapshot, PopulationSnapshot):
        raise _plan_err(
            f"snapshot must be a PopulationSnapshot, got {type(snapshot).__name__}",
            path="snapshot",
        )
    if not isinstance(plan, AssimilationPlan):
        raise _plan_err(
            f"plan must be an AssimilationPlan, got {type(plan).__name__}",
            path="plan",
        )
    if not isinstance(replacements, dict):
        raise _target_err(
            f"replacements must be a dict, got {type(replacements).__name__}",
        )

    # ------------------------------------------------------------------
    # 3. Validate replacement keys are strings matching Thought ID pattern
    # ------------------------------------------------------------------
    for key in replacements:
        if not isinstance(key, str):
            raise _target_err(
                f"replacement key must be a string, got {type(key).__name__}: {key!r}",
            )
        if not _THOUGHT_ID_RE.match(key):
            raise _target_err(
                (
                    "replacement key must match "
                    "^THOUGHT-[A-Za-z0-9._-]+$, "
                    f"got {key!r}"
                ),
            )

    # ------------------------------------------------------------------
    # 4. Revalidate plan against this exact snapshot
    # ------------------------------------------------------------------
    plan.validate_for(snapshot)

    # ------------------------------------------------------------------
    # 5. Validate replacement key set matches plan targets exactly
    # ------------------------------------------------------------------
    plan_target_ids: tuple[str, ...] = tuple(
        imp.target_thought_id for imp in plan.impacts
    )
    replacement_keys = set(replacements.keys())
    plan_target_set = set(plan_target_ids)

    missing = plan_target_set - replacement_keys
    extra = replacement_keys - plan_target_set

    if missing:
        raise _target_err(
            f"missing replacements for plan targets: {sorted(missing)}",
        )
    if extra:
        raise _target_err(
            f"extra replacements not in plan targets: {sorted(extra)}",
        )

    # ------------------------------------------------------------------
    # 6. Validate each replacement ThoughtState
    # ------------------------------------------------------------------
    # Build a mapping from target_id -> impact classification
    impact_map: dict[str, str] = {
        imp.target_thought_id: imp.classification for imp in plan.impacts
    }

    evidence_id = plan.packet.evidence_id

    for target_id in plan_target_ids:
        replacement = replacements[target_id]

        # 6a. Must be a ThoughtState
        if not isinstance(replacement, ThoughtState):
            raise _replacement_err(
                f"replacement must be a ThoughtState, got {type(replacement).__name__}",
                thought_id=target_id,
            )

        # 6b. Get the prior thought
        prior = snapshot.get(target_id)
        # Should not happen since plan.validate_for already checked, but guard
        if prior is None:
            raise _plan_err(
                f"target thought not found: {target_id!r}",
                thought_id=target_id,
            )

        # 6c. Preserve immutable fields exactly
        if replacement.thought_id != prior.thought_id:
            raise _replacement_err(
                (
                    f"thought_id must be preserved: "
                    f"expected {prior.thought_id!r}, got {replacement.thought_id!r}"
                ),
                thought_id=target_id,
            )
        if replacement.parent_ids != prior.parent_ids:
            raise _replacement_err(
                (
                    f"parent_ids must be preserved: "
                    f"expected {prior.parent_ids!r}, got {replacement.parent_ids!r}"
                ),
                thought_id=target_id,
            )
        if replacement.created_at != prior.created_at:
            raise _replacement_err(
                (
                    f"created_at must be preserved: "
                    f"expected {prior.created_at!r}, got {replacement.created_at!r}"
                ),
                thought_id=target_id,
            )
        if replacement.interpretation != prior.interpretation:
            raise _replacement_err(
                "interpretation must be preserved",
                thought_id=target_id,
            )
        if replacement.hypothesis != prior.hypothesis:
            raise _replacement_err(
                "hypothesis must be preserved",
                thought_id=target_id,
            )
        if replacement.assumptions != prior.assumptions:
            raise _replacement_err(
                "assumptions must be preserved",
                thought_id=target_id,
            )
        if replacement.executor_profile != prior.executor_profile:
            raise _replacement_err(
                "executor_profile must be preserved",
                thought_id=target_id,
            )
        if replacement.graph != prior.graph:
            raise _replacement_err(
                "graph must be preserved",
                thought_id=target_id,
            )

        # 6d. Evidence bucket semantics
        classification = impact_map[target_id]

        # The selected bucket must equal prior + (evidence_id,) appended once
        selected_bucket_prior: tuple[str, ...] = getattr(
            prior.evidence, classification
        )
        selected_bucket_replacement: tuple[str, ...] = getattr(
            replacement.evidence, classification
        )
        expected_selected = (*selected_bucket_prior, evidence_id)
        if selected_bucket_replacement != expected_selected:
            raise _replacement_err(
                (
                    f"{classification} bucket must equal prior plus "
                    f"({evidence_id!r},) appended once: "
                    f"expected {expected_selected!r}, "
                    f"got {selected_bucket_replacement!r}"
                ),
                thought_id=target_id,
            )

        # The other two buckets must equal the prior exactly
        for bucket_name in _EVIDENCE_BUCKETS:
            if bucket_name == classification:
                continue
            prior_bucket: tuple[str, ...] = getattr(
                prior.evidence, bucket_name
            )
            replacement_bucket: tuple[str, ...] = getattr(
                replacement.evidence, bucket_name
            )
            if replacement_bucket != prior_bucket:
                raise _replacement_err(
                    (
                        f"{bucket_name} bucket must equal prior exactly: "
                        f"expected {prior_bucket!r}, "
                        f"got {replacement_bucket!r}"
                    ),
                    thought_id=target_id,
                )

    # ------------------------------------------------------------------
    # 7. Compute prior state digest
    # ------------------------------------------------------------------
    prior_digest = _snapshot_digest(snapshot)

    # ------------------------------------------------------------------
    # 8. Construct new snapshot with all replacements applied atomically
    # ------------------------------------------------------------------
    replacement_set = set(plan_target_ids)
    new_thoughts: list[ThoughtState] = []
    for thought in snapshot.thoughts:
        if thought.thought_id in replacement_set:
            new_thoughts.append(replacements[thought.thought_id])
        else:
            new_thoughts.append(thought)

    new_snapshot = PopulationSnapshot(
        thoughts=tuple(sorted(new_thoughts, key=lambda t: t.thought_id)),
        history=snapshot.history,
    )

    # ------------------------------------------------------------------
    # 9. Compute result state digest
    # ------------------------------------------------------------------
    result_digest = _snapshot_digest(new_snapshot)

    # ------------------------------------------------------------------
    # 10. Construct EvidenceUpdateRecord
    # ------------------------------------------------------------------
    record = EvidenceUpdateRecord(
        record_id=record_id,
        timestamp=timestamp,
        actor=actor,
        evidence_id=evidence_id,
        content_hash=plan.packet.content_hash,
        sorted_target_ids=tuple(sorted(plan_target_ids)),
        prior_state_digest=prior_digest,
        result_state_digest=result_digest,
    )

    return new_snapshot, record
