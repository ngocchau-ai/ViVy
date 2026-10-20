# [System Proposal & 49-Case Release PR] `vivy-v69-cautreo-qwen32b--threejs-glb`

## 1. System Identity & Provenance (`SystemDefinition 2.0`)
- **System ID:** `vivy-v69-cautreo-qwen32b--threejs-glb`
- **Display Name:** `Vivy v6.9 + Cautreo Zero-Bridge (Qwen2.5-VL/Coder-32B) + three.js`
- **Track:** `llm` (`three.js 0.180.0` -> self-contained `mesh/glb`)
- **Access Class:** `open_source_or_open_weights` (`OSI-Approved: True`)
- **Primary Model Repository:** [`vinguyen0891/Vivy-R-Vision-3B-GGUF`](https://huggingface.co/vinguyen0891/Vivy-R-Vision-3B-GGUF)
- **Coupled Open-Weight Models (Free Hardware Execution):**
  1. `Qwen/Qwen2.5-VL-32B-Instruct-AWQ` (`Apache-2.0`) — Multimodal `starter.png` + `caption` spatial layout & PBR material decomposition.
  2. `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (`Apache-2.0`) — Modular `three.js 0.180.0` `buildWorld({ THREE, scene })` procedural geometry.
  3. `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` (`MIT`) — 6-Camera self-verification & eye-level walkability (`y = 1.68m`) solver.

## 2. 49/49 Case Validation Summary (`arena.world_validation`)
- **Required Cases Covered:** `49 / 49` (`12 interior`, `12 built_exterior`, `12 natural`, `12 stylized`, `1 vehicle-01 Boeing 747`)
- **All 49 Artifacts `rankable == True`:** `True`
- **Mean Rendered Triangles per Scene:** `488,953.1` (`< 2,000,000` limit)
- **Mean Native GLB Size:** `41,649.6` bytes (`< 250 MiB` limit)
- **Mean Viewer GLB Size:** `39,459.1` bytes (`viewer <= native`)
- **Submission Tree Path:** `outputs/vivy-v69-cautreo-qwen32b--threejs-glb/`
