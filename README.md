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
| 1.3.0 | 23/09/2026 11:30 ICT | Antigravity IDE | Khắc phục toàn diện theo Codex Independent Audit: 1) Hợp nhất SSOT từ `unitary-reasoner` sang `Vivy final/core`; 2) Chuẩn hóa topology `MODEL_ROOT = D:\models`, giải quyết triệt để lỗi verify_all (17/17 PASS); 3) Khẳng định Gemma 4 E4B (Port 8080) là Active Cognitive Soul; 4) Định vị chính xác Qwen2-VL-72B là `DOWNLOADED_ON_DISK / PAGING_LEDGER_VERIFIED`; 5) Chạy thành công HoH known-answer live test. |
| 1.4.0 | 25/09/2026 | Claude Code (Plan 1+2 + Wave 1) | Đồng bộ code từ `vivyChatGPT/training/` vào `core/integration/`: Plan 1 (verify_receipt, sandbox_capture, check_known_limits, run_w2_live, evidence_packet_template), Plan 2 (native_parity_decision, learned_router), Wave 1 (cautreo_weight_map, cautreo_session_log). Bổ sung discussion record + plan-tune vào `docs/plans/`. |
| 1.5.0 | 25/09/2026 | Claude Code (Wave 2A+2B) | Đồng bộ Wave 2 vào `core/integration/`: Weight Pager Interface (`weight_pager.py` — partial load, stream, memory usage) + Cross-Model Adapter (`cross_model_adapter.py` — couple, route, combine_outputs, callback_weights). 41 tests mới. |
| 1.6.0 | 25/09/2026 | Claude Code (Wave 3A) | Đồng bộ Wave 3: Scored Mindmap DAG (`scored_mindmap_dag.py` — plan, score_path, reroute, cycle detection). TD-6: planning + QC. 32 tests mới. |
| 1.7.0 | 25/09/2026 | Claude Code (Wave 4A) | Đồng bộ Wave 4: Model Upgrade Protocol (`model_upgrade_protocol.py` — readiness_check, migrate, inherit_weights, SHA256 chain receipts). TD-8: progressive scaling. 28 tests mới. |
| 2.0.0 | 26/09/2026 | Claude Code (Reorg Vivy+Cautreo — D2/D3/D4) | **Chuẩn hóa repo GitHub độc lập.** Union-merge runtime 3 nguồn (`unitary-reasoner` + `Vivy final/core` + `vivyChatGPT/training`) → `vivy/`. Cây trụ mới: `vivy`·`cautreo`·`engine`·`host`·`ui`·`docs`·`models`·`scripts`·`internal`. Fix search-path `cautreo_binding.py` cho layout mới (bổ sung path repo-relative; giữ path cũ dạng fallback `[ISOLATED]`). Kho checkpoint 6.40 GB → `internal/` (gitignored) + hướng dẫn số liệu `docs/CHECKPOINTS.md`. Data map đầy đủ: `docs/DATA_MAP_2026-09-26.md`. Health stack: tests 676+17 (baseline 693 khớp) + 730+3 training; mypy 7 thư mục `Success: 64 source files`; ruff scope `All checks passed`. |

---

## Tổng Quan Phân Phối (Distribution Overview)

Thư mục `Vivy final` này là **repo CODE độc lập** của hệ sinh thái ViVy V1.0 & Cautreo Native Engine (chị em với repo SPEC `vivyChatGPT/`). Cây trụ sau chuẩn hóa 26/09/2026:

```
Vivy final/
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

1.  **Linh Hồn (Soul):** `vivy/` — ViVy Unitary Reasoner hợp nhất từ 3 nguồn (`unitary-reasoner` + `Vivy final/core` + `vivyChatGPT/training`): Elastic N-Core, Cognitive State Graph, Hebbian Recall, Model Router, AWL/91sh, Weight Pager, Cross-Model Adapter, Scored Mindmap DAG, Model Upgrade Protocol. ViVy là một thực thể nhận thức duy nhất làm chủ toàn bộ quá trình tư duy.
    <!-- [ISOLATED 26/09/2026] prior path: `core/` — đã hợp nhất vào `vivy/` và xóa bản trùng sau khi verify 222/223 file phủ bằng SHA-256 (file còn lại: VIVY_CORE_MANIFEST.md — đã merge vào `docs/`). -->
2.  **Cơ Thể (Vessel):** `engine/` — Cautreo Standalone Native Engine (`cautreo.exe`, `cautreo.dll`, `cautreo-server.exe`) cung cấp bộ nhớ C native in-process (`Context Memory`, `Score Graph`; latency: see benchmark receipt) và bộ điều phối phân trang **Cautreo Weight Pager** (Zero-RAM-Waste Dynamic Sparse Activation). <!-- [ISOLATED 24/09/2026] prior: "0ms latency" — Gate 9: latency claim requires receipt. -->
3.  **Cơ Bắp Tư Duy (Muscle):** Được tổ chức tại kho lưu trữ vật lý `D:\models`:
    *   `gemma4-e4b\vivy-gemma-e4b-q4km.gguf` (8.95GB) — `[ACTIVE_COGNITIVE_SOUL]` Lõi nhận thức và điều phối HoH chính thức tại Port 8080.
    *   `qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf` (44.16GB) + `mmproj-f16` (1.30GB) — `[DOWNLOADED_ON_DISK / PAGING_LEDGER_VERIFIED]` Hồ tri thức sâu và đa phương thức kích hoạt qua Cartography Atlas (`qwen2-vl-72b.catlas`).
    *   `qwen2.5-coder-7b-instruct` (4.68GB) — `[AVAILABLE_ON_DEMAND]` Specialist Coder model.
    *   `vivy-1.5b-reflex` (0.95GB) — `[ROADMAP_PROPOSED]` Student Distillation model phục vụ CUA phản xạ nhanh.
    *   `vivy2.gguf` & `qwen3.8-27b.gguf` — `[ISOLATED / ARCHIVED]` Đã giải phóng dung lượng đĩa NVMe để tối ưu cho Qwen2-VL-72B.

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

*   [docs/ARCHITECTURE_FINAL.md](docs/ARCHITECTURE_FINAL.md) — Toàn văn đặc tả kiến trúc hệ thống và hệ thống phân rã context 2048 tokens.
*   [docs/RUNBOOK.md](docs/RUNBOOK.md) — Cẩm nang hướng dẫn vận hành độc lập Cautreo và vận hành hợp nhất ViVy.
*   [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md) — Hướng dẫn độc lập kho checkpoint nội bộ (6.40 GB, 81 file) kèm số liệu byte.
*   [docs/DATA_MAP_2026-09-26.md](docs/DATA_MAP_2026-09-26.md) — Bản đồ dữ liệu đầy đủ: di chuyển, hợp nhất, xóa bỏ.
*   [CLAUDE.md](CLAUDE.md) — Health stack + quy tắc cho agent kế thừa.
