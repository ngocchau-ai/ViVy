# Quickstart Guide — ViVy Final Core V1.0

## Prerequisites

| Requirement | Minimum | Recommended |
|:---|:---:|:---:|
| Python | 3.10 | 3.11+ |
| RAM | 12GB | 16GB+ |
| Disk | 12GB free | 20GB+ |
| Ollama | 0.3+ | latest |
| OS | Windows 10 / Ubuntu 22.04 | Any |

---

## Cài Đặt

### Bước 1 — Clone repo

```bash
git clone <repo-url>
cd unitary-reasoner
```

### Bước 2 — Cài Python dependencies

```bash
# Tạo virtual environment (khuyến nghị)
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Cài dependencies
pip install -e ".[dev]"
```

### Bước 3 — Cài Ollama

- **Windows/Mac**: Tải từ https://ollama.com/download
- **Linux**:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

### Bước 4 — Pull Gemma 4 E4B và build ViVy

```bash
# Pull base model (~9.6GB)
ollama pull gemma4:e4b

# Build ViVy từ Modelfile (dùng SYSTEM prompt V5.1)
ollama create vivy-final:v1 -f Modelfile.vivy

# Verify
ollama list | grep vivy-final
```

### Bước 5 — Chạy smoke test (offline)

```bash
# 19 tests không cần Ollama server
python scripts/test_integration.py
```

Expected output:
```
Results: 19/19 passed
ViVy Final Core V1.0 is ready for deployment.
```

---

## Sử Dụng

### Interactive — AGENTIC mode (có tool calling)

```bash
# Đảm bảo Ollama đang chạy
ollama serve &   # hoặc chạy Ollama app

# Mở ViVy session
python scripts/run_vivy.py --mode agentic
```

```
Task: Đọc file README.md và tóm tắt kiến trúc chính
ViVy: <vivy_thought>
[EPISTEMIC_ASSESSMENT]
...
Epistemic_Decision: EXECUTE_DIRECTLY
</vivy_thought>
[Gọi engine_file_io để đọc file...]
```

### Interactive — CHAT mode (không tool calling)

```bash
python scripts/run_vivy.py --mode chat
```

### Batch mode (non-interactive)

```bash
python scripts/run_vivy.py --mode batch \
  --input "Giải thích HebbianRecall W=YX⁺ trong 2 câu"
```

---

## Environment Variables

| Variable | Default | Mô tả |
|:---|:---:|:---|
| `VIVY_LLAMA_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `VIVY_MODEL` | `vivy-final:v1` | Model name |
| `VIVY_MAX_ROUNDS` | `10` | Max agentic loop rounds |
| `VIVY_HIDDEN_DIM` | `64` | Hidden dimension cho N-Core |

---

## Tích Hợp Với Python

```python
from integration.vivy_inference_loop import VivyInferenceLoop, InferenceMode

# Tạo ViVy từ env vars
vivy = VivyInferenceLoop.from_env()

# Inference
result = vivy.infer(
    "Phân tích kiến trúc ViVy và đề xuất bước tiếp theo",
    session_id="my_session",
    mode=InferenceMode.AGENTIC,
)

print(result.response_text)
print(f"Epistemic decision: {result.epistemic_decision}")
print(f"Tool calls: {len(result.tool_dispatch_results)}")
print(f"Tokens used: {result.llm_tokens_used}")
```

---

## Troubleshooting

### "Cannot connect to Ollama"

```bash
# Check Ollama running
curl http://127.0.0.1:11434/api/tags

# Start if not running
ollama serve
```

### "Model vivy-final:v1 not found"

```bash
ollama create vivy-final:v1 -f Modelfile.vivy
```

### Inference quá chậm (CPU)

ViVy trên CPU với 9.6GB model: ~30-60s/response bình thường.
- Giảm `--max-tokens` để response ngắn hơn
- Dùng `--mode chat` (không tool calling) để nhanh hơn
- Upgrade lên GPU để tăng tốc gấp 10-20x

### Python import error

```bash
# Đảm bảo đang ở thư mục unitary-reasoner/
pip install -e ".[dev]"
```
