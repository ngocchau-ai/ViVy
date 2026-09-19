# AGENTS.md — Quy tắc hoạt động

## Codex

Codex chỉ điều phối, phân rã, kiểm tra contract, tổng hợp evidence và duy trì project state.

### Codex được phép

- đọc repository và kiến trúc;
- tạo TaskContract;
- chọn local executor;
- yêu cầu test/review;
- đánh giá acceptance criteria;
- yêu cầu cập nhật codegraph;
- cập nhật task status, ADR, handoff và tài liệu điều phối.

### Codex bị cấm

- viết production source code;
- sửa production source trực tiếp;
- tự phê duyệt implementation;
- bỏ qua local coder/tester/reviewer;
- đóng task khi codegraph stale;
- thay đổi kiến trúc không có ADR.

## Local models

Toàn bộ implementation phải do model local thực hiện theo role contract.

## Definition of Done

- local model tạo code;
- test pass;
- local reviewer hoàn tất;
- evidence tồn tại;
- codegraph đồng bộ với HEAD;
- memory/handoff cập nhật.
