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
| **Gemma4 E4B Q4_K_M** | `Vivy final/models/gemma4-e4b.gguf` | Cognitive Reasoner (Tư duy nhận thức gốc) | 14.4 tok/s | **ACTIVE BASELINE** (Port 8080) |
| **Qwen2.5-Coder-7B** | `Vivy final/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf` | Code Specialist (Mã nguồn chuyên biệt) | 9.5 tok/s | **ACTIVE BASELINE** (Port 8081) |
| **ViVy2 Parser** | `Vivy final/models/vivy2.gguf` | Fast Baseline Tokenizer & Parser | 28.0 tok/s | **STANDBY BASELINE** |
| **Qwen2.5-Coder-1.5B (HF Base)** | HuggingFace Cache (`Qwen/Qwen2.5-Coder-1.5B-Instruct`) | Trọng số thô trước khi nạp LoRA CUA | 45.0 tok/s | **TRAINING BASELINE** |
| **ViVy Core Logic (Python)** | `unitary-reasoner/` & `Vivy final/core/` | Kiến trúc thuần túy không vỏ bọc (Wrapperless) | In-process C-ABI | **UNMODIFIED ENGINE CORE** |

---

## 3. Quy Trình Nghiệm Thu Đối Chiếu Sau Huấn Luyện (A/B Evaluation Protocol)

Khi checkpoint `vivy_1.5b_q4km.gguf` được huấn luyện xong và chuyển về:
1. Chạy song song bài test Bounded Candidates trên **Bản thô (Qwen 1.5B Base)** vs **Bản đã huấn luyện (ViVy 1.5B Fine-Tuned)**.
2. Kiểm tra độ lệch xác suất (Probability Calibration) qua hàm thưởng Proper Scoring từ Laya.
3. Chỉ nạp vào `CautreoWeightPager` (Sprint R4) khi chỉ số của bản huấn luyện vượt trội bản thô gốc trên cả 4 trục: **Xung đột — Hợp lý — Dư thừa — Hiệu quả**.
