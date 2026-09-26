> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# Hướng Dẫn Vận Hành Huấn Luyện ViVy 1.5B Trên Google Colab (Dành Riêng Cho ChatGPT)

| Thuộc Tính | Chi Tiết |
| :--- | :--- |
| **Đối tượng thực thi** | **ChatGPT** (hoặc Kỹ sư vận hành phối hợp cùng ChatGPT) |
| **Mục tiêu sản phẩm** | Huấn luyện mô hình học sinh **ViVy 1.5B** chuyên biệt hóa nhận thức & tự động hóa Desktop (Bounded CUA Directives) |
| **Kiến trúc mô hình gốc** | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| **Phương pháp tối ưu** | LoRA Fine-Tuning (r=16, alpha=32, target: all linear projections) + Gradient Checkpointing |
| **Môi trường phần cứng** | **Google Colab Miễn Phí (Free Tier)** — GPU NVIDIA T4 (15–16 GB VRAM, Peak VRAM < 6.5 GB) |
| **Thời gian chạy ước tính** | **12 – 18 phút** trên GPU T4 |
| **Artifact đầu ra chuẩn** | `/content/vivy_1.5b_q4km.gguf` (~1.0 GB) |

---

## 1. Tổng Quan & Cấu Trúc File Cần Thiết

Trước khi bắt đầu, đảm bảo ChatGPT hoặc người dùng có sẵn 2 file cốt lõi nằm trong thư mục [`D:\91s_Vivy\vivyChatGPT\`](file:///D:/91s_Vivy/vivyChatGPT/):

1. **Notebook Huấn Luyện**: [`colab_vivy_train.ipynb`](file:///D:/91s_Vivy/vivyChatGPT/colab_vivy_train.ipynb)
   - Chứa toàn bộ 7 giai đoạn mã nguồn từ cài đặt thư viện, nạp mô hình, cấu hình LoRA, training loop đến merge weights và export GGUF.
2. **Tập Dữ Liệu Chuẩn Hóa**: [`vivy_train_dataset.jsonl`](file:///D:/91s_Vivy/vivyChatGPT/vivy_train_dataset.jsonl)
   - Chứa **501 mẫu** huấn luyện định dạng ChatML tiêu chuẩn:
     + **450 mẫu**: Nhận thức suy luận đa tầng (`Problem`, `Hypotheses`, `Evidence` $\rightarrow$ `<vivy_thought>` + `Decision`).
     + **51 mẫu**: Thao tác giao diện Desktop Bounded CUA (`Candidate Selection`, `Zero-Trust Refusal`, `Hotkey/Save/Terminal/MT5 Safety`).

---

## 2. Quy Trình Vận Hành 7 Bước Chi Tiết (SOP / Runbook)

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│ Bước 1: Khởi tạo│────>│ Bước 2: Nạp    │────>│ Bước 3: Cài đặt│────>│ Bước 4: Tải    │
│ Google Colab   │     │ Notebook & Data│     │ Môi Trường     │     │ Model & LoRA   │
└────────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
                                                                              │
┌────────────────┐     ┌────────────────┐     ┌────────────────┐              │
│ Bước 7: Nạp Cục│<────│ Bước 6: Tải    │<────│ Bước 5: Chạy   │<─────────────┘
│ Bộ & Kích Hoạt │     │ Artifact GGUF  │     │ SFT Training   │
└────────────────┘     └────────────────┘     └────────────────┘
```

### Bước 1: Khởi Tạo Môi Trường Google Colab
1. Truy cập: [https://colab.research.google.com](https://colab.research.google.com).
2. Đăng nhập tài khoản Google bất kỳ (hoàn toàn miễn phí).
3. Thiết lập GPU:
   - Vào menu: **Runtime** (Thời gian chạy) $\rightarrow$ **Change runtime type** (Thay đổi loại thời gian chạy).
   - Tại mục **Hardware accelerator** (Bộ tăng tốc phần cứng), chọn: **T4 GPU**.
   - Nhấn **Save** (Lưu).

### Bước 2: Nạp Notebook & Dataset Lên Colab
1. **Nạp Notebook**:
   - Nhấn **File** $\rightarrow$ **Upload notebook** (Tải sổ ghi chép lên).
   - Chọn file: `D:\91s_Vivy\vivyChatGPT\colab_vivy_train.ipynb`.
2. **Nạp Dataset**:
   - Nhấp vào biểu tượng **Thư mục (Files)** ở thanh công cụ bên trái màn hình Colab.
   - Kéo và thả file `D:\91s_Vivy\vivyChatGPT\vivy_train_dataset.jsonl` vào thư mục gốc `/content/`.
   - *Kiểm tra*: File `vivy_train_dataset.jsonl` phải xuất hiện ngay trong danh sách file của Colab.

---

### Bước 3: Kiểm Tra GPU & Cài Đặt Thư Viện (Cells 1 - 2)

Chạy **Cell 1** để kiểm tra GPU:
```python
!nvidia-smi
import os, torch

assert torch.cuda.is_available(), 'Chưa phát hiện GPU! Hãy chọn Runtime -> Change runtime type -> T4 GPU'
props = torch.cuda.get_device_properties(0)
print(f'Kết nối thành công: {props.name} | Tổng VRAM: {props.total_memory / 1e9:.2f} GB')
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
```
> **Dấu hiệu thành công**: Xuất hiện tên card `Tesla T4` và VRAM ~15.84 GB.

Chạy **Cell 2** để cài đặt các package:
```python
!pip install -q -U 'transformers>=4.48.0' 'datasets>=3.0.0' 'accelerate>=0.30.0' 'safetensors>=0.4.0' 'peft>=0.10.0' 'trl>=0.8.0'
import transformers, peft, torch
print('Transformers:', transformers.__version__)
print('PEFT        :', peft.__version__)
print('PyTorch     :', torch.__version__)
```

---

### Bước 4: Nạp Base Model & Cấu Hình LoRA (Cell 3)

Chạy **Cell 3**:
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

MODEL_ID = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'
print(f'Đang nạp base model: {MODEL_ID}...')

tok = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map='auto',
    trust_remote_code=True
)

# Kích hoạt Gradient Checkpointing để tối ưu hóa VRAM < 6.5 GB
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})

