"""Model Upgrade Protocol — Progressive scaling of model cores (TD-8).

Vivy accumulates orchestration experience over time. When enough experience
sings (memory entries ≥ threshold, avg decision score ≥ threshold) and
hardware permits, Vivy can migrate from a smaller model core to a larger
one. Migration is auditable via SHA256-chained receipts. Old model weights
are inherited (registered) for callback in special cases.

Structure:
    UpgradeProtocol
    ├── readiness_check() -> dict — gates: memory, score, complexity, HW
    ├── migrate(old_alias, new_alias) -> MigrationReceipt
    └── inherit_weights(old_alias) -> dict (weight registry)

    MigrationReceipt (frozen dataclass)
    ├── receipt_id, old_alias, new_alias, timestamp
    ├── prev_sha256, self_sha256 — SHA256 chain for audit
    ├── inherited_weights: dict
    └── label = "PROVISIONAL_RESULT" (Gate 9: no PRODUCTION-READY)

Gate rule: experience + HW → migrate. Otherwise refuse.
Weight inheritance: register old weights so CrossModelAdapter can callback.

Changelog:
    25/09/2026 (Claude Code — Wave 4A): Initial.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from training.weight_pager import WeightPager


def _sha256_json(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class MigrationReceipt:
    """Audit receipt for a model core migration."""

    receipt_id: str
    old_alias: str
    new_alias: str
    timestamp: str
    prev_sha256: str
    self_sha256: str
    inherited_weights: dict[str, Any] = field(default_factory=dict)
    label: str = "PROVISIONAL_RESULT"

    @property
    def is_genesis(self) -> bool:
        return self.prev_sha256 == "GENESIS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "old_alias": self.old_alias,
            "new_alias": self.new_alias,
            "timestamp": self.timestamp,
            "prev_sha256": self.prev_sha256,
            "self_sha256": self.self_sha256,
            "inherited_weights": dict(self.inherited_weights),
            "label": self.label,
        }


@dataclass
class ReadinessReport:
    """Result of a readiness gate check."""

    memory_entries: int
    avg_decision_score: float
    task_complexity: str
    hardware_available: bool
    memory_threshold: int
    score_threshold: float
    is_ready: bool
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_entries": self.memory_entries,
            "avg_decision_score": self.avg_decision_score,
            "task_complexity": self.task_complexity,
            "hardware_available": self.hardware_available,
            "memory_threshold": self.memory_threshold,
            "score_threshold": self.score_threshold,
            "is_ready": self.is_ready,
            "blockers": list(self.blockers),
        }


class UpgradeProtocol:
    """Progressive scaling gate: experience + HW → migrate.

    Tracks accumulated orchestration experience (decision scores), checks
    readiness thresholds, and performs auditable migration between model
    cores. Old weights are registered for later callback via CrossModelAdapter.
    """

    def __init__(
        self,
        *,
        memory_threshold: int = 100,
        score_threshold: float = 0.7,
        weight_pager: WeightPager | None = None,
    ) -> None:
        self._memory_threshold = memory_threshold
        self._score_threshold = score_threshold
        self._pager = weight_pager or WeightPager()
        self._decision_scores: list[float] = []
        self._hardware_available: bool = False
        self._task_complexity: str = "low"
        self._receipts: list[MigrationReceipt] = []
        self._weight_registry: dict[str, dict[str, Any]] = {}

    # --- experience accumulation ---

    def add_experience(self, score: float) -> None:
        """Record one decision score from an orchestration session.

        Raises ValueError if score out of [0, 1].
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {score}")
        self._decision_scores.append(score)

    @property
    def memory_entries(self) -> int:
        return len(self._decision_scores)

    @property
    def avg_decision_score(self) -> float:
        if not self._decision_scores:
            return 0.0
        return sum(self._decision_scores) / len(self._decision_scores)

    # --- configuration ---

    def set_hardware_available(self, available: bool) -> None:
        self._hardware_available = available

    def set_task_complexity(self, complexity: str) -> None:
        """Set current task complexity: 'low', 'medium', or 'high'."""
        if complexity not in ("low", "medium", "high"):
            raise ValueError(f"invalid complexity: {complexity}")
        self._task_complexity = complexity

    # --- readiness gate ---

    def readiness_check(self) -> ReadinessReport:
        """Check all readiness gates. Returns a report with blockers listed."""
        blockers: list[str] = []

        if self.memory_entries < self._memory_threshold:
            blockers.append(
                f"memory_entries {self.memory_entries} < {self._memory_threshold}"
            )
        if self.avg_decision_score < self._score_threshold:
            blockers.append(
                f"avg_decision_score {self.avg_decision_score:.3f} "
                f"< {self._score_threshold}"
            )
        if not self._hardware_available:
            blockers.append("hardware_available = False")

        return ReadinessReport(
            memory_entries=self.memory_entries,
            avg_decision_score=self.avg_decision_score,
            task_complexity=self._task_complexity,
            hardware_available=self._hardware_available,
            memory_threshold=self._memory_threshold,
            score_threshold=self._score_threshold,
            is_ready=len(blockers) == 0,
            blockers=blockers,
        )

    # --- migration ---

    def migrate(
        self,
        old_alias: str,
        new_alias: str,
        *,
        timestamp: str = "",
    ) -> MigrationReceipt:
        """Migrate from old model core to new model core.

        Gate: readiness_check must pass. Refuses otherwise (raises ValueError).
        Produces a SHA256-chained MigrationReceipt and registers inherited
        weights from the old alias for later callback.
        """
        if old_alias == new_alias:
            raise ValueError("old_alias and new_alias must differ")

        report = self.readiness_check()
        if not report.is_ready:
            raise ValueError(
                f"migration blocked: {'; '.join(report.blockers)}"
            )

        # Inherit weights from old model (register for callback).
        inherited = self.inherit_weights(old_alias)

        # Build chained receipt.
        prev_sha = self._receipts[-1].self_sha256 if self._receipts else "GENESIS"
        receipt_id = f"migration-{len(self._receipts) + 1:04d}"

        payload = {
            "receipt_id": receipt_id,
            "old_alias": old_alias,
            "new_alias": new_alias,
            "timestamp": timestamp,
            "prev_sha256": prev_sha,
            "inherited_weights": inherited,
        }
        self_sha = _sha256_json(payload)

        receipt = MigrationReceipt(
            receipt_id=receipt_id,
            old_alias=old_alias,
            new_alias=new_alias,
            timestamp=timestamp,
            prev_sha256=prev_sha,
            self_sha256=self_sha,
            inherited_weights=inherited,
        )
        self._receipts.append(receipt)
        return receipt

    # --- weight inheritance ---

    def inherit_weights(self, old_alias: str) -> dict[str, Any]:
        """Register old model weights for later callback.

        Returns the weight registry entry (alias, path, layers, checksum).
        If the alias is registered in WeightPager, pulls layer metadata.
        Otherwise creates a minimal registry entry.
        """
        reg = self._pager.get_registration(old_alias)
        if reg is not None:
            entry = {
                "alias": old_alias,
                "path": reg.path,
                "format": reg.format,
                "total_layers": reg.total_layers,
                "total_bytes": reg.total_bytes,
                "status": "REGISTERED_FOR_CALLBACK",
            }
        else:
            entry = {
                "alias": old_alias,
                "path": "",
                "format": "",
                "total_layers": 0,
                "total_bytes": 0,
                "status": "MINIMAL_ENTRY",
            }

        self._weight_registry[old_alias] = entry
        return dict(entry)

    def get_inherited_weights(self, old_alias: str) -> dict[str, Any] | None:
        return self._weight_registry.get(old_alias)

    @property
    def inherited_count(self) -> int:
        return len(self._weight_registry)

    # --- receipts ---

    @property
    def receipt_count(self) -> int:
        return len(self._receipts)

    def list_receipts(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts]

    def verify_chain(self) -> bool:
        """Verify SHA256 chain integrity of all migration receipts."""
        if not self._receipts:
            return True
        if self._receipts[0].prev_sha256 != "GENESIS":
            return False
        for i in range(1, len(self._receipts)):
            if self._receipts[i].prev_sha256 != self._receipts[i - 1].self_sha256:
                return False
        return True

    # --- serialization ---

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_scores": list(self._decision_scores),
            "hardware_available": self._hardware_available,
            "task_complexity": self._task_complexity,
            "memory_threshold": self._memory_threshold,
            "score_threshold": self._score_threshold,
            "weight_registry": {
                k: dict(v) for k, v in self._weight_registry.items()
            },
            "receipts": [r.to_dict() for r in self._receipts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, weight_pager: WeightPager | None = None) -> UpgradeProtocol:
        proto = cls(
            memory_threshold=data.get("memory_threshold", 100),
            score_threshold=data.get("score_threshold", 0.7),
            weight_pager=weight_pager,
        )
        proto._decision_scores = list(data.get("decision_scores", []))
        proto._hardware_available = data.get("hardware_available", False)
        proto._task_complexity = data.get("task_complexity", "low")
        proto._weight_registry = {
            k: dict(v) for k, v in data.get("weight_registry", {}).items()
        }
        for rd in data.get("receipts", []):
            receipt = MigrationReceipt(
                receipt_id=rd["receipt_id"],
                old_alias=rd["old_alias"],
                new_alias=rd["new_alias"],
                timestamp=rd.get("timestamp", ""),
                prev_sha256=rd["prev_sha256"],
                self_sha256=rd["self_sha256"],
                inherited_weights=dict(rd.get("inherited_weights", {})),
                label=rd.get("label", "PROVISIONAL_RESULT"),
            )
            proto._receipts.append(receipt)
        return proto
