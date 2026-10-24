---
license: apache-2.0
library_name: gguf
base_model: Qwen/Qwen2.5-3B-Instruct
language:
  - en
tags:
  - vivy-v
  - upgraded-thinking-core
  - open-weights
  - gguf
  - safetensors
---

# Vivy-V-Robotics-3B — Vivy-V Upgraded Generation (Optimized Thinking Core)

- **Model Family:** `Vivy-V`
- **Model ID:** `Vivy-V-Robotics-3B`
- **Domain Focus:** Spatial & Kinematic Control Thinking Core
- **Development Status:** `ACTIVE_MAINTENANCE`
- **Parameter Class:** 3.09B (3,085,938,688 parameters)
- **Release Policy:** **Open-Source Model Weights (`Apache-2.0`)** + **Encrypted Proprietary `Vivy-V` Architecture (`.vcore`)**
- **Legacy Lineage Stamp:** Replaces `Vivy-R-Robotics-3B (v6.6..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`)

---

## Overview

**`Vivy-V-Robotics-3B`** is the upgraded **`Vivy-V`** generation release featuring an **optimized thinking core** for faster decision-making, lower runtime memory overhead, and higher response consistency.

All legacy **`Vivy.v6`** releases (`Vivy-R-Robotics-3B (v6.6..v7.4)`) have been officially archived and stamped as legacy versions (`[ARCHIVED_LEGACY_VIVY_V6]`).

---

## Model Files & Packaging Structure

In accordance with the `Vivy-V` release policy, **model weights are open-source** while the **internal `Vivy-V` thinking-core architecture is cryptographically encapsulated**:

| File | Role | Open-Source / Encrypted | Format |
|---|---|---|---|
| `vivy-v-robotics-3b-q4_k_m.gguf` | Complete full-weight quantized backbone (`Q4_K_M`) | **Open-Source Weights (`Apache-2.0`)** | `GGUF v3` |
| `vivy-v-robotics-3b_weights.safetensors` | Complete `Vivy-V` fine-tuned weight tensors (`weights.layer_*`, SHA-256: `22c8b0b68ab43112...`) | **Open-Source Weights (`Apache-2.0`)** | `.safetensors` |
| `vivy-v-robotics-3b_arch.vcore` | Encrypted `Vivy-V` thinking-core architecture & routing topology (SHA-256: `e0a2c5ac55939a92...`) | **Encrypted Architecture (`VIVY_V_ARCH_ENC_V1`)** | `.vcore` (`VCORE3`) |
| `Modelfile` / `Modelfile.vivy-v` | Complete model definition linking full weights and adapter tensors | **Open-Source Configuration** | `Modelfile` |

---

## Quick Start

### 1. Run with `llama.cpp` or `Ollama` (`Modelfile`)

```bash
# Build model from the complete Modelfile
ollama create vivy-v-robotics-3b:vivy-v -f Modelfile

# Run interactive inference
ollama run vivy-v-robotics-3b:vivy-v
```

### 2. Direct `llama-server` Execution

```bash
llama-server -m ./vivy-v-robotics-3b-q4_k_m.gguf --port 8080 -c 8192
```

---

## Version History & Legacy Archive Notice

- **`Vivy-V` (`Current Active Release`):** Upgraded generation featuring an optimized thinking core, full open-source weights (`.gguf` + `.safetensors` + `Modelfile`), and encrypted `Vivy-V` architecture (`.vcore`).
- **`Vivy.v6` (`[ARCHIVED_LEGACY_VIVY_V6]`):** All prior `Vivy.v6` / `R`-Series versions (`v6.0` – `v7.4`) are archived as historical legacy releases.
