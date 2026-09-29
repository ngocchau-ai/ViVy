# start_vivy_unified.ps1 — 1-Touch Unified Runner for ViVy Final
# Connects ViVy Core (Soul) to Cautreo Engine (Vessel) + Models (Muscle)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ViVy Final V1.0 — Unified Cognitive System (Soul + Vessel)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Resolve-Path "$ScriptDir\.."
$EngineDir = "$RootDir\engine\bin"
$CoreDir   = "$RootDir\vivy"   # [FIXED 26/09/2026] package runtime là vivy/, không còn core/
$ModelsDir = "$RootDir\models"

# 1. Environment configuration
$env:PYTHONIOENCODING = "utf-8"
$env:CAUTREO_DLL_PATH = "$EngineDir\cautreo.dll"
$env:VIVY_LLAMA_URL   = "http://127.0.0.1:8080"
$env:VIVY_MODEL       = "gemma4-e4b"
# [REROUTED 26/09/2026] qwen2.5-coder:7b chưa từng có gguf trên đĩa. Chỉ có
# gemma4-e4b gánh text/code. Đặt VIVY_CODER_URL nếu có specialist server riêng.
$env:VIVY_CODER_MODEL = "gemma4-e4b"

Write-Host "[1/3] Environment configured:" -ForegroundColor Green
Write-Host "      • Native DLL   : $env:CAUTREO_DLL_PATH"
Write-Host "      • In-Engine URL: $env:VIVY_LLAMA_URL"
Write-Host "      • Reasoner     : $env:VIVY_MODEL"
Write-Host "      • Specialist   : $env:VIVY_CODER_MODEL"

# 2. Check native Cautreo DLL
Write-Host "`n[2/3] Checking Cautreo Native C-ABI..." -ForegroundColor Green
if (Test-Path $env:CAUTREO_DLL_PATH) {
    Write-Host "      ✅ Cautreo DLL found (In-process 0ms memory active)" -ForegroundColor Green
} else {
    Write-Host "      ⚠️ Cautreo DLL not found, will use in-memory fallback" -ForegroundColor Yellow
}

# 3. Launch ViVy Core interactive session
Write-Host "`n[3/3] Starting ViVy Core Interactive Runner..." -ForegroundColor Green
Set-Location $CoreDir
python "$CoreDir\scripts\run_vivy.py" @args
