# Kho Lưu Trữ Bản Gốc ViVy Core Thô (Frozen Baseline Core Archive)

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

## 1. Mục Đích & Nguyên Tắc Bảo Tồn (Baseline Isolation)
Thư mục này được thiết lập theo chỉ thị của Ngọc Châu nhằm **cô lập vĩnh viễn trạng thái gốc thô (Raw / Untrained Base Architecture)** của ViVy trước khi tiến hành bất kỳ đợt fine-tuning nào trên Colab hoặc cụm máy tính bên ngoài.

### Nguyên tắc bất biến:
- **Tuyệt đối không ghi đè:** Các file mô hình và cấu hình gốc được bảo vệ để làm thước đo tham chiếu chuẩn (Golden Standard).
- **Phục vụ đối chiếu A/B Testing:** Mọi phiên bản sau khi train (như `vivy_1.5b_q4km.gguf`) khi nạp vào Cautreo Runtime đều phải chạy benchmark đối đầu với bản Baseline này để chứng minh:
  1. *Độ chính xác chọn ứng viên (Bounded Candidate Accuracy)* tăng lên bao nhiêu %?
  2. *Độ trễ phản xạ (Reflex Latency)* có đạt ngưỡng < 300ms không?
  3. *Tỷ lệ tuân thủ định dạng `<vivy_thought>`* có đạt 100% không?
  4. *Tính bảo toàn bộ nhớ (VM-11 dampener; measured rate: Gate-10 receipt)* có được giữ vững trong Cautreo Memory không? <!-- [ISOLATED 24/09/2026] prior: "0% repeat error" — Gate 9: no 0% claim without receipt. -->

## 2. Danh Mục Các Thành Phần Thô Gốc Được Cô Lập

| Tên Mô Hình / Thành Phần | Vị Trí Lưu Trữ | Vai Trò Baseline | Tốc Độ Gốc | Trạng Thái |
| :--- | :--- | :--- | :---: | :--- |
| **Gemma4 E4B Q4_K_M** | `D:\models\gemma4-e4b\vivy-gemma-e4b-q4km.gguf` | Cognitive Reasoner (Tư duy nhận thức gốc) | 14.4 tok/s | **ACTIVE BASELINE** (Port 8080) |
| **Qwen2-VL-72B Q4_K_M** | `D:\models\qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf` (+ `mmproj-f16`) | Multimodal Knowledge Pool (hồ tri thức sâu) | — | **DOWNLOADED_ON_DISK** |
| **Qwen2.5-Coder-1.5B (HF Base)** | HuggingFace Cache (`Qwen/Qwen2.5-Coder-1.5B-Instruct`) | Trọng số thô trước khi nạp LoRA CUA | 45.0 tok/s | **TRAINING BASELINE** |
| **ViVy Core Logic (Python)** | `vivy/` (hợp nhất) · nguồn cũ `unitary-reasoner/` `[ISOLATED]` | Kiến trúc thuần túy không vỏ bọc (Wrapperless) | In-process C-ABI | **UNMODIFIED ENGINE CORE** |

> **[ISOLATED 26/09/2026]** Ba trọng số sau **không còn trên đĩa và bị gỡ toàn bộ tham chiếu sống** (user chỉ thị: *".gguf không còn dùng → xóa"*). Giữ lại đây làm hồ sơ baseline, không dùng làm đích nạp:
>
> | Mô hình | gguf (đã gỡ) | Trạng thái cũ |
> | :--- | :--- | :--- |
> | **Qwen2.5-Coder-7B** | `qwen2.5-coder-7b-instruct-q4_k_m.gguf` | `AVAILABLE_ON_DEMAND` — chưa từng tải |
> | **ViVy2 Parser** | `vivy2.gguf` | `ISOLATED_ARCHIVED` (21/09/2026) — giải phóng NVMe cho Qwen2-VL-72B |
> | **Qwen3.8-27B** | `qwen3.8-27b.gguf` | `ISOLATED_ARCHIVED` (21/09/2026) — giải phóng NVMe cho Qwen2-VL-72B |
>
> Kéo theo: 2 runtime `start_vivy_qwen_coder.ps1` (`scripts/` + `vivy/scripts/`) **đã xóa** vì trỏ vào gguf không tồn tại. Entry metadata vẫn giữ trong `models/model_manifest.json` (đã gắn `ISOLATED_ARCHIVED` / `AVAILABLE_ON_DEMAND`).

> **[ISOLATED 26/09/2026]** Đường dẫn cũ trong bảng này — `Vivy_final/models/*.gguf` — sai 2 chỗ: (1) repo không giữ trọng số (chỉ metadata), (2) tên thư mục là `Vivy_final` sau đổi tên. Nguồn sự thật: `models/model_manifest.json` (`full_path`) + `MODEL_ROOT = D:\models`. Trạng thái theo manifest, không theo bảng cũ.

---

## 3. Quy Trình Nghiệm Thu Đối Chiếu Sau Huấn Luyện (A/B Evaluation Protocol)

Khi checkpoint `vivy_1.5b_q4km.gguf` được huấn luyện xong và chuyển về:
1. Chạy song song bài test Bounded Candidates trên **Bản thô (Qwen 1.5B Base)** vs **Bản đã huấn luyện (ViVy 1.5B Fine-Tuned)**.
2. Kiểm tra độ lệch xác suất (Probability Calibration) qua hàm thưởng Proper Scoring từ Laya.
3. Chỉ nạp vào `CautreoWeightPager` (Sprint R4) khi chỉ số của bản huấn luyện vượt trội bản thô gốc trên cả 4 trục: **Xung đột — Hợp lý — Dư thừa — Hiệu quả**.

---

## 4. Lịch Sử Thay Đổi

| Ngày | Agent | Thay đổi |
| :--- | :--- | :--- |
| 2026-09-26 | Claude Code | **Gỡ tham chiếu gguf không còn trên đĩa** (user chỉ thị). Chuyển Qwen2.5-Coder-7B / ViVy2 / Qwen3.8-27B từ bảng chính sang khối `[ISOLATED]` — trọng số đã gỡ, không dùng làm đích nạp. Thêm dòng **Qwen2-VL-72B** (trước đó thiếu dù có trên đĩa). Xóa 2 runtime `start_vivy_qwen_coder.ps1`. |
| 2026-09-26 | Claude Code | Đồng bộ đường dẫn theo đổi tên thư mục `Vivy final` → `Vivy_final`. Đối chiếu `models/model_manifest.json`: sửa vị trí trọng số về `MODEL_ROOT = D:\models`, sửa trạng thái Qwen2.5-Coder-7B (`AVAILABLE_ON_DEMAND`) và ViVy2 (`ISOLATED_ARCHIVED`). Đường dẫn cũ giữ trong chú thích `[ISOLATED]`. |
