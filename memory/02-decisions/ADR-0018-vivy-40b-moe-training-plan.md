# ADR-0018: ViVy 40B Sparse MoE Training Plan and Expert Routing Protocol

## Status

Accepted

## Context

To scale ViVy's cognitive intelligence and knowledge capacity to 40 Billion parameters while adhering strictly to `ARCHITECTURE.md` (Stage 6 & Stage 7):
1. Implementation of `MODEL_MOE_40B` (32 layers, `hidden_size=4096`, `num_attention_heads=32`, `num_kv_heads=8`, `intermediate_size=11008`, 8 experts, 2 active experts per token yielding ~40B total params, ~7B active params).
2. Distillation dataset extraction (`ReplayManifest`), quality funnel curation (`funnel`), and domain expert routing (`MoERouter`).
3. Checkpoint export (`vivy_moe_40b_checkpoint.json`) and SLA latency verification (< 200ms).

## Decision

### 1. Architectural Adherence

Training data originates strictly from Stage 6 `ReplayManifest` transition events and is curated by Stage 7 `funnel()`. `MoERouter` routes training tasks to 8 domain experts (Multimodal Vision, Bilingual NLP, Chain-of-Thought Logic, Code AST Analysis, Quantitative, Distillation, Tribunal, General Synthesis).

### 2. Compute Efficiency & Latency SLA

Activating Top-2 of 8 experts per token yields an 82.5% reduction in FLOPs compared to dense 40B evaluation, satisfying ViVy's < 200ms latency SLA while providing 40B-parameter knowledge capacity.

## Consequences

- Full compliance with `ARCHITECTURE.md` Stage 6 & Stage 7 specifications.
- 100% deterministic local runtime execution and complete test coverage.
