# ViVy Final V1.0 & Cautreo Native Engine — Cẩm Nang Vận Hành Thực Tiễn (Runbook)

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

---

## 1. Khởi Chạy Nhanh 1 Chạm (1-Touch Quick Start)

### Lệnh 1: Kiểm Tra Toàn Diện Hệ Thống (Pre-flight Sanity Check)
Kiểm tra tính toàn vẹn của binaries, models, Python core và kết nối C-ABI:
```powershell
cd "d:\91s_Vivy\Vivy final"
.\scripts\verify_all.ps1
```
*Kết quả kỳ vọng:* `Summary: 11 PASSED, 0 FAILED - ALL GATES CLEARED`.

### Lệnh 2: Khởi Chạy ViVy Core Hợp Nhất (Soul + Vessel)
Khởi động phiên làm việc tương tác có kích hoạt Cautreo In-Process Memory:
```powershell
cd "d:\91s_Vivy\Vivy final"
.\scripts\start_vivy_unified.ps1
```

---

## 2. Vận Hành Cautreo Standalone (Độc Lập Như Ollama)

Cautreo có thể vận hành độc lập hoàn toàn mà không cần Python:

### Chế độ 1: Tương Tác Dòng Lệnh Trực Tiếp (CLI Chat)
```powershell
cd "d:\91s_Vivy\Vivy final\engine\bin"
.\cautreo.exe chat --model "..\..\models\gemma4-e4b.gguf"
```

### Chế độ 2: Máy Chủ OpenAI-Compatible API (Port 8080)
Khởi chạy server phục vụ Antigravity IDE, Cursor, hoặc WebUI:
```powershell
cd "d:\91s_Vivy\Vivy final\engine\bin"
.\cautreo-server.exe --port 8080 --model "..\..\models\gemma4-e4b.gguf"
```
*Endpoint kiểm tra sức khỏe:* `http://127.0.0.1:8080/health`  
*Endpoint chat chuẩn:* `http://127.0.0.1:8080/v1/chat/completions`

---

## 3. Điều Phối Mô Hình Chuyên Dụng (Multi-Model Dispatch)

ViVy Core tự động điều phối giữa hai mô hình:
1. **Lập luận nhận thức (Cognitive Reasoner):** `gemma4-e4b` (Gemma 4 E4B Q4_K_M ~8.95GB).
2. **Lập trình kỹ thuật (Technical Specialist):** `qwen2.5-coder:7b` (Qwen 2.5 Coder 7B ~4.7GB qua Ollama hoặc Cautreo).

*Cấu hình biến môi trường tùy chỉnh:*
```powershell
$env:VIVY_MODEL       = "gemma4-e4b"
$env:VIVY_CODER_MODEL = "qwen2.5-coder:7b"
```

---

## 4. Vận Hành HoH Default Agent & Dream Engine

Từ phiên bản ViVy Final, mọi tác vụ gắn skill HoH do **ViVy Final** phụ trách trực tiếp. Antigravity IDE đóng vai trò Giám Định (Auditor / Scorer):

### 4.1. Khởi chạy nhiệm vụ HoH với ViVy Final
```powershell
python .agents/skills/hoh-vivy-default/scripts/vivy_call.py `
  --task "Xây dựng tính năng mới" `
  --workspace "d:\91s_Vivy"
```
*(Script sẽ tự động nạp Intuition Digest từ Cautreo RAM, gọi ViVy Final, và kích hoạt Dream Engine khi chờ task mới).*

### 4.2. Antigravity Chấm Điểm & Ghi Nhật Ký Cautreo
```powershell
python .agents/skills/hoh-vivy-default/scripts/hoh_scoring_journal.py `
  --task-id "task_001" `
  --progress 0.95 `
  --efficiency 0.90 `
  --summary "Nhiệm vụ hoàn thành xuất sắc 100% tests pass" `
  --constraint "Error repeats dampened; measured rate: Gate-10 receipt" `
  --dream
```

### 4.3. Cơ Chế Dream Engine (Idle / Standby)
Khi kết thúc nhiệm vụ và rơi vào trạng thái chờ, chu trình Dream tự động:
1. Đọc điểm số & nhận xét từ Cautreo Library (`score_graph`, `context_memory`).
2. Đồng hóa nhận thức, nâng cấp Constraints thành Invariants trong `CognitiveStateGraph`.
3. Tinh lọc `Intuition Digest ~150 tokens` nạp sẵn vào Cautreo RAM native.
4. Đưa ViVy vào trạng thái **`LUCID_STANDBY`** sẵn sàng thức tỉnh tức thì. <!-- [ISOLATED 24/09/2026] prior: "thức tỉnh 0ms" — Gate 9: latency claim requires receipt. -->

---

## 5. Xử Lý Sự Cố & Khôi Phục (Troubleshooting & Recovery)

| Triệu chứng | Nguyên nhân tiềm ẩn | Biện pháp xử lý |
|:---|:---|:---|
| `cautreo.dll not found` | Đường dẫn `CAUTREO_DLL_PATH` chưa trỏ đúng | Chạy script `.\scripts\start_vivy_unified.ps1` (đã tự động bind đường dẫn tuyệt đối). |
| `Cannot connect to llama-server at port 8080` | Server suy luận chưa bật | Bật `cautreo-server.exe` trên port 8080 hoặc khởi động `llama-server`. |
| `Inference latency > 30s` | Context slot bị đầy hoặc CPU bị tranh chấp | ViVy sẽ tự động kích hoạt `Context Chain Engine (CCE)` để bóc tách context về cửa sổ 2048 tokens. |

---

## 6. Lịch Sử Thay Đổi (Changelog)

| Agent | Thời gian | Hành động |
|:---|:---|:---|
| Antigravity IDE | 21/09/2026 17:15 ICT | Khởi tạo tài liệu RUNBOOK.md hướng dẫn vận hành 1 chạm cho ViVy final. |
| Antigravity IDE (HoH ViVy Final Transition) | 21/09/2026 17:40 ICT | Bổ sung Mục 4: Quy trình vận hành HoH Default Agent, Antigravity Scoring Journal vào Cautreo Library, và Dream Engine Standby Cycle. |
