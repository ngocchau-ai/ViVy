# ADR-0003: Layered Memory and Codegraph Freshness

## Status
Accepted

## Decision
Không nạp toàn bộ repository hoặc lịch sử chat vào mọi phiên. Context được truy xuất theo task, symbol và codegraph neighborhood. Codegraph phải khớp repository HEAD.

## Consequences
Khi codegraph stale, không mở task kiến trúc mới và không đóng task hiện tại.
