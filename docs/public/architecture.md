# ViVy Architecture Overview — V5.1

> [!IMPORTANT]
> Agent kế thừa: BẮT BUỘC ghi Changelog. KHÔNG xóa nội dung cũ — chỉ cô lập `[ISOLATED]`.

## Triết Lý Thiết Kế

ViVy được xây dựng trên 3 nguyên tắc cốt lõi:

1. **In-Engine Dweller** — ViVy tồn tại trực tiếp trong inference engine, không qua wrapper
2. **Directive-First** — Biết phải làm gì *trước khi* generate output token đầu tiên
3. **Thought Ecology** — Mọi suy nghĩ đều để lại dấu vết trong CognitiveStateGraph; hệ thống học từ thất bại, không lặp lại sai lầm

---

## Sơ Đồ Luồng Dữ Liệu

```
                    INPUT
           ┌────────────────────┐
           │  MultimodalAdapter │  ← Text / Image / Audio / Video
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │   ElasticNCore     │  ← N hypothesis song song (N∈[2,16])
           │   n_override=2..4  │    GEMM: compute-bound, không memory-bound
           └─────────┬──────────┘
                     │ action_vector
           ┌─────────▼──────────┐
           │  DirectiveMTPHead  │  ← Opcode + HMAC-SHA256 (tamper-proof)
           └─────────┬──────────┘
                     │ directive (pre-computed)
           ┌─────────▼──────────┐
           │   Gemma 4 E4B      │  ← LLM: Text+Vision+Audio, 128K ctx
           │  (Ollama server)   │    Native tool calling + MTP
           └─────────┬──────────┘
                     │ response + tool_calls
           ┌─────────▼──────────┐
           │  ToolDispatcher    │  ← Map tool_call → engine primitive
           └─────────┬──────────┘
                     │ PrimitiveResult
           ┌─────────▼──────────┐
           │   GraphBridge      │  ← Evaluate + Error-Dampening VM-11
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │ CognitiveStateGraph│  ← Node update: confidence, dampen_factor
           │ + HebbianRecall    │    W = YX⁺, O(1) associative recall
           └────────────────────┘
                    OUTPUT
```

---

## Engine Layer (Sprint 1)

### ElasticNCore

Đánh giá N action candidates song song trong **1 GEMM pass**:

```python
# N=2 cores đang chạy song song
n_core = ElasticNCore(n_min=2, n_max=4, hidden_dim=64)
result = n_core.forward(n_override=2)
winner = result.winner  # ActionCandidate với score cao nhất
```

**Tại sao compute-bound?**
- Jev model (Jamba-style parallel evaluation) chứng minh: xử lý N queries trên cùng hidden state chuyển từ *memory-bandwidth-bound* → *compute-bound*
- GPU utilization tăng khi N tăng
- ViVy khai thác điều này ở tầng action selection

### DirectiveMTPHead

```python
directive = mtp_head.forward(action_vector)
# directive.opcode: EXECUTE | FORAGE | DELEGATE
# directive.hmac: tamper-proof signature
assert mtp_head.verify(directive)  # luôn True nếu không bị tamper
```

### Engine Primitives

| Primitive | Signature | Mô tả |
|:---|:---|:---|
| `engine_file_io` | `(action, path, content?, offset?)` | read/write/append/delete/exists/mkdir |
| `engine_exec` | `(command[], cwd?, env?, timeout_s?)` | subprocess với timeout |
| `engine_media_slice` | `(source, start_ms, end_ms, output?)` | ffmpeg slice |
| `engine_cache_control` | `(action, key?, value?)` | in-memory KV cache |

---

## Memory Layer (Sprint 2)

### CognitiveStateGraph

**Thought Ecology Topology** — mọi suy nghĩ là một node, mọi thất bại là một edge `FALSIFIED`:

```
Node (HYPOTHESIS):
  confidence: 0.8
  falsified_count: 0
  dampen_factor(): 1.0          ← no dampening

Node (HYPOTHESIS) after 1 failure:
  falsified_count: 1
  dampen_factor(): 0.5^1 = 0.5  ← VM-11: không bao giờ retry y hệt
```

**VM-11 Invariant**: Error repeat rate = 0%

### HebbianRecall

```
W = Y · X⁺    (pseudoinverse — học một lần, recall mãi mãi)

Recall: similarity = clip(W·query / ||W·query||, 0, 1)
        → O(1) — không cần search vector database
```

---

## Integration Layer (Sprint 3)

### VivyInferenceLoop — 3 Modes

| Mode | Mô tả | Tool calls |
|:---|:---|:---:|
| `CHAT` | Single-turn, text-only | ❌ |
| `AGENTIC` | Multi-turn, up to 10 rounds | ✅ |
| `BATCH` | Non-interactive, first response | ❌ |

### SessionManager

```python
# Mỗi session có CognitiveStateGraph + HebbianRecall riêng
sm = SessionManager(hidden_dim=64, max_sessions=32, ttl_seconds=3600)
session = sm.get_or_create("user_123")
# session.graph, session.recall, session.bridge — hoàn toàn cô lập
```

---

## Upgrade Path

```
                    swap 1 dòng trong Modelfile.vivy
                              │
FROM gemma4:e4b ──────────────┼──► FROM nemotron-nano-omni
                              │        (cần NVIDIA GPU ≥ 8GB)
                              │
                              └──► FROM qwen3.8-omni-flash
                                       (khi open weights ra)

Toàn bộ ViVy Core KHÔNG thay đổi.
```

---

## Lịch Sử Phiên Bản

| Version | Date | Notes |
|:---|:---|:---|
| V5.0 | Sprint 1 | ElasticNCore, MTP, Primitives |
| V5.1 | Sprint 2 | CognitiveStateGraph, HebbianRecall, VM-11 |
| **V5.1 Final** | Sprint 3 | Integration Layer, Gemma 4 E4B, 19/19 tests |
