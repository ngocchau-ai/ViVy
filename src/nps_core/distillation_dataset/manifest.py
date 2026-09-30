"""Dataset Record and Replay Manifest value objects for Stage 6.

Standard-library only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

__all__ = [
    "DatasetRecord",
    "ReplayManifest",
]


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    """Frozen value object holding a single distillation training example."""

    record_id: str
    thought_id: str
    action: str
    state: str
    provenance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "thought_id": self.thought_id,
            "action": self.action,
            "state": self.state,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetRecord:
        return cls(
            record_id=data["record_id"],
            thought_id=data["thought_id"],
            action=data["action"],
            state=data["state"],
            provenance=data["provenance"],
        )


@dataclass(frozen=True, slots=True)
class ReplayManifest:
    """Frozen value object holding complete versioned dataset manifest."""

    version: str
    records: tuple[DatasetRecord, ...]
    train_records: tuple[DatasetRecord, ...]
    val_records: tuple[DatasetRecord, ...]
    test_records: tuple[DatasetRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "records": [r.to_dict() for r in self.records],
            "train_records": [r.to_dict() for r in self.train_records],
            "val_records": [r.to_dict() for r in self.val_records],
            "test_records": [r.to_dict() for r in self.test_records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplayManifest:
        return cls(
            version=data["version"],
            records=tuple(DatasetRecord.from_dict(r) for r in data["records"]),
            train_records=tuple(DatasetRecord.from_dict(r) for r in data["train_records"]),
            val_records=tuple(DatasetRecord.from_dict(r) for r in data["val_records"]),
            test_records=tuple(DatasetRecord.from_dict(r) for r in data["test_records"]),
        )

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()
