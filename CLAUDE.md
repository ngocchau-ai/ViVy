# Vivy Final — ViVy Core (NPS-core) + Cautreo Native · CODE repo

> Repo CODE độc lập, commit riêng lên GitHub. Repo chị em: `vivyChatGPT/` (SPECS — giao ChatGPT).
> Quy tắc 3 điều bắt buộc (changelog / chỉ cô lập không xóa bỏ / đồng bộ `D:\2brain`) — xem `README.md`.

## Health Stack

Chạy từ gốc repo **`Vivy final/vivy/`** (nơi có `pyproject.toml`):

| Mục | Lệnh | Ngưỡng |
|---|---|---|
| typecheck | `python -m mypy core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ --ignore-missing-imports` | `Success: no issues found` |
| lint | `python -m ruff check core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ tests/` | `All checks passed!` |
| test (baseline) | `python -m pytest tests/ -q` | **676 passed + 17 skipped = 693** |
| test (training) | `python -m pytest training/ -q` | **730 passed + 3 skipped** |
| test (toàn bộ) | `python -m pytest -q` | gộp cả hai (testpaths = `tests` + `training`) |

- Windows: pytest cần `--basetemp=_pytest_tmp` (đã có sẵn trong `addopts`).
- **Scope mypy/ruff = 7 thư mục trên** (chuẩn CLAUDE.md gốc, 64 source files).
- Nợ kỹ thuật **ngoài scope** (có sẵn từ nguồn `vivyChatGPT/training` + `src/`, không do merge): 164 lỗi mypy / 109 lỗi ruff ở `training/`+`src/`+`experiments/`. Ghi nhận tại `docs/DATA_MAP_2026-09-26.md` mục 6 — không sửa ồ ạt khi chưa được duyệt.

## Cây trụ (pillar)

```
vivy/       runtime NPS-core hợp nhất  (import top-level: engine. / memory. / training. …)
engine/     Cautreo native C-ABI  (bin/*.dll, include/*.h, src/weight_pager)
cautreo/    atlases + native habitat specs
host/       host mảnh + IPC Bus + plugins
ui/         desktop-studio (Tauri) + cautreo-desktop
models/     model_manifest.json + baselines  (metadata — KHÔNG phải trọng số)
scripts/    launcher + verify_all.ps1
docs/       ARCHITECTURE_FINAL, RUNBOOK, CHECKPOINTS, DATA_MAP…
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

- `docs/CHECKPOINTS.md` — số liệu byte từng checkpoint (D3: lưu nội bộ).
- `docs/DATA_MAP_2026-09-26.md` — bản đồ dữ liệu (di chuyển / hợp nhất / xóa bỏ).
- `docs/ARCHITECTURE_FINAL.md`, `docs/RUNBOOK.md` — kiến trúc + vận hành.

## Lịch sử thay đổi

| Ngày | Thay đổi | Agent |
|---|---|---|
| 2026-09-26 | Khởi tạo CLAUDE.md cho repo code sau reorg D2–D4; chốt health stack scope 7 thư mục; ghi nhận nợ training/+src/ | Claude Code |
