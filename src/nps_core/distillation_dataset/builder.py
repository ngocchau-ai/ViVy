"""Distillation Dataset Builder for Stage 6.

Extracts records from PopulationSnapshot and TransitionEvent history.
Standard-library only.
"""

from __future__ import annotations


from nps_core.distillation_dataset.manifest import DatasetRecord, ReplayManifest
from nps_core.distillation_dataset.splitter import DatasetSplitter
from nps_core.hypothesis_population import PopulationSnapshot

__all__ = [
    "DatasetBuilder",
]


class DatasetBuilder:
    """Builds versioned ReplayManifest from PopulationSnapshots."""

    @staticmethod
    def extract_records(snapshot: PopulationSnapshot) -> tuple[DatasetRecord, ...]:
        """Extract DatasetRecord entries for all thoughts and history in snapshot."""
        records: list[DatasetRecord] = []
        for t in snapshot.thoughts:
            rec_id = f"REC-{t.thought_id}"
            records.append(
                DatasetRecord(
                    record_id=rec_id,
                    thought_id=t.thought_id,
                    action=f"transition_to_{t.status.state}",
                    state=t.status.state,
                    provenance=f"snapshot_digest:{hashlib_digest(t.thought_id)}",
                )
            )
        return tuple(sorted(records, key=lambda r: r.record_id))

    @staticmethod
    def build_manifest(version: str, snapshot: PopulationSnapshot) -> ReplayManifest:
        """Extract records and build full ReplayManifest with train/val/test splits."""
        records = DatasetBuilder.extract_records(snapshot)
        train, val, test = DatasetSplitter.split(records)
        return ReplayManifest(
            version=version,
            records=records,
            train_records=train,
            val_records=val,
            test_records=test,
        )


def hashlib_digest(val: str) -> str:
    import hashlib
    return hashlib.sha256(val.encode("utf-8")).hexdigest()[:16]
