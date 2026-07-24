"""Evidence impact and assimilation plan models for evidence assimilation.

Provides frozen, slotted ``EvidenceImpact`` and ``AssimilationPlan`` dataclasses
with strict validation, exact-key ``from_dict``/``to_dict``, and deterministic
canonical JSON round-trips.  Standard-library only; no runtime ``jsonschema``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from nps_core.evidence_assimilator.errors import (
    ImpactValidationError,
    PlanValidationError,
)
from nps_core.evidence_assimilator.packet import EvidencePacket
from nps_core.hypothesis_population.lifecycle import PopulationSnapshot
from nps_core.hypothesis_population.thought_state import TERMINAL_STATES

__all__ = [
    "IMPACT_CLASSIFICATIONS",
    "EvidenceImpact",
    "AssimilationPlan",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMPACT_CLASSIFICATIONS: tuple[str, ...] = ("opposing", "supporting", "unresolved")
_IMPACT_CLASSIFICATION_SET: frozenset[str] = frozenset(IMPACT_CLASSIFICATIONS)

_THOUGHT_ID_RE = re.compile(r"^THOUGHT-[A-Za-z0-9._-]+$")

# Evidence bucket field names on ThoughtState
_EVIDENCE_BUCKETS = ("supporting", "opposing", "unresolved")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _impact_err(msg: str, **kwargs: Any) -> ImpactValidationError:
    return ImpactValidationError(msg, **kwargs)


def _plan_err(msg: str, **kwargs: Any) -> PlanValidationError:
    return PlanValidationError(msg, **kwargs)


def _validate_thought_id_pattern(value: str, *, path: str) -> None:
    if not isinstance(value, str):
        raise _impact_err(
            f"expected str, got {type(value).__name__}",
            path=path,
        )
    if not _THOUGHT_ID_RE.match(value):
        raise _impact_err(
            (
                "target_thought_id must match "
                "^THOUGHT-[A-Za-z0-9._-]+$, "
                f"got {value!r}"
            ),
            path=path,
        )


def _validate_classification(value: str, *, path: str) -> None:
    if not isinstance(value, str):
        raise _impact_err(
            f"expected str, got {type(value).__name__}",
            path=path,
        )
    if value not in _IMPACT_CLASSIFICATION_SET:
        raise _impact_err(
            (
                f"classification must be one of {sorted(_IMPACT_CLASSIFICATION_SET)}, "
                f"got {value!r}"
            ),
            path=path,
        )


# ---------------------------------------------------------------------------
# EvidenceImpact
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvidenceImpact:
    """Immutable per-hypothesis impact classification.

    ``target_thought_id`` must match the ``THOUGHT-`` pattern.
    ``classification`` must be exactly one of ``IMPACT_CLASSIFICATIONS``.
    """

    target_thought_id: str
    classification: str

    def __post_init__(self) -> None:
        _validate_thought_id_pattern(
            self.target_thought_id,
            path="target_thought_id",
        )
        _validate_classification(
            self.classification,
            path="classification",
        )

    # -- serialization -------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Any, *, path: str = "impact") -> EvidenceImpact:
        """Strict construction from a plain dict."""
        if not isinstance(data, dict):
            raise _impact_err(
                f"expected dict, got {type(data).__name__}",
                path=path,
            )
        required = {"target_thought_id", "classification"}
        missing = required - data.keys()
        if missing:
            raise _impact_err(
                f"missing keys: {sorted(missing)}",
                path=path,
            )
        extra = data.keys() - required
        if extra:
            raise _impact_err(
                f"unexpected keys: {sorted(extra)}",
                path=path,
            )
        target = data["target_thought_id"]
        classification = data["classification"]
        _validate_thought_id_pattern(target, path=f"{path}.target_thought_id")
        _validate_classification(classification, path=f"{path}.classification")
        return cls(target_thought_id=target, classification=classification)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "target_thought_id": self.target_thought_id,
            "classification": self.classification,
        }


# ---------------------------------------------------------------------------
# AssimilationPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AssimilationPlan:
    """Immutable normalized assimilation plan mapping one evidence packet to
    per-hypothesis impacts.

    Direct construction validates types, non-empty impacts, unique targets,
    and set equality with ``packet.affected_hypotheses``.  The stored impacts
    tuple is sorted lexicographically by ``target_thought_id``.

    ``create(packet, impacts, snapshot)`` additionally validates target
    existence, non-terminal status, and evidence_id absence against the
    supplied snapshot.

    ``validate_for(snapshot)`` revalidates all snapshot-dependent invariants
    so that a deserialized or stale plan can be checked against the exact
    snapshot being updated.
    """

    packet: EvidencePacket
    impacts: tuple[EvidenceImpact, ...]

    def __post_init__(self) -> None:
        # Type checks
        if not isinstance(self.packet, EvidencePacket):
            raise _plan_err(
                f"expected EvidencePacket, got {type(self.packet).__name__}",
                path="packet",
            )
        if not isinstance(self.impacts, tuple):
            raise _plan_err(
                f"expected tuple for impacts, got {type(self.impacts).__name__}",
                path="impacts",
            )
        if len(self.impacts) == 0:
            raise _plan_err(
                "impacts must be non-empty",
                path="impacts",
            )
        # Validate each impact
        for i, impact in enumerate(self.impacts):
            if not isinstance(impact, EvidenceImpact):
                raise _plan_err(
                    (
                        f"impacts[{i}] must be EvidenceImpact, "
                        f"got {type(impact).__name__}"
                    ),
                    path=f"impacts[{i}]",
                )
        # Unique targets
        target_ids: list[str] = []
        seen: set[str] = set()
        for i, impact in enumerate(self.impacts):
            tid = impact.target_thought_id
            if tid in seen:
                raise _plan_err(
                    f"duplicate target_thought_id: {tid!r}",
                    path=f"impacts[{i}].target_thought_id",
                    thought_id=tid,
                )
            seen.add(tid)
            target_ids.append(tid)
        # Set equality with packet.affected_hypotheses
        packet_targets = set(self.packet.affected_hypotheses)
        impact_targets = set(target_ids)
        if impact_targets != packet_targets:
            missing_in_impacts = packet_targets - impact_targets
            extra_in_impacts = impact_targets - packet_targets
            parts: list[str] = []
            if missing_in_impacts:
                parts.append(
                    f"targets in packet but not in impacts: "
                    f"{sorted(missing_in_impacts)}"
                )
            if extra_in_impacts:
                parts.append(
                    f"targets in impacts but not in packet: "
                    f"{sorted(extra_in_impacts)}"
                )
            raise _plan_err(
                "; ".join(parts) if parts else "impact target set mismatch",
                path="impacts",
            )
        # Normalize: sort impacts by target_thought_id
        sorted_impacts = tuple(
            sorted(self.impacts, key=lambda imp: imp.target_thought_id)
        )
        if sorted_impacts is not self.impacts:
            object.__setattr__(self, "impacts", sorted_impacts)

    # -- snapshot-dependent validation ---------------------------------------

    def validate_for(self, snapshot: PopulationSnapshot) -> None:
        """Revalidate snapshot-dependent invariants against the supplied snapshot.

        Checks that every target exists, is non-terminal, and that the
        evidence ID is absent from all three evidence buckets.

        Raises :class:`PlanValidationError` on any violation.
        """
        if not isinstance(snapshot, PopulationSnapshot):
            raise _plan_err(
                f"expected PopulationSnapshot, got {type(snapshot).__name__}",
                path="snapshot",
            )
        evidence_id = self.packet.evidence_id
        for impact in self.impacts:
            tid = impact.target_thought_id
            thought = snapshot.get(tid)
            if thought is None:
                raise _plan_err(
                    f"target thought not found: {tid!r}",
                    thought_id=tid,
                    evidence_id=evidence_id,
                )
            if thought.status.state in TERMINAL_STATES:
                raise _plan_err(
                    (
                        f"target thought is in terminal state: "
                        f"{thought.status.state!r}"
                    ),
                    thought_id=tid,
                    evidence_id=evidence_id,
                )
            # Check evidence_id absence across all three buckets
            for bucket_name in _EVIDENCE_BUCKETS:
                bucket: tuple[str, ...] = getattr(thought.evidence, bucket_name)
                if evidence_id in bucket:
                    raise _plan_err(
                        (
                            f"evidence_id {evidence_id!r} already present in "
                            f"{bucket_name} bucket of thought {tid!r}"
                        ),
                        thought_id=tid,
                        evidence_id=evidence_id,
                    )

    # -- factory with snapshot validation ------------------------------------

    @classmethod
    def create(
        cls,
        packet: EvidencePacket,
        impacts: tuple[EvidenceImpact, ...],
        snapshot: PopulationSnapshot,
    ) -> AssimilationPlan:
        """Construct an AssimilationPlan and validate against the supplied snapshot.

        This is the primary construction path for runtime use.  Structural
        validation happens in ``__post_init__``; snapshot-dependent validation
        happens via ``validate_for``.
        """
        plan = cls(packet=packet, impacts=impacts)
        plan.validate_for(snapshot)
        return plan

    # -- serialization -------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Any, *, path: str = "plan") -> AssimilationPlan:
        """Structural-only construction from a plain dict.

        Requires a JSON list for impacts.  Cannot claim snapshot validation.
        """
        if not isinstance(data, dict):
            raise _plan_err(
                f"expected dict, got {type(data).__name__}",
                path=path,
            )
        required = {"packet", "impacts"}
        missing = required - data.keys()
        if missing:
            raise _plan_err(
                f"missing keys: {sorted(missing)}",
                path=path,
            )
        extra = data.keys() - required
        if extra:
            raise _plan_err(
                f"unexpected keys: {sorted(extra)}",
                path=path,
            )
        packet_data = data["packet"]
        packet = EvidencePacket.from_dict(packet_data, path=f"{path}.packet")
        impacts_data = data["impacts"]
        if not isinstance(impacts_data, list):
            raise _plan_err(
                f"expected JSON list for impacts, got {type(impacts_data).__name__}",
                path=f"{path}.impacts",
            )
        impacts_list: list[EvidenceImpact] = []
        for i, item in enumerate(impacts_data):
            impact = EvidenceImpact.from_dict(
                item,
                path=f"{path}.impacts[{i}]",
            )
            impacts_list.append(impact)
        return cls(packet=packet, impacts=tuple(impacts_list))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "packet": self.packet.to_dict(),
            "impacts": [imp.to_dict() for imp in self.impacts],
        }

    # -- canonical JSON ------------------------------------------------------

    def to_canonical_json(self) -> str:
        """Serialize to deterministic canonical JSON string.

        Sorted keys, compact separators, ``ensure_ascii=False``,
        ``allow_nan=False``.
        """
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_canonical_json(cls, text: str) -> AssimilationPlan:
        """Deserialize from a canonical JSON string.

        Raises :class:`PlanValidationError` on invalid JSON, wrong root type,
        or structural/value violations.  Does not perform snapshot validation.
        """
        if not isinstance(text, str):
            raise _plan_err(
                f"expected str, got {type(text).__name__}",
                path="root",
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _plan_err(
                f"invalid JSON: {exc}",
                path="root",
            ) from exc
        if not isinstance(data, dict):
            raise _plan_err(
                (
                    "expected JSON object at root, "
                    f"got {type(data).__name__}"
                ),
                path="root",
            )
        return cls.from_dict(data)
