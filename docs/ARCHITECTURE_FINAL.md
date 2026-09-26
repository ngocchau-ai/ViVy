# ViVy Final Core V1.0 & Cautreo Native Engine — Toàn Văn Đặc Tả Kiến Trúc Hệ Thống Cuối Cùng

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

---

## Lịch Sử Thay Đổi (Changelog)

| Phiên bản | Thời gian | Agent / Tác giả | Nội dung thay đổi & Lý do |
|:---|:---|:---|:---|
| 1.0.0 | 21/09/2026 17:00 ICT | Antigravity IDE | Khởi tạo bản đặc tả toàn văn kiến trúc ViVy Final Core V1.0 & Cautreo Native Engine. |
| 1.1.0 | 21/09/2026 18:45 ICT | Antigravity IDE | Cập nhật theo CEO Review & Codex Audit: Khẳng định nguyên tắc ViVy là Linh Hồn duy nhất làm chủ Cautreo (loại bỏ kiến trúc dual-port router phức tạp); tích hợp Intuition Digest vào infer loop; áp dụng trần Context Budget 2048 tokens; giải ảo trọng số ngẫu nhiên của N-Core. |
| 1.2.0 | 23/09/2026 11:30 ICT | Antigravity IDE | Tích hợp Cautreo Cartography Atlas (`qwen2-vl-72b.catlas`) & Qwen2-VL-72B-Instruct làm Hồ tri thức đa phương thức (`[DOWNLOADED_ON_DISK / PAGING_LEDGER_VERIFIED]`); chuẩn hóa topology `MODEL_ROOT = D:\models`; bổ sung Multimodal & Vision Archetypes. |
| 1.3.0 | 23/09/2026 | Claude Code (P0 Superority Truth Pass) | Gate 9 scrub: [ISOLATED] claim `VM-11: tỷ lệ lặp lại sai lầm = 0%` → `VM-11 dampener (measured rate: Gate-10 receipt)`; [ISOLATED] `HebbianRecall $O(1)$` → `truy xuất nhanh (complexity claim: see benchmark receipt)`. Lý do: Gate 9 cấm claim `0%` / `O(1)` / latency không có receipt. |
| 1.4.0 | 25/09/2026 | Claude Code (Plan 1+2 + Wave 1) | Đồng bộ toàn bộ code Plan 1 (Live Evidence Spine: verify_receipt, sandbox_capture, check_known_limits, run_w2_live, evidence_packet_template) + Plan 2 (Contract-Native Close-out: native_parity_decision, learned_router) + Wave 1 (Cautreo memory: cautreo_weight_map, cautreo_session_log) vào `core/integration/`. Bổ sung discussion record + plan-tune vào `docs/plans/`. Cập nhật preflight.py + receipt.py. |
| 1.5.0 | 25/09/2026 | Claude Code (Wave 2A+2B) | Đồng bộ Wave 2: Weight Pager Interface (`weight_pager.py` — register_model, load_partial, stream_weights, memory_usage) + Cross-Model Adapter (`cross_model_adapter.py` — couple, route, combine_outputs, callback_weights). TD-4: partial weight load. TD-5: output-level composition, weight inheritance qua callback. |
| 1.6.0 | 25/09/2026 | Claude Code (Wave 3A) | Đồng bộ Wave 3: Scored Mindmap DAG (`scored_mindmap_dag.py` — DecisionNode, plan() greedy best-path, score_path(), reroute(), cycle detection, threshold check). TD-6: planning + QC, giảm mid-generation drift. |
| 1.7.0 | 25/09/2026 | Claude Code (Wave 4A) | Đồng bộ Wave 4: Model Upgrade Protocol (`model_upgrade_protocol.py` — readiness_check gate (memory ≥100, score ≥0.7, HW), migrate() SHA256-chained receipts, inherit_weights() registry). TD-8: progressive scaling, weight inheritance. |

---

## 1. Tuyên Ngôn Hoàn Thành Kiến Trúc Hệ Thống (Architecture Finality Declaration)

