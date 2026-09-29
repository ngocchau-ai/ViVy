# benchmarks/

Hai thứ **khác nhau** cùng nằm trong thư mục này. Đừng gộp.

| Đường | Là gì | Thuộc |
|:--|:--|:--|
| `harness.py`, `checker.py`, `eval_set/` | **Đo lường T2** — pipeline vs Gemma thuần, có receipt | WP-7 / O-02 (kế hoạch hoàn thiện 29/09/2026) |
| `bench_core.py` | Benchmark **lượng tử** (MPS bond-dimension / độ trễ) | nhánh nghiên cứu D-2 — **không** phải T2 |

`bench_core.py` không đọc `eval_set/`, không viết receipt `T2-*.json`, và không
tham gia nghiệm thu nào của GĐ1. Để nguyên nó.

## Đo T2

```
benchmarks/
├── harness.py          # chạy A/B/C, ghi receipt
├── checker.py          # chấm điểm lập trình (cấm khớp chuỗi con)
├── eval_set/
│   ├── schema.py
│   ├── generate.py
│   ├── dev_set.jsonl          # 32 câu dev — commit
│   ├── heldout_manifest.json  # 88 hash held-out — commit
│   └── README.md              # quy trình D-7 cho chủ dự án
└── README.md           # file này
```

### Ba nhánh đo

| Nhánh | Chạy gì | Trả lời câu hỏi |
|:--|:--|:--|
| `baseline` | Gemma thuần, một lần `chat` mỗi câu | sàn của phép đo |
| `pipeline` | `VivyInferenceLoop.infer` — đường sản phẩm | pipeline có hơn sàn không |
| `pipeline_decoder` | pipeline, rồi `Decoder.decode` với **câu hỏi gốc** trong `LogicForm.query` | tổng hợp lại có giữ được đáp án không |

### Chạy

```powershell
cd D:\91s- Tái cấu trúc lân thứ 4\Vivy_final\vivy

# dev — có sẵn trong repo, dùng để chỉnh
python benchmarks/harness.py --split dev --arms baseline --limit 8

# held-out — cần file của chủ dự án (xem eval_set/README.md)
$env:VIVY_HELDOUT_PATH = "D:\91s_heldout\vivy_T2\heldout_set.jsonl"
python benchmarks/harness.py --split heldout --arms baseline,pipeline,pipeline_decoder
```

Receipt ghi ra `evidence/T2-<run_id>.json`.

### Nghiệm thu (T2)

> pipeline ≥ baseline − 2 điểm %. Nếu < baseline − 5 điểm % → **dừng, thiết kế lại.**

`harness.py` chấm đúng quy tắc đó và trả `PASS` / `MARGINAL` / `STOP_REDESIGN`.
Giữa −2pp và −5pp là vùng xám: không tính đạt, không tính dừng — xem theo miền.

Muốn **giữ thành phần lượng tử** trong sản phẩm, thanh cao hơn: ≥ baseline +
5 điểm %, McNemar p<0.05, ở ≤ 2× độ trễ. Receipt ghi cả ba con số này.

### D-8 — trần treo, chốt số sau T2

| Trần hiện tại | Giá trị | Ý nghĩa |
|:--|--:|:--|
| Thời gian mỗi câu | 120 s | chặn treo — **không** phải ngân sách |
| Token hoàn thành | 4096 | chặn sinh vô hạn |

Độ trễ và token **được ghi lại thô** cho từng câu trong receipt. Ngân sách T11
thật sự chốt từ baseline đo được — mọi con số độ trễ trong tài liệu cho tới lúc
đó là `UNMEASURED` (Gate 9).

**Trần treo là quan sát bị che, không phải câu trả lời sai.** Khi model chỉ
*chậm* chứ không treo, gộp lần trượt đó vào `accuracy` sẽ biến T2 thành phép đo
"ai kịp trả lời trong thời gian" thay vì "ai đúng". Receipt vì thế ghi **cả hai**:

| Trường | Nghĩa |
|:--|:--|
| `accuracy` | nghiêm ngặt — câu bị che mặt vẫn tính là sai |
| `accuracy_uncensored` | chỉ trên những câu trả lời được |
| `n_ceiling_hits` / `n_uncensored` | bao nhiêu câu bị che mặt |

Nếu `n_ceiling_hits` lớn, hai con số lệch nhau và con số nào đúng tùy câu hỏi
đang hỏi — đó chính là dữ liệu để chốt lại con số 120 s ở trên.

### Gate 9 — `model_call_made` ba giá trị

Mỗi ô trong receipt ghi `model_call_made`:

| Giá trị | Nghĩa |
|:--|:--|
| `true` | arm **có** gọi model và trả lời |
| `false` | arm **không** gọi model (ví dụ stub) |
| `null` | **không rõ** — hết thời gian hoặc sập trước khi kịp báo |

Không bao giờ khai một lời gọi đã xảy ra mà không quan sát được, và không bao
giờ khai "không có lời gọi" khi chính ta cũng không biết.

## Changelog

- **29/09/2026 (Claude Code — WP-7/O-02):** Tạo nhánh đo T2 (`harness.py`,
  `checker.py`, `eval_set/`). `bench_core.py` có sẵn từ trước, không đụng tới.
