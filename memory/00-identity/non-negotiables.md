# Non-Negotiables

- INV-01: Codex chỉ điều phối.
- INV-02: Production code do model local thực hiện.
- INV-03: Mọi patch phải có test hoặc lý do miễn test.
- INV-04: Codegraph phải khớp repository HEAD.
- INV-05: Không đồng nhất N hypothesis với N executor.
- INV-06: Không lưu chain-of-thought dài làm memory.
- INV-07: Mọi evidence phải có provenance.
- INV-08: Executor cùng model/prompt/data không được coi là độc lập hoàn toàn.
- INV-09: Chưng cất không thay thế runtime identity.
- INV-10: Mọi thay đổi kiến trúc phải có ADR.
- INV-11: Model được phép báo thiếu bằng chứng.
- INV-12: Context phải truy xuất theo task và codegraph.
