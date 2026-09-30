# Context Strategy

Mặc định chỉ nạp:

1. Identity capsule.
2. TaskContract.
3. Architecture refs liên quan.
4. Codegraph neighborhood.
5. Target symbol và tests.

Mở rộng theo progressive disclosure:

```text
summary → symbol → file section → full file → adjacent module
```

Không nạp raw files hoặc toàn bộ lịch sử chat nếu không có yêu cầu truy nguyên.