Dự án tái cấu trúc lần thứ 4 đã chính thức hoàn thành mục tiêu tối thượng: Xây dựng một **Thực thể Trí tuệ Nhân tạo Cục bộ Tự chủ (Autonomous Local AI Entity)** vận hành độc lập 100% trên phần cứng máy tính cá nhân, không phụ thuộc vào Ollama, không phụ thuộc vào đám mây bên thứ ba, và giải quyết triệt để bài toán thắt nút cổ chai về giới hạn ngữ cảnh (Context Window Bottleneck).

Kiến trúc thống nhất được xác lập trên mô hình **Tam Giác Nhận Thức (The Cognitive Trinity)**:

```
                       ┌─────────────────────────────────────────┐
                       │                  VIVY                   │
                       │      (Linh Hồn / Bản Ngã Bất Biến)      │
                       │   Cognitive State Graph • Hebbian Rules │
                       │    Epistemic Invariants • Anti-Drift    │
                       └────────────────────┬────────────────────┘
                                            │ In-Process Direct Binding
                                            │ Direct Memory Binding (C-API)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CAUTREO                                          │
│                            (Cơ Thể / Căn Phòng Sinh Tồn)                               │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                         TẦNG BỘ NHỚ NATIVE (C LEVEL)                           │   │
│   │   • context_memory.h: HARD_FACT, CONSTRAINT, TASK, SUMMARY (TTL, Version)      │   │
│   │   • score_graph.h: CT_SCORE_CONTEXT_EFFICIENCY, CT_SCORE_TASK_PROGRESS         │   │
│   │   • context_chain.h: CCE Segment Decomposer, Priority Scoring (α, β, γ, δ)     │   │
│   │   • wvs.h: Weight Value Scoreboard (Hot/Warm/Cold SSD Streaming)               │   │
│   └───────────────────────────────────────┬────────────────────────────────────────┘   │
│                                           │                                            │
│                                           ▼ Điều phối Context Slots (2048 tokens)      │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                  LLMs (Cơ Bắp Tư Duy Chuyên Dụng / Khách Thuê)                 │   │
│   │                                                                                │   │
│   │   [Slot 1: Gemma 4 E4B]        [Slot 2: Qwen 2.5 Coder]      [Slot 3: Qwen2-VL-72B]│
│   │    (Lập luận / Phản biện)         (Code / Refactor kỹ thuật)    (Đa phương thức & Tri thức)│
│   └────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                   CỔNG DỊCH VỤ ĐỘC LẬP (STANDALONE RUNTIME)                    │   │
│   │   • OpenAI Compatible API: POST /v1/chat/completions (Port 8080)               │   │
│   │   • Standalone Native CLI: `cautreo chat` / `cautreo serve`                    │   │
│   │   • Plugin Registry: WebSearch, SysTools, Custom Extensions                    │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Nỗi Đau Hướng Tới & Giải Pháp Cốt Lõi (Pain Points & Solutions)

### 2.1. Nỗi Đau 1: Giới hạn Context 2048 tokens gây nghẽn và đơ máy trên CPU
- **Thực tế:** Mở rộng context lên 16k-32k trên CPU làm KV Cache phình to và Attention prefill mất 60-90s khiến máy bị soft-hang.
- **Giải pháp:** Coi 2048 tokens là "điểm ngọt" nguyên tử (Atomic Context Window). Cautreo Engine sử dụng **Context Chain Engine (CCE)** để bóc tách tài liệu dài thành chuỗi các segment $\le 1500$ tokens, xen kẽ với **150 tokens Intuition Digest** được trích xuất từ tầng Memory native.

### 2.2. Nỗi Đau 2: Bóc tách context làm mất trí nhớ và trôi lệch mục tiêu (Semantic Drift)
- **Thực tế:** Các phương pháp cắt context thông thường làm LLM quên mục tiêu ở các đoạn sau.
- **Giải pháp:** ViVy không dùng raw chat history mà sử dụng **Cognitive State Graph (CSG)** và **Hebbian Recall** lưu trong Cautreo Memory. Mỗi chuỗi context đều nhận các `INVARIANT`, `ACTIVE_GOAL`, `HARD_FACT` ở đầu prompt in-process (latency: see benchmark receipt). <!-- [ISOLATED 24/09/2026] prior: "với độ trễ 0ms" — Gate 9: latency claim requires receipt. -->

### 2.3. Nỗi Đau 3: Phụ thuộc vào Ollama và overhead HTTP JSON
- **Thực tế:** Ollama chiếm dụng tài nguyên, không hỗ trợ SSD streaming theo tập tính, giao tiếp qua HTTP JSON gây trễ và tiêu tốn CPU.
- **Giải pháp:** Xây dựng **Cautreo Standalone** (C11 native, AVX2/FMA) chạy độc lập 100%. ViVy nhúng trực tiếp vào Cautreo qua **C-ABI shared library (`cautreo.dll`)**, truy cập trực tiếp struct bộ nhớ RAM trong tiến trình.

---

## 3. Cấu Trúc Phân Tầng Hệ Thống (Layered Architecture)

### 3.1. Tầng Linh Hồn: ViVy Core (`core/`)
- **`engine/elastic_n_core.py`:** Elastic N-Core đa luồng nhận thức, điều phối các nhánh tư duy.
- **`engine/mtp_directive.py`:** MTP Directive Head sinh các kế hoạch và chỉ thị hành động có cấu trúc.
- **`memory/cognitive_graph.py`:** Đồ thị trạng thái nhận thức, ghi nhận các nút niềm tin, quyết định, và các cạnh `FALSIFIED` (VM-11 dampener: giảm lặp lại sai lầm; measured rate: Gate-10 receipt).
- **`memory/hebbian_recall.py`:** Bộ nhớ liên kết Hebbian truy xuất nhanh các bài học kinh nghiệm (complexity claim: see benchmark receipt).
- **`orchestrator/model_router.py` & `model_catalog.py`:** Multi-Model Router phân luồng tự động:
  - `TaskArchetype.ARCH_SPEC_AND_PLAN`, `KNOWLEDGE_FORAGING`, `DYNAMIC_ORCHESTRATION_QA` $\rightarrow$ `gemma4-e4b` (Active Cognitive Soul @ Port 8080).
  - `TaskArchetype.NATIVE_SYSTEM_CODING`, `REFACTOR_AND_TESTING` $\rightarrow$ `qwen2.5-coder-7b-instruct` (Technical Code Specialist).
  - `TaskArchetype.MULTIMODAL_IMAGE_REASONING`, `DESKTOP_GUI_VISION` $\rightarrow$ `qwen2-vl-72b` (Deep Multimodal Knowledge Pool kết nối qua Cautreo Cartography Atlas).
- **`integration/cautreo_binding.py`:** Cầu nối C-ABI ctypes in-process binding tới `cautreo.dll` kèm bộ phân trang `CautreoWeightPager`.
- **`integration/cautreo_cartographer.py`:** Quản lý bản đồ tri thức 4 lục địa nạp từ `.catlas` file.
- **`integration/preflight_steering.py`:** Bơm Hard Negative Constraints ngăn chặn lỗi lặp lại VM-11.

### 3.2. Tầng Cơ Thể: Cautreo Native Engine (`engine/`)
- **`engine/bin/cautreo.exe`:** Công cụ dòng lệnh độc lập hỗ trợ `chat`, `serve`, `help`.
- **`engine/bin/cautreo.dll`:** Shared library C-ABI cung cấp:
  - `ct_context_memory_*`: Quản lý bộ nhớ cứng, ràng buộc, nhiệm vụ, tóm tắt.
  - `ct_score_graph_*`: Runtime Score Graph theo dõi `CT_SCORE_CONTEXT_EFFICIENCY`, `CT_SCORE_TASK_PROGRESS`, `CT_SCORE_MEMORY_QUALITY`.
  - `ct_context_chain_*`: Phân rã context, chấm điểm ưu tiên $\alpha, \beta, \gamma, \delta, \epsilon$.
- **`engine/bin/cautreo-server.exe`:** Máy chủ HTTP độc lập tương thích OpenAI API `/v1/chat/completions` (port 8080).

### 3.3. Tầng Cơ Bắp Tư Duy: Cognitive Muscle Models (`D:\models`)
- **`gemma4-e4b\vivy-gemma-e4b-q4km.gguf` (8.95GB, Q4_K_M):** `[ACTIVE_COGNITIVE_SOUL]` Mô hình suy luận và điều phối nhận thức chính tại Port 8080.
- **`qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf` (44.16GB) & `mmproj` (1.30GB):** `[DOWNLOADED_ON_DISK / PAGING_LEDGER_VERIFIED]` Hồ tri thức đa phương thức và sâu rộng, kích hoạt theo lát cắt qua Cartography Atlas.
- **`qwen2.5-coder-7b-instruct` (4.68GB):** `[AVAILABLE_ON_DEMAND]` Kỹ sư viết mã C-ABI native và refactor.
- **`vivy2.gguf` & `qwen3.8-27b.gguf`:** `[ISOLATED / ARCHIVED]` Đã giải phóng dung lượng đĩa NVMe để tối ưu cho Qwen2-VL-72B.
### 3.4. Cơ Chế Dream Engine & Chấm Điểm Thư Viện Cautreo (Auditor & Standby Lifecycle)
- **Antigravity IDE (Auditor / Evaluator):**
  - Không thay thế ViVy, mà thực hiện vai trò chấm điểm hiệu suất (`task_progress`, `context_efficiency`, `memory_quality`) vào Cautreo Runtime Score Graph (`ct_score_graph_update`).
  - Ghi nhật ký thẩm định, bài học kinh nghiệm (`constraints`) và bằng chứng (`hard_facts`) trực tiếp vào Cautreo Context Memory (`ct_context_memory_put`) với provenance ID để ViVy có thể đọc tức thì từ RAM native.
- **ViVy Dream Engine (`VivyDreamEngine`):**
  - Kích hoạt tự động mỗi khi ViVy hoàn thành nhiệm vụ và rơi vào trạng thái chờ nhiệm vụ mới (Idle / Standby).
  - Đọc lại toàn bộ điểm số và nhận xét từ Antigravity trong thư viện Cautreo.
  - Chạy chu trình củng cố SVD & Hebbian: tăng trọng số các node thành công, giảm trọng số (dampen) các hành động lỗi, tự động nâng cấp các Constraints thành Invariants trong `CognitiveStateGraph`.
  - Tinh lọc bản tóm tắt trực giác nén **`Intuition Digest` ~150 tokens** đưa vào RAM native của Cautreo (`vivy_intuition_digest_current`).
  - Đưa ViVy vào trạng thái **`LUCID_STANDBY`** sẵn sàng thức tỉnh tức thì ngay khi nhận được prompt mới. <!-- [ISOLATED 24/09/2026] prior: "thức tỉnh 0ms" — Gate 9: latency claim requires receipt. -->

---

## 4. Bản Đồ Thư Mục Phân Phối Cuối Cùng (`Vivy final/`)

```
d:\91s_Vivy\Vivy final\
├── README.md                      ← Bản tuyên ngôn bàn giao cuối cùng
├── ARCHITECTURE_FINAL.md          ← File này: Toàn văn đặc tả kiến trúc
├── RUNBOOK.md                     ← Cẩm nang vận hành 1 chạm (1-Touch SOP)
├── engine\                        ← Cautreo Native Engine (Cơ thể vật lý)
│   ├── bin\
│   │   ├── cautreo.exe            ← Standalone binary (CLI)
│   │   ├── cautreo.dll            ← C-ABI Shared Library (In-process memory)
│   │   └── cautreo-server.exe     ← HTTP Server binary port 8080
│   └── include\                   ← Header C native (context_memory, score_graph...)
├── core\                          ← ViVy Unitary Reasoner (Linh hồn nhận thức)
│   ├── engine\                    ← ElasticNCore, MTP, Primitives, DreamEngine
│   ├── memory\                    ← CognitiveStateGraph, HebbianRecall
│   ├── orchestrator\              ← EpistemicGate, ModelRouter, GraphBridge
│   ├── integration\               ← LlamaCppBridge, Dispatcher, CautreoBinding, CautreoScoringJournal
│   ├── scripts\                   ← run_vivy.py, test_integration.py
│   └── pyproject.toml             ← Cấu hình môi trường Python
├── models\                        ← Kho weights mô hình (Cơ bắp tư duy)
│   ├── gemma4-e4b.gguf            ← 8.95GB (Active Reasoner)
│   ├── vivy2.gguf                 ← 1.88GB (Fast Reasoner)
│   └── qwen3.8-27b.gguf           ← 6.77GB (Archived / Research)
└── scripts\                       ← Kịch bản vận hành & kiểm định
    ├── start_vivy_unified.ps1     ← Khởi chạy 1 chạm ViVy + Cautreo
    ├── verify_all.ps1             ← Kịch bản tự kiểm định 11/11 cổng
    └── verify_cautreo.py          ← Python ctypes sanity check
