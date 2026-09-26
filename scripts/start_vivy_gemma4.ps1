# start_vivy_gemma4.ps1
# [ISOLATED 26/09/2026] BẢN CŨ HƠN — GIỮ LÀM TÀI LIỆU SO SÁNH.
#   Bản vận hành: `vivy/scripts/start_vivy_gemma4.ps1` (có thêm commit 23/09/2026
#   nâng --reasoning-budget lên 1024 cho P1 Dynamic Thinking Budget).
#   Bản này dừng ở --reasoning-budget 384 (static hard cap).
# Fallback: Khởi động ViVy với Gemma4 E4B GGUF (nhanh hơn, đã proven)
#
# Changelog:
#   21/09/2026 (Antigravity IDE): Created as fallback nếu Qwen27B quá chậm.
#   21/09/2026 (Codex): Dùng canonical Gemma4 template; giữ GGUF/runtime cũ làm rollback.
#   23/09/2026 (Antigravity IDE): Cập nhật đường dẫn an toàn D:\models và D:\91s_Vivy\templates sau khi gom lưu trữ old-docs.
#   23/09/2026 (Antigravity IDE): Thêm --alias "gemma4-e4b" để chuẩn hóa model ID qua /v1/models theo chỉ thị CEO.
#   23/09/2026 (Antigravity IDE): Thêm --reasoning-format none, --reasoning-budget 384, --parallel 2 để khắc phục triệt để lỗi treo/rỗng content khi Codex gọi inference trực tiếp.

$MODEL_PATH = "D:\models\gemma4-e4b\vivy-gemma-e4b-q4km.gguf"
$LLAMA_SERVER = "D:\models\bin\llama-server.exe"
$TEMPLATE_PATH = "D:\91s_Vivy\templates\gemma4-canonical-2026-07-09.jinja"
$PORT = 8080

if (-not (Test-Path $MODEL_PATH)) {
    Write-Host "❌ Gemma4 E4B not found: $MODEL_PATH" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $TEMPLATE_PATH)) {
    Write-Host "❌ Gemma4 canonical template not found: $TEMPLATE_PATH" -ForegroundColor Red
    exit 1
}

$size = [math]::Round((Get-Item $MODEL_PATH).Length / 1GB, 2)
Write-Host "✅ Fallback model: Gemma4 E4B ($size GB)" -ForegroundColor Yellow
Write-Host "🚀 Starting llama-server on port $PORT..." -ForegroundColor Cyan
Write-Host "   Set env: `$env:VIVY_LLAMA_URL = 'http://127.0.0.1:$PORT'"
Write-Host "            `$env:VIVY_MODEL = 'gemma4-e4b'"

& $LLAMA_SERVER `
    --model $MODEL_PATH `
    --alias "gemma4-e4b" `
    --host "127.0.0.1" `
    --port $PORT `
    --ctx-size 4096 `
    --threads 8 `
    --load-mode mmap `
    --parallel 2 `
    --flash-attn auto `
    --reasoning-format none `
    --reasoning-budget 384 `
    --jinja `
    --chat-template-file $TEMPLATE_PATH `
    2>&1