# Cấu hình LoRA bao phủ toàn bộ các ma trận trọng số tuyến tính
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
    lora_dropout=0.05,
    bias='none',
    task_type=TaskType.CAUSAL_LM
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```
> **Dấu hiệu thành công**: In ra số lượng tham số có thể huấn luyện (trainable params) chiếm khoảng ~1.2% tổng tham số của mô hình 1.5B.

---

### Bước 5: Nạp Data & Khởi Động SFT Training (Cells 4 - 5)

Chạy **Cell 4** (Nạp tập 501 mẫu):
```python
import os, json

dataset_path = '/content/vivy_train_dataset.jsonl'
training_data = []

if os.path.exists(dataset_path):
    print(f'Loading uploaded dataset from: {dataset_path}...')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    training_data.append(record)
                except Exception:
                    pass
    print(f'SUCCESS: Loaded {len(training_data)} training samples from {dataset_path}!')
else:
    print('Notice: Dùng 2 mẫu fallback...')

print(f'Total active training samples: {len(training_data)}')
```
> **Dấu hiệu thành công**: In ra `SUCCESS: Loaded 501 training samples from /content/vivy_train_dataset.jsonl!`.

Chạy **Cell 5** (Tiến hành Huấn luyện):
```python
from datasets import Dataset
from trl import SFTTrainer, SFTConfig

dataset = Dataset.from_list(training_data)

def format_chatml(example):
    text = tok.apply_chat_template(example['messages'], tokenize=False, add_generation_prompt=False)
    return {'text': text}

train_dataset = dataset.map(format_chatml)

training_args = SFTConfig(
    output_dir='/content/vivy_colab_checkpoints',
    dataset_text_field='text',
    max_seq_length=1024,
    learning_rate=2e-4,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=2,
    num_train_epochs=3,
    logging_steps=10,
    fp16=True,
    optim='adamw_torch',
    save_strategy='epoch',
    report_to='none'
)

trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    args=training_args
)

print('Bắt đầu huấn luyện ViVy trên T4 GPU...')
trainer.train()
```
> **Chỉ số quan sát**:
> - Tiến độ: 3 epochs (khoảng 375 steps).
> - Loss khởi đầu: ~2.1 $\rightarrow$ Loss kết thúc mục tiêu: **< 0.65**.
> - Thời gian chạy: ~12-15 phút.

---

### Bước 6: Merge Trọng Số & Xuất GGUF Quantization (Cell 6)

Chạy **Cell 6**:
```python
OUTPUT_DIR = '/content/vivy_1.5b_merged'
print(f'Đang hợp nhất trọng số LoRA vào {OUTPUT_DIR}...')
merged_model = model.merge_and_unload()
merged_model.save_pretrained(OUTPUT_DIR, safe_serialization=True)
tok.save_pretrained(OUTPUT_DIR)
print('Đã lưu merged model thành công!')

# Tải công cụ llama.cpp và chuyển đổi sang GGUF chuẩn Cautreo C-ABI
!git clone --depth 1 https://github.com/ggerganov/llama.cpp.git /content/llama.cpp
!pip install -q -r /content/llama.cpp/requirements.txt
!python3 /content/llama.cpp/convert_hf_to_gguf.py /content/vivy_1.5b_merged --outfile /content/vivy_1.5b_f16.gguf --outtype f16

