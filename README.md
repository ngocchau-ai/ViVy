# NPS Core — N-Thought Principal Scientist AI Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)
[![Build & Tests](https://img.shields.io/badge/tests-645%20passed-brightgreen.svg)](tests/)

**NPS Core (N-Thought Principal Scientist Core)** is an advanced AI cognitive reasoning engine developed by **Ngoc Chau AI Product Team**. It is designed around **Population Reasoning**, a **4-Level Self-Verification Filter Funnel**, and **Quantum-Inspired Associative Memory** for high-confidence, transparent, and reproducible reasoning.

---

## 🌟 Key Architecture & Capabilities

### 1. 🧠 N-Thought Population Reasoning
Unlike standard linear single-chain LLMs, NPS Core maintains an adaptive population of hypotheses $\mathcal{P} = \{T_1, T_2, \dots, T_N\}$. The population evolves iteratively through state-space transformations, branch pruning, and formal evidence assimilation.

### 2. 🔍 4-Level Self-Verification Filter Funnel (`nps_core.filter_funnel`)
The Self-Verification Filter Funnel provides metacognitive self-scrutiny over state vectors:
- **Level 1: Amplitude & Phase Analyzer (`AmplitudeAnalyzer`)**
  - Measures state probability distribution $p_k = |c_k|^2$ and Shannon thought entropy $S = -\sum p_k \log_2 p_k$.
  - Detects destructive phase interference ($\Delta \phi \approx \pi$) signaling logical contradictions.
- **Level 2: SVD Stream Decomposer (`SVDDecomposer`)**
  - Matricizes state tensors across partition spaces (Premise $A$ vs Conclusion $B$).
  - Performs One-Sided Jacobi SVD to isolate independent thought streams $\sigma_i$.
- **Level 3: Evaluator & Logic Filter (`LogicFilter`)**
  - Computes confidence scores $C_i = \sigma_i \times \text{consistency}_i \times \text{brevity}_i$ incorporating Occam's razor.
  - Classifies streams into `ACCEPTED`, `MONITORED`, or `PRUNED` states.
- **Level 4: Metacognitive Trigger (`FilterFunnel`)**
  - Emits real-time control signals: `CONTINUE_EVOLUTION`, `MEASURE_AND_HALT`, `BACKTRACK`, or `DELEGATE_EXTERNAL`.

### 3. ⚡ Quantum-Inspired Associative Memory (`nps_core.memory`)
- **1-Touch Intuition Retrieval:** Recalls previously successful reasoning patterns instantly via $W = \sum |y_p\rangle\langle x_p|$.
- **SVD Polar Unitarization:** Transforms complex weight matrix $W \to U_{\text{unitary}}$ using polar decomposition ($U \cdot V^\dagger$), ensuring unitary norm conservation.
- **Continuous Learning:** Updates memory weights continuously online via complex Hebbian learning rules.

---

## 📁 Repository Structure

```
.
├── src/
│   └── nps_core/
│       ├── filter_funnel/          # 4-Level Self-Verification Filter Funnel
│       │   ├── amplitude_analyzer.py
│       │   ├── svd_decomposer.py
│       │   ├── logic_filter.py
│       │   └── funnel.py
│       ├── memory/                 # Quantum-Inspired Associative Memory
│       │   └── associative_memory.py
│       ├── verification_tribunal/  # Stage 5 Tribunal & Evidence Verification
│       ├── hypothesis_population/  # Population Reasoning State & Snapshot
│       ├── adaptive_n/             # Adaptive Hypothesis Scale Controller
│       ├── executor_router/        # Delegated Cognition Router
│       ├── codegraph/              # Incremental Code Graph & Retrieval
│       └── vivy_ollama/            # Ollama Model Exporter & Integration
├── modelfiles/
│   └── Modelfile.vivy              # Ollama Modelfile for ViVy AI
├── tests/
│   ├── unit/                       # Unit Test Suite (Filter Funnel, Memory, etc.)
│   └── integration/                # End-to-End Integration Tests
├── pyproject.toml                  # Packaging & Metadata configuration
├── setup.py                        # Setuptools setup configuration
└── LICENSE                         # MIT License
```

---

## 🚀 Quick Start

### 1. Installation

Requires **Python 3.11+**. Standard library compatible.

```bash
# Clone repository
git clone https://github.com/ngocchau/91sViVy-Aider.git
cd 91sViVy-Aider

# Install package in editable mode
pip install -e .
```

### 2. Python API Example

```python
from nps_core.filter_funnel import FilterFunnel, FunnelSignal
from nps_core.memory import QuantumAssociativeMemory

# --- 1-Touch Intuition Retrieval ---
memory = QuantumAssociativeMemory(dim_input=2, dim_output=2)
memory.store(input_vec=[1.0, 0.0], output_vec=[0.0, 1.0])

match = memory.query([0.99, 0.01])
print(f"Intuition Confidence: {match.confidence:.4f}")

# --- Self-Verification Filter Funnel ---
funnel = FilterFunnel()
state_vector = [1.0, 0.0, 0.0, 0.0]  # Converged state

result = funnel.evaluate_state(state_vector=state_vector, partition=(1, 1))
print(f"Control Signal: {result.signal}")
print(f"Thought Entropy: {result.entropy:.4f}")
print(f"Overall Confidence: {result.overall_confidence:.4f}")
```

### 3. Ollama Model Creation

Register the ViVy Multimodal Bilingual AI model into Ollama:

```bash
ollama create vivy -f modelfiles/Modelfile.vivy
ollama run vivy "Explain the Self-Verification Filter Funnel"
```

---

## 🧪 Testing

Run the full automated test suite using `pytest`:

```bash
python -m pytest
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

Developed with ❤️ by **Ngoc Chau AI Product Team**.
