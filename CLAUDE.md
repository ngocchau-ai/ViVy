# Vivy Final — ViVy Core (NPS-core) + Cautreo Native · CODE repo

> Repo CODE độc lập, commit riêng lên GitHub. Repo chị em: `vivyChatGPT/` (SPECS — giao ChatGPT).
> Quy tắc 3 điều bắt buộc (changelog / chỉ cô lập không xóa bỏ / đồng bộ `D:\2brain`) — xem `README.md`.

## Health Stack

Chạy từ gốc repo **`Vivy_final/vivy/`** (nơi có `pyproject.toml`):

| Mục | Lệnh | Ngưỡng |
|---|---|---|
| typecheck | `python -m mypy core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ --ignore-missing-imports` | `Success: no issues found` |
| lint | `python -m ruff check core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ tests/` | `All checks passed!` |
| test (baseline) | `python -m pytest tests/ -q` | **976 passed + 0 skipped** |
| test (training) | `python -m pytest training/ -q` | **768 passed + 3 skipped** |
| test (toàn bộ) | `python -m pytest -q` | gộp cả hai (testpaths = `tests` + `training`) |

- Windows: pytest cần `--basetemp=_pytest_tmp` (đã có sẵn trong `addopts`).
- **Scope mypy/ruff = 7 thư mục trên** (chuẩn CLAUDE.md gốc, 66 source files).
- Nợ kỹ thuật **ngoài scope** (có sẵn từ nguồn `vivyChatGPT/training` + `src/`, không do merge): 164 lỗi mypy / 109 lỗi ruff ở `training/`+`src/`+`experiments/`. Ghi nhận tại `docs/TREE_MAP_AND_CHANGELOG.md` §Phần 1 mục 6 (nguyên bản `docs/DATA_MAP_2026-09-26.md`) — không sửa ồ ạt khi chưa được duyệt.

## Cây trụ (pillar)

```
vivy/       runtime NPS-core hợp nhất  (import top-level: engine. / memory. / training. …)
engine/     Cautreo native C-ABI  (bin/*.dll, include/*.h, src/weight_pager)
cautreo/    atlases + native habitat specs
host/       host mảnh + IPC Bus + plugins
ui/         desktop-studio (Tauri) + cautreo-desktop
models/     model_manifest.json + baselines  (metadata — KHÔNG phải trọng số)
scripts/    launcher + verify_all.ps1
docs/       5 doc chuẩn + RUNBOOK + CHECKPOINTS + adr/  (xem mục Liên quan)
internal/   kho checkpoint 6.40 GB — GITIGNORED, xem docs/CHECKPOINTS.md
```

**Import style:** absolute top-level packages (`from engine.…`, `from memory.…`, `from training.…`). **Không đổi tên package** — 28 module import `training.*`. `pythonpath`/cwd = `vivy/`.

## Ràng buộc cứng

1. **GitHub chặn file > 100 MB** — mọi `.pt/.gguf/.npy/.npz/.safetensors` nằm trong `internal/` và bị `.gitignore`. Không bao giờ `git add` trọng số.
2. **`.env` không bao giờ commit** (secret).
3. **Không đổi tên package import.** Nếu buộc đổi, phải sửa toàn bộ importer + chạy lại full health stack.
4. **Cô lập, không xóa** nội dung kiến trúc cũ — đánh dấu `[ISOLATED / DEPRECATED / REPLACED]` + ghi vào changelog `README.md`.
5. **Cautreo DLL search path** nằm ở `vivy/integration/cautreo_binding.py` (`_find_cautreo_dll` / `_find_pager_dll`). Path repo-relative đứng đầu; các path cũ giữ làm fallback `[ISOLATED]`. Sau khi di chuyển repo, kiểm lại hàm này.

## Nợ / cô lập đang mở

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| `training/test_dataset_audit.py::DatasetAuditTests` | `[ISOLATED 2026-09-26]` | test kỳ vọng API cũ `audit(path)→dict`; module đã fail-closed `audit_rows/audit_file`. Vỡ sẵn từ nguồn — giữ để tham khảo |
| mypy/ruff `training/`+`src/`+`experiments/` | ghi nhận | ngoài scope health-stack; 164/109 findings, phần lớn F401/UP035 fix được |

