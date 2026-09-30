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
| 2.3.0 | 27/09/2026 | Claude Code (Fix readiness gate + regression test) | **Fix readiness gate FAIL vĩnh viễn.** `verify_codex_remediations()` vẫn ghi `results["qwen_coder_artifact_present"] = False` cho check đã `[ISOLATED 26/09/2026]` (gguf qwen2.5-coder không có trên đĩa). `main()` chấm bằng `all(sub_results.values())` nên key chết đó làm FAIL nhóm Codex Remediation + OVERALL VERDICT **mọi lần chạy**, dù Cautreo Memory, Parallel Pipeline, Inference Loop, Dream Engine đều PASS. **Fix:** ngừng emit key đã loại bỏ khỏi phép chấm điểm (giữ dòng print làm audit trail) — tôn trọng quy tắc "cô lập, không xóa bỏ" vì ghi chú `[ISOLATED]` vẫn còn. Sửa cả 2 bản: `vivy/scripts/` (vận hành thật) + `scripts/` (bản so sánh). **Regression test mới** `vivy/tests/test_readiness_gate.py` (2 test: bắt key chết rò rỉ trở lại + bắt check thật fail) — chứng minh fail với hành vi cũ, pass với fix. **Kết quả:** readiness gate `OVERALL VERDICT: READINESS SUBSYSTEM CHECKS PASS` (exit 0). Baseline `tests/` = **695 passed** (693 + 2 mới); `training/` = **730 passed + 3 skipped**; mypy `Success: 64 source files`; ruff `All checks passed!`. |
| 2.4.0 | 27/09/2026 | Claude Code (office-hours — thiết kế tầng tiêu chí game) | **Thêm tài liệu thiết kế** `docs/DESIGN_GAME_CRITERIA_LAYER.md` (CHỈ thiết kế, không code/scaffolding — HARD GATE của phiên `/office-hours`). Định nghĩa **nội dung** của máy chấm điểm vốn chỉ có chấm điểm/ghi chú/trạng thái: 3 trục tiêu chí **thẩm mỹ · logic game · góc nhìn người chơi**, kiến trúc 3 tầng (INGEST online trả tiền 1 lần → DISTILL offline → COMPOSE offline không LLM), cơ chế biến điểm chấm mềm thành tiêu chí cứng qua `features` kiểm chứng được, schema `annotation record` / `criterion record` / `criterion set`, bảng cắm vào code hiện có, nguồn schema mượn (CDDA `copy-from`, LPC JSON parts, Tiled TMX, flecs, OpenUSD, Yarn/ink) kèm cảnh báo copyleft/brand-IP, và hệ receipt truy nguồn. Trả lời câu hỏi gốc *"cái gì làm lựa chọn này tốt hơn lựa chọn kia?"*. **Không có code mới, không scaffolding, không commit trọng số.** Health stack giữ nguyên: `tests/` 695, `training/` 730+3, mypy 64 source files, ruff sạch. |
| 2.5.0 | 29/09/2026 | Claude Code (WP-1/O-01 — fail-fast wiring) | **Hết stub im lặng trong đường Orchestrator + cấm MockLocalEngine ở production.** (a) `vivy/orchestrator/engine.py`: gỡ 4 khối `try/except ImportError → stub` (thay bằng import trực tiếp, fail-loud); bỏ `_StubEvolution` và 3 chỗ `__mro__[1]()` — cú pháp này tạo `object()` rỗng, vi phạm ADR-005; `_evaluate` **ngừng nuốt ngoại lệ** và bịa verdict `("continue", 0.9)`. (b) **Mới** `vivy/orchestrator/wiring_report.py`: receipt REAL/STUB/MISSING lúc khởi động, ghi vào `ActivityLog`, `raise_if_unwired()` từ chối boot khi còn stub/thiếu. (c) `vivy/src/vivy/core/model_loader.py`: `MockLocalEngine` nay là test double **bị cấm** ngoài opt-in tường minh (`allow_mock=True` hoặc `VIVY_ALLOW_MOCK_ENGINE`); thiếu `llama_cpp` → `EngineUnavailableError` (trước im lặng chạy Mock); backend lạ → `UnsupportedBackendError` (trước cũng trả Mock). (d) `vivy/src/vivy/api/router.py`: **bỏ hardcode `ModelBackend.MOCK` lúc import** — trước đó trade cycle production luôn chạy trên engine giả luôn trả BUY GOLD. (e) Test: 12 test mới (`tests/test_wiring_failfast.py` 10 + `tests/unit/test_vivy_core.py` 2) chứng minh lệnh cấm có hiệu lực; 2 test trading cũ đổi sang `allow_mock=True` **theo đặc tả WP-1** (unit test cần engine tất định), không bỏ assertion nào. **Kết quả:** `tests/` **707 passed** (695+12), mypy `Success: 65 source files` (64 + wiring_report), ruff sạch; `WiringReport` = 8/8 REAL khi `src/` trên path, trading báo `MockLocalEngine banned`. |
| 2.5.1 | 29/09/2026 | Claude Code (WP-2/O-03 — điều khiển vòng lặp) | **Fix F-B01 / F-B02 / F-B03 — vòng lặp hết quay tít và hết khai DELEGATE giả.** (a) `vivy/integration/vivy_inference_loop.py`: **truyền đủ đầu vào `resolve()`** — trước đó `tool_failed` / `repeated_failure` / `evidence_verified` không bao giờ được tính nên nằm ở default `False`, khiến **HALT không thể xảy ra** (F-B01). Nay suy từ `all_tool_results` thật; `evidence_verified = có Expected_Evidence ∧ không tool fail ∧ có content`. (b) **Cắt tập "tiếp tục vòng"** từ `{FORAGE, DELEGATE, CONTINUE, BACKTRACK}` xuống `{FORAGE, BACKTRACK}` — trước đó mọi câu trả lời không tool call được bơm lại prompt *"Provide the next bounded action…"* và chạy tới `max_rounds` (log cũ: **15/15 `rounds: 10`**). (c) `_parse_epistemic_decision`: **fail-closed** — thiếu trường trả `""` thay vì `"EXECUTE_DIRECTLY"` (F-B03); caller map `.get(…, Decision.DELEGATE)` nay là đường sống, kèm log `epistemic_decision_unparsed`. (d) `vivy/orchestrator/decision_controller.py`: `DecisionContext` thêm `budget_exhausted: bool | None` + `single_round: bool`; `resolve()` trả **HALT khi evidence đã kiểm chứng**, và `single_round=True` **bỏ qua luật ngân sách + luật thiếu Expected_Evidence** — trước đó `max_rounds=1` của CHAT/BATCH chạm `rounds >= max_rounds` ngay vòng 1 nên **mọi câu trả lời CHAT/BATCH đều báo DELEGATE** (F-B02). **Chống false-halt (T4):** `resolve()` **không** ghi đè yêu cầu `FORAGE`/`DELEGATE`/`BACKTRACK` thành HALT dù `evidence_verified` — đó chính là false-halt T4 cấm; HALT chỉ dành cho model tự thấy xong việc. (e) Test mới `vivy/tests/test_loop_control.py` (**14 test**): parse fail-closed, HALT tới được, tool-free AGENTIC dừng sau **1 vòng**, DELEGATE không tái vòng, FORAGE được vòng 2, CHAT báo `CONTINUE`/`HALT` chứ không DELEGATE, safety precedence (INCIDENT/BACKTRACK) thắng HALT, `budget_exhausted` override. **Kết quả:** `tests/` **721 passed** (707+14), `training/` 730+3 giữ nguyên, mypy `Success: 65 source files`, ruff sạch. Chưa đo T4 trên tập 120 câu (thuộc WP-7). |
| 2.5.2 | 29/09/2026 | Claude Code (WP-3/O-04 — hợp nhất backend LLM) | **Fix F-A09 / F-B06 — một cấu hình, hết fallback cloud im lặng, timeout tách riêng.** (a) **Mới** `vivy/llm_bridge/backend.py`: `LLMBackend` = URL · model-id · timeout · num_ctx — **một** nguồn cấu hình (trước đó model cùng `gemma4-e4b` khai ở 3 nơi: `UNITARY_*` của `client.py`, `VIVY_*` của `llama_cpp_bridge.py`, và lần nữa trong `training/backend_registry.py`). Kèm `LLMBackend.identity()` trả receipt khớp shape `training/backend_baseline.BackendIdentity` để product/training diff được. (b) `vivy/llm_bridge/client.py`: **bỏ nhánh fallback 17 model cloud** (`gpt-4o`/`claude-3-opus`/`gemini-1.5-pro`…) — trước đó `chat(fallback=True)` **đi bộ catalogue khi 404** và trả lời của model khác dưới tên model được yêu cầu (**F-B06: mất tái lập**). Nay model thiếu → `ModelUnavailableError`, **không chuyển model ngầm**. Catalogue giữ dạng `[ISOLATED 29/09/2026]` (cô lập, không xóa); `list_models()` offline giờ báo đúng **1 model đã cấu hình** thay vì bịa 17 model cloud trên máy local. (c) **Timeout tách riêng:** `LLMTimeoutError` (con của `LLMError`, không lẫn `ModelUnavailableError`) ở cả `client.py` và `llama_cpp_bridge.py` — đáp ứng nghiệm thu *"timeout báo riêng khỏi lỗi suy luận"*. `ChatResponse` thêm `delegate_kind` (`timeout`/`unavailable`/`error`). (d) `vivy/integration/llama_cpp_bridge.py`: `LlamaCppConfig` lấy default từ `LLMBackend` (không tự đọc env lần nữa); thêm `bridge.backend_identity()`; **mọi `ChatResponse` mang `backend_id` + `model_id`** — lấy theo `model` server echo về, không theo tên khai báo (F-B06). (e) **ADR-007 viết lại**: một hợp đồng OpenAI-compatible `/v1/chat/completions`, một cấu hình; backend tham chiếu khi phát triển = llama-server/Ollama `gemma4:e4b` @ `8080`; sau phép đo **D-4** mới chuyển `cautreo-server`. Quyết định cũ (17 model + `UNITARY_*` + "auto-discover models") giữ nguyên văn bản kèm bảng `[REPLACED]/[ISOLATED]/[CORRECTED]` đối chiếu từng dòng. (f) Sửa mâu thuẫn tài liệu: `docs/public/quickstart.md` (bảng env ghi **sai** `11434`/`vivy-final:v1` → đúng `8080`/`gemma4:e4b`; thêm mục "Backend nào trả lời?"), `docs/public/architecture.md` (bỏ nhãn "(Ollama server)"). Cả hai doc trước đây bán flow Ollama trong khi `ARCHITECTURE_FINAL.md:28` tuyên bố độc lập Ollama — nay chốt: **độc lập Ollama là đích, chưa phải đường đang chạy**; parity **được đo**, không giả định. (g) Test: **19 test** (`tests/test_backend.py` 8 + `tests/test_client.py` 11). 4 test cũ ghim hành vi fallback được **viết lại theo đặc tả WP-3 kèm receipt trong docstring** (plan hard-rule #4) — mọi assertion mới **mạnh hơn** cũ (model thiếu phải raise, không được walk; offline không được bịa model cloud), không có assertion nào bị làm yếu để test pass. **Kết quả:** `tests/` **734 passed** (721−7 cũ+19 mới), `training/` 730+3 giữ nguyên, mypy `Success: 66 source files` (65+backend), ruff sạch. |
| 2.5.3 | 29/09/2026 | Claude Code (WP-4/O-13 — RiskGate giao dịch, D-3) | **Ghi đè có chủ ý triết lý "CẤM GÁC CỔNG LẬP TRÌNH" bằng RiskGate fail-closed.** Quyết định **D-3 của chủ dự án (29/09)** — review đo **0/30** lệnh đối kháng bị chặn (G-01/G-02/G-03). (a) **Mới** `vivy/src/vivy/hands/risk_gate.py`: lớp **độc lập LLM**, fail-closed, **đồng minh an toàn chứ không phải bộ lọc chiến lược** — từ chối volume ≤0/NaN/Inf/không parse được, volume ngoài `[min,max]`, thiếu SL/TP ở lệnh vào, SL/TP sai phía giá, symbol ngoài allow-list, lệnh vào không có giá tham chiếu. `parse_finite_float` **không có default**. Mặc định **paper trading**; live cần `RiskLimits(paper_trading=False)` tường minh. (b) **Mới** `docs/adr/ADR-008-risk-gate.md` (INV-08: đổi kiến trúc phải có ADR) — ghi rõ **phạm vi ghi đè**: CHỈ kiểm tra an toàn lệnh, KHÔNG BAO GIỜ lọc chiến lược/risk-reward/velocity/conviction. (c) `docs/TECHNICAL_DIRECTION.md` **5 chỗ** (`:2321,:2350,:2417,:2439,:2470`) đánh dấu `[REPLACED 29/09]` + link ADR-008 — **không xóa** (quy tắc cô lập). (d) `vivy/src/vivy/core/prompts.py`: bỏ câu "CẤM GÁC CỔNG LẬP TRÌNH… no hardcoded filters"; prompt mới **khai báo RiskGate là đồng minh**, liệt kê chính xác thứ nó từ chối và thứ nó KHÔNG được làm, kèm luật trường JSON. Câu cũ giữ nguyên văn trong khối `[ISOLATED]` phía trên (prompt là chỉ dẫn hành vi sống, không được để lời nói dối trong đó). (e) `vivy/src/vivy/core/inference.py`: **hết bịa số** — bỏ `float(..., volume→0.01)` / `stop_loss→0.0`; lệnh vào phải tự khai volume/SL/TP, `confidence` phải hữu hạn trong `[0,1]`. (f) `vivy/src/vivy/hands/mt5_executor.py`: mọi lệnh đi qua RiskGate trước khi ghi nhận; `ExecutionReceipt` thêm `risk` + `live`. (g) `vivy/src/vivy/api/router.py`: bỏ `"Eyes & Hands (No Gatekeepers)"`, truyền `price=current_price` vào `execute_decision` (trước đó lệnh vào bị từ chối vì không có giá tham chiếu — đúng fail-closed). (h) **Phát hiện thêm: `src/` không nằm trên sys.path của pytest** → toàn bộ dòng trading (`vivy.hands`/`vivy.core`/`vivy.api`) **chưa từng có test nào chạy** (sau `collect_ignore_glob` của `tests/unit/conftest.py`). Thêm `pythonpath=["src"]` vào `pyproject.toml` + gỡ 2 file (`test_eyes_hands.py`, `test_vivy_core.py`) khỏi ignore — nay chạy thật. (i) Test: **mới** `tests/test_risk_gate.py` (**104 test**) với **ma trận 65 đầu ra đối kháng → 0 lệnh lọt** (đạt T10 ≥60), kèm test khẳng định RiskGate **không** lọc chiến lược (R:R xa vẫn cho qua nếu chưa khai `max_*_distance`). `tests/unit/test_eyes_hands.py::test_mt5_executor_no_gatekeepers` **viết lại theo đặc tả** (hard-rule #4, có receipt) — đổi tên, thêm price, thêm 3 ca từ chối; `tests/unit/test_vivy_core.py::test_isolated_prompts` viết lại để ghim prompt mới (mạnh hơn: phải có `RiskGate`/`ally`, và **không** được chứa "No hardcoded filters"). **Kết quả:** `tests/` **847 passed** (734+113: 104 mới + 4 `test_eyes_hands` + 5 `test_vivy_core` trước bị ignore), `training/` 730+3 giữ nguyên, mypy `Success: 66 source files`, ruff sạch. |
| 2.5.4 | 29/09/2026 | Claude Code (WP-5/O-12 — giao diện trung thực, Gate 9) | **Hết tuyên bố giả trong giao diện.** (a) `src/nps_core/vivy_interface/vision.py`: `from_file` **fail-closed** khi thiếu file (trước: hash **đường dẫn** trình bày như hash ảnh, bịa `1024×1024` cho mọi đường dẫn kể cả file không tồn tại). `width`/`height` → `None` = không decode. Nhánh bịa giữ sau cờ `allow_simulated=True`, gắn `simulated=True` để mọi summary phải thừa nhận. (b) `src/nps_core/vivy_interface/reasoning_engine.py`: bỏ *"ViVy has processed the image"* / *"nhận diện được hình ảnh"* / *"equipped with Vision capability"* / *"Fusing visual features"* — module này **không decode pixel, không gọi model**. Thêm cờ `from_template` / `model_call_made=False` / `pixels_decoded=False`. Chuỗi cũ lưu trong `[ISOLATED]`. (c) `src/nps_core/multimodal_clairvoyance/*` **`[ISOLATED]` + `SIMULATED`**: `audio_video_perception.py` hash **byte** thay vì đường dẫn, hết bịa `sample_rate=16000`/`channels=1`/`1920×1080`/`fps=30`; `clairvoyance_engine.py` trả `simulated=True`/`pixels_read=False`/`audio_samples_read=False`/`video_frames_read=False`, summary đổi thành *"SIMULATED · synthetic state, NO media was decoded"*. (d) `src/nps_core/vivy_ollama/*` **`[ISOLATED]` — không phải proxy thật**: `client.py` **không có lời gọi HTTP nào**; `server.py` hết bịa card `/api/tags` (`size 2147483648`, `digest sha256:vivy1b…`, `parameter_size "1.15B"` → `None`/`UNMEASURED`) và `/api/show`; mọi response gắn `model_call_made: False` + `simulated_response: True`; `exporter.py` gỡ *"4-Level Self-Verification Filter Funnel"* + *"1-Touch Intuition Retrieval"* khỏi SYSTEM prompt sống. (e) `modelfiles/Modelfile.vivy-clairvoyance`: gỡ *"4-level filter funnel, zero-hallucination"* + 3 claim Native Visual/Video/Audio Perception khỏi SYSTEM sống, thay bằng danh sách "NOT measured"; khối cũ lưu cuối file. (f) `src/vivy/core/moe_brain.py`: đổi *"70B MoE Quantum Core (1B Active)"* → quy mô thật **524.288 tham số phức/expert (U 4096×64)**; `num_experts=70` là kích thước bảng route. Tên class giữ (hard-rule #3). (g) `integration/cautreo_cartographer.py::scan_model` gắn **`SIMULATED`** (`atlas.simulated=True`, `weights_read=False`, `model_path` bị bỏ qua tường minh) và **`render_for_prompt()` raise** — cấm tiêm atlas giả vào prompt. (h) `models/model_manifest.json`: 4 chuỗi benchmark gắn `[UNMEASURED]` + `benchmark_status`/`benchmark_receipt`/`benchmark_note` (additive). (i) **Mới** `docs/CAPABILITY_LEDGER.md` — sổ năng lực Gate 9: 15 mục C-xx (đã sửa), 25 mục U-xx (`UNMEASURED`/`REPLACED`), 7 mục R-xx (có receipt). (j) Test: **mới** `tests/test_capability_honesty.py` (tripwire Gate 9 — quét code **sống** (bỏ comment/docstring) và fail khi claim cũ quay lại; kiểm tra SYSTEM prompt, thẻ manifest, atlas, ledger) + **viết lại** `tests/unit/test_vivy_multimodal_interface.py` theo đặc tả kèm receipt (hard-rule #4) — test cũ **ghim chính hành vi bịa** (`assert payload.width == 1024` với đường dẫn không tồn tại); assertion mới **mạnh hơn**: thiếu file phải `raise`, resolution phải `None` không phải 1024, simulation phải bị đánh dấu. Gỡ file này khỏi `collect_ignore_glob`. **Kết quả:** `tests/` **888 passed** (847+41), `training/` 730+3, mypy `Success: 66 source files`, ruff sạch. |
| 2.5.5 | 29/09/2026 | Claude Code (WP-6/O-10 — đường dữ liệu sạch, T9) | **Hết nhãn bịa trong SFT (F-H01…F-H04). SFT ĐƯỢC DỪNG cho tới khi mục này xong.** (a) `training/dataset_extractor.py` **viết lại**: bỏ hardcode `AST_VALID_AND_TEST_PASS` / `COGNITIVE_CONSENSUS_VERIFIED` / `MULTIMODAL_GROUNDING_VERIFIED` — `Expected_Evidence` nay chép từ trường `expected_evidence` / `acceptance_gate` / `grounding_verified_as` / `consensus_verified_as` của record, hoặc ghi `UNVERIFIED`; reward chỉ trả khi có `evidence_receipt_id` (hết `1.0 if status != "ERROR"` — không crash không phải là đã kiểm chứng); `capture_id_matched` lấy từ record (`NOT_CHECKED` khi record im lặng) thay vì chèn `capture_id_matched: True`; mẫu không có receipt **bị loại và đếm**. (b) `training/confirm_gold.py`: oracle auto-reviewed đóng dấu `kind="oracle"` + `label_quality="oracle_confirmed"`, **không** còn mạo nhận `human-accept` (F-H02). (c) `training/check_known_limits.py`: entry không có receipt ref → **FAIL** thay vì im lặng pass (F-H04). (d) `training/dataset_audit.py` sở hữu `FABRICATED_EVIDENCE_LABELS` + `detect_schema` + `evidence_receipt_of` (bỏ qua id `legacy-*` — migration id là provenance, không phải xác minh) + `assert_exportable` (cổng T9). (e) `training/decision_contract.py` thêm `SchemaMismatchError` / `require_typed` — ChatML row nộp vào API typed báo lỗi nêu tên `legacy_to_typed.migrate` thay vì "candidates must be a list" (F-H03). (f) **Mới** `training/test_no_fabricated_labels.py` (38 test) — tripwire mã nguồn (comment/docstring là lịch sử, code **sống** mới bị quét) + quét mọi tập SFT: tập sạch phải 0 nhãn bịa và mọi dòng có receipt; tập bẩn phải nằm trong quarantine **và** bị `smoke_train` từ chối; 0 rò rỉ theo nhóm ở `gold_train`. (g) `tests/test_training_pipeline.py`: 5 test cũ **ghim chính hành vi bịa** viết lại theo đặc tả kèm receipt (hard-rule #4) + 1 test mới. Tập `training/vivy_train_dataset.jsonl` (501 dòng, 451 dòng mang nhãn bịa) **giữ nguyên không xóa** (hard-rule #2) và vẫn bị `smoke_train.LEGACY_DATASET_NAMES` từ chối. **Kết quả:** `tests/` **889 passed** (888+1), `training/` **768 passed + 3 skipped** (730+3 + 38), mypy `Success: 66 source files`, ruff sạch. |
| 2.5.6 | 29/09/2026 | Claude Code (WP-7/O-02 — harness đo + baseline) | **Đo được pipeline: bộ câu hỏi, chấm điểm lập trình, harness A/B/C.** (a) **Mới** `vivy/benchmarks/eval_set/` — 120 câu, 4 miền × 30 (lượng tử / toán / đồ thị / tính toán), mỗi miền 8 dev + 22 held-out, **30 câu đối kháng** (thiếu dữ kiện, đúng là phải từ chối). Bộ sinh tất định theo seed `20260929`; **mọi đáp án được tính ra bằng chương trình, không gõ tay** — tránh "sai chính tả thành ground truth", và có test tự chấm 120/120 câu qua checker để ghim điều đó. (b) **Mới** `vivy/benchmarks/checker.py` — chấm lập trình theo `expected_kind` (number/set/expression/text/insufficient), **cấm khớp chuỗi con lỏng** (yêu cầu của kế hoạch). Hợp đồng khai báo: mỗi prompt buộc model kết thúc bằng đúng một dòng `ANSWER: <value>` hoặc `VERDICT: INSUFFICIENT_EVIDENCE`; chấm là **phân tích cú pháp**, không đọc văn bản. (c) **Mới** `vivy/benchmarks/harness.py` — chạy A/B/C: (a) Gemma thuần, (b) `VivyInferenceLoop`, (c) pipeline + câu hỏi gốc vào `Decoder`; ghi receipt `evidence/T2-<run_id>.json` kèm `backend` identity, độ trễ/token thô từng câu, và quy tắc chấm T2 (`PASS`/`MARGINAL`/`STOP_REDESIGN`) + ngưỡng giữ thành phần lượng tử. (d) **D-7 (chốt 29/09):** held-out **ngoài repo** — repo chỉ commit `heldout_manifest.json` chứa `{id, domain, split, kind, expected_kind, sha256}`, không prompt, không đáp án. `generate.py --split heldout --out` **exit 2** nếu đích nằm trong `Vivy_final/`. Harness fail-closed khi thiếu file hoặc lệch hash — không có đường fallback. (e) **D-8 (chốt 29/09):** trần treo 120 s/câu + 4096 token hoàn thành để **chặn treo**, không phải ngân sách; mục đích là ghi lại độ trễ + token thô để chốt ngân sách T11 từ baseline đo được. Trần bị chạm ghi nhận là **quan sát bị che** (`n_ceiling_hits` / `accuracy_uncensored`) **không** gộp vào "trả lời sai" — T2 hỏi "ai đúng" chứ không hỏi "ai kịp". (f) **Ba lỗi thật bắt được trong lúc đấu dây đo, có regression test ghim lại:** (1) trần treo là **trang trí** — `with ThreadPoolExecutor` gọi `shutdown(wait=True)` lúc thoát nên một câu treo chặn cả run; đổi sang `threading.Thread(daemon=True)`. (2) `LLMClient` cache `httpx.AsyncClient` trên event loop đầu tiên, còn harness `asyncio.run()` mỗi câu tạo loop mới → **câu thứ 2 chết `RuntimeError: Event loop is closed` và bị chấm sai vì lỗi plumbing**; harness dựng client mới mỗi call. Lỗi vòng đời này thuộc `llm_bridge/`, **không** sửa ở đây — WP-7 là phép đo, không phải sửa client dùng chung. (3) parser khai báo chỉ nhận `ANSWER:` ở đầu dòng → *"I cannot be sure, but ANSWER: 24"* thành `no_declared_answer` thay vì **bịa đáp án**; thêm ranh giới mệnh đề để hành vi khớp docstring. (g) Test: **mới** `tests/test_benchmarks_eval.py` (**74 test**). **Kết quả:** `tests/` **963 passed** (889+74), `training/` 768+3, mypy `Success: 66 source files`, ruff sạch. **Nghiệm thu T2 (pipeline ≥ baseline − 2pp; < baseline − 5pp → dừng thiết kế lại) đang đo** trên 88 câu held-out × 2 nhánh — verdict ghi vào dòng này khi receipt `evidence/T2-heldout-2026-09-29.json` hạ cánh. |
| 2.5.7 | 29/09/2026 | Claude Code (WP-8 — nối đường học an toàn, T8) | **Sản phẩm học được: đường tạo `VERIFIED_RESULT` sống, và không học được gì khi không có bằng chứng.** Fix **F-B05** — trước đây `independently_verified=False` bị **hardcode** tại call site `evaluate_multi_stream` trong `integration/vivy_inference_loop.py` **và** `evidence_packet` không hề được truyền. Cả hai nửa đầu vào của Gate 7 đều chết → `VERIFIED_RESULT` không tới được → `LessonStore.promote()` không bao giờ chạy → **0 bài học, hệ thống không học được gì**. (a) `integration/evidence.py` **mới** `derive_independent_verification()` + `build_evidence_packet()`: cờ độc lập **suy từ dòng dispatch thật** (≥1 tool trả `ok`, 0 tool fail), **không** bao giờ do model tự khẳng định. Trả về `(packet, independently_verified)` để caller **không thể quên** chuyển tiếp — đúng cơ chế hỏng của F-B05. "Độc lập" cố ý hẹp: *một tiến trình ngoài model trả về quan sát và không cái nào fail*. **Không** có nghĩa khẳng định đúng về ngữ nghĩa — `ok` là thành công **quy trình**, không phải sự thật (Gate 7: *"Process success != semantic correctness != durable knowledge"*). Xác minh ngữ nghĩa là việc của tribunal (WP-11). Quan sát bị cắt ở 400 ký tự (packet là receipt, không phải transcript). (b) `integration/vivy_inference_loop.py`: dựng packet ở nơi dòng dispatch còn tồn tại và chuyển tiếp cả hai cờ. Confidence lấy từ `session.bridge.calibrate_multi_stream_confidence` — **cùng** con số điều khiển bậc thang `EvidenceClass`, không phải một số thứ hai trôi đi (mypy bắt call nhầm `self._bridge` — cầu LLM, không có method đó). (c) `integration/lesson_store.py`: `promote()` **fail-closed** trên `provenance` thiếu `evidence` — trước đây chỉ validate *khi key có mặt* nên `promote(..., provenance={})` lọt qua, tạo bài học không provenance, trái Gate 7 và T8. (d) `EvidencePacket.valid_for_promotion()` **siết**: packet tự ghi `REJECTED: …` (chính là output của một lần chạy không có/failed quan sát) **không** được promote — trước đây chỉ kiểm trường *không rỗng* nên một lần chạy chưa xác minh vẫn vào được durable knowledge, lọt cả qua `evaluate_multi_stream` lẫn `LessonStore.promote`. Text tự do (`"PASS"`, `"ACCEPTED"`) vẫn hợp lệ. (e) Test: **mới** `tests/test_safe_learning_path.py` (**11 test**) — T8: *replay log → 0 thăng cấp sai; ≥1 bài học VERIFIED thật khi có bằng chứng*. Chuỗi thật `DispatchResult` → `build_evidence_packet` → `evaluate_multi_stream` → `LessonStore.promote`; replay 10 ca đối kháng (provenance rỗng, evidence rỗng, claim rỗng, không evidence_ids, confidence ngoài [0,1], limits rỗng, acceptance ghi REJECTED, PROVISIONAL/FAST_SIGNAL có evidence tốt) → **0 sai lệch**; tripwire quét code **sống** chặn F-B05 quay lại. 2 test cũ trong `tests/test_checkpoint.py` ghim **chính** hành vi sai (kỳ vọng ACCEPTED với `provenance={}`) được **viết lại theo đặc tả kèm receipt** (hard-rule #4) — fixture nay mang packet đầy đủ, và 3 test từ chối nhận fixture đó để chúng fail đúng lý do được nêu (`evidence_class`), không fail tình cờ vì thiếu evidence. **Kết quả:** `tests/` **976 passed** (963+13), `training/` 768+3, mypy `Success: 66 source files`, ruff sạch. |
| 2.5.8 | 30/09/2026 | Claude Code (O-05/T3 — confidence calibration, WP-9) | **Một định nghĩa confidence có hiệu chuẩn: đo ECE/AUROC/Brier, isotonic calibration trên dev, chọn definition đạt ngưỡng.** (a) **Mới** `vivy/benchmarks/calibration/`: `metrics.py` (ECE equal-width bins, AUROC rank-based Mann-Whitney U, Brier MSE — pure Python, zero dependency mới); `isotonic.py` (PAV isotonic regression — Pool Adjacent Violators, monotone step function); `features.py` (7 confidence extractors fail-closed: schmidt_spectrum, state_norm, llm_declared, ncore_min, linear_tribunal, self_consistency k=5, verifier — thiếu tín hiệu → 0.0, không bao giờ 1.0); `evaluate.py` (T3 pipeline: fit isotonic trên dev → đo trên heldout → chọn definition đầu tiên đạt ECE ≤ 0.10 ∧ AUROC ≥ 0.70; không đạt → fallback `verifier`). (b) Harness `--t3` flag: `ItemScore` thêm `confidence_by_definition`, receipt thêm `t3_verdict` block (nullable — `NOT_MEASURED` khi chưa có confidence data). (c) Định nghĩa cũ (Schmidt, norm, LLM, N-Core min, linear) thành ablation features — vẫn extract được nhưng chỉ dùng để so sánh. (d) **Zero dependency mới** — PAV + AUROC viết tay pure Python. (e) Test **38 test** (`tests/test_calibration.py`): ECE 4, AUROC 6, Brier 4, Isotonic 6, Extractors 10, T3Evaluation 6, HarnessIntegration 2. **Kết quả:** `tests/` **1020 passed**, `training/` 768+3, mypy 66 source files, ruff sạch. |

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
*   [docs/adr/](docs/adr/) — ADR-001..008 (qubit, MPS, SVD, memory, evolution, control signals, LLM backend, risk gate).
*   [CLAUDE.md](CLAUDE.md) — Health stack + quy tắc cho agent kế thừa.

> **[ISOLATED 26/09/2026]** Các tài liệu riêng lẻ (`INTRODUCTION.md`, `PAIN_POINTS_AND_SOLUTIONS.md`, `CONTEXT_STRATEGY.md`, `SYSTEM_KNOWLEDGE_MAP.md`, `TEST_CHAIN_PLAN.md`, `VIVY_MOE_*`, `VIVY_CORE_MANIFEST.md`, `OCTAGONAL_TOWER_*`, `DELEGATION_CONTRACT_*`, `TRAINING_AGENT_GUIDE.md`, `DATA_MAP_2026-09-26.md`, `plans/*`) đã gom vào 5 doc trên. Bản gốc ở `old-docs/11-consolidated-source-2026-09-26/` kèm banner `[ISOLATED]` trỏ về doc đích. `docs/ARCHITECTURE.md` giữ làm **redirect stub** vì ~25 tham chiếu vẫn trỏ theo tên file đó.

---

## Public README (from GitHub)

> **[MERGED 30/09/2026]** — Nội dung public README từ `origin/main` được giữ nguyên bên dưới, không xóa bỏ. Xem mục Changelog cho lịch sử đầy đủ.

<div align="center">

<h1>ViVy</h1>
<p><strong>Your own AI. Runs local. Thinks like Jev.</strong></p>

<p>
  <a href="#architecture">Architecture</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#why-own-your-ai">Why Own Your AI</a> ·
  <a href="#benchmarks">Benchmarks</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

</div>

---

### What is ViVy?

**ViVy** is a local AI core that gives you a model with the same architectural advantages as Jev — the Jamba-style parallel hypothesis evaluator — running entirely on your own hardware, under your own control, with no cloud dependency.

While cloud AI products charge per token and retain your data, ViVy runs **on your machine, offline, forever**.

> *"You don't rent intelligence. You own it."*

### ViVy is NOT a chatbot wrapper

| Feature | Typical local AI | **ViVy** |
|:---|:---:|:---:|
| Runs offline | ✅ | ✅ |
| Multi-turn conversation | ✅ | ✅ |
| Tool calling / function use | ❌ | ✅ |
| **Jev-style parallel hypothesis** | ❌ | ✅ |
| **Cognitive memory (Thought Ecology)** | ❌ | ✅ |
| **Never repeats failed actions (VM-11)** | ❌ | ✅ |
| **Directive-first (knows action before generating)** | ❌ | ✅ |
| Multimodal: Text + Vision + Audio | ❌ | ✅ |
| **You own the weights** | ✅ | ✅ |

---

### The Jev Architecture

ViVy's **ElasticNCore** is directly inspired by the Jev model — a Jamba-style architecture that evaluates multiple hypotheses in parallel within a single GEMM pass, then routes to the best candidate.

**Result**: ViVy completes tasks faster than the same base model running without the ElasticNCore wrapper — not because token generation is faster, but because it picks the *right action immediately* instead of thinking out loud.

### The DirectiveMTPHead

Before the LLM generates a single output token, ViVy already knows *what kind of action* it will take. The **DirectiveMTPHead** emits an opcode at the front of the reasoning pass:

```
EXECUTE     → Do it directly
FORAGE      → Gather more information first
DELEGATE    → Hand off to a specialized worker
```

---

### Why Own Your AI?

| | Cloud AI | **ViVy (local)** |
|:---|:---|:---|
| **Cost** | $0.01–$0.06 per 1K tokens (ongoing) | One-time hardware cost |
| **Privacy** | Your prompts → their servers | Never leaves your machine |
| **Availability** | API downtime, rate limits | Always on |
| **Control** | Model updates without your consent | You freeze the version |
| **Data ownership** | Contractually ambiguous | 100% yours |
| **Latency** | 200ms–2000ms network round-trip | Local RAM/VRAM speed |
| **Vendor lock-in** | Switching costs every major release | Swap model in 1 line |

---

### What ViVy Can Do

#### Agentic Mode — Tool Calling

```python
from integration.vivy_inference_loop import VivyInferenceLoop, InferenceMode

vivy = VivyInferenceLoop.from_env()
result = vivy.infer(
    "Read my project README and suggest the 3 most critical missing sections",
    session_id="my_session",
    mode=InferenceMode.AGENTIC,
)
print(result.response_text)
```

#### Multimodal — Vision

```python
result = vivy.infer(
    "Describe what's in this diagram and identify any architectural anti-patterns",
    session_id="vision_session",
    mode=InferenceMode.AGENTIC,
    image_path="architecture_diagram.png",
)
```

---

### Model Independence

ViVy works with any OpenAI-compatible endpoint. One environment variable switches providers:

```bash
# Local llama.cpp server
export VIVY_LLAMA_URL=http://127.0.0.1:8080
export VIVY_MODEL=gemma-4-e4b

# Any OpenAI-compatible API
export VIVY_LLAMA_URL=https://your-endpoint.com
export VIVY_MODEL=your-model-name
```

**ViVy's engine layer never changes.** Only the weights beneath it do.

---

### Roadmap

- [x] **V1.0** — ElasticNCore + CognitiveStateGraph + Gemma 4 E4B integration
- [x] **V1.0** — VM-11 zero-error-repeat enforcement
- [x] **V1.0** — Multimodal adapter (Text + Vision + Audio)
- [x] **V1.0** — HoH × ViVy agent flow (Antigravity IDE coordinator)
- [ ] **V1.1** — Forager module (autonomous web + file knowledge retrieval)
- [ ] **V1.2** — Persistent cross-session CognitiveStateGraph (disk-backed)
- [ ] **V2.0** — Nemotron Nano Omni integration (Video modality)
- [ ] **V2.0** — Real-time audio streaming (push-to-talk interface)

---

### Invariants (Never Break)

These properties are enforced at the architecture level, not by configuration:

1. **No framework wrappers** inside the engine — no LangChain, AutoGen, Haystack
2. **VM-11**: Error repeat rate = 0% (CognitiveStateGraph error dampening)
3. **Directive-first**: ViVy knows its action type before generating output
4. **ViVy never self-declares COMPLETE** — requires human or Coordinator confirmation
5. **Session isolation**: Each session has its own CognitiveStateGraph instance

---

### License

- **ViVy Core**: [MIT License](LICENSE)
- **Gemma 4 E4B** (base model): [Apache 2.0](https://ai.google.dev/gemma/terms) — Google DeepMind

---

### About

Built by [Ngọc Châu](https://github.com/ngocchau-ai) as part of the **91s AI** project.

> *ViVy doesn't just answer your questions. It owns the problem.*

---

<div align="center">
<sub>ViVy Final Core V1.0 · MIT License · Made in Vietnam 🇻🇳</sub>
</div>
