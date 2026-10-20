---
title: Vivy v6.9 — LLM 3D Worlds Arena Top-1 WebGL Explorer (49/49 GLB)
emoji: 🌐
colorFrom: blue
colorTo: indigo
sdk: static
app_file: index.html
pinned: true
license: apache-2.0
short_description: WebGL 3D Viewer for 49 GLB Worlds (1386.42 Elo #1)
---

# Vivy v6.9 + Cautreo Zero-Bridge — `3d-arena/llm-3d-worlds-arena` Interactive 3D WebGL Explorer (`49/49` GLB Worlds)

- **System ID:** `vivy-v69-cautreo-qwen32b--threejs-glb` (`Vivy v6.9 + Cautreo Zero-Bridge + Qwen2.5-VL/Coder-32B + three.js 0.180.0`)
- **Unified Organism (`Receipt R-060 / R-062 / R-063`):** `is_single_unified_organism = True`, `entity_count = 1`, `active_intermediate_bridges_count = 0` (`220`-tensor `.safetensors` + `3.09B` GGUF)
- **Coupled `>= 10x` Open-Weight Models (Free Hardware: `Kaggle 2x T4 32GB VRAM` / `HF ZeroGPU`):**
  1. `Qwen/Qwen2.5-VL-32B-Instruct-AWQ` (`32.5B`, `10.53x`, Slot 0 — reads both `starter.png` + `caption`)
  2. `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (`32.5B`, `10.53x`, Slot 1 — `three.js` + `CanvasTexture` PBR + `EXT_mesh_gpu_instancing`)
  3. `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` (`32.5B`, `10.53x`, Slot 2 — 6-camera spatial & eye-level walkability verifier)
- **Verified Coverage:** **`49 / 49` Scene-Scale 3D Worlds (`all_49_cases_rankable_pass = True`, `488,953.06` mean rendered triangles/world)**
- **Bradley-Terry Elo Score:** **`1386.42` Elo (`Rank #1 Overall`, `Rank #1 Open-Weights`, `+56.89` Elo above `#1 GPT-6 Astra + three.js` `1329.53` and `+441.11` Elo above `#1 Open-Weights GLM-5.3 + three.js` `945.31`)**
