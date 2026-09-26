# ViVy Final V1.0 — Unified Autonomous Cognitive Architecture

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

---

---

## Lịch Sử Thay Đổi (Changelog)

| Phiên bản | Thời gian | Agent / Tác giả | Nội dung thay đổi & Lý do |
|:---|:---|:---|:---|
| 1.0.0 | 21/09/2026 17:00 ICT | Antigravity IDE | Khởi tạo bản phân phối hợp nhất ViVy Final V1.0 & Cautreo Engine. |
| 1.2.0 | 23/09/2026 09:25 ICT | Antigravity IDE | Tích hợp Qwen2-VL-72B-Instruct (44.16GB) & Cautreo Cartography Atlas (`qwen2-vl-72b.catlas`). |
| 1.3.0 | 23/09/2026 11:30 ICT | Antigravity IDE | Khắc phục toàn diện theo Codex Independent Audit: 1) Hợp nhất SSOT từ `unitary-reasoner` sang `Vivy_final/core`; 2) Chuẩn hóa topology `MODEL_ROOT = D:\models`, giải quyết triệt để lỗi verify_all (17/17 PASS); 3) Khẳng định Gemma 4 E4B (Port 8080) là Active Cognitive Soul; 4) Định vị chính xác Qwen2-VL-72B là `DOWNLOADED_ON_DISK / PAGING_LEDGER_VERIFIED`; 5) Chạy thành công HoH known-answer live test. |
| 1.4.0 | 25/09/2026 | Claude Code (Plan 1+2 + Wave 1) | Đồng bộ code từ `vivyChatGPT/training/` vào `core/integration/`: Plan 1 (verify_receipt, sandbox_capture, check_known_limits, run_w2_live, evidence_packet_template), Plan 2 (native_parity_decision, learned_router), Wave 1 (cautreo_weight_map, cautreo_session_log). Bổ sung discussion record + plan-tune vào `docs/plans/`. |
| 1.5.0 | 25/09/2026 | Claude Code (Wave 2A+2B) | Đồng bộ Wave 2 vào `core/integration/`: Weight Pager Interface (`weight_pager.py` — partial load, stream, memory usage) + Cross-Model Adapter (`cross_model_adapter.py` — couple, route, combine_outputs, callback_weights). 41 tests mới. |
| 1.6.0 | 25/09/2026 | Claude Code (Wave 3A) | Đồng bộ Wave 3: Scored Mindmap DAG (`scored_mindmap_dag.py` — plan, score_path, reroute, cycle detection). TD-6: planning + QC. 32 tests mới. |
| 1.7.0 | 25/09/2026 | Claude Code (Wave 4A) | Đồng bộ Wave 4: Model Upgrade Protocol (`model_upgrade_protocol.py` — readiness_check, migrate, inherit_weights, SHA256 chain receipts). TD-8: progressive scaling. 28 tests mới. |
| 2.0.0 | 26/09/2026 | Claude Code (Reorg Vivy+Cautreo — D2/D3/D4) | **Chuẩn hóa repo GitHub độc lập.** Union-merge runtime 3 nguồn (`unitary-reasoner` + `Vivy_final/core` + `vivyChatGPT/training`) → `vivy/`. Cây trụ mới: `vivy`·`cautreo`·`engine`·`host`·`ui`·`docs`·`models`·`scripts`·`internal`. Fix search-path `cautreo_binding.py` cho layout mới (bổ sung path repo-relative; giữ path cũ dạng fallback `[ISOLATED]`). Kho checkpoint 6.40 GB → `internal/` (gitignored) + hướng dẫn số liệu `docs/CHECKPOINTS.md`. Data map đầy đủ: `docs/DATA_MAP_2026-09-26.md`. Health stack: tests 676+17 (baseline 693 khớp) + 730+3 training; mypy 7 thư mục `Success: 64 source files`; ruff scope `All checks passed`. |
| 2.1.0 | 26/09/2026 | Claude Code (Path Sync — đổi tên thư mục) | **Đồng bộ đường dẫn sau khi đổi tên thư mục `Vivy final` → `Vivy_final`** (bỏ dấu cách để trỏ từ terminal). 72 occurrences / 27 file trong repo. Sửa thêm path lệch layout cũ mà rename không tự hết: `Vivy_final/core/integration/…` → `vivy/integration/…`, `Vivy_final/core/memory/…` → `vivy/memory/…`, `Vivy_final/engine/include/…` → `engine/include/…`; `run_vivy_benchmark_suite.py` & `start_vivy_qwen_coder.ps1` (bản `vivy/scripts/`) bị nhân đôi segment `Vivy_final/` do `WORKSPACE_ROOT` đã là repo root; `verify_vivy_cautreo_readiness.py` (`vivy/scripts/`) `sys.path` `core/` → `vivy/`. Đối chiếu `models/model_manifest.json` sửa vị trí trọng số (`MODEL_ROOT = D:\models`) và trạng thái baseline trong `models/baselines/README.md` + `docs/RUNBOOK.md`. Đường dẫn/layout cũ giữ ghi chú `[ISOLATED]`, không xóa. |
| 2.2.0 | 26/09/2026 | Claude Code (Gom tài liệu + gỡ gguf/runtime) | **Gom tài liệu về 5 doc chuẩn + dọn trùng lặp.** (a) **Xóa 2 runtime** `scripts/start_vivy_qwen_coder.ps1` + `vivy/scripts/start_vivy_qwen_coder.ps1` — trọng số `qwen2.5-coder-7b-instruct-q4_k_m.gguf` không tồn tại. (b) **Gỡ tham chiếu sống** của 3 gguf không còn trên đĩa (`qwen2.5-coder-7b`, `vivy2`, `qwen3.8-27b`) trong `verify_vivy_cautreo_readiness.py`, `models/baselines/*`, `docs/VIVY_CORE_MANIFEST.md`; hồ sơ giữ dạng `[ISOLATED]` trong `models/baselines/README.md`. (c) **Giữ script giả định** làm tài liệu so sánh (qwen27b ×2, `run_cartography_batch.py`, `run_vivy_benchmark_suite.py`, `verify_vivy_cautreo_readiness.py`) — gắn `[ISOLATED]` nêu giả định layout cũ. (d) **Dọn trùng lặp:** 28 file 0 byte `BAO_CAO_THUC_NGHIEM_PHUONG_AN_A (n).md`, `run_python.bat` (trùng byte `py_runner.bat`) → redirect, bảng trọng số lặp ở `README.md` §3 ↔ `ARCHITECTURE_FINAL.md` §3.3 ↔ `models/baselines/README.md` §2 → gom 1 nguồn, 2 mục changelog trùng trong `ARCHITECTURE_FINAL.md` §6. (e) **Gom tài liệu về 5 doc** (xem mục Tài Liệu Tham Chiếu): 18 file rời `docs/` → `old-docs/11-consolidated-source-2026-09-26/` + banner `[ISOLATED]`; `docs/ARCHITECTURE.md` → redirect stub (giữ vì ~25 tham chiếu); Phụ lục A–N data cũ vào `ARCHITECTURE_FINAL.md`. |

