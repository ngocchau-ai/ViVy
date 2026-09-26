# Vivy Final — ViVy Core (NPS-core) + Cautreo Native · CODE repo

> Repo CODE độc lập, commit riêng lên GitHub. Repo chị em: `vivyChatGPT/` (SPECS — giao ChatGPT).
> Quy tắc 3 điều bắt buộc (changelog / chỉ cô lập không xóa bỏ / đồng bộ `D:\2brain`) — xem `README.md`.

## Health Stack

Chạy từ gốc repo **`Vivy_final/vivy/`** (nơi có `pyproject.toml`):

| Mục | Lệnh | Ngưỡng |
|---|---|---|
| typecheck | `python -m mypy core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ --ignore-missing-imports` | `Success: no issues found` |
| lint | `python -m ruff check core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ tests/` | `All checks passed!` |
| test (baseline) | `python -m pytest tests/ -q` | **676 passed + 17 skipped = 693** |
| test (training) | `python -m pytest training/ -q` | **730 passed + 3 skipped** |
| test (toàn bộ) | `python -m pytest -q` | gộp cả hai (testpaths = `tests` + `training`) |

- Windows: pytest cần `--basetemp=_pytest_tmp` (đã có sẵn trong `addopts`).
- **Scope mypy/ruff = 7 thư mục trên** (chuẩn CLAUDE.md gốc, 64 source files).
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

Bản gốc đã gom: `old-docs/11-consolidated-source-2026-09-26/` (banner `[ISOLATED]` trỏ về doc đích). `docs/ARCHITECTURE.md` là **redirect stub** — ~25 tham chiếu trong `vivy/memory/`, `vivy/orchestration/codex/tasks/` vẫn trỏ đúng tên file.

## Lịch sử thay đổi

| Ngày | Thay đổi | Agent |
|---|---|---|
| 2026-09-26 | Khởi tạo CLAUDE.md cho repo code sau reorg D2–D4; chốt health stack scope 7 thư mục; ghi nhận nợ training/+src/ | Claude Code |
| 2026-09-26 | **Gom tài liệu về 5 doc chuẩn** (xem mục Liên quan). Gỡ tham chiếu 3 gguf không còn trên đĩa, xóa 2 runtime `start_vivy_qwen_coder.ps1`. Dọn trùng lặp (28 file 0 byte, `run_python.bat`, bảng trọng số). Cập nhật baseline test: `tests/` = **693 passed + 0 skipped** (trước ghi 676+17; lệch vì `engine/bin/cautreo_pager.dll` có sẵn nên 17 test native pager chạy thật — tổng 693 khớp). | Claude Code |
