# start_vivy_qwen27b.ps1
# Khởi động ViVy với Qwen3.8-27B IQ2_XXS qua llama-server
#
# Changelog:
#   21/09/2026 (Antigravity IDE, Model Upgrade): Initial — thay thế Ollama backend
#
# Usage:
#   .\scripts\start_vivy_qwen27b.ps1
#   Sau đó: $env:VIVY_LLAMA_URL = "http://127.0.0.1:8080"
#            $env:VIVY_MODEL = "qwen3.8-27b"
#            python scripts\run_vivy.py

$MODEL_PATH = "D:\models\qwen3.8-27b\Qwen3.8-27B-UD-IQ2_XXS.gguf"
$LLAMA_SERVER = "D:\models\bin\llama-server.exe"
$HOST = "127.0.0.1"
$PORT = 8080
$CTX = 32768
$THREADS = 8

# Validate
if (-not (Test-Path $MODEL_PATH)) {
    Write-Host "❌ Model not found: $MODEL_PATH" -ForegroundColor Red
    Write-Host "   Run: hf download unsloth/Qwen3.8-27B-GGUF Qwen3.8-27B-UD-IQ2_XXS.gguf --local-dir D:\models\qwen3.8-27b"
    exit 1
}
if (-not (Test-Path $LLAMA_SERVER)) {
    Write-Host "❌ llama-server not found: $LLAMA_SERVER" -ForegroundColor Red
    exit 1
}

$size = [math]::Round((Get-Item $MODEL_PATH).Length / 1GB, 2)
Write-Host "✅ Model: $MODEL_PATH ($size GB)" -ForegroundColor Green
Write-Host "✅ Server: $LLAMA_SERVER" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Starting llama-server on http://$HOST:$PORT ..." -ForegroundColor Cyan
Write-Host "   Context: $CTX tokens | Threads: $THREADS"
Write-Host "   Set env: `$env:VIVY_LLAMA_URL = 'http://${HOST}:${PORT}'"
Write-Host "            `$env:VIVY_MODEL = 'qwen3.8-27b'"
Write-Host ""

# Start server (blocking — run in separate terminal)
& $LLAMA_SERVER `
    --model $MODEL_PATH `
    --host $HOST `
    --port $PORT `
    --ctx-size $CTX `
    --threads $THREADS `
    --no-mmap `
    --flash-attn `
    --log-prefix `
    2>&1