---

## Tổng Quan Phân Phối (Distribution Overview)

Thư mục `Vivy_final` này là **repo CODE độc lập** của hệ sinh thái ViVy V1.0 & Cautreo Native Engine (chị em với repo SPEC `vivyChatGPT/`). Cây trụ sau chuẩn hóa 26/09/2026:

```
Vivy_final/
├── vivy/       ← LINH HỒN (Soul): runtime NPS-core hợp nhất
├── engine/     ← CƠ THỂ (Vessel): Cautreo native C-ABI
├── cautreo/    ← Atlases + native habitat specs
├── host/       ← Host mảnh + IPC Bus + plugins
├── ui/         ← desktop-studio (Tauri) + cautreo-desktop
├── models/     ← model_manifest.json + baselines (metadata)
├── scripts/    ← launcher + verify_all.ps1
├── docs/       ← ARCHITECTURE_FINAL, RUNBOOK, CHECKPOINTS, DATA_MAP…
└── internal/   ← kho checkpoint 6.40 GB (gitignored)
```

1.  **Linh Hồn (Soul):** `vivy/` — ViVy Unitary Reasoner hợp nhất từ 3 nguồn (`unitary-reasoner` + `Vivy_final/core` + `vivyChatGPT/training`): Elastic N-Core, Cognitive State Graph, Hebbian Recall, Model Router, AWL/91sh, Weight Pager, Cross-Model Adapter, Scored Mindmap DAG, Model Upgrade Protocol. ViVy là một thực thể nhận thức duy nhất làm chủ toàn bộ quá trình tư duy.
    <!-- [ISOLATED 26/09/2026] prior path: `core/` — đã hợp nhất vào `vivy/` và xóa bản trùng sau khi verify 222/223 file phủ bằng SHA-256 (file còn lại: VIVY_CORE_MANIFEST.md — đã merge vào `docs/`). -->
