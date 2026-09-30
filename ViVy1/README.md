# Tài liệu ViVy 1 (Legacy / Llama-based)

Thư mục này cô lập toàn bộ các tài sản thuộc về phiên bản **ViVy 1**, phiên bản tiền nhiệm dựa trên kiến trúc Transformer của Llama/Ollama (external weights).

## Mục đích cô lập
Theo quyết định kiến trúc mới nhất, dự án Vytrading không phụ thuộc vào trọng số bên ngoài (hộp đen). Lõi nhận thức ViVy Core (ViVy 2) được xây dựng độc lập bằng toán học ma trận tại `src/vivy/core/`. Do đó, toàn bộ các script chưng cất, package và Modelfile của phiên bản cũ được di dời vào đây để lưu trữ lịch sử và làm đối chứng.

## Cấu trúc thư mục
- `modelfiles/`: Chứa cấu hình Ollama Modelfile cho bản ViVy (3B) và ViVy-4B.
- `scripts/`: Chứa các script Python dùng để chưng cất (compress) từ 40B MoE xuống 4B và script đóng gói lên Ollama.