## Liên quan

**5 tài liệu chuẩn** (gom 26/09/2026 — hết nạn tài liệu thô / sửa đổi / v1-v2-v3):

| # | File | Tên | Nội dung |
|---|---|---|---|
| 1 | `docs/RAW_CONSOLIDATED.md` | Tài liệu thô tổng hợp | Ý tưởng gốc 3 model + hình học siêu chiều + kế hoạch v2 |
| 2 | `docs/TECHNICAL_DIRECTION.md` | Tài liệu định hướng kỹ thuật | NPS Core, nỗi đau/giải pháp, context, MoE, orchestration |
| 3 | `docs/ARCHITECTURE_FINAL.md` | Tài liệu thiết kế cuối cùng | Đặc tả kiến trúc **có hiệu lực** + Phụ lục A–N (data cũ, ghi chú cô lập) |
| 4 | `docs/TREE_MAP_AND_CHANGELOG.md` | Tree map diễn biến & lịch sử | Data map, biên bản reorg, snapshot tối ưu, báo cáo công việc |
| 5 | `docs/REVIEWS.md` | Tài liệu review | Mọi review / thẩm định / quyết định bền vững |

Tài liệu **ngoài** 5 doc (vận hành / meta, không gom): `README.md`, `CLAUDE.md`, `docs/RUNBOOK.md`, `docs/CHECKPOINTS.md`, `docs/adr/ADR-001..007`, `docs/public/{architecture,quickstart}.md`.

Tài liệu thiết kế (đặc tả chưa triển khai): `docs/DESIGN_GAME_CRITERIA_LAYER.md` (27/09/2026 — tầng tiêu chí thẩm mỹ · logic game · góc nhìn người chơi; CHỈ thiết kế, không code).

Bản gốc đã gom: `old-docs/11-consolidated-source-2026-09-26/` (banner `[ISOLATED]` trỏ về doc đích). `docs/ARCHITECTURE.md` là **redirect stub** — ~25 tham chiếu trong `vivy/memory/`, `vivy/orchestration/codex/tasks/` vẫn trỏ đúng tên file.

## Lịch sử thay đổi

