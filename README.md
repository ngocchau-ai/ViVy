# ViVy — Omni-Epistemic AI Core

> **ViVy Final Core V1.0** — Local AI với kiến trúc Elastic N-Core, Cognitive State Graph và Native Tool Orchestration.
> Base model: **Gemma 4 E4B** (Apache 2.0) · Runtime: **Ollama** · Platform: CPU/GPU

---

## Tổng Quan

ViVy là **AI local tự chủ** được thiết kế để suy luận, lập kế hoạch và thực thi nhiệm vụ trực tiếp thông qua engine primitives — không qua framework trung gian (no LangChain, no AutoGen).

```
Input (Text / Image / Audio)
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  ElasticNCore — N hypothesis song song, GEMM-based    │
├───────────────────────────────────────────────────────┤
│  DirectiveMTPHead — Emit opcode TRƯỚC khi LLM gen     │
├───────────────────────────────────────────────────────┤
│  Gemma 4 E4B — Text + Vision + Audio (Apache 2.0)     │
├───────────────────────────────────────────────────────┤
│  ToolDispatcher — LLM tool_call → engine primitive    │
├───────────────────────────────────────────────────────┤
│  CognitiveStateGraph — Thought Ecology Topology       │
│  HebbianRecall — W=YX⁺, O(1) associative recall      │
└───────────────────────────────────────────────────────┘
    │
    ▼
Output + CognitiveStateGraph update
```

### Tại sao ViVy nhanh hơn khi dùng cùng một base model?

ViVy không tăng tốc token generation — ViVy tăng tốc **tổng thời gian hoàn thành nhiệm vụ**:

| Cơ chế | Hiệu quả |
|:---|:---|
| **DirectiveMTPHead** — biết action trước khi generate | Bỏ "thinking out loud" tokens |
| **CognitiveStateGraph + Error-Dampening** | 0% retry lỗi cũ (VM-11) |
| **HebbianRecall O(1)** | Recall kinh nghiệm tức thì |
| **ElasticNCore N-parallel** | N hypotheses trong 1 GEMM pass |

---

## Kiến Trúc 3 Lớp

| Layer | Package | Mô tả |
|:---|:---|:---|
| **Engine** (Sprint 1) | `engine/` | ElasticNCore, DirectiveMTPHead, Primitives (file/exec/media/cache) |
| **Memory** (Sprint 2) | `memory/`, `orchestrator/` | CognitiveStateGraph, HebbianRecall, GraphBridge, Error-Dampening |
| **Integration** (Sprint 3) | `integration/` | LlamaCppBridge, MultimodalAdapter, ToolDispatcher, SessionManager, InferenceLoop |

---

## Cài Đặt Nhanh

### Yêu cầu
- Python 3.10+
- [Ollama](https://ollama.com) đã cài đặt
- ~10GB disk (model) + 16GB RAM khuyến nghị

### 1. Clone và cài dependencies

```bash
git clone <repo-url>
cd unitary-reasoner
pip install -e ".[dev]"
```

### 2. Pull model Gemma 4 E4B

```bash
ollama pull gemma4:e4b
```

### 3. Build ViVy từ Modelfile

```bash
ollama create vivy-final:v1 -f Modelfile.vivy
```

### 4. Chạy smoke test (không cần server)

```bash
python scripts/test_integration.py
# Expected: 19/19 passed
```

### 5. Khởi động và chạy

```powershell
# Terminal 1: đảm bảo Ollama đang serve
ollama serve

# Terminal 2: chạy ViVy interactive
python scripts/run_vivy.py --mode agentic
```

---

## Cấu Trúc Thư Mục

```
unitary-reasoner/
├── engine/                     # Sprint 1: Engine Primitives
│   ├── primitives.py           # file_io, exec, media_slice, cache_control
│   ├── elastic_n_core.py       # ElasticNCore N∈[2,16], OOM Guard
│   └── mtp_directive.py        # DirectiveMTPHead + HMAC-SHA256
│
├── memory/                     # Sprint 2: Memory Systems
│   ├── cognitive_graph.py      # CognitiveStateGraph (Thought Ecology)
│   └── hebbian_recall.py       # HebbianRecall W=YX⁺ O(1)
│
├── orchestrator/               # Sprint 2: Orchestration
│   ├── graph_bridge.py         # GraphBridge + Error-Dampening VM-11
│   └── epistemic_gate.py       # EpistemicGate 3-way routing
│
├── integration/                # Sprint 3: LLM Integration Layer
│   ├── llama_cpp_bridge.py     # OpenAI-compat HTTP client (Ollama/llama.cpp)
│   ├── multimodal_adapter.py   # Text/Image/Audio/VideoFrame encoder
│   ├── tool_dispatcher.py      # LLM tool_call → engine primitive
│   ├── session_manager.py      # Per-session CognitiveStateGraph isolation
│   └── vivy_inference_loop.py  # Main loop: think → act → observe → learn
│
├── tests/                      # 515 pytest tests (Sprint 1+2+3)
├── scripts/
│   ├── setup_vivy.ps1          # Windows setup (download model + deps)
│   ├── run_vivy.py             # Interactive launcher (chat/agentic/batch)
│   └── test_integration.py     # 19 offline smoke tests
│
├── Modelfile.vivy              # FROM gemma4:e4b + V5.1 SYSTEM prompt
├── VIVY_CORE_MANIFEST.md       # Package manifest + completion gates
└── pyproject.toml              # Package config
```

---

## Chạy Tests

```bash
# Full pytest suite (515 tests, Sprint 1+2)
pytest tests/ -v

# Integration smoke tests (19 tests, offline — không cần Ollama)
python scripts/test_integration.py
```

---

## Base Model & Upgrade Path

ViVy Core được thiết kế để **swap base model dễ dàng** — chỉ thay đổi 1 dòng trong `Modelfile.vivy`:

| Stage | Model | Modalities | RAM | Notes |
|:---|:---|:---:|:---:|:---|
| **Hiện tại** | `gemma4:e4b` | Text+Vision+Audio | ~10GB | Local, Apache 2.0 |
| **Upgrade** | Nemotron Nano Omni | Text+Vision+Audio+Video | GPU 8GB+ | Khi có NVIDIA GPU |
| **Final** | Qwen3.8-Omni-Flash | Full omni | API / local | Khi open weights ra |

Toàn bộ ViVy Core (Engine, Memory, Integration) **không thay đổi** khi swap model.

---

## Invariants (Không Được Phá Vỡ)

1. **No wrappers**: Không có LangChain, AutoGen, Haystack trong engine
2. **VM-11**: Error repeat rate = 0% (enforced bởi CognitiveStateGraph)
3. **ViVy không tự tuyên bố COMPLETE** — cần Coordinator (Antigravity IDE) confirm
4. **Directive-first**: DirectiveMTPHead emit opcode trước khi LLM generate output

---

## License

- **ViVy Core** (this repo): MIT License
- **Base model (Gemma 4 E4B)**: Apache 2.0 — [Google DeepMind](https://ai.google.dev/gemma/terms)

---

## Changelog

Xem [`VIVY_CORE_MANIFEST.md`](VIVY_CORE_MANIFEST.md) để biết full changelog và completion gates.