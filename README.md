# NPS Core — Codex Context Package

Đây là gói context khởi tạo cho dự án **N-Thought Principal Scientist Core (NPS Core)**.

## Cách dùng

1. Giải nén thư mục này vào máy local.
2. Mở thư mục bằng Codex như một project/repository.
3. Bắt đầu bằng prompt trong `CODEX_BOOTSTRAP.md`.
4. Codex chỉ điều phối; toàn bộ production code phải do model local thực hiện.
5. Không được đóng task khi codegraph chưa đồng bộ với repository HEAD.

## Thứ tự đọc bắt buộc

1. `memory/00-identity/project-charter.md`
2. `memory/00-identity/non-negotiables.md`
3. `memory/07-sessions/handoff.md`
4. `memory/03-codegraph/codegraph-summary.md`
5. TaskContract hiện tại
6. ADR liên quan
7. Symbol/file do codegraph chỉ định

## Nguồn gốc

Ba tài liệu trong `raw/` là dữ liệu tư duy thô theo ba giai đoạn. `ARCHITECTURE.md` là baseline V1 chính thức đã tái cấu trúc từ các nguồn đó.
