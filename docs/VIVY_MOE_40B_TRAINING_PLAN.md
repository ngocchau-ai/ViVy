# 🏛️ PHƯƠNG ÁN ĐÀO TẠO MÔ HÌNH VIVY 40B SPARSE MOE (TUÂN THỦ KIẾN TRÚC TƯ DUY NPS CORE)

**Thương hiệu & Tác giả:** Ngọc Châu Digital Product Development  
**Mô hình Target:** ViVy 40B Sparse MoE (40 tỷ tham số tổng / 7 tỷ tham số active per token)  
**Kiến trúc Nền tảng:** NPS Core V1 Specification ([ARCHITECTURE.md](file:///d:/91sViVy-Aider/ARCHITECTURE.md))  

---

## 1. NGUYÊN TẮC CỐT LÕI & TUÂN THỦ TƯ DUY GỐC

Phương án đào tạo cho ViVy 40B tuân thủ tuyệt đối quy trình 8 Stage tư duy và logic gốc quy định trong `ARCHITECTURE.md`:
1. **Dữ liệu huấn luyện xuất phát từ Vòng đời Giả thuyết & Tập dữ liệu chắt lọc (Stage 6):**
   - Bộ dữ liệu `ReplayManifest` và `DatasetBuilder` trích xuất các chuyển dịch trạng thái `ThoughtState`, giả thuyết bị loại bỏ, lý do điều hướng và nguồn gốc provenance.
   - Phân chia tập dữ liệu contamination-safe train/val/test bằng thuật toán hash SHA-256 (`DatasetSplitter`).
2. **Lọc chất lượng qua phễu Funnel (Stage 7):**
   - Loại bỏ dữ liệu nhiễu, điểm tin cậy thấp (`confidence < 0.3`) hoặc thiếu bằng chứng xác minh.
3. **Phân bổ Chuyên gia định hướng MoERouter:**
   - Điều hướng các ví dụ huấn luyện cho 8 Chuyên gia MoE độc lập dựa trên loại tác vụ (Thị giác, Ngôn ngữ Anh/Việt, Logic tư duy, Mã nguồn AST, Số liệu).

---

## 2. THÔNG SỐ KIẾN TRÚC MÔ HÌNH VIVY 40B MOE (`MODEL_MOE_40B`)

```
┌────────────────────────────────────────────────────────────────────────┐
│                      VIVY 40B MOE ARCHITECTURE                         │
│  - Total Parameters: 40,000,000,000 (40 Billion)                       │
│  - Active Parameters: 7,000,000,000 (7 Billion per token)              │
│  - Geometry: 32 layers, hidden_size=4096, 32 heads, 8 kv_heads         │
│  - Experts: 8 Total Experts, Top-2 Gated Active Experts                │
│  - Compute FLOPs Reduction: 82.5% vs Dense 40B                         │
└────────────────────────────────────────────────────────────────────────┘
```

| Thông Số Kiến Trúc | Giá Trị Cấu Hình | Diễn Giải |
|---|---|---|
| `vocab_size` | 32,000 | Bộ từ vựng song ngữ chuẩn Anh/Việt |
| `num_layers` | 32 | Số lớp Transformer |
| `hidden_size` | 4,096 | Kích thước ẩn ẩn |
| `num_attention_heads` | 32 | Số đầu chú ý Multi-Head Attention |
| `num_kv_heads` | 8 | Grouped-Query Attention (GQA 4:1) |
| `intermediate_size` | 11,008 | SwiGLU FFN dimension |
| `num_total_experts` | 8 | Total Experts |
| `num_active_experts` | 2 | Top-2 Gated Active Experts (~7B active) |

---

## 3. QUY TRÌNH 5 BƯỚC THỰC THI ĐÀO TẠO (TRAINING PIPELINE)

```
 ┌────────────────┐     ┌──────────────────┐     ┌─────────────────┐
 │ Population     │ ──► │ ReplayManifest   │ ──► │ TrainingExample │
 │ Snapshot       │     │ (Stage 6 Split)  │     │ Bridge (Stage 7)│
 └────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
 ┌────────────────┐     ┌──────────────────┐     ┌─────────────────┐
 │ Save Checkpoint│ ◄── │ MoE TrainingStep │ ◄── │ Quality Funnel  │
 │ & SLA Audit    │     │ (Top-2 Experts)  │     │ Curation        │
 └────────────────┘     └──────────────────┘     └─────────────────┘
```

1. **Bước 1: Trích xuất ReplayManifest (Stage 6):** Gom các `PopulationSnapshot` lịch sử, tạo `DatasetRecord`s và phân chia train/val/test.
2. **Bước 2: Bridge & Curation (Stage 7):** Chuyển đổi thành `TrainingExample`s, lọc qua phễu `funnel()` giữ lại ví dụ đạt chuẩn chất lượng.
3. **Bước 3: Phân bổ Router:** `MoERouter.route_task()` định hướng từng ví dụ về đúng Chuyên gia đảm nhận.
4. **Bước 4: Huấn luyện Gradient:** Khởi tạo `TrainingState`, áp dụng Cosine Warmup Learning Rate Schedule (`learning_rate=3e-4`), tính loss và cập nhật metrics.
5. **Bước 5: Xuất Checkpoint & Kiểm định SLA:** Xuất `vivy_moe_40b_checkpoint.json` và kiểm định độ trễ đề xuất `< 200ms`.

---

## 4. KỊCH BẢN THỰC THI

Kịch bản thực thi được cài đặt tại [scripts/train_vivy_moe_40b.py](file:///d:/91sViVy-Aider/scripts/train_vivy_moe_40b.py):
```powershell
.venv\Scripts\python scripts/train_vivy_moe_40b.py
```
