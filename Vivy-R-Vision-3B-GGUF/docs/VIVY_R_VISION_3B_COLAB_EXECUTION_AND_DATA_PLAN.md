> [!IMPORTANT]
> **MANDATORY GOVERNANCE FOR INHERITING AGENTS & DOCUMENT EDITORS:**
> 1. **Mandatory Changelog:** Any agent editing this document MUST append an entry to the Changelog section (Agent Name/ID, timestamp, reason for change).
> 2. **Isolate Only, NEVER Delete:** NEVER delete legacy content or architecture definitions. Any superseded section must be enclosed in a quote block and marked `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Full Synchronization with `D:\2brain`:** Synchronize all architectural decisions, specifications, and lessons learned into `D:\2brain`.
> 4. **Public Language Policy (Hard Invariant #10):** All public HuggingFace and GitHub documentation MUST be written in 100% English. Internal Vietnamese editions are archived exclusively under `docs/internal_vi/` and `D:\2brain`.

# Vivy-R-Vision-3B (`R-VISION-3B`) — Training Data & Execution Pipeline Specification

## 1. Open-Source HuggingFace Datasets Integrated

| Dataset Repository | Domain | Training Stage |
|---|---|---|
| `MrOvkill/svg-stack-labeled` | Labeled SVG primitives & paths | Stage 1: $N=4,096$ Foundational Vector-Chain Archetypes |
| `starvector/text2svg-stack` | Text-to-SVG structural topologies | Stage 1: $N=4,096$ Foundational Vector-Chain Archetypes |
| `ranjaykrishna/visual_genome` | Scene graphs & spatial relationships | Stage 2: 2-Tier Canvas (`2000×1000` + `1000×1000`) Arrangement SFT |
| `TheBirdLegacy/SimulacraUnsupervised` | Aesthetic prompt compositions | Stage 2: Coupled Lighting & Camera Driver Alignment |
| `ShareGPT4Video/ShareGPT4Video` | Multi-shot temporal captions | Stage 3: 30-Shot-Block (`180.0s`) Temporal Trajectory Alignment |
| `TencentARC/MiraData` | Long-form video motion dynamics | Stage 3: 3-Minute Temporal Ceiling Enforcement |
| `TeoGchx/HumanML3D` | 3D human skeletal kinematics | Stage 3: Socket-Lock & Catmull-Rom Spline Verification |

---

## 2. Strict Data Split & Held-Out Exam Isolation (Hard Invariant #5)

- `train.jsonl` and `dev.jsonl` reside inside the repository (`data/vision_r3b_colab/`).
- `sealed_test.jsonl` is strictly isolated outside the repository (`~/.vivy_heldout_exams/`) with zero overlap against `train` or `dev`.

---

## 3. Full-Weight 3.09B Packaging & Verification Gate (Hard Invariant #9)

1. Extract the `181` native `F32` Transformer tensors (`241,664` parameters across `blk.0..35` + `output_norm.weight`) from the `3,085,938,688`-parameter (`435` tensors, `~2.10 GB`) `Qwen2.5-3B-Instruct` GGUF v3 backbone.
2. Train the 36-layer BitFit + RMSNorm-IA³ parameters jointly with the `d_model = 2048` Semantic Projection Compiler on `train.jsonl`, verifying `interrupt_resume_max_delta <= 1e-5` and `100%` joint accuracy on `dev.jsonl` and held-out `sealed_test.jsonl`.
3. Write the trained `181` `F32` Transformer tensors back into the complete `~2.10 GB` (`3,085,938,688`-parameter, `435`-tensor) standalone `Q4_K_M` GGUF v3 binary (`vivy-r-vision-3b-q4_k_m.gguf`) and export the companion `.safetensors` checkpoint.
4. Verify standalone execution via `llama-completion.exe` (`llama.cpp`) and native Rust `vivy_core.dll` before publishing to HuggingFace Hub.

---

## Changelog

| Agent | Timestamp | Reason |
|---|---|---|
| Antigravity IDE | 2026-10-17 | Initial Colab execution and dataset specification. |
| Antigravity IDE | 2026-10-18 | Updated for full-weight `3,085,938,688`-parameter (`~2.10 GB` `Q4_K_M` GGUF) packaging and translated to 100% English per Hard Invariants #9 and #10. |
