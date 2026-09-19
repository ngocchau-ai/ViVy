"""Contamination-Safe Dataset Splitter for Stage 6.

Standard-library only; splits dataset records deterministically based on record_id digest.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

from nps_core.distillation_dataset.errors import SplitError
from nps_core.distillation_dataset.manifest import DatasetRecord

__all__ = [
    "DatasetSplitter",
]


class DatasetSplitter:
    """Splits dataset records into contamination-safe train/val/test splits."""

    @staticmethod
    def split(
        records: Sequence[DatasetRecord],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
    ) -> tuple[tuple[DatasetRecord, ...], tuple[DatasetRecord, ...], tuple[DatasetRecord, ...]]:
        """Deterministically split records into (train, val, test) tuples based on SHA-256 hash."""
        if not (0.0 < train_ratio < 1.0 and 0.0 <= val_ratio < 1.0 and (train_ratio + val_ratio) <= 1.0):
            raise SplitError("Ratios must satisfy train_ratio + val_ratio <= 1.0", path="train_ratio")

        train: list[DatasetRecord] = []
        val: list[DatasetRecord] = []
        test: list[DatasetRecord] = []

        for rec in sorted(records, key=lambda r: r.record_id):
            # Compute hash bucket between 0.0 and 1.0
            digest = hashlib.sha256(rec.record_id.encode("utf-8")).hexdigest()
            score = int(digest[:8], 16) / 0xFFFFFFFF
            if score < train_ratio:
                train.append(rec)
            elif score < (train_ratio + val_ratio):
                val.append(rec)
            else:
                test.append(rec)

        return tuple(train), tuple(val), tuple(test)
