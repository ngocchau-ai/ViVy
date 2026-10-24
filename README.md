# ViVy (`Vivy-V` Upgraded Generation) — Optimized Thinking Core & Open-Weight Model Suite

- **Current Active Generation:** **`Vivy-V`** (Upgraded Version — Optimized Thinking Core)
- **Prior Generation Status:** **`Vivy.v6`** (`v6.0` – `v7.4`) is officially stamped and archived as **`[ARCHIVED_LEGACY_VIVY_V6]`**
- **Release & Licensing Policy:**
  - **Model Weights (`.gguf`, `.safetensors`, `Modelfile`):** **Open-Source (`Apache-2.0`)**
  - **`Vivy-V` Thinking-Core Architecture (`.vcore`):** **Proprietary & Cryptographically Encrypted (`VIVY_V_ARCH_ENC_V1`, `open_source_architecture = False`)**

---

## 1. Overview

**`Vivy-V`** is the upgraded generation of the ViVy model family, engineered with an **optimized thinking core** that improves reasoning speed, decision consistency, and runtime memory efficiency.

In this release:
1. **Legacy `Vivy.v6` Archival:** All products previously completed under `Vivy.v6` are stamped and preserved as legacy versions (`[ARCHIVED_LEGACY_VIVY_V6]`).
2. **Rebuilt `Vivy-V` Model Suite:** Every model in the suite has been rebuilt with a complete `Modelfile`, full open-source weight tensors (`.gguf` and `.safetensors`), and an encrypted `Vivy-V` architecture package (`.vcore`).

---

## 2. `Vivy-V` Complete Model Suite

| Model ID | Parameter Class | Open-Source Weights (`Apache-2.0`) | Encrypted Architecture (`VIVY_V_ARCH_ENC_V1`) | Superseded Legacy Version |
|---|---|---|---|---|
| **`Vivy-V-Core-4B`** | `4.09B (3.09B + 0.49B + 0.51B Vivy-V Core)` | `vivy-v-core-4b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-core-4b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-v6.8-Unified-Organism` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-Vision-3B`** | `3.09B (3,085,938,688 parameters)` | `vivy-v-vision-3b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-vision-3b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-Vision-3B (v6.6..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-Finance-3B`** | `3.09B (3,085,938,688 parameters)` | `vivy-v-finance-3b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-finance-3b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-Finance-3B (v6.6..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-Robotics-3B`** | `3.09B (3,085,938,688 parameters)` | `vivy-v-robotics-3b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-robotics-3b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-Robotics-3B (v6.6..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-SWE-Code-3B`** | `3.09B (3,085,938,688 parameters)` | `vivy-v-swe-code-3b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-swe-code-3b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-SWE-Code-3B (v7.0..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-Science-Bio-3B`** | `3.09B (3,085,938,688 parameters)` | `vivy-v-science-bio-3b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-science-bio-3b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-Science-Bio-3B (v7.0..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-CyberSec-3B`** | `3.09B (3,085,938,688 parameters)` | `vivy-v-cybersec-3b_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-cybersec-3b_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-CyberSec-3B (v7.3..v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |
| **`Vivy-V-Robotics-Micro-Edge`** | `0.50B Embedded + Vivy-V Micro Core` | `vivy-v-robotics-micro-edge_weights.safetensors` + `.gguf` (`Open-Source Weights`) | `vivy-v-robotics-micro-edge_arch.vcore` (`Encrypted Vivy-V Architecture`) | `Vivy-R-Robotics-Micro-Edge (v7.4)` (`[ARCHIVED_LEGACY_VIVY_V6]`) |

---

## 3. Quick Start

Each model directory provides a complete `Modelfile` (`Modelfile.vivy-v`), open-source weight files (`.gguf` + `*_weights.safetensors`), and the encrypted `Vivy-V` architecture file (`*_arch.vcore`):

```bash
# Build and run any Vivy-V model with Ollama
ollama create vivy-v-core-4b -f Vivy-V-Suite/vivy-v-core-4b/Modelfile
ollama run vivy-v-core-4b
```

---

## 4. Legacy `Vivy.v6` Archive Notice

All historical `Vivy.v6` (`R`-Series `v6.0` – `v7.4`) model definitions and release records are stamped as `[ARCHIVED_LEGACY_VIVY_V6]` in [`LEGACY_VIVY_V6_ARCHIVE_STAMP_MANIFEST.json`](./LEGACY_VIVY_V6_ARCHIVE_STAMP_MANIFEST.json).
