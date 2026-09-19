# ADR-0002: Codex–Local Boundary

## Status
Accepted

## Decision
Codex chỉ điều phối. Toàn bộ production code do model local thực hiện. Local tester và local reviewer cung cấp evidence độc lập tương đối.

## Consequences
Mọi TaskContract code phải ghi executor local, test yêu cầu, reviewer và codegraph refresh.
