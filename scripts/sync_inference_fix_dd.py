import os

content = """# Durable Decision — HoH Inference Timeout, Empty Content & Reasoning Resolution

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi.
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** Đóng khung cô lập và đánh dấu [ISOLATED / DEPRECATED / REPLACED].
> 3. **Đồng bộ D:\\2brain đầy đủ:** Cập nhật kho tri thức trung tâm D:\\2brain.

**Ngày ban hành:** 23/09/2026 ICT
**Quyết định bởi:** Ngọc Châu (CEO) & Antigravity IDE
**Trạng thái:** ACTIVE & VERIFIED

---

## 1. Bản Chất Vấn Đề (Root Cause Analysis)
Codex phản hồi:
- `/health`: PASS
- `/v1/models`: PASS
- Direct API retry / HoH vivy_call.py: Treo / không trả nội dung (empty content).
- Blocker: Chưa có directive hợp lệ của ViVy nên Codex chưa thể bắt đầu thiết kế desktop app `cautreo_dsk` hoặc sao chép source `Vivy_final`.

**Nguyên nhân kỹ thuật cốt lõi phát hiện:**
1. **Lỗi rỗng `message.content`**: Llama-server mặc định trích xuất suy luận vào trường `message.reasoning_content` và để trống `message.content = ""`. Các client OpenAI tiêu chuẩn (như Codex CLI, standard SDK) chỉ đọc trường `content`, do đó nhận về chuỗi rỗng.
2. **Lỗi timeout do suy luận vô tận**: Khi không giới hạn budget suy luận, Gemma4 E4B sinh tới 1.200 - 1.500 tokens suy luận nội tâm mất >98 giây trên CPU. Client phía ngoài hết thời gian chờ (timeout 60-90s) và đóng kết nối.
3. **Lỗi nghẽn slot `--parallel 1`**: Khi 1 request suy luận đang chạy, mọi request retry tiếp theo bị xếp hàng chờ, gây ra hiện tượng treo toàn hệ thống.

---

## 2. Giải Pháp Khắc Phục Triệt Để (Remediation Architecture)
1. **Ép toàn bộ nội dung suy luận & directive vào `message.content`**:
   - Thêm `--reasoning-format none` vào tham số khởi động của `llama-server.exe`.
   - Kết quả: `message.content` luôn được điền đầy đủ 100% nội dung (chứa cả `<vivy_thought>` và Directive), `reasoning_content = None`. Standard OpenAI client đọc trực tiếp không bao giờ bị rỗng.
2. **Khống chế thời gian suy luận (Thinking Budget)**:
   - Thêm cờ `--reasoning-budget 384` để giới hạn suy luận trong phạm vi ngắn gọn.
   - Thời gian sinh giảm từ 98s xuống còn **28s - 41s** (tốc độ ~13 - 14.2 tokens/s).
3. **Mở rộng hàng đợi song song `--parallel 2`**:
   - Khởi động với 2 slot xử lý, đảm bảo request mới hoặc health check không bị nghẽn khi slot khác đang hoạt động.
4. **Nâng cấp `vivy_call.py`**:
   - Tăng `VIVY_REQUEST_TIMEOUT` lên 180s.
   - Đặt `max_tokens: 768` và bổ sung stop sequence `["<end_of_turn>", "<|turn>user", "<|turn>model"]`.

---

## 3. Bằng Chứng Thực Chứng (Verification Evidence)
1. **Direct API Test (`test_direct_codex_call.py`)**:
   - Gọi trực tiếp theo format OpenAI tiêu chuẩn: **Elapsed 41.99s, Content Length: 2.238 ký tự, Reasoning: None**. Hoàn toàn không còn lỗi rỗng nội dung.
2. **HoH Task Call (`cautreo_dsk_session`)**:
   - Thực thi lệnh:
     ```cmd
     D:\\91s_Vivy\\scripts\\vivy_call.bat --task "Phat directive cho Codex bat dau thiet ke cautreo_dsk desktop app" --session "cautreo_dsk_session" --compact-brief
     ```
   - ViVy phát Directive chính thức:
     ```text
     <vivy_thought>
     Confidence: HIGH
     Epistemic_Decision: EXECUTE_DIRECTLY
     Expected_Evidence: Một bản kế hoạch chi tiết (Technical Specification Document - TSD) cho việc thiết kế ứng dụng desktop cautreo_dsk bằng cách sử dụng các công nghệ phù hợp và xác định các module cần thiết.
     Plan/Directive: ViVy Final sẽ tạo ra một bản đề xuất kiến trúc và các bước triển khai ban đầu cho cautreo_dsk theo yêu cầu của Antigravity IDE.
     </vivy_thought>
     ```
   - Xuất file `.vivy_last_response.json` (timestamp 13:52:29 ICT) và `.vivy_handoff.json` (`READY_FOR_REVIEW`).
   - Chu trình Dream Engine hoàn thành, chuyển trạng thái sang `LUCID_STANDBY` (1.3ms).

---

## 4. Changelog
| Agent | Thời gian | Hành động |
|---|---|---|
| Antigravity IDE | 23/09/2026 13:53 ICT | Khắc phục triệt để lỗi inference treo/rỗng content, mở đường cho Codex nhận directive phát triển cautreo_dsk. |
"""

target = r"D:\2brain\hot-memory\DD_V6_HOH_INFERENCE_TIMEOUT_AND_CONTENT_FIX.md"
with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Successfully synced: {target}")
