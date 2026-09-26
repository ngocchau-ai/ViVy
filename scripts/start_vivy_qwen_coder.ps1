# start_vivy_qwen_coder.ps1
# Khởi động Specialist Coder: Qwen2.5-Coder-7B trên port 8081 (Dual-Model Concurrency)
#
# Changelog:
#   21/09/2026 (Antigravity IDE): Triển khai dynamic path resolution.

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$WORKSPACE_ROOT = Resolve-Path (Join-Path $SCRIPT_DIR "..\..")
$MODEL_PATH = (Get-Item (Join-Path $WORKSPACE_ROOT "Vivy final\models\qwen2.5-coder-7b-instruct-q4_k_m.gguf")).FullName
$LLAMA_SERVER = "D:\models\bin\llama-server.exe"
$PORT = 8081

if (-not (Test-Path $MODEL_PATH)) {
    Write-Host "❌ Qwen2.5-Coder not found: $MODEL_PATH" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $LLAMA_SERVER)) {
    Write-Host "❌ llama-server.exe not found: $LLAMA_SERVER" -ForegroundColor Red
    exit 1
}

$size = [math]::Round((Get-Item $MODEL_PATH).Length / 1GB, 2)
Write-Host "✅ Specialist Model: Qwen2.5-Coder-7B ($size GB)" -ForegroundColor Green
Write-Host "🚀 Starting llama-server on port $PORT..." -ForegroundColor Cyan

& $LLAMA_SERVER `
    --model $MODEL_PATH `
    --host "127.0.0.1" `
    --port $PORT `
    --ctx-size 4096 `
    --threads 4 `
    --load-mode mmap `
    --parallel 1 `
    --flash-attn auto `
    --jinja
