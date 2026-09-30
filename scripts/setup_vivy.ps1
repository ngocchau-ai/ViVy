# ViVy Final Core V1.0 — Windows Setup Script
# Base model: Gemma 4 E4B (Apache 2.0, Text+Vision+Audio, MTP native)
# Runtime: llama.cpp (llama-server)
#
# Usage: .\scripts\setup_vivy.ps1
# Requires: Windows 10+, PowerShell 5+, 16GB RAM, ~8GB disk space
#
# Changelog:
#   19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.

param(
    [string]$ModelDir = "$PSScriptRoot\..\models",
    [string]$LlamaDir = "$PSScriptRoot\..\llama.cpp",
    [switch]$SkipModelDownload,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$VivyVersion = "1.0.0"
$ModelFile = "gemma-4-e4b-q4_k_m.gguf"
$ModelUrl = "https://huggingface.co/ggml-org/gemma-4-e4b-GGUF/resolve/main/gemma-4-e4b-q4_k_m.gguf"
$LlamaUrl = "https://github.com/ggml-org/llama.cpp/releases/latest/download/llama-*-bin-win-avx2-x64.zip"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ViVy Final Core V$VivyVersion — Setup Script (Windows)"       -ForegroundColor Cyan
Write-Host "  Base model: Gemma 4 E4B (Q4_K_M)"                              -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ─── Step 1: Check Python ───────────────────────────────────────────
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found. Install Python 3.10+ first."
    exit 1
}
$pyver = python --version 2>&1
Write-Host "  Found: $pyver" -ForegroundColor Green

# ─── Step 2: Install Python dependencies ────────────────────────────
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot\.."
python -m pip install --upgrade pip -q
python -m pip install httpx pillow -q
python -m pip install -e ".[dev]" -q
Pop-Location
Write-Host "  Dependencies installed." -ForegroundColor Green

# ─── Step 3: Download llama.cpp prebuilt binary ──────────────────────
if (-not $SkipBuild) {
    Write-Host "[3/5] Setting up llama.cpp server..." -ForegroundColor Yellow

    $llamaServerPath = "$LlamaDir\llama-server.exe"
    if (Test-Path $llamaServerPath) {
        Write-Host "  llama-server already exists, skipping download." -ForegroundColor Green
    } else {
        Write-Host "  Downloading llama.cpp prebuilt binary..."
        New-Item -ItemType Directory -Path $LlamaDir -Force | Out-Null

        # Try to download latest release
        try {
            $releases = Invoke-RestMethod "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
            $asset = $releases.assets | Where-Object { $_.name -match "win-avx2-x64\.zip" } | Select-Object -First 1
            if ($asset) {
                $zipPath = "$env:TEMP\llama-cpp.zip"
                Write-Host "  Downloading: $($asset.name)"
                Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath
                Expand-Archive -Path $zipPath -DestinationPath $LlamaDir -Force
                Remove-Item $zipPath
                Write-Host "  llama.cpp downloaded." -ForegroundColor Green
            } else {
                Write-Warning "  Could not find Windows AVX2 binary. Please download manually from:"
                Write-Warning "  https://github.com/ggml-org/llama.cpp/releases"
            }
        } catch {
            Write-Warning "  Download failed: $_"
            Write-Warning "  Please install llama.cpp manually."
        }
    }
} else {
    Write-Host "[3/5] Skipping llama.cpp setup (--SkipBuild)." -ForegroundColor Gray
}

# ─── Step 4: Download Gemma 4 E4B GGUF ──────────────────────────────
if (-not $SkipModelDownload) {
    Write-Host "[4/5] Downloading Gemma 4 E4B Q4_K_M GGUF..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $ModelDir -Force | Out-Null

    $modelPath = Join-Path $ModelDir $ModelFile
    if (Test-Path $modelPath) {
        Write-Host "  Model already exists: $modelPath" -ForegroundColor Green
    } else {
        Write-Host "  Downloading from HuggingFace (~5GB)..."
        Write-Host "  URL: $ModelUrl"
        Write-Host "  This may take a while on slow connections."
        try {
            $wc = New-Object System.Net.WebClient
            $wc.DownloadFile($ModelUrl, $modelPath)
            Write-Host "  Model downloaded: $modelPath" -ForegroundColor Green
        } catch {
            Write-Warning "  Download failed: $_"
            Write-Warning "  Alternative: use huggingface-cli to download:"
            Write-Warning "    pip install huggingface_hub"
            Write-Warning "    huggingface-cli download ggml-org/gemma-4-e4b-GGUF $ModelFile --local-dir models/"
        }
    }
} else {
    Write-Host "[4/5] Skipping model download (--SkipModelDownload)." -ForegroundColor Gray
}

# ─── Step 5: Verify installation ────────────────────────────────────
Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow

$failures = @()

# Check llama-server
$llamaServer = Get-ChildItem "$LlamaDir\llama-server*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($llamaServer) {
    Write-Host "  llama-server: $($llamaServer.FullName)" -ForegroundColor Green
} else {
    Write-Warning "  llama-server not found at $LlamaDir"
    $failures += "llama-server"
}

# Check model
$modelPath = Join-Path $ModelDir $ModelFile
if (Test-Path $modelPath) {
    $sizeMB = [math]::Round((Get-Item $modelPath).Length / 1MB, 0)
    Write-Host "  Model: $modelPath ($sizeMB MB)" -ForegroundColor Green
} else {
    Write-Warning "  Model not found: $modelPath"
    $failures += "model"
}

# Check Python imports
$pyCheck = python -c "import httpx; from engine.elastic_n_core import ElasticNCore; from memory.cognitive_graph import CognitiveStateGraph; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python imports: OK" -ForegroundColor Green
} else {
    Write-Warning "  Python imports failed: $pyCheck"
    $failures += "python-imports"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($failures.Count -eq 0) {
    Write-Host "  Setup COMPLETE. To run ViVy:" -ForegroundColor Green
    Write-Host ""
    Write-Host "  1. Start llama-server:" -ForegroundColor White
    Write-Host "     $($llamaServer.FullName) -m models\$ModelFile -c 32768 --port 8080 --jinja" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Run ViVy:" -ForegroundColor White
    Write-Host "     python scripts\run_vivy.py --mode chat" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. Smoke test:" -ForegroundColor White
    Write-Host "     python scripts\test_integration.py" -ForegroundColor Gray
} else {
    Write-Host "  Setup incomplete. Failed: $($failures -join ', ')" -ForegroundColor Red
    Write-Host "  Fix the above issues and re-run setup." -ForegroundColor Red
}
Write-Host "============================================================" -ForegroundColor Cyan
