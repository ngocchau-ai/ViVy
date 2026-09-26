import os

content = """# Durable Decision — ViVy 1.5B Google Colab Training Plan & ChatGPT Runbook

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi.
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** Đóng khung cô lập và đánh dấu [ISOLATED / DEPRECATED / REPLACED].
> 3. **Đồng bộ D:\\2brain đầy đủ:** Cập nhật kho tri thức trung tâm D:\\2brain.

**Ngày ban hành:** 23/09/2026 ICT
**Quyết định bởi:** Ngọc Châu (CEO) & Antigravity IDE
**Trạng thái:** ACTIVE & VERIFIED

---

## 1. Mục Tiêu & Kiến Trúc Kế Hoạch Huấn Luyện
Theo chỉ thị của CEO Ngọc Châu, kế hoạch huấn luyện mô hình học sinh **ViVy 1.5B** trên Google Colab đã được thiết lập hoàn chỉnh để ChatGPT (hoặc kỹ sư vận hành) có thể thực thi 1-chạm độc lập:

1. **Backbone Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
2. **Phương pháp**: LoRA Fine-Tuning (r=16, alpha=32, target all linear modules) + Gradient Checkpointing
3. **Phần cứng**: Google Colab T4 GPU miễn phí (15–16 GB VRAM, Peak VRAM <6.5 GB)
4. **Dataset chuẩn hóa**: `vivy_train_dataset.jsonl` đã được biên dịch hoàn chỉnh với **501 mẫu** (450 mẫu nhận thức suy luận 2Brain + 51 mẫu Bounded CUA & Safety Refusal)
5. **Artifact mục tiêu**: `vivy_1.5b_q4km.gguf` (~1.0 GB) nạp vào `D:\\models\\vivy-1.5b\\` cho Cautreo C-ABI 0ms memory.

---

## 2. Danh Mục Tài Liệu & Artifact Đã Xuất Bản
1. **File Hướng Dẫn Chi Tiết (SOP/Runbook)**:
   - `D:\\91s_Vivy\\vivyChatGPT\\HUONG_DAN_TRAIN_VIVY_COLAB_CHO_CHATGPT.md`
   - `D:\\91s_Vivy\\unitary-reasoner\\training\\HUONG_DAN_TRAIN_VIVY_COLAB_CHO_CHATGPT.md`
   - `D:\\2brain\\projects\\vivy-final-v1\\HUONG_DAN_TRAIN_VIVY_COLAB_CHO_CHATGPT.md`
2. **Notebook Chuẩn Bị Sẵn**:
   - `D:\\91s_Vivy\\vivyChatGPT\\colab_vivy_train.ipynb`
   - `D:\\91s_Vivy\\unitary-reasoner\\training\\colab_vivy_train.ipynb`
3. **Tập Dữ Liệu 501 Mẫu**:
   - `D:\\91s_Vivy\\vivyChatGPT\\vivy_train_dataset.jsonl`
   - `D:\\91s_Vivy\\unitary-reasoner\\training\\vivy_train_dataset.jsonl`

---

## 3. Changelog
| Agent | Thời gian | Hành động |
|---|---|---|
| Antigravity IDE | 23/09/2026 14:00 ICT | Ban hành kế hoạch và hướng dẫn chuẩn hóa huấn luyện ViVy 1.5B trên Google Colab cho ChatGPT, biên dịch 501 mẫu dataset và đồng bộ 2Brain. |
"""

target = r"D:\2brain\hot-memory\DD_V6_COLAB_TRAINING_PLAN_CHATGPT.md"
with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Successfully synced: {target}")
