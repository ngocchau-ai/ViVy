# ADR-0001: NPS Core V1 Architecture Baseline

## Status
Accepted

## Context
Ba tài liệu nguồn thể hiện ba giai đoạn tư duy: polyhedral/soft-qubit, unitary reasoner và hybrid synthesis.

## Decision
Dùng NPS Core V1 làm baseline. Giữ các ý tưởng population reasoning, state-space, constraint reasoning, delegation, evidence và verification. Không coi ngôn ngữ lượng tử là chứng minh kỹ thuật nếu chưa có thuật toán và benchmark.

## Consequences
Mọi module mới phải ánh xạ vào kiến trúc V1 hoặc có ADR thay đổi.
