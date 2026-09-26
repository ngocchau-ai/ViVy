# Codex Orchestration Policy

Codex chỉ tạo, điều phối và kiểm tra TaskContract.

## Pre-task checks

- Identity files đã đọc.
- Codegraph fresh.
- Task không trùng active task.
- ADR liên quan đã truy xuất.
- Token budget đã đặt.

## Post-task checks

- Local author evidence.
- Test evidence.
- Review evidence.
- Acceptance criteria.
- Codegraph refresh.
- Handoff update.
