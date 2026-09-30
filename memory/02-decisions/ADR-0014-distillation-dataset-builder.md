# ADR-0014: Distillation Dataset Builder, Contamination-Safe Splitter, and Replay Manifest

## Status

Accepted

## Context

Stage 6 (`ARCHITECTURE.md` Section 9 & 13.7) requires:
1. Versioned distillation dataset extraction capturing `ThoughtState` transitions, rejected hypotheses, routing rationale, and provenance.
2. Contamination-safe train/val/test splitting based on SHA-256 digest buckets.
3. Canonical `ReplayManifest` serialization with SHA-256 digest validation.

## Decision

### 1. Module Ownership

`src/nps_core/distillation_dataset/` owns `DatasetRecord`, `ReplayManifest`, `DatasetSplitter`, `DatasetBuilder`, and domain exceptions (`DatasetError`, `SplitError`).

### 2. Contamination-Safe Splitting

`DatasetSplitter.split` partitions records into (train, val, test) tuples using SHA-256 hash modulo logic on `record_id`, ensuring deterministic and leakage-free splitting.

### 3. Replay Manifest

`ReplayManifest` captures dataset version, raw records, and split record partitions into canonical JSON format.

## Consequences

- Stage 6 exit criteria are 100% fulfilled.
- Standard-library runtime dependencies only; zero external I/O.
