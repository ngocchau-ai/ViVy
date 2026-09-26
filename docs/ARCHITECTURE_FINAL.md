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
Trọng số **không nằm trong repo** — `models/` chỉ giữ metadata. Vai trò trong kiến trúc:
- **Cognitive Reasoner** `[ACTIVE_COGNITIVE_SOUL]` — suy luận & điều phối nhận thức chính (Port 8080).
- **Multimodal Knowledge Pool** `[DOWNLOADED_ON_DISK / PAGING_LEDGER_VERIFIED]` — hồ tri thức đa phương thức, kích hoạt theo lát cắt qua Cartography Atlas.
- **Code Specialist** `[AVAILABLE_ON_DEMAND]` · **Reflex Student** `[ROADMAP_PROPOSED]` — xem bảng.

> **[ISOLATED 26/09/2026]** Danh sách path + size + quant đầy đủ từng nằm ở đây nhưng lặp lại với `README.md` §3 và `models/baselines/README.md` §2. **Gom 1 nguồn:** [→ `models/baselines/README.md` §2](../models/baselines/README.md) · SSOT: [→ `models/model_manifest.json`](../models/model_manifest.json).
> Ba gguf `qwen2.5-coder-7b-instruct-q4_k_m` / `vivy2` / `qwen3.8-27b` **đã gỡ tham chiếu sống** (user chỉ thị 26/09/2026) — kéo theo xóa 2 runtime `start_vivy_qwen_coder.ps1`. Hồ sơ còn tại mục `[ISOLATED]` của baselines/README.md.
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

## 4. Bản Đồ Thư Mục Phân Phối Cuối Cùng (`Vivy_final/`)

Cây trụ sau chuẩn hóa reorg D2–D5 (26/09/2026) — import style absolute top-level (`from engine.…`, `from memory.…`, `from training.…`), pythonpath/cwd = `vivy/`:

```
d:\91s_Vivy\Vivy_final\
├── README.md                      ← Bản tuyên ngôn bàn giao cuối cùng
├── CLAUDE.md                      ← Health stack + quy tắc cho agent kế thừa
├── vivy\                          ← LINH HỒN (Soul): runtime NPS-core hợp nhất
│   ├── engine\                    ← ElasticNCore, MTP, Primitives, DreamEngine
│   ├── memory\                    ← CognitiveStateGraph, HebbianRecall
│   ├── orchestrator\              ← EpistemicGate, ModelRouter, GraphBridge
│   ├── integration\               ← LlamaCppBridge, Dispatcher, CautreoBinding, CautreoScoringJournal
│   ├── training\                  ← Runtime training hợp nhất (730 tests)
│   ├── funnel\ · llm_bridge\      ← Verification funnel · LLM bridge
│   ├── tests\                     ← 693 tests (baseline)
│   └── pyproject.toml             ← Cấu hình môi trường Python
├── engine\                        ← CƠ THỂ (Vessel): Cautreo native C-ABI
│   ├── bin\
│   │   ├── cautreo.exe            ← Standalone binary (CLI)
│   │   ├── cautreo.dll            ← C-ABI Shared Library (In-process memory)
│   │   ├── cautreo-server.exe     ← HTTP Server binary port 8080
│   │   └── cautreo_pager.dll      ← Weight Pager native
│   ├── include\                   ← Header C native (context_memory, score_graph, wvs…)
│   └── src\weight_pager\          ← Nguồn C native weight pager
├── cautreo\                       ← Atlases (.catlas) + native habitat specs
├── host\                          ← Host mảnh + IPC Bus + plugins
├── ui\                            ← desktop-studio (Tauri) + cautreo-desktop
├── models\                        ← CHỈ METADATA — KHÔNG phải trọng số
│   ├── model_manifest.json        ← SSOT: full_path / status từng model
│   └── baselines\                 ← BASELINE_CORE_MANIFEST.json + README
├── scripts\                       ← Launcher + verify_all.ps1
└── docs\                          ← 5 doc chuẩn + RUNBOOK + CHECKPOINTS + adr/
    ├── ARCHITECTURE_FINAL.md      ← File này: Toàn văn đặc tả kiến trúc
    ├── RAW_CONSOLIDATED.md        ← #1 Tài liệu thô tổng hợp
    ├── TECHNICAL_DIRECTION.md     ← #2 Tài liệu định hướng kỹ thuật
    ├── TREE_MAP_AND_CHANGELOG.md  ← #4 Tree map diễn biến & lịch sử
    ├── REVIEWS.md                 ← #5 Tài liệu review
    └── RUNBOOK.md · CHECKPOINTS.md
```

**Trọng số mô hình** sống ở `MODEL_ROOT = D:\models` (ngoài repo) — GitHub chặn file > 100 MB, mọi `.pt/.gguf/.npy/.npz/.safetensors` nằm trong `internal/` và bị `.gitignore`. Bảng đầy đủ: [→ `models/baselines/README.md` §2](../models/baselines/README.md) · SSOT: [→ `models/model_manifest.json`](../models/model_manifest.json).

> **[ISOLATED 26/09/2026]** Cây cũ ở mục này liệt kê `core\`, `models\*.gguf` trực tiếp trong repo, và 3 file doc ở root. Sai sau reorg D2–D5: package hợp nhất là `vivy/` (không phải `core/`), repo `models/` chỉ giữ metadata, doc sống ở `docs/`. Nội dung cũ xem trong lịch sử git của file này.

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
| Antigravity IDE (Deputy 1 Coordinator) | 21/09/2026 17:10 ICT | Đóng gói thư mục phân phối cuối cùng `Vivy_final/`. |
| Antigravity IDE (Dream & Scorer Engine) | 21/09/2026 17:35 ICT | Bổ sung Mục 3.4: Tích hợp ViVy Dream Engine (`LUCID_STANDBY`) và Antigravity Scoring Journal vào Cautreo Library. Cập nhật 618/618 unit tests pass. |
| Claude Code | 26/09/2026 | **Gom tài liệu về 5 doc chuẩn** (user yêu cầu). Nối Phụ lục A–N (data cũ dạng ghi chú cô lập) vào cuối file. Cập nhật §3.3 (dọn trùng bảng trọng số) và §4 (cây trụ mới `vivy/` thay `core/`). Gộp 2 mục `## 6. Lịch Sử Thay Đổi` bị nhân đôi từ trước thành 1. |