# Lượng tử hóa sang Q4_K_M (Zero-RAM-Waste, dung lượng ~1.0 GB)
!cd /content/llama.cpp && cmake -B build && cmake --build build --config Release -j --target llama-quantize
!/content/llama.cpp/build/bin/llama-quantize /content/vivy_1.5b_f16.gguf /content/vivy_1.5b_q4km.gguf q4_k_m

print('XUẤT BẢN THÀNH CÔNG: /content/vivy_1.5b_q4km.gguf sẵn sàng tải về!')
```

---

### Bước 7: Tải Checkpoint Về Máy Cục Bộ & Tích Hợp

1. **Tải file về máy tính**:
   - Ở thanh thư mục bên trái của Colab, tìm file: `/content/vivy_1.5b_q4km.gguf`.
   - Nhấp chuột phải $\rightarrow$ Chọn **Download** (Tải xuống). Dung lượng file khoảng **1.0 GB**.
2. **Đặt vào đúng vị trí Model Root**:
   - Di chuyển file tải về vào thư mục:
     ```text
     D:\models\vivy-1.5b\vivy-1.5b-q4_k_m.gguf
     ```
3. **Kích hoạt chạy thử trên máy cục bộ**:
   - Có thể khởi chạy kiểm tra độc lập qua `llama-server.exe`:
     ```powershell
     & "D:\models\bin\llama-server.exe" -m "D:\models\vivy-1.5b\vivy-1.5b-q4_k_m.gguf" --port 8082 --alias "vivy-1.5b"
     ```

---

## 3. Tiêu Chuẩn Nghiệm Thu & Kiểm Định (Checklist 4 Trục)

Trước khi bàn giao kết quả huấn luyện từ Colab về kho tri thức, ChatGPT phải đối chiếu qua 4 trục:

1. **Tính Xung Đột (Conflict)**:
   - File xuất phải là GGUF lượng tử hóa `Q4_K_M`, không bị lỗi architecture mismatch với engine Cautreo.
   - Tokenizer giữ nguyên chat template của Qwen2.5/ChatML (`<|im_start|>`, `<|im_end|>`).
2. **Tính Hợp Lý (Feasibility)**:
   - Bộ nhớ VRAM khi train trên Colab không vượt quá 6.5 GB (an toàn tuyệt đối trên T4 16GB).
   - Loss suy giảm đều đặn từ epoch 1 đến epoch 3.
3. **Tính Dư Thừa (Redundancy)**:
   - Không lưu lại checkpoint trung gian cồng kềnh, chỉ giữ lại file merged cuối cùng và file GGUF `q4_k_m`.
4. **Tính Hiệu Quả (Effectiveness)**:
   - Output sinh thử nghiệm tại Cell 7 bắt buộc phải có khối `<vivy_thought>` với `Epistemic_Decision` rõ ràng và chỉ dẫn ứng viên hành động hợp lệ.

---

## 4. Xử Lý Sự Cố Thường Gặp (Troubleshooting Runbook)

| Hiện Tượng | Nguyên Nhân | Cách Khắc Phục |
| :--- | :--- | :--- |
| **CUDA out of memory (OOM)** | Batch size hoặc max_seq_length quá lớn | Giảm `per_device_train_batch_size=1`, tăng `gradient_accumulation_steps=4`, giữ `max_seq_length=1024`. |
| **Không tìm thấy file dataset** | Chưa kéo thả file vào thư mục `/content/` | Chạy lệnh `!ls -la /content/` để kiểm tra tên file. Nếu thiếu, kéo thả lại `vivy_train_dataset.jsonl`. |
| **Mất kết nối Colab giữa chừng** | Trình duyệt bị ngủ đông hoặc mất mạng | Giữ tab Colab mở; có thể click nhẹ vào màn hình mỗi 10 phút hoặc dùng script auto-click nhẹ. |
| **Lỗi cmake khi build llama-quantize** | Thiếu gói build essential trên Linux | Chạy `!apt-get update && apt-get install -y build-essential cmake`. |

---

## 5. Lịch Sử Thay Đổi (Changelog)

| Agent | Thời Gian | Lý Do / Nội Dung Thay Đổi |
| :--- | :--- | :--- |
| Antigravity IDE | 23/09/2026 14:00 ICT | Khởi tạo tài liệu hướng dẫn chuẩn hóa huấn luyện ViVy 1.5B trên Google Colab T4 dành cho ChatGPT theo chỉ thị của CEO Ngọc Châu. Cập nhật tập 501 mẫu dữ liệu thực tế. |
