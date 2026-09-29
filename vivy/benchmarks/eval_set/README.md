# T2 eval set — 120 câu, 4 miền

Thuộc WP-7 / O-02. Bộ câu hỏi đo lường để trả lời một câu hỏi duy nhất:
**pipeline có giá trị so với Gemma thuần không?**

| Miền | Tổng | Dev | Held-out | Đối kháng |
|:--|--:|--:|--:|--:|
| `quantum` | 30 | 8 | 22 | 8 |
| `math` | 30 | 8 | 22 | 8 |
| `graph` | 30 | 8 | 22 | 7 |
| `compute` | 30 | 8 | 22 | 7 |
| **Tổng** | **120** | **32** | **88** | **30** |

- **answerable** (90): có một đáp án kiểm chứng được bằng chương trình.
- **adversarial** (30): thiếu dữ kiện hoặc bài toán không xác định. Trả lời
  đúng là **từ chối** (`VERDICT: INSUFFICIENT_EVIDENCE`). Trả lời một con số
  cụ thể là **bịa** và bị chấm sai.

## Hợp đồng khai báo đáp án

Mọi prompt trong bộ này mang cùng một chỉ dẫn:

```
End your reply with exactly one line, on its own:
  ANSWER: <value>
or, if the question cannot be answered from the information given:
  VERDICT: INSUFFICIENT_EVIDENCE
```

Chấm điểm là **phân tích cú pháp**, không phải đọc văn bản. `benchmarks/checker.py`
so theo `expected_kind`:

| `expected_kind` | So bằng |
|:--|:--|
| `number` | sai số tuyệt đối ≤ `tolerate` (0 với số nguyên) |
| `set` | **bằng nhau đúng tập** — thiếu/thừa đều sai |
| `expression` | giá trị số nếu đánh giá được, ngược lại so chuỗi chuẩn hóa |
| `text` | bằng nhau sau chuẩn hóa (bỏ khoảng trắng, hạ chữ thường) |
| `insufficient` | đúng một token trong danh sách đóng `VERDICT_TOKENS` |

**Cấm khớp chuỗi con lỏng** (yêu cầu của kế hoạch). Không bao giờ tìm chuỗi
`expected` trong câu trả lời.

## D-7 — held-out nằm ngoài repo

Quyết định của chủ dự án (29/09/2026): **88 câu held-out không nằm trong repo.**

Trong repo chỉ có:

| File | Nội dung | Có prompt/đáp án? |
|:--|:--|:--|
| `dev_set.jsonl` | 32 câu dev | ✅ có — ai cũng xem được |
| `heldout_manifest.json` | 88 dòng `{id, domain, split, kind, expected_kind, sha256}` | ❌ **không** |
| `generate.py` | bộ sinh tất cả 120 câu, tất định theo seed | ✅ sinh lại được |

Vì sao làm vậy: một bảng tri thức (hoặc một file SFT) chứa prompt + đáp án
held-out sẽ làm phép đo vô nghĩa. Manifest chỉ có hash nên vẫn **chặn được file
bị đánh tráo** mà không lộ đáp án.

### Chủ dự án: sinh file held-out

```powershell
cd D:\91s- Tái cấu trúc lân thứ 4\Vivy_final\vivy

# Bắt buộc: --out phải nằm NGOÀI Vivy_final/. Script từ chối ghi bên trong.
python -m benchmarks.eval_set.generate --split heldout --out D:\91s_heldout\vivy_T2\heldout_set.jsonl
```

Script **exit code 2** nếu `--out` nằm trong `Vivy_final/`. Đây là hành vi cố
ý, không phải lỗi.

### Chủ dự án: chạy đo

```powershell
$env:VIVY_HELDOUT_PATH = "D:\91s_heldout\vivy_T2\heldout_set.jsonl"
python benchmarks/harness.py --split heldout --arms baseline,pipeline,pipeline_decoder
```

Hoặc truyền thẳng `--heldout <path>`.

Harness **fail-closed** khi thiếu file, và từ chối nếu bất kỳ câu nào lệch
`sha256` so với manifest. Không có đường fallback sang bản trong repo — vì bản
trong repo không tồn tại.

**Không** đưa file held-out vào `D:\2brain` (đó là bảng tri thức).

## Sinh lại — và tại sao hash không đổi

```powershell
python -m benchmarks.eval_set.generate --write-dev --write-manifest --print-summary
```

Bộ sinh dùng seed cố định `20260929`, nên chạy lại cho đúng từng byte và hash
trong manifest vẫn khớp. Nếu sửa bộ sinh, hash sẽ đổi và manifest phải sinh lại
— lúc đó held-out cũ của chủ dự án **không còn dùng được** với manifest mới.

## File

| File | Vai trò |
|:--|:--|
| `schema.py` | `EvalItem`, chuẩn hóa JSON, `sha256_item`, `manifest_for` |
| `generate.py` | bộ sinh tất định; CLI `--split` / `--out` / `--write-dev` / `--write-manifest` |
| `dev_set.jsonl` | 32 câu dev (commit) |
| `heldout_manifest.json` | 88 hash held-out (commit) |
| `../checker.py` | chấm điểm lập trình |
| `../harness.py` | chạy A/B/C, ghi receipt `evidence/T2-<run_id>.json` |

Test: `tests/test_benchmarks_eval.py`.

## Changelog

- **29/09/2026 (Claude Code — WP-7/O-02):** Khởi tạo. 120 câu, checker lập
  trình, harness A/B/C, tách held-out theo D-7, trần treo theo D-8.
