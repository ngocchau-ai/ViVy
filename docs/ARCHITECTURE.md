# NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

---

## [ISOLATED 26/09/2026] File này đã trở thành REDIRECT STUB

> **Nội dung gốc (1995 dòng) đã được gom vào**
> **[→ `docs/TECHNICAL_DIRECTION.md` §Phần 1 — NPS Core: Kiến trúc Principal Scientist Model](TECHNICAL_DIRECTION.md)**
> theo yêu cầu *"gom về 5 tài liệu"* (26/09/2026).

**Lý do giữ lại file này thay vì xóa:** ~25 vị trí vẫn tham chiếu theo tên
`ARCHITECTURE.md` — gồm `vivy/memory/02-decisions/ADR-0005..0018.md`,
`vivy/memory/01-architecture/system-overview.md`,
`vivy/memory/04-tasks/PROJECT-COMPLETION-MATRIX.md`,
`vivy/orchestration/codex/tasks/TASK-001..005.yaml` (deep link theo anchor),
`vivy/tests/unit/test_department_orchestration.py`. Stub này giữ đường dẫn sống
để các tham chiếu đó không vỡ (Quy tắc 4: cô lập, không xóa).

**Bản đầy đủ lưu trữ gốc (byte-identical):**
[`old-docs/01-architecture-legacy/ARCHITECTURE_UNITARY_REASONER.md`](../../old-docs/01-architecture-legacy/ARCHITECTURE_UNITARY_REASONER.md)

**Lưu ý anchor:** các anchor trong `TASK-00*.yaml` (vd `#6-kien-truc-he-thong`)
được viết theo kiểu ASCII-fold, **không** khớp slug Unicode của GitHub
(`#6-kiến-trúc-hệ-thống`). Tình trạng này có từ trước khi gom tài liệu —
không phải lỗi sinh ra bởi lần gom này. Bảng dưới đây ánh xạ **số mục → tiêu đề →
anchor thật** để nav dễ hơn anchor cũ.

---

## Chỉ mục mục gốc (→ TECHNICAL_DIRECTION.md)

