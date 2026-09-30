# Bản Đồ Tri Thức Toàn Hệ Thống 91sViVy (System Knowledge Map)

---

## 🗺️ 1. Tổng Quan Kiến Trúc (Architectural Blueprint)

Sản phẩm **91sViVy** được thiết kế dựa trên triết lý **Mắt - Tay Architecture** với **Não trung tâm là Local AI Engine (ViVy)**.

```
                  ┌────────────────────────────────────────┐
                  │          SYSTEM KNOWLEDGE MAP          │
                  └──────────────────┬─────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │  MẮT (EYES)   │           │ CENTRAL BRAIN │           │ TAY (HANDS)   │
 │ Market/News   │──────────►│ ViVy Local AI │──────────►│ MT5 Executor  │
 │  Perception   │           │    Engine     │           │ No Gatekeeper │
 └───────────────┘           └───────┬───────┘           └───────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │ MEMORY STORE  │           │ AUTH & PASSKEY│           │ SELF-LEARNING │
 │ Vector/SQLite │           │ Argon2id/JWT  │           │ Feedback PnL  │
 └───────────────┘           └───────────────┘           └───────────────┘
```

---

## 🧩 2. Danh Mục Các Module & Thành Phần Hệ Thống

| Module | Đường dẫn File | Mô tả Chức năng | Nguyên tắc/Quy tắc |
| :--- | :--- | :--- | :--- |
| **Isolated Prompts** | [prompts.py](file:///d:/91sViVy-Aider/src/vivy/core/prompts.py) | Quản lý toàn bộ System Prompt cho 91sViVy (`VIVY_TRADING_SYSTEM_PROMPT`, `VIVY_REASONING_SYSTEM_PROMPT`). | Cô lập 100% khỏi các dự án bên ngoài. |
| **Model Loader** | [model_loader.py](file:///d:/91sViVy-Aider/src/vivy/core/model_loader.py) | Engine nạp model weights local (`.gguf` via `llama-cpp-python`, PyTorch/Safetensors via `transformers`, Ollama API, hoặc Mock). | Open Source First. |
| **Inference Engine** | [inference.py](file:///d:/91sViVy-Aider/src/vivy/core/inference.py) | Engine suy luận sinh ra Transparent Reasoning & Structured JSON decision. | Sinh JSON chuẩn định dạng `thought`, `action`, `symbol`, `volume`, `stop_loss`, `take_profit`. |
| **Mắt (Data Collector)** | [mt5_collector.py](file:///d:/91sViVy-Aider/src/vivy/eyes/mt5_collector.py) | Thu thập giá nến OHLC, rổ lệnh hiện tại, chỉ báo RSI, EMA 20/50, ATR 14. | Không chứa logic quyết định. |
| **Mắt (News Bridge)** | [news_bridge.py](file:///d:/91sViVy-Aider/src/vivy/eyes/news_bridge.py) | Cầu nối thu thập dữ liệu vĩ mô và tin tức kinh tế. | Cung cấp thông tin vĩ mô cho AI. |
| **Tay (MT5 Executor)** | [mt5_executor.py](file:///d:/91sViVy-Aider/src/vivy/hands/mt5_executor.py) | Chuyển tiếp và gửi lệnh thô (`BUY`, `SELL`, `MODIFY`, `CLOSE`) trực tiếp tới MT5 Terminal. | **CẤM tuyệt đối bộ lọc cản hay gác cổng lập trình cứng (No Programmatic Gatekeepers)**. |
| **Vector Memory** | [vector_store.py](file:///d:/91sViVy-Aider/src/vivy/memory/vector_store.py) | Bộ nhớ lưu vết trade lessons và thu hồi 1-touch intuition context. | SQLite/Vector local storage. |
| **Auth & Passkey** | [user_manager.py](file:///d:/91sViVy-Aider/src/vivy/auth/user_manager.py)<br>[webauthn_passkey.py](file:///d:/91sViVy-Aider/src/vivy/auth/webauthn_passkey.py) | Mã hóa Argon2id/SHA256, JWT Token generation/verification, Session invalidation, và WebAuthn 1-touch passkey login. | Vô hiệu hóa session tức thì khi có lệnh revocation. |
| **API Server** | [router.py](file:///d:/91sViVy-Aider/src/vivy/api/router.py) | Điều phối REST API, WebSockets và chạy chu kỳ trade cycle tự động. | FastAPI lightweight open source. |
| **Continuous Learning** | [feedback_logger.py](file:///d:/91sViVy-Aider/src/vivy/self_improvement/feedback_logger.py) | Ghi nhận kết quả PnL, trích xuất bài học và nạp lại vào memory cho ViVy tự học. | Self-improvement loop. |
| **Fine-Tuning Scripts** | [train_lora.py](file:///d:/91sViVy-Aider/scripts/train_lora.py)<br>[export_gguf.py](file:///d:/91sViVy-Aider/scripts/export_gguf.py) | Pipeline fine-tune LoRA/PEFT và script nén/quantize weights GGUF. | Hỗ trợ huấn luyện local. |

---

## 🔒 3. Bảo Mật & Quản Trị Session Tức Thì

Hệ thống quản trị phiên làm việc (Session Management) hỗ trợ **Vô hiệu hóa toàn bộ session trước đây** (Global Session Revocation):
- Phương thức `revoke_all_sessions()` lưu mốc thời gian `_min_valid_timestamp`.
- Mọi JWT token được phát hành trước mốc thời gian này sẽ lập tức bị từ chối (`verify_jwt_token` trả về `None`).
- Cho phép quản trị viên hủy toàn bộ quyền truy cập tức thì khi cần bảo mật cao.

---

## ⚡ 4. Quy Trình Vận Hành Thực Tế (Execution Workflow)

```
1. Client Authenticate (Login 1-touch Passkey / JWT)
   │
2. Trigger Autonomous Trade Cycle (`handle_trade_cycle`)
   │
   ├─► [Eyes] MT5DataCollector & NewsBridge thu thập dữ liệu real-time.
   │
   ├─► [Memory] ViVyVectorMemory truy vấn bài học quá khứ (Recall Intuition).
   │
   ├─► [Brain] ViVyInferenceEngine xử lý context, ra quyết định JSON.
   │
   ├─► [Hands] MT5Executor gửi lệnh trực tiếp lên MT5 (Không có gác cổng cứng).
   │
   └─► [Self-Improvement] FeedbackLogger lưu kết quả PnL vào Memory.
```

---

## 🧪 5. Kiểm Thử Hệ Thống (Testing & Evidence)

Tất cả các thành phần được kiểm thử tự động với suite `pytest`:
- **Chạy duy nhất lệnh:** `python -m pytest --basetemp=.pytest_basetemp`
- **Kết quả:** 671 tests passed 100%.
