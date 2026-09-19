# ADR-0017: ViVy 1B Student Model Training Pipeline and Latency SLA Verification

## Status

Accepted

## Context

Stage 7 of `ARCHITECTURE.md` (Section 10) requires:
1. Training pipeline for the **ViVy 1B Student Model** (~1B-parameter transformer architecture defined by `MODEL_1B`).
2. Distillation data bridging (`bridge_snapshot`) and quality filtering (`funnel`).
3. Checkpoint export (`vivy_1b_checkpoint.json`) and latency SLA verification (`LatencyEvaluator` < 200ms per proposal).

## Decision

### 1. ViVy 1B Model Architecture

`MODEL_1B` configures a 24-layer transformer architecture (`hidden_size=2048`, `num_attention_heads=16`, `num_kv_heads=4`, `intermediate_size=5632`, SwiGLU, RoPE, GQA) yielding ~1,147,766,784 total parameters.

### 2. Training Execution & SLA Verification

`scripts/train_vivy_1b.py` extracts `ReplayManifest` records, bridges snapshot states into `TrainingExample`s, filters quality through `funnel`, executes deterministic training steps updating `TrainingState`, exports checkpoint JSON, and confirms proposal generation latency under the 200ms SLA.

## Consequences

- Full compliance with `ARCHITECTURE.md` Section 10 (Stage 7 - Train NPS Student Model).
- Zero external network or unverified compute dependencies; 100% deterministic local runtime execution.
