"""EvidencePacket V1 strict immutable value model and canonical serialization.

Provides frozen, slotted ``Reproducibility`` and ``EvidencePacket`` dataclasses
with direct validation, exact-key ``from_dict``/``to_dict``, and deterministic
canonical JSON round-trips.  Standard-library only; no runtime ``jsonschema``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from nps_core.evidence_assimilator.errors import PacketValidationError

__all__ = [
    "Reproducibility",
    "EvidencePacket",
]

_EVIDENCE_ID_RE = re.compile(r"^EV-[A-Za-z0-9._-]+$")
_TASK_ID_RE = re.compile(r"^TASK-[A-Za-z0-9._-]+$")

_REQUIRED_KEYS = frozenset({
    "evidence_id",
    "task_id",
    "executor_id",
    "claim",
    "result",
    "method",
    "artifacts",
    "confidence",
    "limitations",
    "failure_modes",
    "reproducibility",
    "affected_hypotheses",
    "provenance",
    "content_hash",
})

_REPRODUCIBILITY_KEYS = frozenset({"command", "environment", "seed"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _err(msg: str, *, path: str | None = None) -> PacketValidationError:
    return PacketValidationError(msg, path=path)


def _check_non_empty_str(value: Any, *, path: str) -> None:
    if not isinstance(value, str):
        raise _err(
            f"expected str, got {type(value).__name__}",
            path=path,
        )
    if not value.strip():
        raise _err("string must be non-empty", path=path)


def _check_str_array(items: Any, *, path: str) -> tuple[str, ...]:
    if not isinstance(items, (list, tuple)):
        raise _err(
            f"expected list, got {type(items).__name__}",
            path=path,
        )
    result: list[str] = []
    for i, item in enumerate(items):
        p = f"{path}[{i}]"
        if not isinstance(item, str):
            raise _err(
                f"expected str, got {type(item).__name__}",
                path=p,
            )
        if not item.strip():
            raise _err("string must be non-empty", path=p)
        result.append(item)
    return tuple(result)


def _check_unique(values: tuple[str, ...], *, path: str) -> None:
    seen: set[str] = set()
    for v in values:
        if v in seen:
            raise _err(f"duplicate entry: {v!r}", path=path)
        seen.add(v)


def _check_confidence(value: Any, *, path: str) -> float:
    if isinstance(value, bool):
        raise _err(
            "bool is not a valid confidence number",
            path=path,
        )
    if not isinstance(value, (int, float)):
        raise _err(
            f"expected number, got {type(value).__name__}",
            path=path,
        )
    if value != value:  # NaN
        raise _err("confidence must be finite", path=path)
    if value == float("inf") or value == float("-inf"):
        raise _err("confidence must be finite", path=path)
    if value < 0 or value > 1:
        raise _err(
            f"confidence must be in [0, 1], got {value}",
            path=path,
        )
    return float(value)


def _check_seed(value: Any, *, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise _err("bool is not a valid seed", path=path)
    if isinstance(value, int):
        return value
    raise _err(
        f"expected int or null, got {type(value).__name__}",
        path=path,
    )


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Reproducibility:
    """Immutable reproducibility descriptor for an evidence packet."""

    command: str
    environment: str
    seed: int | None

    def __post_init__(self) -> None:
        _check_non_empty_str(
            self.command,
            path="reproducibility.command",
        )
        _check_non_empty_str(
            self.environment,
            path="reproducibility.environment",
        )
        _check_seed(self.seed, path="reproducibility.seed")

    # -- serialization -------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Any,
        *,
        path: str = "reproducibility",
    ) -> Reproducibility:
        """Strict construction from a plain dict."""
        if not isinstance(data, dict):
            raise _err(
                f"expected dict, got {type(data).__name__}",
                path=path,
            )
        extra = set(data.keys()) - _REPRODUCIBILITY_KEYS
        if extra:
            raise _err(
                f"unexpected keys: {sorted(extra)}",
                path=path,
            )
        missing = _REPRODUCIBILITY_KEYS - set(data.keys())
        if missing:
            raise _err(
                f"missing keys: {sorted(missing)}",
                path=path,
            )
        cmd = data["command"]
        env = data["environment"]
        seed = data["seed"]
        _check_non_empty_str(cmd, path=f"{path}.command")
        _check_non_empty_str(env, path=f"{path}.environment")
        checked_seed = _check_seed(seed, path=f"{path}.seed")
        return cls(command=cmd, environment=env, seed=checked_seed)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "command": self.command,
            "environment": self.environment,
            "seed": self.seed,
        }


# ---------------------------------------------------------------------------
# EvidencePacket
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvidencePacket:
    """Immutable EvidencePacket V1 value model with strict validation.

    JSON arrays are stored as tuples.  ``reproducibility`` is a
    :class:`Reproducibility` value object.
    """

    evidence_id: str
    task_id: str
    executor_id: str
    claim: str
    result: str
    method: str
    artifacts: tuple[str, ...]
    confidence: float
    limitations: tuple[str, ...]
    failure_modes: tuple[str, ...]
    reproducibility: Reproducibility
    affected_hypotheses: tuple[str, ...]
    provenance: tuple[str, ...]
    content_hash: str

    def __post_init__(self) -> None:
        # Validate non-empty strings before regex
        _check_non_empty_str(
            self.evidence_id,
            path="evidence_id",
        )
        _check_non_empty_str(
            self.task_id,
            path="task_id",
        )
        # Patterns
        if not _EVIDENCE_ID_RE.match(self.evidence_id):
            raise _err(
                (
                    "evidence_id must match "
                    "^EV-[A-Za-z0-9._-]+$, "
                    f"got {self.evidence_id!r}"
                ),
                path="evidence_id",
            )
        if not _TASK_ID_RE.match(self.task_id):
            raise _err(
                (
                    "task_id must match "
                    "^TASK-[A-Za-z0-9._-]+$, "
                    f"got {self.task_id!r}"
                ),
                path="task_id",
            )
        # Non-empty strings
        for field in (
            "executor_id",
            "claim",
            "result",
            "method",
            "content_hash",
        ):
            _check_non_empty_str(getattr(self, field), path=field)
        # Confidence â reuse helper and normalize to float
        checked = _check_confidence(
            self.confidence,
            path="confidence",
        )
        object.__setattr__(self, "confidence", checked)
        # Reproducibility type
        if not isinstance(self.reproducibility, Reproducibility):
            raise _err(
                (
                    "expected Reproducibility, "
                    f"got {type(self.reproducibility).__name__}"
                ),
                path="reproducibility",
            )
        # Tuple types
        for field in (
            "artifacts",
            "limitations",
            "failure_modes",
            "affected_hypotheses",
            "provenance",
        ):
            val = getattr(self, field)
            if not isinstance(val, tuple):
                raise _err(
                    f"expected tuple, got {type(val).__name__}",
                    path=field,
                )
        # Non-empty provenance
        if not self.provenance:
            raise _err(
                "provenance must be non-empty",
                path="provenance",
            )
        # Non-empty affected_hypotheses
        if not self.affected_hypotheses:
            raise _err(
                "affected_hypotheses must be non-empty",
                path="affected_hypotheses",
            )
        # Unique affected_hypotheses
        _check_unique(self.affected_hypotheses, path="affected_hypotheses")
        # Unique artifacts
        _check_unique(self.artifacts, path="artifacts")
        # Unique provenance
        _check_unique(self.provenance, path="provenance")
        # All string-array entries non-empty
        for field in (
            "artifacts",
            "limitations",
            "failure_modes",
            "affected_hypotheses",
            "provenance",
        ):
            for i, item in enumerate(getattr(self, field)):
                if not isinstance(item, str):
                    raise _err(
                        f"expected str, got {type(item).__name__}",
                        path=f"{field}[{i}]",
                    )
                if not item.strip():
                    raise _err(
                        "string must be non-empty",
                        path=f"{field}[{i}]",
                    )

    # -- serialization -------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Any,
        *,
        path: str = "",
    ) -> EvidencePacket:
        """Strict construction from a plain dict (JSON-like structure).

        Requires JSON lists (not tuples) for array fields.  Converts to tuples
        only after strict item validation.
        """
        if not isinstance(data, dict):
            raise _err(
                f"expected dict, got {type(data).__name__}",
                path=path or "root",
            )
        extra = set(data.keys()) - _REQUIRED_KEYS
        if extra:
            raise _err(
                f"unexpected keys: {sorted(extra)}",
                path=path or "root",
            )
        missing = _REQUIRED_KEYS - set(data.keys())
        if missing:
            raise _err(
                f"missing keys: {sorted(missing)}",
                path=path or "root",
            )

        def p(field: str) -> str:
            return f"{path}.{field}" if path else field

        evidence_id = data["evidence_id"]
        task_id = data["task_id"]
        executor_id = data["executor_id"]
        claim = data["claim"]
        result = data["result"]
        method = data["method"]
        content_hash = data["content_hash"]

        _check_non_empty_str(evidence_id, path=p("evidence_id"))
        _check_non_empty_str(task_id, path=p("task_id"))
        _check_non_empty_str(executor_id, path=p("executor_id"))
        _check_non_empty_str(claim, path=p("claim"))
        _check_non_empty_str(result, path=p("result"))
        _check_non_empty_str(method, path=p("method"))
        _check_non_empty_str(content_hash, path=p("content_hash"))

        if not _EVIDENCE_ID_RE.match(evidence_id):
            raise _err(
                (
                    "evidence_id must match "
                    "^EV-[A-Za-z0-9._-]+$, "
                    f"got {evidence_id!r}"
                ),
                path=p("evidence_id"),
            )
        if not _TASK_ID_RE.match(task_id):
            raise _err(
                (
                    "task_id must match "
                    "^TASK-[A-Za-z0-9._-]+$, "
                    f"got {task_id!r}"
                ),
                path=p("task_id"),
            )

        confidence = _check_confidence(
            data["confidence"],
            path=p("confidence"),
        )

        # Require JSON lists for arrays
        for arr_field in (
            "artifacts",
            "limitations",
            "failure_modes",
            "affected_hypotheses",
            "provenance",
        ):
            if not isinstance(data[arr_field], list):
                raise _err(
                    (
                        f"expected JSON list for {arr_field}, "
                        f"got {type(data[arr_field]).__name__}"
                    ),
                    path=p(arr_field),
                )

        artifacts = _check_str_array(
            data["artifacts"],
            path=p("artifacts"),
        )
        limitations = _check_str_array(
            data["limitations"],
            path=p("limitations"),
        )
        failure_modes = _check_str_array(
            data["failure_modes"],
            path=p("failure_modes"),
        )
        affected_hypotheses = _check_str_array(
            data["affected_hypotheses"],
            path=p("affected_hypotheses"),
        )
        provenance = _check_str_array(
            data["provenance"],
            path=p("provenance"),
        )

        reproducibility = Reproducibility.from_dict(
            data["reproducibility"],
            path=p("reproducibility"),
        )

        return cls(
            evidence_id=evidence_id,
            task_id=task_id,
            executor_id=executor_id,
            claim=claim,
            result=result,
            method=method,
            artifacts=artifacts,
            confidence=confidence,
            limitations=limitations,
            failure_modes=failure_modes,
            reproducibility=reproducibility,
            affected_hypotheses=affected_hypotheses,
            provenance=provenance,
            content_hash=content_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict with JSON-compatible lists."""
        return {
            "evidence_id": self.evidence_id,
            "task_id": self.task_id,
            "executor_id": self.executor_id,
            "claim": self.claim,
            "result": self.result,
            "method": self.method,
            "artifacts": list(self.artifacts),
            "confidence": self.confidence,
            "limitations": list(self.limitations),
            "failure_modes": list(self.failure_modes),
            "reproducibility": self.reproducibility.to_dict(),
            "affected_hypotheses": list(self.affected_hypotheses),
            "provenance": list(self.provenance),
            "content_hash": self.content_hash,
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
    def from_canonical_json(cls, text: str) -> EvidencePacket:
        """Deserialize from a canonical JSON string.

        Raises :class:`PacketValidationError` on invalid JSON, wrong root type,
        or structural/value violations.
        """
        if not isinstance(text, str):
            raise _err(
                f"expected str, got {type(text).__name__}",
                path="root",
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _err(
                f"invalid JSON: {exc}",
                path="root",
            ) from exc
        if not isinstance(data, dict):
            raise _err(
                (
                    "expected JSON object at root, "
                    f"got {type(data).__name__}"
                ),
                path="root",
            )
        return cls.from_dict(data)
