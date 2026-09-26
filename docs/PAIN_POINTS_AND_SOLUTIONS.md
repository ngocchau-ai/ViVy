# Tài liệu Phân tích Nỗi đau, Giải pháp & Kiến trúc ViVy AI Framework

## 1. Nỗi đau Sản phẩm (Pain Points)

1. **Thiếu Local AI Engine thực sự:**
   - Trước đây, sản phẩm chỉ sử dụng wrapper prompt đơn giản dựa vào Ollama (`FROM llama3.2:3b`) hoặc mô phỏng lý thuyết trong `nps_core`.
   - Không có khả năng trực tiếp nạp và suy luận weights local (`.gguf`, `.safetensors`, `.bin`), thiếu pipeline fine-tuning LoRA riêng cho miền dữ liệu tài chính/trading.

2. **Xung đột Kiến trúc Mắt - Tay (Programmatic Gatekeeping):**
   - Sự hiện diện của các bộ lọc cản logic cứng (hardcoded R:R ratio check, netting filter, velocity guard) bằng mã Python đã can thiệp vào quyết định độc lập của AI.
   - Vi phạm nguyên tắc cốt lõi: ViVy phải là **Não trung tâm** duy nhất ra quyết định và tự quản trị rủi ro thông qua weights & static lessons.

3. **Thiếu Hệ thống Quản trị & Login 1-Chạm Bảo mật:**
   - Chưa có giải pháp phân quyền User, mã hóa mật khẩu Argon2id, JWT Token và WebAuthn (Passkey) login 1-chạm bằng sinh trắc học/hardware key cho dashboard điều khiển.

---

## 2. Giải pháp Sản phẩm (ViVy Solution Stack)

1. **Local Model Core (`src/vivy/core`):**
   - Hỗ trợ nạp model weights trực tiếp từ file `.gguf` (qua `llama-cpp-python`), PyTorch/Safetensors (`transformers`), hoặc kết nối linh hoạt tới Ollama / vLLM local API.
   - Engine suy luận sinh JSON cấu trúc (`Structured Reasoning JSON Output`) đảm bảo câu trả lời nhất quán, giải thích được (explainable reasoning).

2. **Kiến trúc Mắt - Tay Chuẩn (`src/vivy/eyes` & `src/vivy/hands`):**
   - **Mắt (Eyes):** Thu thập dữ liệu nến OHLC, RSI, EMA, ATR, rổ lệnh MT5, và tin tức kinh tế vĩ mô.
   - **Tay (Hands):** Chuyển tiếp và gửi lệnh thô (`BUY`, `SELL`, `MODIFY`, `CLOSE`, `CANCEL`) trực tiếp tới MT5 Terminal. CẤM tuyệt đối bộ lọc cản hay gác cổng lập trình cứng trong Python.

3. **Bộ nhớ & Tự Hoàn Thiện (`src/vivy/memory` & `src/vivy/self_improvement`):**
   - **Associative Vector Memory:** SQLite/FAISS vector store lưu giữ các mẫu giao dịch và bài học kinh nghiệm past trades.
   - **Feedback Loop:** Tự động ghi nhận PnL, lý do thắng/thua để làm bài học tĩnh (static lessons) nạp lại vào prompt cho ViVy tự học.

4. **Quản trị User & Login 1-Chạm (`src/vivy/auth`):**
   - Hỗ trợ mã hóa mật khẩu Argon2id + JWT Access/Refresh Tokens + WebAuthn/Passkey sinh trắc học 1-chạm.

---

## 3. Luồng Xử Lý Dữ Liệu (Data Flow Architecture)

```
[ MT5 Terminal / News Feeds ]
           │
           ▼
    [ Eyes Module ]  (mt5_collector & news_bridge)
           │
           │ (Nạp giá, chỉ báo, tin tức & rổ lệnh)
           ▼
  [ Vector Memory ]  (Lấy bài học quá khứ thành công/thất bại)
           │
           │ (Ghép Context & Static Lessons)
           ▼
[ Central Brain ViVy ] (core/model_loader & inference)
           │
           │ (Sinh Structured JSON Decision: Thought + Action)
           ▼
   [ Hands Module ]  (mt5_executor - Không có gác cổng logic)
           │
           │ (Gửi Lệnh Thô)
           ▼
    [ MT5 Terminal ]
           │
           ▼
[ Self-Improvement ] (Ghi log PnL & Cập nhật bài học quá khứ vào Memory)
```

---

## 4. Giải Pháp Quản Trị User & Login 1-Chạm

- **Hệ thống Authentication:**
  - Standard Login: Username + Password (Argon2id hashing algorithm).
  - 1-Touch Passkey Login: WebAuthn FIDO2 / Passkey API (TouchID / FaceID / YubiKey).
  - Token Management: Bearer JWT Token với thời hạn hết hạn 60 phút và refresh token 7 ngày.