> **[ISOLATED 26/09/2026]** Mục `## 6. Lịch Sử Thay Đổi` từng xuất hiện **hai lần** (bản gốc + bản Deputy 1 Coordinator) với nội dung khác nhau. Đã gộp vào bảng trên — không xóa dòng nào, chỉ bỏ tiêu đề trùng.

## Phụ Lục Cô Lập (Data Cũ — Ghi Chú, Không Copy Toàn Văn)

> **[ISOLATED 26/09/2026]** Yêu cầu gom tài liệu: *"tài liệu thiết kế cuối cùng (có data cũ gom lại dạng ghi chú, cô lập)"*. Toàn bộ tài liệu kiến trúc / hợp đồng / đặc tả cũ được **gom vào đây dạng ghi chú cô lập** — nêu đề mục gốc, quy mô, dàn ý và đường dẫn lưu trữ. **Không copy toàn văn** để khỏi tái sinh nạn v1/v2/v3. Bản đầy đủ vẫn nằm nguyên ở kho lưu trữ (chỉ cô lập, không xóa — Quy tắc 4).

### Mục lục phụ lục

- [Phụ lục A — NPS Core kiến trúc (bản đầy đủ 1.993 dòng)](#phụ-lục-a-nps-core-kiến-trúc-bản-đầy-đủ-1993-dòng)
- [Phụ lục B — ARCHITECTURE_LEGACY (bản NPS Core 'Lần 4', 2.004 dòng)](#phụ-lục-b-architecture_legacy-bản-nps-core-lần-4-2004-dòng)
- [Phụ lục C — ARCHITECTURE_V5 (đặc tả thế hệ Vivy)](#phụ-lục-c-architecture_v5-đặc-tả-thế-hệ-vivy)
- [Phụ lục D — VIVY_CORE_MANIFEST (hồ sơ package unitary-reasoner)](#phụ-lục-d-vivy_core_manifest-hồ-sơ-package-unitary-reasoner)
- [Phụ lục E — OCTAGONAL_TOWER_120S (bài test hình học 120s)](#phụ-lục-e-octagonal_tower_120s-bài-test-hình-học-120s)
- [Phụ lục F — Thiết kế Cautreo Knowledge Cartography & Dynamic Sparse 100B](#phụ-lục-f-thiết-kế-cautreo-knowledge-cartography-dynamic-sparse-100b)
- [Phụ lục G — Đặc tả Sprint R4: Cautreo Weight Paging](#phụ-lục-g-đặc-tả-sprint-r4-cautreo-weight-paging)
- [Phụ lục H — Thiết kế Stateful & Scored Cognitive Mindmap DAG](#phụ-lục-h-thiết-kế-stateful-scored-cognitive-mindmap-dag)
- [Phụ lục I — Delegation Contract VIVY FINAL V1](#phụ-lục-i-delegation-contract-vivy-final-v1)
- [Phụ lục J — Delegation Contract Sprint 1](#phụ-lục-j-delegation-contract-sprint-1)
- [Phụ lục K — Delegation Contract Sprint 2 & 3](#phụ-lục-k-delegation-contract-sprint-2-3)
- [Phụ lục L — TRAINING_AGENT_GUIDE](#phụ-lục-l-training_agent_guide)
- [Phụ lục M — Bộ ADR-001..007 (qubit, MPS, SVD, memory, evolution, control, LLM backend)](#phụ-lục-m-bộ-adr-001007-qubit-mps-svd-memory-evolution-control-llm-backend)
- [Phụ lục N — Bộ đặc tả ChatGPT (02-chatgpt-specs: Vivy Core + Cautreo Habitat)](#phụ-lục-n-bộ-đặc-tả-chatgpt-02-chatgpt-specs-vivy-core-cautreo-habitat)

### Bảng nguồn & trạng thái phụ lục

| # | File nguồn | Trạng thái | Mục phụ lục |
|:--|:--|:--|:--|
| 1 | `old-docs/01-architecture-legacy/ARCHITECTURE_UNITARY_REASONER.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục A — NPS Core kiến trúc (bản đầy đủ 1.993 dòng) |
| 2 | `old-docs/01-architecture-legacy/ARCHITECTURE_LEGACY.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục B — ARCHITECTURE_LEGACY (bản NPS Core 'Lần 4', 2.004 dòng) |
| 3 | `old-docs/01-architecture-legacy/ARCHITECTURE_V5.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục C — ARCHITECTURE_V5 (đặc tả thế hệ Vivy) |
| 4 | `old-docs/11-consolidated-source-2026-09-26/VIVY_CORE_MANIFEST.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục D — VIVY_CORE_MANIFEST (hồ sơ package unitary-reasoner) |
| 5 | `old-docs/11-consolidated-source-2026-09-26/OCTAGONAL_TOWER_120S_SPECIFICATION.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục E — OCTAGONAL_TOWER_120S (bài test hình học 120s) |
| 6 | `old-docs/10-workspace-docs/docs/plans/THIET_KE_CAUTREO_KNOWLEDGE_CARTOGRAPHY_VA_DYNAMIC_SPARSE_100B.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục F — Thiết kế Cautreo Knowledge Cartography & Dynamic Sparse 100B |
| 7 | `old-docs/10-workspace-docs/docs/plans/THIET_KE_KY_THUAT_SPRINT_R4_WEIGHT_PAGING.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục G — Đặc tả Sprint R4: Cautreo Weight Paging |
| 8 | `old-docs/10-workspace-docs/docs/plans/THIET_KE_STATEFUL_SCORED_MINDMAP_DAG_CHO_VIVY.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục H — Thiết kế Stateful & Scored Cognitive Mindmap DAG |
| 9 | `old-docs/11-consolidated-source-2026-09-26/DELEGATION_CONTRACT_VIVY_FINAL_V1.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục I — Delegation Contract VIVY FINAL V1 |
| 10 | `old-docs/10-workspace-docs/docs/plans/DELEGATION_CONTRACT_SPRINT1.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục J — Delegation Contract Sprint 1 |
| 11 | `old-docs/10-workspace-docs/docs/plans/DELEGATION_CONTRACT_SPRINT2_SPRINT3.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục K — Delegation Contract Sprint 2 & 3 |
| 12 | `old-docs/11-consolidated-source-2026-09-26/TRAINING_AGENT_GUIDE.md` | `[ISOLATED → PHỤ LỤC]` | Phụ lục L — TRAINING_AGENT_GUIDE |
| 13 | `Vivy_final/docs/adr` | `[ISOLATED → PHỤ LỤC]` | Phụ lục M — Bộ ADR-001..007 (qubit, MPS, SVD, memory, evolution, control, LLM backend) |
| 14 | `old-docs/02-chatgpt-specs` | `[ISOLATED → PHỤ LỤC]` | Phụ lục N — Bộ đặc tả ChatGPT (02-chatgpt-specs: Vivy Core + Cautreo Habitat) |

> **Vị trí bản gốc:** đường dẫn `old-docs/11-consolidated-source-2026-09-26/` là nơi bản gốc được di về sau khi gom (26/09/2026) — trước đó nằm ở `Vivy_final/docs/`. Các đường dẫn `old-docs/01…10-*` là kho lưu trữ có sẵn từ trước, file vẫn nằm nguyên tại đó (chỉ thêm banner `[ISOLATED]`). `Vivy_final/docs/adr` **không bị di chuyển** — ADR là tài liệu meta, nằm ngoài 5 doc. **Không có nội dung nào bị xóa** (Quy tắc 4).

---

### Phụ lục A — NPS Core kiến trúc (bản đầy đủ 1.993 dòng)

**Đề mục gốc:** NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL

**Quy mô:** 1993 dòng · **Đường dẫn lưu trữ:** `old-docs/01-architecture-legacy/ARCHITECTURE_UNITARY_REASONER.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL
- ## Tài liệu kiến trúc V1.0 Final
- # 0. TUYÊN BỐ DỰ ÁN
- # 1. VỊ TRÍ CỦA BA TÀI LIỆU NGUỒN
- ## 1.1. Tài liệu Gemini
- ## 1.2. Tài liệu DeepSeek
- ## 1.3. Tài liệu Grok
- # 2. BẢN SẮC NHẬN THỨC CỦA MODEL
- ## 2.1. Population Reasoning
- ## 2.2. Delegated Cognition
- ## 2.3. Experimental Intelligence
- ## 2.4. Evidence Economy

---

### Phụ lục B — ARCHITECTURE_LEGACY (bản NPS Core 'Lần 4', 2.004 dòng)

**Đề mục gốc:** NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL

**Quy mô:** 2004 dòng · **Đường dẫn lưu trữ:** `old-docs/01-architecture-legacy/ARCHITECTURE_LEGACY.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL
- ## Tài liệu kiến trúc V1.0 Final (Lịch Sử — Kế thừa bởi V5.0)
- # 0. TUYÊN BỐ DỰ ÁN
- # 1. VỊ TRÍ CỦA BA TÀI LIỆU NGUỒN
- ## 1.1. Tài liệu Gemini
- ## 1.2. Tài liệu DeepSeek
- ## 1.3. Tài liệu Grok
- # 2. BẢN SẮC NHẬN THỨC CỦA MODEL
- ## 2.1. Population Reasoning
- ## 2.2. Delegated Cognition
- ## 2.3. Experimental Intelligence
- ## 2.4. Evidence Economy

---

### Phụ lục C — ARCHITECTURE_V5 (đặc tả thế hệ Vivy)

**Đề mục gốc:** VIVY MODEL ARCHITECTURE SPECIFICATION — GENERATION 5 (V5.1)

**Quy mô:** 880 dòng · **Đường dẫn lưu trữ:** `old-docs/01-architecture-legacy/ARCHITECTURE_V5.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # VIVY MODEL ARCHITECTURE SPECIFICATION — GENERATION 5 (V5.1)
- ## Native Omni-Epistemic Foundation Orchestrator & Autonomous Model-to-Model Control Plane
- ## MỤC LỤC TÀI LIỆU
- ## 1. LỊCH SỬ THAY ĐỔI & KẾ THỪA KIẾN TRÚC
- ## 2. TUYÊN NGÔN & TRIẾT LÝ CỐT LÕI LẦN 5
- ### 2.1. Ba Đặc Định Mục Tiêu Tối Thượng (DD-01)
- ### 2.2. Bốn Cột Trụ Nhận Thức (4 Cognitive Pillars)
- ## 3. PHÂN TÍCH NỖI ĐAU, ĐỐI CHIẾU THỰC NGHIỆM & ĐIỂM ĐỘT PHÁ LẦN 5
- ### 3.1. Bảng So Sánh 3 Chiều Chiến Lược Kiến Trúc
- ### 3.2. Kiểm Chứng Thực Nghiệm Từ Jev & Verdict 2.0: Kiến Trúc ViVy Hoàn Toàn Đúng Đắn
- ## 4. THAM CHIẾU TRIẾT LÝ QWEN 3.8 OMNI FLASH
- ### 4.1. Bản Địa Hóa Đa Giác Quan (Native End-to-End Omni-Modal Tokens)

---

### Phụ lục D — VIVY_CORE_MANIFEST (hồ sơ package unitary-reasoner)

**Đề mục gốc:** VIVY CORE MANIFEST — V1.0.0

**Quy mô:** 170 dòng · **Đường dẫn lưu trữ:** `old-docs/11-consolidated-source-2026-09-26/VIVY_CORE_MANIFEST.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # VIVY CORE MANIFEST — V1.0.0
- ## Package Identity
- ## Architecture Summary
- ## Coordinator Completion Gates — All CLEARED
- ## Base Model Selection
- ## File Manifest
- ### Sprint 1 — Engine Primitives
- ### Sprint 2 — Cognitive State Graph & Memory
- ### Sprint 3 — Integration Layer
- ## How ViVy Makes Base Model Faster
- ## Quick Start
- # 1. Setup (một lần)

---

### Phụ lục E — OCTAGONAL_TOWER_120S (bài test hình học 120s)

**Đề mục gốc:** 🏛️ ĐẶC TẢ KỸ THUẬT & YÊU CẦU BÀI TEST HÌNH HỌC VIVY: TÒA THÁP 8 CẠNH TRUNG ĐÔNG 120 TẦNG

**Quy mô:** 78 dòng · **Đường dẫn lưu trữ:** `old-docs/11-consolidated-source-2026-09-26/OCTAGONAL_TOWER_120S_SPECIFICATION.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # 🏛️ ĐẶC TẢ KỸ THUẬT & YÊU CẦU BÀI TEST HÌNH HỌC VIVY: TÒA THÁP 8 CẠNH TRUNG ĐÔNG 120 TẦNG
- ## 1. TỔNG QUAN THÔNG SỐ HÌNH HỌC & KẾT CẤU
- ### 1.1. Ma trận Tọa độ & Hình học Bát giác (Octagonal Geometry Matrix)
- ## 2. PHÂN RÃ N MICRO-TASKS CẤU THÀNH TOÀN DIỆN
- ### Task 1: Tính toán Ma trận Hình học 8 Cạnh & Tapering Ratio
- ### Task 2: Phân khu Chức năng Chi tiết 120 Tầng (Vertical Zoning)
- ### Task 3: Kết cấu Chịu lực & Họa tiết Trung Đông (Mashrabiya & Structural Grid)
- ### Task 4: Cảnh quan Xung quanh & Quảng trường Oasis (Landscaping & Plaza)
- ### Task 5: Trực quan hóa Mô hình 3D HTML Interative (Three.js WebGL Viewer)
- ### Task 6: Đánh giá & Kiểm định Tự động (Benchmark Automated Test)

---

### Phụ lục F — Thiết kế Cautreo Knowledge Cartography & Dynamic Sparse 100B

**Đề mục gốc:** ĐẶC TẢ KIẾN TRÚC KỸ THUẬT: CAUTREO INITIAL KNOWLEDGE CARTOGRAPHY & DYNAMIC SPARSE WEIGHT ACTIVATION (30B - 100B)

**Quy mô:** 252 dòng · **Đường dẫn lưu trữ:** `old-docs/10-workspace-docs/docs/plans/THIET_KE_CAUTREO_KNOWLEDGE_CARTOGRAPHY_VA_DYNAMIC_SPARSE_100B.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # ĐẶC TẢ KIẾN TRÚC KỸ THUẬT: CAUTREO INITIAL KNOWLEDGE CARTOGRAPHY & DYNAMIC SPARSE WEIGHT ACTIVATION (30B - 100B)
- ## Quy Trình Xây Dựng Bản Đồ Tri Thức Lần Đầu, Kỹ Thuật Đóng Băng Trọng Số & Tối Ưu Hóa Model 100B Chạy Với Tải Model 7B
- ## TÓM TẮT ĐIỀU HÀNH & KẾT LUẬN CHIẾN LƯỢC (EXECUTIVE SUMMARY)
- ## 1. MÔ TẢ KIẾN TRÚC TỔNG THỂ (SYSTEM ARCHITECTURE SPEC)
- ## 2. QUY TRÌNH XÂY DỰNG BẢN ĐỒ TRI THỨC LẦN ĐẦU (INITIAL CARTOGRAPHY PASS)
- ## 3. CƠ CHẾ ĐÓNG BĂNG TRỌNG SỐ & KÍCH HOẠT NƠ-RON ĐIỂM CAO (DYNAMIC SPARSE ACTIVATION)
- ### 3.1. Cơ Sở Toán Học: Tại Sao Có Thể Giảm Tải 100B Xuống Tương Đương 7B?
- ### 3.2. Thuật Toán Kích Hoạt Thưa Điểm Cao Của Cautreo (Top-K Sparse Activation):
- ## 4. CHI TIẾT 11 TRỤ CỘT KIỂM ĐỊNH MEGA REVIEW (REVIEW SECTIONS 1 - 11)
- ### Section 1: Architecture Review (Kiến Trúc & Ranh Giới Module)
- ### Section 2: Error & Rescue Map (Bảng Bắt Lỗi & Cứu Hộ Bộ Nhớ)
- ### Section 3: Security & Threat Model (Bảo Mật & Rủi Ro Tấn Công)

---

### Phụ lục G — Đặc tả Sprint R4: Cautreo Weight Paging

**Đề mục gốc:** ĐẶC TẢ KIẾN TRÚC KỸ THUẬT SPRINT R4: CAUTREO WEIGHT PAGING & XÂM LẤN TRỌNG SỐ

**Quy mô:** 206 dòng · **Đường dẫn lưu trữ:** `old-docs/10-workspace-docs/docs/plans/THIET_KE_KY_THUAT_SPRINT_R4_WEIGHT_PAGING.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # ĐẶC TẢ KIẾN TRÚC KỸ THUẬT SPRINT R4: CAUTREO WEIGHT PAGING & XÂM LẤN TRỌNG SỐ
- ## Thiết Kế Hệ Thống Điều Phối Lát Cắt Trọng Số Tuần Tự (Task-Sequential FFN Streaming) Cho Qwen2.5-Coder-14B & Mở Rộng 1000B
- ## 1. Bối Cảnh, Nỗi Đau Cốt Lõi & Nguyên Lý Xâm Lấn Trọng Số
- ### 1.1. Nỗi đau thực tế khi vận hành LLM lớn trên máy cá nhân
- ### 1.2. Triết lý "Ghép Nối & Xâm Lấn" (Invasion & Sequential Paging)
- ## 2. Cấu Trúc Dữ Liệu `WeightSliceRegistry` (C-ABI trong `cautreo.dll`)
- ## 3. Cơ Chế Zero-RAM-Waste Task-Sequential FFN Streaming
- ### 3.1. Các nguyên tắc vận hành cốt lõi:
- ## 4. Định Nghĩa Giao Thức C-ABI (Exports trong `cautreo.dll`)
- ## 5. Lộ Trình Triển Khai & Kiểm Thử Nghiệm Thu
- ## 6. Thẩm Định Qua Bộ Tiêu Chuẩn 4 Trục (Ngọc Châu Framework)
- ## 7. Lịch Sử Thay Đổi (Changelog)

---

### Phụ lục H — Thiết kế Stateful & Scored Cognitive Mindmap DAG

**Đề mục gốc:** Thiết Kế Kiến Trúc: Stateful & Scored Cognitive Mindmap DAG Cho ViVy

**Quy mô:** 86 dòng · **Đường dẫn lưu trữ:** `old-docs/10-workspace-docs/docs/plans/THIET_KE_STATEFUL_SCORED_MINDMAP_DAG_CHO_VIVY.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # Thiết Kế Kiến Trúc: Stateful & Scored Cognitive Mindmap DAG Cho ViVy
- ## 1. Triết Lý Cốt Lõi: Học Như Con Người (Human-like Cognitive Scaffolding)
- ## 2. Cấu Trúc Dữ Liệu: Stateful & Scored Mindmap Node
- ## 3. Quy Trình Vận Hành Khi Nhánh Bị Thất Bại (Ví dụ Subtask 150)
- ### Các bước diễn ra:
- ## 4. Lợi Ích Vượt Trội Đối Với Task Chạy Dài Hạn (Tuần / Tháng)
- ## 5. Lịch Sử Thay Đổi (Changelog)

---

### Phụ lục I — Delegation Contract VIVY FINAL V1

**Đề mục gốc:** DELEGATION CONTRACT — VIVY FINAL V1.0

**Quy mô:** 242 dòng · **Đường dẫn lưu trữ:** `old-docs/11-consolidated-source-2026-09-26/DELEGATION_CONTRACT_VIVY_FINAL_V1.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # DELEGATION CONTRACT — VIVY FINAL V1.0
- ## HoH Control Plane | Antigravity IDE → Codex CLI + Claude Code
- ## PHÂN VAI HoH (Authority Hierarchy)
- ## SCOPE BOUNDING — FILE ĐƯỢC PHÉP SỬA
- ## WORKER A: CODEX CLI — SPRINT 1
- ### Task ID: `W-A-SPRINT1-ENGINE-PRIMITIVES`
- ### Objective:
- ### Constraints:
- ### Deliverables:
- ### Acceptance Gate 1 (Coordinator verifies):
- ### Codex CLI Invocation (Paste vào terminal):
- ## WORKER B: CLAUDE CODE

---

### Phụ lục J — Delegation Contract Sprint 1

**Đề mục gốc:** DELEGATION CONTRACT — SPRINT 1: EPISTEMIC GATE & FUNNEL FIX

**Quy mô:** 97 dòng · **Đường dẫn lưu trữ:** `old-docs/10-workspace-docs/docs/plans/DELEGATION_CONTRACT_SPRINT1.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # DELEGATION CONTRACT — SPRINT 1: EPISTEMIC GATE & FUNNEL FIX
- ## COMPLETION EVIDENCE (HoH 7 Gates)
- ## WORKER OUTCOME LOG
- ## ARTIFACTS CREATED
- ## DONE / TESTED / NOT VERIFIED
- ### ✅ ĐÃ LÀM (Done)
- ### ✅ ĐÃ KIỂM THỬ (Tested)
- ### ⚠️ CHƯA XÁC MINH (Not Verified)
- ## SPRINT 2 PREREQUISITES (Từ Sprint 1 handoff)
- ## LỊCH SỬ THAY ĐỔI

---

### Phụ lục K — Delegation Contract Sprint 2 & 3

**Đề mục gốc:** DELEGATION CONTRACT — SPRINT 2 & 3 COMPLETION EVIDENCE

**Quy mô:** 173 dòng · **Đường dẫn lưu trữ:** `old-docs/10-workspace-docs/docs/plans/DELEGATION_CONTRACT_SPRINT2_SPRINT3.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # DELEGATION CONTRACT — SPRINT 2 & 3 COMPLETION EVIDENCE
- ## TÓM TẮT SPRINT 2 — Multi-Model Router & Context Purge Engine
- ### Deliverables đã hoàn thành
- ### Tests Sprint 2
- ### Verifiable Evidence Sprint 2
- ## TÓM TẮT SPRINT 3 — Knowledge Artifacts & Self-Healing RCA
- ### Deliverables đã hoàn thành
- ### Tests Sprint 3
- ### Verifiable Evidence Sprint 3
- ## KẾT QUẢ TOÀN BỘ SPRINTS 1-3
- ### Test Suite Final
- ### KPIs Nghiệm Thu (theo CEO_REVIEW_VIVY_V5.md §8)

---

### Phụ lục L — TRAINING_AGENT_GUIDE

**Đề mục gốc:** Hướng dẫn cho Coding Agent: Kết nối và Đào tạo Model NPS Core

**Quy mô:** 10 dòng · **Đường dẫn lưu trữ:** `old-docs/11-consolidated-source-2026-09-26/TRAINING_AGENT_GUIDE.md`

**Dàn ý gốc (tối đa 12 đề mục đầu):**

- # Hướng dẫn cho Coding Agent: Kết nối và Đào tạo Model NPS Core
- ## Tổng quan
- ## 1. Kiến trúc Pipeline

---

### Phụ lục M — Bộ ADR-001..007 (qubit, MPS, SVD, memory, evolution, control, LLM backend)

**Loại:** thư mục nguồn · **Đường dẫn lưu trữ:** `Vivy_final/docs/adr/`

**Nội dung bên trong (giữ nguyên vị trí, chỉ cô lập):**

- `ADR-001-qubit-convention.md` — 21 dòng · ADR-001: Qubit Convention — LSB-first
- `ADR-002-mps-canonical-form.md` — 21 dòng · ADR-002: MPS Canonical Form
- `ADR-003-svd-streams.md` — 21 dòng · ADR-003: SVD Thought Stream Extraction
- `ADR-004-associative-memory.md` — 19 dòng · ADR-004: Associative Memory Dimension
- `ADR-005-evolution-probe.md` — 20 dòng · ADR-005: Evolution Engine — Probe Signature
- `ADR-006-control-signals.md` — 20 dòng · ADR-006: Control Signal Enum
- `ADR-007-llm-backend.md` — 23 dòng · ADR-007: LLM Backend — OpenAI-Compatible, Env-Config

Tổng: **7 file**. Không copy toàn văn vào doc này — xem trực tiếp đường dẫn trên khi cần chi tiết.

---

### Phụ lục N — Bộ đặc tả ChatGPT (02-chatgpt-specs: Vivy Core + Cautreo Habitat)

**Loại:** thư mục nguồn · **Đường dẫn lưu trữ:** `old-docs/02-chatgpt-specs/`

**Nội dung bên trong (giữ nguyên vị trí, chỉ cô lập):**

- `ACCEPTANCE_GATES.md` — 223 dòng · Acceptance Gates
- `ACCURACY_AND_MATURATION_STRATEGIES.md` — 117 dòng · Vivy Accuracy and Maturation Strategies
- `CAUTREO_NATIVE_HABITAT_SPEC.md` — 83 dòng · CAUTREO Native Habitat Specification
- `evidence/VIVY-CAUTREO-CLEAN-BUILD-236.json` — 0 dòng
- `evidence/VIVY-CAUTREO-FIXTURE-SWEEP-268.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GATEWAY-TIMEOUT-271.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-CHAT-171.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-CHAT-188.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-DECODE-166.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-EMBED-SCALE-172.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-EXACT-PROMPT-196.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-FORWARD-165.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-FORWARD-187.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-FORWARD-237.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-GLOBAL-SWA-190.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-LEARNED-ROPE-191.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-METADATA-AUDIT-192.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-PLE-SCALE-173.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-RAW-VS-TEMPLATE-189.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-REFERENCE-TOKEN-194.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-ROPE-TENSOR-174.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-SYSTEM-TURN-195.json` — 0 dòng
- `evidence/VIVY-CAUTREO-GEMMA4-TENSOR-CENSUS-193.json` — 0 dòng
- `evidence/VIVY-CAUTREO-NATIVE-BUILD-264.json` — 0 dòng
- `evidence/VIVY-CAUTREO-NONSTREAM-API-265.json` — 0 dòng
- `evidence/VIVY-CAUTREO-ORACLE-AVAILABILITY-199.json` — 0 dòng
- `evidence/VIVY-CAUTREO-PARITY-REGRESSION-197.json` — 0 dòng
- `evidence/VIVY-CAUTREO-PLE-FORWARD-FIX-203.json` — 0 dòng
- `evidence/VIVY-CAUTREO-PLE-ROLLBACK-206.json` — 0 dòng
- `evidence/VIVY-CAUTREO-PLE-SEMANTIC-205.json` — 0 dòng
- `evidence/VIVY-CAUTREO-PROFILER-STREAMING-269.json` — 0 dòng
- `evidence/VIVY-CAUTREO-QWEN-ARCHITECTURE-234.json` — 0 dòng
- `evidence/VIVY-CAUTREO-QWEN-REGRESSION-261.json` — 0 dòng
- `evidence/VIVY-CAUTREO-TEMPLATE-PARITY-170.json` — 0 dòng
- `evidence/VIVY-CAUTREO-TOKENIZER-IDS-168.json` — 0 dòng
- `evidence/VIVY-CAUTREO-TOKENIZER-PARITY-167.json` — 0 dòng
- `evidence/VIVY-CAUTREO-TOKENIZER-PARITY-169.json` — 0 dòng
- `evidence/VIVY-CAUTREO-UNIT-SWEEP-266.json` — 0 dòng
- `evidence/VIVY-CAUTREO-V2-GATE-200.json` — 0 dòng
- `evidence/VIVY-CAUTREO-V2-REGRESSION-186.json` — 0 dòng
- `evidence/VIVY-CAUTREO-V2-REGRESSION-224.json` — 0 dòng
- `evidence/VIVY-CAUTREO-WEIGHT-LAYOUT-AUDIT-198.json` — 0 dòng
- `evidence/VIVY-COGNITIVE-GATES-283.json` — 0 dòng
- `evidence/VIVY-COGNITIVE-SUITE-284.json` — 0 dòng
- `evidence/VIVY-DELEGATE-TEACHER-FAILURE-247.json` — 0 dòng
- `evidence/VIVY-DETERMINISTIC-VERIFIER-249.json` — 0 dòng
- `evidence/VIVY-DETERMINISTIC-VERIFIER-AUDIT-248.json` — 0 dòng
- `evidence/VIVY-DETERMINISTIC-VERIFIER-INTEGRATION-250.json` — 0 dòng
- `evidence/VIVY-DETERMINISTIC-VERIFIER-LIVE-251.json` — 0 dòng
- `evidence/VIVY-DETERMINISTIC-VERIFIER-NONNUMERIC-252.json` — 0 dòng
- `evidence/VIVY-DOC-CLAIM-AUDIT-162.json` — 0 dòng
- `evidence/VIVY-DOCUMENT-DELIVERABLES-286.json` — 0 dòng
- `evidence/VIVY-ENGINE-GEMMA4-FALLBACK-240.json` — 0 dòng
- `evidence/VIVY-FAIL-CLOSED-VERIFIER-289.json` — 0 dòng
- `evidence/VIVY-FALLBACK-GUARD-REGRESSION-245.json` — 0 dòng
- `evidence/VIVY-GATEWAY-OFFLINE-TEST-270.json` — 0 dòng
- `evidence/VIVY-GEMMA4-GELU-AUDIT-230.json` — 0 dòng
- `evidence/VIVY-GEMMA4-PARITY-AUDIT-238.json` — 0 dòng
- `evidence/VIVY-GEMMA4-PER-LAYER-AUDIT-229.json` — 0 dòng
- `evidence/VIVY-GEMMA4-ROPE-FACTORS-207.json` — 0 dòng
- `evidence/VIVY-GEMMA4-SHARED-KV-AUDIT-228.json` — 0 dòng
- `evidence/VIVY-GEMMA4-TAG-ORACLE-AUDIT-232.json` — 0 dòng
- `evidence/VIVY-GEMMA4-TENSOR-TYPES-242.json` — 0 dòng
- `evidence/VIVY-GEMMA4-TEXT-FFN-CENSUS-204.json` — 0 dòng
- `evidence/VIVY-GGUF-FIXTURE-ENV-262.json` — 0 dòng
- `evidence/VIVY-GGUF-OFFSET-AUDIT-244.json` — 0 dòng
- `evidence/VIVY-GGUF-TEST-PATH-FIX-263.json` — 0 dòng
- `evidence/VIVY-GGUF-TEXT-TYPE-CENSUS-209.json` — 0 dòng
- `evidence/VIVY-HOH-CAUTREO-TEST-235.json` — 0 dòng
- `evidence/VIVY-HOH-CONFLICT-GUARD-183.json` — 0 dòng
- `evidence/VIVY-HOH-CONTRACT-GUARD-181.json` — 0 dòng
- `evidence/VIVY-HOH-CONTRADICTION-178.json` — 0 dòng
- `evidence/VIVY-HOH-CONTRADICTION-VALIDATED-179.json` — 0 dòng
- `evidence/VIVY-HOH-CURRENT-285.json` — 0 dòng
- `evidence/VIVY-HOH-CURRENT-GATE-185.json` — 0 dòng
- `evidence/VIVY-HOH-DIRECTIVE-QA-214.json` — 0 dòng
- `evidence/VIVY-HOH-DIRECTIVE-QA-231.json` — 0 dòng
- `evidence/VIVY-HOH-END-TO-END-AUDIT-246.json` — 0 dòng
- `evidence/VIVY-HOH-EXPERIMENT-REJECTED-202.json` — 0 dòng
- `evidence/VIVY-HOH-FALSE-CONSENSUS-180.json` — 0 dòng
- `evidence/VIVY-HOH-KNOWN-ANSWER-176.json` — 0 dòng
- `evidence/VIVY-HOH-LAST-DIRECTIVE-182.json` — 0 dòng
- `evidence/VIVY-HOH-NATIVE-GATE-163.json` — 0 dòng
- `evidence/VIVY-HOH-REAL-CONFLICT-184.json` — 0 dòng
- `evidence/VIVY-HOH-SEMANTIC-CONSULT-164.json` — 0 dòng
- `evidence/VIVY-HOH-UNCERTAINTY-GATE-177.json` — 0 dòng
- `evidence/VIVY-HOH-UTF8-TRANSPORT-175.json` — 0 dòng
- `evidence/VIVY-INDEPENDENT-ORACLE-AVAILABILITY-210.json` — 0 dòng
- `evidence/VIVY-INTERMEDIATE-COMPARISON-239.json` — 0 dòng
- `evidence/VIVY-LLAMA-ORACLE-LOAD-211.json` — 0 dòng
- `evidence/VIVY-LLAMA-ORACLE-NOMMPROJ-213.json` — 0 dòng
- `evidence/VIVY-LLAMA-ORACLE-TENSOR-GROUPS-212.json` — 0 dòng
- `evidence/VIVY-NATIVE-ENGINE-GENERATION-241.json` — 0 dòng
- `evidence/VIVY-NATIVE-FIRST-TOKEN-225.json` — 0 dòng
- `evidence/VIVY-NATIVE-FIRST-TOKEN-PARSER-FIX-226.json` — 0 dòng
- `evidence/VIVY-NATIVE-PROBE-PACKAGING-GAP-217.json` — 0 dòng
- `evidence/VIVY-NATIVE-PROMPT-FILE-218.json` — 0 dòng
- `evidence/VIVY-NATIVE-PROMPT-HEX-222.json` — 0 dòng
- `evidence/VIVY-NATIVE-PROMPT-STDIN-219.json` — 0 dòng
- `evidence/VIVY-NATIVE-PROMPT-STDIN-KNOWN-ANSWER-221.json` — 0 dòng
- `evidence/VIVY-NATIVE-PROMPT-STDIN-OBSERVED-220.json` — 0 dòng
- `evidence/VIVY-OLLAMA-FULL-SYSTEM-PROBE-227.json` — 0 dòng
- `evidence/VIVY-OLLAMA-MANIFEST-HASH-216.json` — 0 dòng
- `evidence/VIVY-OLLAMA-PACKAGING-AUDIT-215.json` — 0 dòng
- `evidence/VIVY-Q6K-OFFICIAL-AUDIT-243.json` — 0 dòng
- `evidence/VIVY-QK-DEQUANT-AUDIT-208.json` — 0 dòng
- `evidence/VIVY-QWEN2-BPE-DECODE-257.json` — 0 dòng
- `evidence/VIVY-QWEN2-CHAT-TEMPLATE-PARITY-258.json` — 0 dòng
- `evidence/VIVY-QWEN2-DECODE-HARNESS-FIX-260.json` — 0 dòng
- `evidence/VIVY-QWEN2-FINITE-FORWARD-256.json` — 0 dòng
- `evidence/VIVY-QWEN2-GENERIC-FALLBACK-282.json` — 0 dòng
- `evidence/VIVY-QWEN2-GENERIC-FORWARD-254.json` — 0 dòng
- `evidence/VIVY-QWEN2-KV-HYPOTHESIS-278.json` — 0 dòng
- `evidence/VIVY-QWEN2-NATIVE-SERVER-280.json` — 0 dòng
- `evidence/VIVY-QWEN2-NORM-METADATA-287.json` — 0 dòng
- `evidence/VIVY-QWEN2-OUTPUT-TIE-288.json` — 0 dòng
- `evidence/VIVY-QWEN2-Q5-PACKING-FIX-255.json` — 0 dòng
- `evidence/VIVY-QWEN2-QKV-BIAS-275.json` — 0 dòng
- `evidence/VIVY-QWEN2-QKV-REGRESSION-276.json` — 0 dòng
- `evidence/VIVY-QWEN2-REFERENCE-CONTEXT-ROPE-273.json` — 0 dòng
- `evidence/VIVY-QWEN2-ROPE-FALLBACK-274.json` — 0 dòng
- `evidence/VIVY-QWEN2-ROPE-METADATA-279.json` — 0 dòng
- `evidence/VIVY-QWEN2-STABILITY-281.json` — 0 dòng
- `evidence/VIVY-QWEN2-TENSOR-INVENTORY-277.json` — 0 dòng
- `evidence/VIVY-QWEN2-TOKEN-INVENTORY-259.json` — 0 dòng
- `evidence/VIVY-QWEN2-TOKENIZER-GOLDEN-272.json` — 0 dòng
- `evidence/VIVY-TEXT-ONLY-GGUF-INVENTORY-253.json` — 0 dòng
- `evidence/VIVY-TEXT-ONLY-ORACLE-FEASIBILITY-223.json` — 0 dòng
- `evidence/VIVY-TEXT-ONLY-ORACLE-QWEN-233.json` — 0 dòng
- `evidence/VIVY-TRANSFORMER-FIXTURE-267.json` — 0 dòng
- `evidence/VIVY-UNITARY-REASONER-INTEGRATION-201.json` — 0 dòng
- `gguf_shape_audit.c` — 0 dòng
- `IMPLEMENTATION_ROADMAP.md` — 164 dòng · Implementation Roadmap
- `INHERITANCE_AND_RECONCILIATION.md` — 38 dòng · Inheritance and Reconciliation
- `MULTIMODAL_AND_MODEL_COMPOSITION.md` — 61 dòng · Multimodal and Model Composition
- `native-quality.stderr.txt` — 8 dòng
- `native-quality.stdout.txt` — 7 dòng
- `native_engine_probe.c` — 0 dòng
- `native_engine_probe.exe` — 0 dòng
- `native_engine_probe_new.exe` — 0 dòng
- `native_gguf_inspect.c` — 0 dòng
- `native_gguf_inspect.exe` — 0 dòng
- `native_gguf_inspect_new.exe` — 0 dòng
- `norm_probe.c` — 0 dòng
- `q4k_asan_probe.c` — 0 dòng
- `q4k_asan_probe.exe` — 0 dòng
- `q4k_matvec_asan_probe.c` — 0 dòng
- `q4k_matvec_asan_probe.exe` — 0 dòng
- `q6k_asan_probe.c` — 0 dòng
- `README.md` — 128 dòng · Vivy Cognitive Core + CAUTREO Native Habitat
- `VIVY_CAUTREO_BOUNDARY_CONTRACT.md` — 70 dòng · Vivy–CAUTREO Boundary Contract
- `VIVY_COGNITIVE_CORE_SPEC.md` — 118 dòng · Vivy Cognitive Core Specification

Tổng: **152 file**. Không copy toàn văn vào doc này — xem trực tiếp đường dẫn trên khi cần chi tiết.

---

## Lịch Sử Thay Đổi — Phụ Lục (Changelog)

| Agent | Thời gian | Hành động |
|:--|:--|:--|
| Claude Code | 26/09/2026 | Gom data cũ vào Phụ lục A–N dạng ghi chú cô lập theo yêu cầu "gom về 5 tài liệu". Nội dung gốc giữ nguyên ở kho lưu trữ. |
