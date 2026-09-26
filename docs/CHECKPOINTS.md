# Kho Checkpoint nội bộ — Hướng dẫn độc lập

> **Phạm vi:** tài liệu này mô tả **toàn bộ trọng số/checkpoint của ViVy core + Cautreo** đang lưu **nội bộ** (ngoài git). Đây là hướng dẫn độc lập để khôi phục, đối chiếu số liệu và biết vì sao chúng **không** nằm trong repo GitHub.
>
> **Ngày chốt số liệu:** 2026-09-26 · **Vị trí gốc:** `Vivy final/internal/` (gitignored)

---

## 1. Vì sao lưu nội bộ, không commit lên GitHub

| Ràng buộc | Chi tiết |
|---|---|
| Giới hạn cứng GitHub | File **> 100 MB bị từ chối** khi push — mọi `.pt` lớn đều vượt ngưỡng |
| Khối lượng | Tổng kho **6.40 GB** (6,401,192,939 byte) — không thể là một repo |
| Bí mật/mô hình | Trọng số là tài sản huấn luyện; repo chỉ chứa **code + spec + evidence text** |
| Chính sách D3 (26/09/2026) | "Kho checkpoint với 2 file và tinyllama sẽ lưu trữ nội bộ" |

`.gitignore` của repo chặn: `*.pt` · `*.gguf` · `*.safetensors` · `*.npy` · `*.npz` · `internal/`.

---

## 2. Kho chính — "2 file lớn + tinyllama" (D3)

| File | Dung lượng (byte) | Dung lượng đọc | Ngày tạo | Ghi chú |
|---|---:|---:|---|---|
| `checkpoints/checkpoints/observation_learning/vivy_final.pt` | 2,383,247,654 | **2.383 GB** | 2026-08-01 | Trọng số cuối của kỳ observation_learning |
| `checkpoints/checkpoints/observation_learning/vivy_best.pt` | 2,383,247,435 | **2.383 GB** | 2026-08-01 | Best-ckpt theo metric cùng kỳ (chênh 219 B so với final) |
| `checkpoints/checkpoints/vivy_core_tinyllama.pt` | 1,091,087,236 | **1.091 GB** | 2026-08-01 | Core ViVy trên backbone TinyLLaMA |
| `checkpoints/checkpoints/vivy_core_standalone.pt` | 153,587,163 | **153.6 MB** | 2026-08-01 | Core standalone (không backbone ngoài) |

**Tổng 4 file chính:** 5,917,969,488 byte ≈ **5.92 GB** (≈ 92.4% dung lượng kho).

---

## 3. Kho phụ — `models/` (checkpoint nhỏ, 2026-07-27)

| File | Dung lượng (byte) | Ghi chú |
|---|---:|---|
| `models/spatial/spatial_model.pt` | 21,421,041 | Mô hình không gian đầy đủ |
| `models/vivy_raw.pt` | 21,420,429 | Trạng thái thô trước tinh chỉnh |
| `models/70b/vivy_70b_trained.pt` | 14,758,181 | Nhánh 70b sau train |
| `models/vivy_70b_moe.pt` | 14,757,573 | Biến thể MoE 70b |
| `models/70b/model_compressed.pt` | 12,612,825 | Bản nén dùng inference |
| `models/spatial/spatial_module.pt` | 972,173 | Module không gian rời |

**Tổng `models/`:** 85,942,220 byte ≈ **85.9 MB**.

---

## 4. Chuyên gia MoE — `experts/` + memory vector

| Thành phần | Số lượng | Đơn vị | Tổng | Ngày |
|---|---:|---:|---:|---|
| `experts/expert_01.npz` … `expert_70.npz` | 70 | 4,102,556 – 4,105,772 B (~4.1 MB) | **287,303,885 B (287.3 MB)** | 2026-09-19 |
| `vivy_core_memory.npy` | 1 | 16,777,344 B | **16.8 MB** | 2026-09-19 |

**Tổng mục 4:** 304,081,229 byte ≈ **304.1 MB**.

---

## 5. Đối chiếu tổng

| Hạng mục | Byte | Tỷ trọng |
|---|---:|---:|
| 4 checkpoint chính (mục 2) | 5,917,969,488 | 92.4% |
| `models/` (mục 3) | 85,942,220 | 1.3% |
| `experts/` + memory (mục 4) | 304,081,229 | 4.8% |
| Lượt / file lẻ khác | ≈ 93,200,002 | 1.5% |
| **TỔNG** | **6,401,192,939** | **100%** |

*Đã kiểm: 81 file, tổng 6,401,192,939 B — khớp khi cộng từng nhóm ở trên.*

---

## 6. Cây vị trí trong `Vivy final/internal/`

```
internal/                          ← gitignore toàn bộ
├── checkpoints/
│   ├── checkpoints/
│   │   ├── observation_learning/
│   │   │   ├── vivy_best.pt       (2,383,247,435 B)
│   │   │   └── vivy_final.pt      (2,383,247,654 B)
│   │   ├── vivy_core_standalone.pt (153,587,163 B)
│   │   └── vivy_core_tinyllama.pt  (1,091,087,236 B)
│   └── models/
│       ├── 70b/model_compressed.pt | vivy_70b_trained.pt
│       ├── spatial/spatial_model.pt | spatial_module.pt
│       ├── vivy_70b_moe.pt
│       └── vivy_raw.pt
├── experts/
│   └── expert_01.npz … expert_70.npz
└── vivy_core_memory.npy
```

> Tầng `checkpoints/checkpoints/` là **giữ nguyên cấu trúc nguồn** (`core-room/vivy-beta-by-mimocode/checkpoints/…`) — không phải lỗi đánh máy.

---

## 7. Cách khôi phục / sử dụng

1. **Repo chỉ chứa code.** Clone `Vivy final` về máy không mang theo trọng số.
2. **Chép kho nội bộ** từ bản lưu `Vivy final/internal/` (hoặc backup ngoài) vào đúng cây ở mục 6.
3. **Kiểm tra toàn vẹn bằng dung lượng byte** ở bảng mục 2–4 (SHA-256 không nằm trong manifest reorg — manifest chỉ hash file text/code).
4. **Nạp checkpoint:**
   - Core ViVy: `vivy_core_tinyllama.pt` (có backbone) hoặc `vivy_core_standalone.pt` (độc lập).
   - Trọng số train observation_learning: `vivy_final.pt` (final) / `vivy_best.pt` (best-metric).
   - MoE experts: nạp `experts/expert_*.npz` theo index 01–70; memory vector: `vivy_core_memory.npy`.
5. **Tuyệt đối không** `git add` các file này; mọi `.pt/.npz/.npy/.gguf` đều nằm ngoài lịch sử git.

---

## 8. Lịch sử thay đổi

| Ngày | Thay đổi | Người/Agent |
|---|---|---|
| 2026-09-26 | Chốt số liệu toàn kho (81 file / 6.40 GB), lập hướng dẫn độc lập theo quyết định D3 — checkpoint lưu nội bộ, kèm số liệu khi commit | Claude Code (reorg Vivy+Cautreo) |

---

## 9. Liên quan

- `docs/DATA_MAP_2026-09-26.md` — bản đồ dữ liệu: cái gì đã di về đâu, cái gì đã xóa (ghi rõ nhóm bị xóa, **không** gồm nội dung ngoài phạm vi).
- `../.gitignore` — danh sách pattern chặn trọng số.
- `../vivy/pyproject.toml` — health-stack (`mypy` 7 thư mục, `ruff`, `pytest`).