| Ngày | Thay đổi | Agent |
|---|---|---|
| 2026-09-26 | Khởi tạo CLAUDE.md cho repo code sau reorg D2–D4; chốt health stack scope 7 thư mục; ghi nhận nợ training/+src/ | Claude Code |
| 2026-09-26 | **Gom tài liệu về 5 doc chuẩn** (xem mục Liên quan). Gỡ tham chiếu 3 gguf không còn trên đĩa, xóa 2 runtime `start_vivy_qwen_coder.ps1`. Dọn trùng lặp (28 file 0 byte, `run_python.bat`, bảng trọng số). Cập nhật baseline test: `tests/` = **693 passed + 0 skipped** (trước ghi 676+17; lệch vì `engine/bin/cautreo_pager.dll` có sẵn nên 17 test native pager chạy thật — tổng 693 khớp). | Claude Code |
| 2026-09-27 | **Fix readiness gate FAIL vĩnh viễn** — `verify_codex_remediations()` vẫn ghi `results["qwen_coder_artifact_present"] = False` cho check đã `[ISOLATED 26/09/2026]`, mà `main()` chấm bằng `all(values)` → OVERALL VERDICT luôn FAIL dù 5 nhóm còn lại xanh. Ngừng emit key đã loại bỏ (giữ print làm audit trail) ở cả `vivy/scripts/` + `scripts/`. Thêm regression test `vivy/tests/test_readiness_gate.py` (2 test). Đồng bộ baseline `tests/` = **695 passed + 0 skipped** (693 + 2 test mới) — sửa bảng trên vốn còn ghi 676+17 lệch với changelog 26/09. Health stack: mypy `64 source files` sạch, ruff sạch, training `730+3` khớp. | Claude Code |
| 2026-09-27 | **Thêm `docs/DESIGN_GAME_CRITERIA_LAYER.md`** (đặc tả thiết kế, CHỈ tài liệu — HARD GATE `/office-hours`, không code/scaffolding). Nội dung: 3 trục tiêu chí **thẩm mỹ · logic game · góc nhìn người chơi** làm nội dung cho máy chấm điểm sẵn có; kiến trúc 3 tầng INGEST (online, trả tiền 1 lần) → DISTILL (offline) → COMPOSE (offline, không LLM); cơ chế biến điểm chấm mềm thành tiêu chí cứng qua `features` kiểm chứng được; schema annotation/criterion/criterion-set; bảng cắm vào code hiện có; nguồn schema mượn (CDDA `copy-from`, LPC JSON parts, Tiled TMX, flecs, OpenUSD, Yarn/ink) kèm cảnh báo copyleft/brand-IP; receipt truy nguồn. Quyết định D11/D12/D14. Health stack giữ nguyên: tests 695, mypy 64 source files, ruff sạch. | Claude Code |
| 2026-09-29 | **WP-1/O-01 — Fail-fast wiring, hết stub im lặng (T0).** Sửa F-A07/G-02: `orchestrator/engine.py` gỡ 4 khối `try/except ImportError → stub` (import trực tiếp, fail-loud); bỏ `_StubEvolution` + 3 chỗ `__mro__[1]()` (vi phạm ADR-005); `_evaluate` ngừng nuốt ngoại lệ và bịa `("continue", 0.9)`. **Mới** `orchestrator/wiring_report.py` — receipt REAL/STUB/MISSING, `raise_if_unwired()` từ chối boot khi còn stub/thiếu. `src/vivy/core/model_loader.py`: `MockLocalEngine` bị cấm ngoài opt-in tường minh (`allow_mock=True` / `VIVY_ALLOW_MOCK_ENGINE`); thiếu `llama_cpp` → `EngineUnavailableError`. `src/vivy/api/router.py` bỏ hardcode `ModelBackend.MOCK` lúc import. Test mới `tests/test_wiring_failfast.py` (12). Baseline `tests/` **695 → 707 passed**. | Claude Code |
| 2026-09-29 | **WP-2/O-03 — Điều khiển vòng lặp (T4).** Fix F-B01/B02/B03: `vivy_inference_loop.py` truyền đủ đầu vào `resolve()` (`tool_failed`/`repeated_failure`/`evidence_verified` — trước luôn default `False` nên HALT không thể xảy ra); cắt tập "tiếp tục vòng" từ `{FORAGE, DELEGATE, CONTINUE, BACKTRACK}` xuống `{FORAGE, BACKTRACK}`; `_parse_epistemic_decision` fail-closed (thiếu trường → `""`, không phải `"EXECUTE_DIRECTLY"`). `decision_controller.py`: `DecisionContext` thêm `budget_exhausted` + `single_round`; `resolve()` trả HALT khi evidence VERIFIED; `single_round=True` bỏ luật ngân sách (hết F-B02: CHAT/BATCH luôn DELEGATE). Chống false-halt: không ghi đè FORAGE/DELEGATE/BACKTRACK thành HALT. Test mới `tests/test_loop_control.py` (14). Baseline `tests/` **707 → 721 passed**. | Claude Code |
| 2026-09-29 | **WP-3/O-04 — Hợp nhất backend LLM (F-A09/F-B06).** **Mới** `llm_bridge/backend.py` (`LLMBackend`: URL · model-id · timeout · num_ctx, một nguồn cấu hình). `client.py` **bỏ fallback 17 model cloud** — model thiếu → `ModelUnavailableError`, không chuyển model ngầm; catalogue giữ `[ISOLATED]`. Timeout tách `LLMTimeoutError`. `llama_cpp_bridge.py`: `LlamaCppConfig` lấy default từ `LLMBackend`; mọi `ChatResponse` mang `backend_id`+`model_id` theo server echo. ADR-007 viết lại (một hợp đồng OpenAI-compatible, một cấu hình). Test mới `tests/test_backend.py` (8) + `tests/test_client.py` (11); 4 test cũ ghim hành vi fallback viết lại theo đặc tả kèm receipt. Baseline `tests/` **721 → 734 passed** (721−7 cũ+19 mới). | Claude Code |
| 2026-09-29 | **WP-4/O-13 — RiskGate giao dịch (D-3, ghi đè triết lý \"CẤM GÁC CỔNG LẬP TRÌNH\").** Chủ dự án quyết định D-3 (29/09) thay triết lý cấm mọi gác cổng lập trình bằng lớp an toàn fail-closed, sau khi review đo 0/30 lệnh đối kháng bị chặn (G-01/G-02/G-03). Thêm `vivy/src/vivy/hands/risk_gate.py` (độc lập LLM, giấy phép an toàn **không** phải bộ lọc chiến lược; `parse_finite_float` không default; mặc định paper trading) + `docs/adr/ADR-008-risk-gate.md` (INV-08). `docs/TECHNICAL_DIRECTION.md` 5 chỗ đánh dấu `[REPLACED 29/09]` + link ADR-008, **không xóa**. Sửa prompt (`prompts.py`) — hết nói dối \"no hardcoded filters\"; `inference.py` hết bịa volume/SL mặc định; `mt5_executor.py` mọi lệnh qua RiskGate; `api/router.py` bỏ \"No Gatekeepers\" + truyền `current_price`. **Phát hiện:** `src/` không trên sys.path của pytest → toàn bộ dòng trading chưa từng có test chạy; thêm `pythonpath=["src"]` vào `pyproject.toml` + gỡ `test_eyes_hands.py`/`test_vivy_core.py` khỏi `collect_ignore_glob`. Test mới `tests/test_risk_gate.py` (104 test, **ma trận 65 đầu ra đối kháng → 0 lệnh lọt**, đạt T10 ≥60). 2 test cũ viết lại theo đặc tả kèm receipt (hard-rule #4). Baseline `tests/` **695 → 847 passed** (734 tại WP-3 + 113). Training 730+3, mypy 66 source files, ruff sạch. | Claude Code |
| 2026-09-29 | **WP-5/O-12 — Giao diện trung thực (Gate 9).** Sửa F-F01…F-F07, F-C07: `vision.py` fail-closed + hết bịa 1024×1024; `reasoning_engine.py` hết claim "đã xử lý hình ảnh"; `multimodal_clairvoyance/*` + `vivy_ollama/*` gắn `[ISOLATED]`+`SIMULATED`; `cautreo_cartographer.py::scan_model` gắn `SIMULATED` + `render_for_prompt()` **raise**; `moe_brain.py` đổi "70B MoE / 1B active" → 524.288 tham số phức/expert; `Modelfile.vivy-clairvoyance` bỏ "zero-hallucination"; `model_manifest.json` gắn `[UNMEASURED]`. **Mới** `docs/CAPABILITY_LEDGER.md` (sổ năng lực: claim → receipt hoặc `UNMEASURED`) + `tests/test_capability_honesty.py` (tripwire Gate 9). `tests/unit/test_vivy_multimodal_interface.py` viết lại theo đặc tả (test cũ ghim hành vi bịa). Baseline `tests/` **847 → 888 passed**. |
| 2026-09-29 | **WP-6/O-10 — Đường dữ liệu sạch, hết nhãn bịa (T9).** Sửa F-H01…F-H04. `training/dataset_extractor.py` **viết lại**: bỏ hardcode `AST_VALID_AND_TEST_PASS` / `COGNITIVE_CONSENSUS_VERIFIED` / `MULTIMODAL_GROUNDING_VERIFIED` — nhãn suy từ trường bằng chứng của record hoặc ghi `UNVERIFIED`; reward chỉ trả khi có `evidence_receipt_id`; `capture_id_matched` lấy từ record (`NOT_CHECKED` khi im lặng); mẫu không receipt bị loại. `confirm_gold.py`: oracle đóng dấu `kind="oracle"` + `oracle_confirmed`, hết mạo nhận `human-accept`. `check_known_limits.py`: entry thiếu receipt ref → FAIL. `dataset_audit.py` sở hữu `FABRICATED_EVIDENCE_LABELS`/`assert_exportable`; `decision_contract.py` thêm `SchemaMismatchError`/`require_typed`. **Mới** `training/test_no_fabricated_labels.py` (38 test). 5 test cũ ghim hành vi bịa viết lại theo đặc tả kèm receipt. `training/vivy_train_dataset.jsonl` (501 dòng, 451 mang nhãn bịa) giữ nguyên, vẫn bị `smoke_train` từ chối. **SFT dừng cho tới khi T9 đạt.** Baseline `training/` **730+3 → 768+3**, `tests/` **888 → 889 passed**. |
| 2026-09-29 | **WP-7/O-02 — Harness đo + baseline (T2).** **Mới** `vivy/benchmarks/`: `eval_set/` 120 câu 4 miền × 30 (8 dev + 22 held-out mỗi miền, 30 đối kháng), bộ sinh tất định seed `20260929` với **đáp án tính ra bằng chương trình**; `checker.py` chấm lập trình theo `expected_kind`, **cấm khớp chuỗi con**; `harness.py` chạy A/B/C (Gemma thuần · `VivyInferenceLoop` · pipeline + `Decoder`) và ghi receipt `evidence/T2-<run_id>.json`. **D-7:** held-out ngoài repo, repo chỉ giữ SHA256 (`heldout_manifest.json`), `generate.py` exit 2 nếu ghi vào `Vivy_final/`. **D-8:** trần treo 120 s / 4096 token là **chặn treo** không phải ngân sách; trần bị chạm tính là **quan sát bị che** (`n_ceiling_hits`/`accuracy_uncensored`), không gộp vào "trả lời sai". **3 lỗi thật bắt được khi đấu dây đo, có regression test:** trần treo trang trí do `ThreadPoolExecutor.shutdown(wait=True)` → `threading.Thread(daemon=True)`; `LLMClient` cache `httpx.AsyncClient` cross-event-loop làm câu thứ 2 chết và **bị chấm sai vì lỗi plumbing** (thuộc `llm_bridge/`, để WP-15); parser khai báo sót ranh giới mệnh đề nên *"…, but ANSWER: 24"* không bị tính là bịa đáp án. **Mới** `tests/test_benchmarks_eval.py` (74 test). Baseline `tests/` **889 → 963 passed**, `training/` 768+3, mypy 66 source files, ruff sạch. Nghiệm thu T2 đang đo trên 88 câu held-out. |
| 2026-09-29 | **WP-8 — Nối đường học an toàn (T8).** Fix **F-B05**: `independently_verified=False` hardcode tại call site `evaluate_multi_stream` **và** `evidence_packet` không được truyền → `VERIFIED_RESULT` không tới được → `LessonStore.promote()` không bao giờ chạy → **0 bài học, hệ thống không học được**. `integration/evidence.py` thêm `derive_independent_verification()` + `build_evidence_packet()` — cờ độc lập **suy từ dòng dispatch thật** (≥1 tool `ok`, 0 tool fail), không do model tự khẳng định; trả `(packet, independently_verified)` để caller không quên chuyển tiếp. "Độc lập" cố ý hẹp = **thành công quy trình**, không phải đúng ngữ nghĩa (xác minh ngữ nghĩa là WP-11). `vivy_inference_loop.py` dựng packet tại chỗ dòng dispatch còn tồn tại; confidence lấy từ `session.bridge.calibrate_multi_stream_confidence` (mypy bắt call nhầm `self._bridge` — cầu LLM). `lesson_store.promote()` **fail-closed** khi `provenance` thiếu `evidence` (trước: chỉ validate khi key có mặt → `provenance={}` lọt qua). `EvidencePacket.valid_for_promotion()` siết: packet tự ghi `REJECTED:` không được promote (trước chỉ kiểm không rỗng). **Mới** `tests/test_safe_learning_path.py` (11 test) — replay 10 ca đối kháng → **0 thăng cấp sai**; chuỗi thật `DispatchResult → build_evidence_packet → evaluate_multi_stream → promote` ra ≥1 bài học VERIFIED; tripwire quét code sống chặn F-B05 quay lại. 2 test cũ ghim hành vi sai (`provenance={}` vẫn ACCEPTED) viết lại theo đặc tả kèm receipt. Baseline `tests/` **963 → 976 passed**, `training/` 768+3, mypy 66 source files, ruff sạch. |
