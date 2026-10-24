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

# Vivy-V-Core-4B — Vivy-V Upgraded Generation (Optimized Thinking Core)

- **Model Family:** `Vivy-V`
- **Model ID:** `Vivy-V-Core-4B`
- **Domain Focus:** Unified General & Multimodal Thinking Core
- **Development Status:** `ACTIVE_CORE_FOUNDATION`
- **Parameter Class:** 4.09B (3.09B + 0.49B + 0.51B Vivy-V Core)
- **Release Policy:** **Open-Source Model Weights (`Apache-2.0`)** + **Encrypted Proprietary `Vivy-V` Architecture (`.vcore`)**
- **Legacy Lineage Stamp:** Replaces `Vivy-v6.8-Unified-Organism` (`[ARCHIVED_LEGACY_VIVY_V6]`)

---

## Overview

**`Vivy-V-Core-4B`** is the upgraded **`Vivy-V`** generation release featuring an **optimized thinking core** for faster decision-making, lower runtime memory overhead, and higher response consistency.

All legacy **`Vivy.v6`** releases (`Vivy-v6.8-Unified-Organism`) have been officially archived and stamped as legacy versions (`[ARCHIVED_LEGACY_VIVY_V6]`).

---

## Model Files & Packaging Structure

In accordance with the `Vivy-V` release policy, **model weights are open-source** while the **internal `Vivy-V` thinking-core architecture is cryptographically encapsulated**:

| File | Role | Open-Source / Encrypted | Format |
|---|---|---|---|
| `vivy-v-core-4b-q4_k_m.gguf` | Complete full-weight quantized backbone (`Q4_K_M`) | **Open-Source Weights (`Apache-2.0`)** | `GGUF v3` |
| `vivy-v-core-4b_weights.safetensors` | Complete `Vivy-V` fine-tuned weight tensors (`weights.layer_*`, SHA-256: `86568e019d488708...`) | **Open-Source Weights (`Apache-2.0`)** | `.safetensors` |
| `vivy-v-core-4b_arch.vcore` | Encrypted `Vivy-V` thinking-core architecture & routing topology (SHA-256: `69f0a880f21aa821...`) | **Encrypted Architecture (`VIVY_V_ARCH_ENC_V1`)** | `.vcore` (`VCORE3`) |
| `Modelfile` / `Modelfile.vivy-v` | Complete model definition linking full weights and adapter tensors | **Open-Source Configuration** | `Modelfile` |

---

## Quick Start

### 1. Run with `llama.cpp` or `Ollama` (`Modelfile`)

```bash
# Build model from the complete Modelfile
ollama create vivy-v-core-4b:vivy-v -f Modelfile

# Run interactive inference
ollama run vivy-v-core-4b:vivy-v
```

### 2. Direct `llama-server` Execution

```bash
llama-server -m ./vivy-v-core-4b-q4_k_m.gguf --port 8080 -c 8192
```

---

## Version History & Legacy Archive Notice

- **`Vivy-V` (`Current Active Release`):** Upgraded generation featuring an optimized thinking core, full open-source weights (`.gguf` + `.safetensors` + `Modelfile`), and encrypted `Vivy-V` architecture (`.vcore`).
- **`Vivy.v6` (`[ARCHIVED_LEGACY_VIVY_V6]`):** All prior `Vivy.v6` / `R`-Series versions (`v6.0` – `v7.4`) are archived as historical legacy releases.