2.  **Cơ Thể (Vessel):** `engine/` — Cautreo Standalone Native Engine (`cautreo.exe`, `cautreo.dll`, `cautreo-server.exe`) cung cấp bộ nhớ C native in-process (`Context Memory`, `Score Graph`; latency: see benchmark receipt) và bộ điều phối phân trang **Cautreo Weight Pager** (Zero-RAM-Waste Dynamic Sparse Activation). <!-- [ISOLATED 24/09/2026] prior: "0ms latency" — Gate 9: latency claim requires receipt. -->
3.  **Cơ Bắp Tư Duy (Muscle):** Được tổ chức tại kho lưu trữ vật lý `D:\models`. Trọng số **không nằm trong repo** — `models/` chỉ giữ metadata.
    *   Hai model đang sống: **Gemma4 E4B** (`ACTIVE_COGNITIVE_SOUL`, Port 8080) và **Qwen2-VL-72B** (`DOWNLOADED_ON_DISK`, hồ tri thức đa phương thức).
    *   Bảng đầy đủ path / size / quant / benchmark: **[→ `models/baselines/README.md` §2](models/baselines/README.md)** · SSOT metadata: **[→ `models/model_manifest.json`](models/model_manifest.json)**.
    <!-- [ISOLATED 26/09/2026] Danh sách path+size+status đầy đủ từng nằm ở đây nhưng lặp lại với
         `docs/ARCHITECTURE_FINAL.md` §3.3 và `models/baselines/README.md` §2. Gom về baselines/README.md.
         Các gguf `qwen2.5-coder-7b` / `vivy2` / `qwen3.8-27b` đã gỡ tham chiếu sống (user chỉ thị) — xem mục [ISOLATED] tại baselines/README.md. -->

---

## Bắt Đầu Nhanh (Quick Start)

```powershell
# 1. Kiểm tra 17 cổng nghiệm thu tự động:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_all.ps1

# 2. Khởi chạy ViVy Core hợp nhất:
.\scripts\start_vivy_unified.ps1
```

---

## Tài Liệu Tham Chiếu

**5 tài liệu chuẩn** (gom 26/09/2026 — hết nạn tài liệu thô / sửa đổi / v1-v2-v3):

*   [docs/RAW_CONSOLIDATED.md](docs/RAW_CONSOLIDATED.md) — **#1 Tài liệu thô tổng hợp.** Ý tưởng gốc 3 model, lõi suy luận hình học siêu chiều, kế hoạch phát triển v2.
*   [docs/TECHNICAL_DIRECTION.md](docs/TECHNICAL_DIRECTION.md) — **#2 Tài liệu định hướng kỹ thuật.** NPS Core, nỗi đau/giải pháp, context strategy, knowledge map, test chain, MoE, orchestration.
*   [docs/ARCHITECTURE_FINAL.md](docs/ARCHITECTURE_FINAL.md) — **#3 Tài liệu thiết kế cuối cùng.** Đặc tả kiến trúc **có hiệu lực** + hệ thống phân rã context 2048 tokens + Phụ lục A–N (data cũ, ghi chú cô lập).
*   [docs/TREE_MAP_AND_CHANGELOG.md](docs/TREE_MAP_AND_CHANGELOG.md) — **#4 Tree map diễn biến & lịch sử.** Data map tái cấu trúc, biên bản reorg, snapshot tối ưu, báo cáo công việc.
*   [docs/REVIEWS.md](docs/REVIEWS.md) — **#5 Tài liệu review.** Mọi review / thẩm định / quyết định bền vững, ghi rõ còn hiệu lực hay đã cô lập.

Tài liệu vận hành / meta (nằm ngoài 5 doc):

*   [docs/RUNBOOK.md](docs/RUNBOOK.md) — Cẩm nang hướng dẫn vận hành độc lập Cautreo và vận hành hợp nhất ViVy.
*   [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md) — Hướng dẫn độc lập kho checkpoint nội bộ (6.40 GB, 81 file) kèm số liệu byte.
*   [docs/adr/](docs/adr/) — ADR-001..007 (qubit, MPS, SVD, memory, evolution, control signals, LLM backend).
*   [CLAUDE.md](CLAUDE.md) — Health stack + quy tắc cho agent kế thừa.

> **[ISOLATED 26/09/2026]** Các tài liệu riêng lẻ (`INTRODUCTION.md`, `PAIN_POINTS_AND_SOLUTIONS.md`, `CONTEXT_STRATEGY.md`, `SYSTEM_KNOWLEDGE_MAP.md`, `TEST_CHAIN_PLAN.md`, `VIVY_MOE_*`, `VIVY_CORE_MANIFEST.md`, `OCTAGONAL_TOWER_*`, `DELEGATION_CONTRACT_*`, `TRAINING_AGENT_GUIDE.md`, `DATA_MAP_2026-09-26.md`, `plans/*`) đã gom vào 5 doc trên. Bản gốc ở `old-docs/11-consolidated-source-2026-09-26/` kèm banner `[ISOLATED]` trỏ về doc đích. `docs/ARCHITECTURE.md` giữ làm **redirect stub** vì ~25 tham chiếu vẫn trỏ theo tên file đó.