| # | Tiêu đề gốc | Link tới TECHNICAL_DIRECTION.md |
|:--|:--|:--|
| 1 | NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL | [`#nps-core-kiến-trúc-principal-scientist-model`](TECHNICAL_DIRECTION.md#nps-core-kiến-trúc-principal-scientist-model) |
| 2 | 0. TUYÊN BỐ DỰ ÁN | [`#0-tuyên-bố-dự-án`](TECHNICAL_DIRECTION.md#0-tuyên-bố-dự-án) |
| 3 | 1. VỊ TRÍ CỦA BA TÀI LIỆU NGUỒN | [`#1-vị-trí-của-ba-tài-liệu-nguồn`](TECHNICAL_DIRECTION.md#1-vị-trí-của-ba-tài-liệu-nguồn) |
| 4 | 2. BẢN SẮC NHẬN THỨC CỦA MODEL | [`#2-bản-sắc-nhận-thức-của-model`](TECHNICAL_DIRECTION.md#2-bản-sắc-nhận-thức-của-model) |
| 5 | 3. ĐƠN VỊ CƠ BẢN: THOUGHT STATE | [`#3-đơn-vị-cơ-bản-thought-state`](TECHNICAL_DIRECTION.md#3-đơn-vị-cơ-bản-thought-state) |
| 6 | 4. BA GIÁ TRỊ N TÁCH BIỆT | [`#4-ba-giá-trị-n-tách-biệt`](TECHNICAL_DIRECTION.md#4-ba-giá-trị-n-tách-biệt) |
| 7 | 5. ADAPTIVE N CONTROLLER | [`#5-adaptive-n-controller`](TECHNICAL_DIRECTION.md#5-adaptive-n-controller) |
| 8 | 6. KIẾN TRÚC HỆ THỐNG | [`#6-kiến-trúc-hệ-thống`](TECHNICAL_DIRECTION.md#6-kiến-trúc-hệ-thống) |
| 9 | 7. VAI TRÒ CODEX VÀ MODEL LOCAL | [`#7-vai-trò-codex-và-model-local`](TECHNICAL_DIRECTION.md#7-vai-trò-codex-và-model-local) |
| 10 | 8. TASK CONTRACT CHO PHÁT TRIỂN CODE | [`#8-task-contract-cho-phát-triển-code`](TECHNICAL_DIRECTION.md#8-task-contract-cho-phát-triển-code) |
| 11 | 9. MEMORY ARCHITECTURE | [`#9-memory-architecture`](TECHNICAL_DIRECTION.md#9-memory-architecture) |
| 12 | 10. CODEGRAPH | [`#10-codegraph`](TECHNICAL_DIRECTION.md#10-codegraph) |
| 13 | 11. GIẢI PHÁP TIẾT KIỆM TOKEN | [`#11-giải-pháp-tiết-kiệm-token`](TECHNICAL_DIRECTION.md#11-giải-pháp-tiết-kiệm-token) |
| 14 | 12. REPOSITORY ĐỀ XUẤT | [`#12-repository-đề-xuất`](TECHNICAL_DIRECTION.md#12-repository-đề-xuất) |
| 15 | 13. CÁC DATA CONTRACT CHÍNH | [`#13-các-data-contract-chính`](TECHNICAL_DIRECTION.md#13-các-data-contract-chính) |
| 16 | 14. VERIFICATION TRIBUNAL | [`#14-verification-tribunal`](TECHNICAL_DIRECTION.md#14-verification-tribunal) |
| 17 | 15. PHƯƠNG ÁN CHƯNG CẤT | [`#15-phương-án-chưng-cất`](TECHNICAL_DIRECTION.md#15-phương-án-chưng-cất) |
| 18 | 16. KẾ HOẠCH PHÁT TRIỂN | [`#16-kế-hoạch-phát-triển`](TECHNICAL_DIRECTION.md#16-kế-hoạch-phát-triển) |
| 19 | Giai đoạn 0 — Foundation Freeze | [`#giai-đoạn-0-foundation-freeze`](TECHNICAL_DIRECTION.md#giai-đoạn-0-foundation-freeze) |
| 20 | Giai đoạn 1 — Deterministic Runtime Prototype | [`#giai-đoạn-1-deterministic-runtime-prototype`](TECHNICAL_DIRECTION.md#giai-đoạn-1-deterministic-runtime-prototype) |
| 21 | Giai đoạn 2 — Local Software Department | [`#giai-đoạn-2-local-software-department`](TECHNICAL_DIRECTION.md#giai-đoạn-2-local-software-department) |
| 22 | Giai đoạn 3 — Codegraph + Token-Efficient Context | [`#giai-đoạn-3-codegraph-token-efficient-context`](TECHNICAL_DIRECTION.md#giai-đoạn-3-codegraph-token-efficient-context) |
| 23 | Giai đoạn 4 — Adaptive N + Experiment Designer | [`#giai-đoạn-4-adaptive-n-experiment-designer`](TECHNICAL_DIRECTION.md#giai-đoạn-4-adaptive-n-experiment-designer) |
| 24 | Giai đoạn 5 — Verification Tribunal | [`#giai-đoạn-5-verification-tribunal`](TECHNICAL_DIRECTION.md#giai-đoạn-5-verification-tribunal) |
| 25 | Giai đoạn 6 — Distillation Dataset | [`#giai-đoạn-6-distillation-dataset`](TECHNICAL_DIRECTION.md#giai-đoạn-6-distillation-dataset) |
| 26 | Giai đoạn 7 — Train NPS Student Model | [`#giai-đoạn-7-train-nps-student-model`](TECHNICAL_DIRECTION.md#giai-đoạn-7-train-nps-student-model) |
| 27 | Giai đoạn 8 — Scientific Principal Model | [`#giai-đoạn-8-scientific-principal-model`](TECHNICAL_DIRECTION.md#giai-đoạn-8-scientific-principal-model) |
| 28 | 17. BENCHMARK CỐT LÕI | [`#17-benchmark-cốt-lõi`](TECHNICAL_DIRECTION.md#17-benchmark-cốt-lõi) |
| 29 | 18. RỦI RO | [`#18-rủi-ro`](TECHNICAL_DIRECTION.md#18-rủi-ro) |
| 30 | 19. NGUYÊN TẮC BẤT BIẾN | [`#19-nguyên-tắc-bất-biến`](TECHNICAL_DIRECTION.md#19-nguyên-tắc-bất-biến) |
| 31 | 20. WORKFLOW CHUẨN CHO MỖI TASK CODE | [`#20-workflow-chuẩn-cho-mỗi-task-code`](TECHNICAL_DIRECTION.md#20-workflow-chuẩn-cho-mỗi-task-code) |
| 32 | 21. WORKFLOW CHUẨN CHO MỖI TASK NGHIÊN CỨU | [`#21-workflow-chuẩn-cho-mỗi-task-nghiên-cứu`](TECHNICAL_DIRECTION.md#21-workflow-chuẩn-cho-mỗi-task-nghiên-cứu) |
| 33 | 22. FILE ĐỌC ĐẦU TIÊN CHO CODEX | [`#22-file-đọc-đầu-tiên-cho-codex`](TECHNICAL_DIRECTION.md#22-file-đọc-đầu-tiên-cho-codex) |
| 34 | 23. FILE ĐỌC ĐẦU TIÊN CHO LOCAL CODER | [`#23-file-đọc-đầu-tiên-cho-local-coder`](TECHNICAL_DIRECTION.md#23-file-đọc-đầu-tiên-cho-local-coder) |
| 35 | 24. DEFINITION OF DONE | [`#24-definition-of-done`](TECHNICAL_DIRECTION.md#24-definition-of-done) |
| 36 | 25. ƯU TIÊN TRIỂN KHAI NGAY | [`#25-ưu-tiên-triển-khai-ngay`](TECHNICAL_DIRECTION.md#25-ưu-tiên-triển-khai-ngay) |
| 37 | 26. KẾT LUẬN KIẾN TRÚC V1 | [`#26-kết-luận-kiến-trúc-v1`](TECHNICAL_DIRECTION.md#26-kết-luận-kiến-trúc-v1) |
| 38 | PHỤ LỤC A — PROJECT CHARTER RÚT GỌN | [`#phụ-lục-a-project-charter-rút-gọn`](TECHNICAL_DIRECTION.md#phụ-lục-a-project-charter-rút-gọn) |
| 39 | PHỤ LỤC B — CHECKLIST KIỂM TRA DRIFT | [`#phụ-lục-b-checklist-kiểm-tra-drift`](TECHNICAL_DIRECTION.md#phụ-lục-b-checklist-kiểm-tra-drift) |
| 40 | PHỤ LỤC C — TRẠNG THÁI TÀI LIỆU | [`#phụ-lục-c-trạng-thái-tài-liệu`](TECHNICAL_DIRECTION.md#phụ-lục-c-trạng-thái-tài-liệu) |

---

## Lịch Sử Thay Đổi (Changelog)

| Agent | Thời gian | Hành động |
|:--|:--|:--|
| Claude Code | 26/09/2026 | Chuyển nội dung (1995 dòng) vào `docs/TECHNICAL_DIRECTION.md` §Phần 1. Thay file này bằng redirect stub kèm chỉ mục mục. Lý do: user yêu cầu gom tài liệu về 5 doc chuẩn, ngừng nạn tài liệu v1/v2/v3. |
