# Thảo luận Kiến trúc Vivy — Orchestration, Coupling & Cautreo Memory

**Ngày:** 2026-09-25
**Phạm vi:** Xác minh kiến trúc, chiến lược coupling, mindmap DAG, Cautreo weight map
**Trạng thái:** DISCUSSION RECORD — không thực thi

---

## 1. Xác minh kiến trúc: Model ghép nối

**Kết luận:** Gemma4 là core LLM (brain), Vivy là orchestration layer.

```
┌─────────────────────────────────────┐
│           VIVY (orchestrator)        │
│  decision · skill routing · self-improve│
├──────────┬──────────┬───────────────┤
│ Gemma4   │ Qwen     │ Model khác... │
│ :8080    │ :xxxx    │  qua coupling │
└──────────┴──────────┴───────────────┘
```

- **Gemma4** sinh text, suy luận qua llama-server :8080
- **Vivy** điều phối: system prompt steering, context pipeline, tool dispatch, inference loop
- **Cautreo** native component: memory (put/get/delete), forward parity (L-40 FAIL)

## 2. Chiến lược: Ghép nối, xâm lấn, chiếm đoạt, sở hữu

Vivy **không học toàn bộ Gemma4**. Vivy học **cách dùng** model core:

| Distillation (sai hướng) | Xâm lấn (đúng hướng) |
|---|---|
| Học output → model copy | Học cách dùng → controller |
| Ceiling = Gemma4 | Ceiling = orchestration experience |
| 1 model, 1 năng lực | 1 orchestrator, nhiều model |
| Copy reasoning | Absorb meta-reasoning |

**Cơ chế "chạy càng nhiều → càng thông minh":**
- Context pattern → strategy nào hiệu quả
- Model core nào mạnh ở task nào (skill routing)
- Khi nào abstain / escalate / tự sửa
- Tích lũy → decision quality tăng → tự cải thiện không cần retrain model core

## 3. Memory + Weight Management

Vivy cần **bộ nhớ (Cautreo)** + **weight pager**:

| Thành phần | Vai trò |
|---|---|
| **Cautreo memory** | Maps + logs + experience replay |
| **Weight pager** | Partial load, Q4_K/Q6_K streaming, không load toàn bộ |
| **Model coupling** | Swap model core khi HW cho phép |
| **Weight inheritance** | Gọi ngược trọng số cũ sau khi chuyển model |

**Progressive scaling:**
```
Hiện tại:  Vivy ──couple──→ Gemma4 (hardware-fit)
                │
                ▼ (tích lũy + task lớn + HW cho phép)
Tương lai: Vivy ──couple──→ Model lớn hơn
                │
                └──call-back──→ Gemma4 weights (special cases)
```

## 4. Câu hỏi kỹ thuật đã thảo luận

### Q1: Gemma4 dùng trọng số/kích hoạt Qwen 2-70B?

**Trực tiếp share weights: KHÔNG khả thi** — khác tokenizer, hidden dim, attention architecture.

**Giải pháp — Vivy làm adapter:**
```
Input → Vivy (routing)
          ├──→ Gemma4 (general, fast)
          └──→ Qwen-70B (specific, via weight pager, partial load)
                    └── ghép output
```

### Q2: Mindmap DAG tối ưu token coupling lớn?

| Vấn đề | Mindmap DAG giúp? |
|---|---|
| Output bị đứt | ⚠️ Gián tiếp (plan structure trước) |
| Sai sót token lớn | ✅ Scoring nodes → re-route |
| Input/output coupling | ✅ DAG trace được |
| Generator coherence | ❌ Không — vẫn cần model core mạnh |

### Q3: Tree map vs Session tracing cho Cautreo?

**Dùng cả hai — bổ trợ nhau:**

```
Cautreo Weight Map
├── tree_index (hierarchical, O(log n) lookup)
│   ├── model_weights/
│   │   ├── gemma4/
│   │   └── qwen-70b/ (partial)
│   └── capability_map/
│       └── task → model → layer_range
└── session_log (append-only, scored)
    ├── session-001: decisions + scores + state_delta
    └── session-002: ...
```

- **Tree map** = cấu trúc truy vấn (tốc độ)
- **Session log** = dữ liệu thời gian (audit + self-improve)

---

## 5. Quyết định kỹ thuật (Decision Ledger)

| ID | Quyết định | Trạng thái | Ghi chú |
|---|---|---|---|
| TD-1 | Vivy = orchestrator, không phải model | **CONFIRMED** | Không distill Gemma4 |
| TD-2 | Chiến lược xâm lấn + kế thừa | **CONFIRMED** | Meta-learning tầng orchestration |
| TD-3 | Cautreo memory bắt buộc (maps + logs) | **CONFIRMED** | Persistent orchestration knowledge |
| TD-4 | Weight pager cho partial weight access | **CONFIRMED** | Q4_K/Q6_K streaming |
| TD-5 | Cross-model = adapter, không share weights | **CONFIRMED** | Vivy ghép output từ nhiều model |
| TD-6 | Mindmap DAG = planning + QC, không thay generator | **CONFIRMED** | |
| TD-7 | Tree map + session tracing (cả hai) | **CONFIRMED** | Index + audit |
| TD-8 | Progressive scaling model core | **CONFIRMED** | HW-fit → upgrade khi sẵn sàng |
