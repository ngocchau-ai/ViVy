# scripts/ — Bộ Script Vận Hành (Operational Toolkit)

> [!IMPORTANT]
> **Đây là bản MIRROR CÓ CHỦ ĐÍCH — KHÔNG được "dọn trùng lặp".**
>
> Bộ 22 script vận hành này **hiện diện đầy đủ, byte-identical tại CẢ 2 repo**:
>
> | Repo | Vai trò | Cam kết |
> |:---|:---|:---|
> | `Vivy_final/scripts/` | **CODE** (ViVy Core + Cautreo Native) | commit độc lập |
> | `vivyChatGPT/scripts/` | **SPECS** (đặc tả, giao ChatGPT) | commit độc lập |
>
> **Lý do (quyết định D5, 26/09/2026):** hai repo được giao cho hai agent/đầu mối
> khác nhau. Nếu chỉ một bên có script, agent kia sẽ phải **truy cập chéo** sang
> workspace root hoặc repo đối diện — dẫn tới lẫn lộn source code giữa CODE và
> SPECS. Mirror đầy đủ là cách rẻ nhất để mỗi repo tự khép kín.
>
> **Quy tắc cho agent kế thừa:**
> 1. **KHÔNG** xóa, gộp hay "dedupe" `scripts/` giữa 2 repo.
> 2. Sửa script → sửa ở **cả 2 bản** (hoặc sửa 1 bên rồi copy sang bên còn lại),
>    giữ SHA-256 khớp nhau.
> 3. Thêm script vận hành mới → thêm vào **cả 2 repo**.
> 4. Script **dùng một lần** cho migrate/reorg thì **KHÔNG** đưa vào đây —
>    chuyển vào `old-docs/10-workspace-docs/reorg-tooling/` (xem
>    `old-docs/README.md`).

---

## Danh mục script vận hành (cập nhật 2026-09-26)

### Khởi động / vận hành runtime
| Script | Loại | Chức năng |
|:---|:---|:---|
| `start_vivy_unified.ps1` | PowerShell | Khởi động ViVy unified (runtime chính) |
| `start_vivy_gemma4.ps1` | PowerShell | Khởi động ViVy với Gemma 4 E4B Q4_K_M |
| `start_vivy_qwen27b.ps1` | PowerShell | `[ISOLATED 26/09/2026]` Giữ làm tài liệu so sánh — target `qwen3.8-27b.gguf` đã archived, và bản này còn giả định path `D:\Vivy1\.llama-build\bin\llama-server.exe` (sai). Bản sống: `vivy/scripts/start_vivy_qwen27b.ps1`. |
| `start_desktop.ps1` | PowerShell | Khởi động Desktop Studio (Tauri + Vite) |
| `vivy_call.bat` | Batch | Gọi nhanh ViVy từ CLI |
| `vivy_health_check.bat` | Batch | Kiểm tra sức khỏe ViVy nhanh |
| `py_runner.bat` | Batch | Runner Python có kiểm soát (**bản sống**) |
| `run_python.bat` | Batch | `[ISOLATED 26/09/2026]` Trùng byte với `py_runner.bat` (MD5 `07-FE-BD`) → redirect sang `py_runner.bat`. Giữ để không vỡ caller. |
| `convert_to_physical.bat` | Batch | Chuyển đổi sang chế độ physical |

> **[ISOLATED 26/09/2026]** `start_vivy_qwen_coder.ps1` **đã xóa** — trọng số `qwen2.5-coder-7b-instruct-q4_k_m.gguf` không tồn tại trên đĩa (user chỉ thị 26/09/2026), kéo theo gỡ tham chiếu trong `verify_vivy_cautreo_readiness.py` và `models/baselines/*`. Xem `models/baselines/README.md` mục `[ISOLATED]`.

### Kiểm thử / xác minh
| Script | Loại | Chức năng |
|:---|:---|:---|
| `verify_all.ps1` | PowerShell | Chạy full health stack (mypy + ruff + pytest) |
| `verify_cautreo.py` | Python | Xác minh Cautreo C-ABI binding (**stub nhanh**, 18 dòng) |
| `verify_vivy_cautreo_readiness.py` | Python | **Xác minh E2E đầy đủ** (223 dòng) *(bổ sung D5.2)*: (1) Codex Findings Remediation P1 & P2, (2) Cautreo C-ABI in-process Memory & Score Graph, (3) Parallel Decomposition & Compression Input Pipeline, (4) ViVy Inference Loop Context Budget 2048 & Intuition Digest, (5) Dream Engine `LUCID_STANDBY` cycle |
| `run_91sh_workflow_e2e.py` | Python | E2E test adapter `cautreo_91sh_workflow` |
| `test_direct_codex_call.py` | Python | Probe gọi thẳng Codex |

### Đồng bộ tri thức / model
| Script | Loại | Chức năng |
|:---|:---|:---|
| `sync_2brain_dd.py` | Python | Đồng bộ quyết định vào `D:\2brain` (durable-decision) |
| `sync_colab_plan_dd.py` | Python | Đồng bộ kế hoạch Colab vào 2brain |
| `sync_inference_fix_dd.py` | Python | Đồng bộ record fix inference vào 2brain |
| `update_notebook_loader.py` | Python | Cập nhật loader cho notebook |
| `finish_model_download.py` | Python | Hoàn tất tải model về |
| `watch_model_download.ps1` | PowerShell | Theo dõi tiến trình tải model |
| `watch_model_download.py` | Python | Theo dõi tiến trình tải model (Python) |

---

## Kiểm tra mirror

```powershell
# Từ workspace root — so SHA-256 toàn bộ file giữa 2 repo
Get-ChildItem "Vivy_final\scripts" -File | ForEach-Object {
  $a = (Get-FileHash $_.FullName).Hash
  $b = (Get-FileHash ("vivyChatGPT\scripts\" + $_.Name)).Hash
  [PSCustomObject]@{ Name=$_.Name; Match=($a -eq $b) }
} | Where-Object { -not $_.Match }
# -> rỗng nghĩa là mirror OK
```

---

## Lịch Sử Thay Đổi (Changelog)

| Agent | Thời Gian | Hành Động |
|:---|:---|:---|
| Claude Code (D5) | 26/09/2026 | Tạo bản mirror 20 script vận hành vào cả 2 repo (SHA-256 khớp 20/20); viết hướng dẫn chống truy cập chéo; phân biệt với `reorg-tooling/` (dùng một lần) trong `old-docs/10-workspace-docs/`. |
| Claude Code (D5.2) | 26/09/2026 | **Kéo thêm 2 script từ `unitary-reasoner/scripts/`** (phát hiện khi audit coverage): `verify_vivy_cautreo_readiness.py` (bộ E2E 223 dòng — trước đó repo chỉ có stub 18 dòng) và `start_vivy_qwen27b.ps1` (target model khác `qwen_coder`). Mirror 20 → **22**, SHA-256 khớp cả 3 bản (unitary-reasoner + 2 repo). Lý do: đúng cam kết *"script vận hành cần đầy đủ ở cả 2 repo"*. Các script training/benchmark/experiment của `unitary-reasoner/` **vẫn để ngoài** theo *"không phải mang tất cả"*. |