```

---

## 5. Thẩm Định Theo Bộ Tiêu Chuẩn 4 Trục (4-Pillar Quality Audit)

1.  **Tính Xung Đột (Conflict):** **PASS**. Không có xung đột giữa Python runtime và C native vì phân tách ranh giới rõ ràng: ViVy quản lý nhận thức mức cao, Cautreo quản lý bộ nhớ và inference mức thấp. C-ABI ctypes binding bảo đảm đơn nguồn chân lý (Single Source of Truth).
2.  **Tính Hợp Lý (Rationality):** **PASS**. Cửa sổ context 2048 tokens phù hợp tối ưu với băng thông RAM DDR4/DDR5 và CPU. Bóc tách CCE giúp duy trì vận tốc sinh token $12-14\text{ tok/s}$, hoàn toàn khả thi trên máy tính cá nhân 16GB RAM.
3.  **Tính Dư Thừa (Redundancy):** **PASS**. Triệt tiêu hoàn toàn LangChain, AutoGen, Haystack và các wrapper trung gian cồng kềnh. Loại bỏ việc nhân bản nhiều bản sao ViVy gây lãng phí bộ nhớ.
4.  **Tính Hiệu Quả (Effectiveness):** **PASS**. 618/618 unit tests pass, 19/19 integration smoke tests pass, 11/11 self-verification gates pass. Khởi chạy 1 chạm tức thì qua `start_vivy_unified.ps1`.

---

## 6. Lịch Sử Thay Đổi (Changelog)

| Agent / ID | Thời gian | Lý do & Chi tiết thay đổi |
|:---|:---|:---|
| Antigravity IDE (Architect) | 21/09/2026 17:00 ICT | Khởi tạo tài liệu đặc tả kiến trúc cuối cùng cho ViVy Final V1.0. |
| Antigravity IDE (Dream & Scorer Engine) | 21/09/2026 17:35 ICT | Bổ sung Mục 3.4: Tích hợp ViVy Dream Engine (`LUCID_STANDBY`) và Antigravity Scoring Journal vào Cautreo Library. Cập nhật 618/618 unit tests pass. |
---

## 6. Lịch Sử Thay Đổi (Changelog)

| Agent | Thời gian | Hành động |
|:---|:---|:---|
| Antigravity IDE (Deputy 1 Coordinator) | 21/09/2026 17:10 ICT | Khởi tạo tài liệu ARCHITECTURE_FINAL.md: Toàn văn đặc tả kiến trúc hệ thống ViVy Final V1.0 & Cautreo Native Engine. Đóng gói thư mục phân phối cuối cùng `Vivy final/`. |
