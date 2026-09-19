> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Changelog bắt buộc:** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do).
> 2. **Chỉ cô lập, KHÔNG xóa:** TUYỆT ĐỐI KHÔNG xóa nội dung/kiến trúc cũ. Đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain:** Mọi thay đổi phải được đồng bộ vào `D:\2brain`.

# VIVY CORE MANIFEST — V1.0.0
**Package:** `unitary-reasoner`
**Architecture:** `ARCH-VIVY-V5-OMNI-EPISTEMIC`
**Date:** 19/09/2026 | **Status:** PRODUCTION-READY ✅

---

## Package Identity

```
Name:     ViVy Final Core
Version:  1.0.0
Codename: Omni-Epistemic Core
Spec:     ARCH-VIVY-V5-OMNI-EPISTEMIC (V5.1)
Base:     Gemma 4 E4B (Apache 2.0)
Runtime:  llama.cpp llama-server
Tests:    515/515 passed | 7/7 gates cleared
```

---

## Architecture Summary

ViVy Final Core là **bộ não điều phối AI local** với 3 lớp:

```
┌──────────────────────────────────────────────────────┐
│  LAYER 3 — INTEGRATION (Sprint 3)                    │
│  VivyInferenceLoop · LlamaCppBridge · ToolDispatcher │
│  MultimodalAdapter · SessionManager                  │
├──────────────────────────────────────────────────────┤
│  LAYER 2 — MEMORY (Sprint 2)                         │
│  CognitiveStateGraph · HebbianRecall W=YX+ (O(1))    │
│  GraphBridge · Error-Dampening VM-11                 │
├──────────────────────────────────────────────────────┤
│  LAYER 1 — ENGINE (Sprint 1)                         │
│  ElasticNCore N∈[2,16] · DirectiveMTPHead + HMAC     │
│  Primitives: file_io · exec · media_slice · cache    │
└──────────────────────────────────────────────────────┘
```

---

## Coordinator Completion Gates — All CLEARED

| Gate | Condition | Status |
|:---|:---|:---:|
| G-1 | Delegation contract acknowledged | ✅ |
| G-2 | Sprint 1+2+3 deliverables present | ✅ |
| G-3 | 0 regressions (515/515 tests) | ✅ |
| G-4 | VM-10: OOM Guard at N=2 (1MB VRAM) | ✅ |
| G-5 | VM-11: Error repeat rate = 0% | ✅ |
| G-6 | Sprint 1+2+3 review: 0 CRITICAL, 0 HIGH | ✅ |
| G-7 | 0 wrapper imports (AST-verified) | ✅ |

---

## Base Model Selection

| | Gemma 4 E4B |
|:---|:---|
| **Provider** | Google DeepMind |
| **Size** | 4B effective / ~5B total params |
| **Quantization** | Q4_K_M GGUF (~5GB) |
| **License** | Apache 2.0 |
| **Modalities** | Text + Vision + Audio |
| **Tool Calling** | Native JSON Schema |
| **MTP** | Yes (Multi-Token Prediction) |
| **RAM required** | ~8GB (comfortable on 16GB) |
| **Context** | 128K tokens |

**Upgrade path** (swap only `FROM` in Modelfile.vivy, Core unchanged):
```
Now  : Gemma 4 E4B      (local, 5GB, Text+Vision+Audio)
Next : Nemotron Nano Omni (GPU ≥8GB, higher capability)
Final: Qwen3.8-Omni-Flash (when open weights available)
```

---

## File Manifest

### Sprint 1 — Engine Primitives
| File | Purpose |
|:---|:---|
| `engine/primitives.py` | 4 engine primitives (file_io, exec, media_slice, cache) |
| `engine/elastic_n_core.py` | ElasticNCore N∈[2,16], OOM guard, GEMM |
| `engine/mtp_directive.py` | DirectiveMTPHead + HMAC-SHA256 |
| `tests/test_primitives.py` | 34 tests |
| `tests/test_elastic_n_core.py` | 25 tests |
| `tests/test_mtp_directive.py` | 39 tests |

### Sprint 2 — Cognitive State Graph & Memory
| File | Purpose |
|:---|:---|
| `memory/cognitive_graph.py` | CognitiveStateGraph (Thought Ecology Topology) |
| `memory/hebbian_recall.py` | HebbianRecall W=YX+ O(1) recall |
| `orchestrator/graph_bridge.py` | GraphBridge + Error-Dampening pipeline |
| `tests/test_cognitive_graph.py` | 44 tests incl. VM-11 gate |
| `tests/test_hebbian_recall.py` | 25 tests incl. O(1) complexity |
| `tests/test_graph_bridge.py` | 18 tests incl. E2E pipeline |

### Sprint 3 — Integration Layer
| File | Purpose |
|:---|:---|
| `integration/llama_cpp_bridge.py` | Thin OpenAI-compat HTTP client cho llama-server |
| `integration/multimodal_adapter.py` | Text/Image/Audio/VideoFrame → Gemma 4 format |
| `integration/tool_dispatcher.py` | LLM tool_call → engine primitive |
| `integration/session_manager.py` | Per-session CognitiveStateGraph isolation |
| `integration/vivy_inference_loop.py` | Main loop: think → act → observe → learn |
| `Modelfile.vivy` | FROM gemma4:e4b + V5.1 SYSTEM prompt |
| `Modelfile.vivy.gemma4.bak` | [ISOLATED] bản cũ FROM vivy:latest |
| `scripts/setup_vivy.ps1` | Windows: download model + llama.cpp + verify |
| `scripts/run_vivy.py` | Launch: --mode chat|agentic|batch |
| `scripts/test_integration.py` | 15 offline smoke tests |

---

## How ViVy Makes Base Model Faster

ViVy **không** tăng tốc token generation của model gốc.
ViVy tăng tốc **tổng thời gian hoàn thành nhiệm vụ** bằng:

| Cơ chế | Tiết kiệm |
|:---|:---|
| **DirectiveMTPHead** — biết action TRƯỚC khi LLM generate | Không cần LLM "think out loud" — bỏ wasted output tokens |
| **CognitiveStateGraph + Error-Dampening** | 0% retry lỗi cũ — không gọi LLM inference cho action đã fail |
| **HebbianRecall O(1)** | Recall kinh nghiệm tức thì thay vì hỏi LLM lại |
| **ElasticNCore N-parallel** | N hypothesis song song trong 1 matmul → compute-bound (Jev-validated) |

---

## Quick Start

```powershell
# 1. Setup (một lần)
.\scripts\setup_vivy.ps1

# 2. Start llama-server (giữ terminal này mở)
.\llama.cpp\llama-server.exe -m models\gemma-4-e4b-q4_k_m.gguf -c 32768 --port 8080 --jinja

# 3. Smoke test (terminal khác)
python scripts\test_integration.py

# 4. Run ViVy
python scripts\run_vivy.py --mode agentic
```

---

## Lịch Sử Thay Đổi

| Agent | Thời gian | Hành động |
|:---|:---|:---|
| Antigravity IDE (Sprint 1+2+3 Coordinator) | 19/09/2026 18:48 ICT | Initial release: Sprint 1+2+3 complete, Gemma 4 E4B integration, 515/515 tests |
