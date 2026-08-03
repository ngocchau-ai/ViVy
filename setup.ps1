# setup.ps1 — Unitary Reasoner dev environment (Windows PowerShell)
param()

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

Write-Host "=== Unitary Reasoner — setup ==="

# 1. Python version
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
       elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
       else { throw "Python not found" }
$ver = & $py --version
Write-Host "Python: $ver"

# 2. Create venv
if (-not (Test-Path .venv)) {
    Write-Host "Creating .venv..."
    & $py -m venv .venv
}
.\.venv\Scripts\Activate.ps1

# 3. Install deps
Write-Host "Installing dependencies..."
pip install -q -e ".[dev]"

# 4. Verify Ollama
Write-Host "Checking Ollama..."
try {
    $ollamaVer = & ollama --version 2>$null
    Write-Host "Ollama: $ollamaVer"
    $models = & ollama list 2>$null
    if ($models -match "gemma4") {
        Write-Host "Gemma 4EB: available"
    } else {
        Write-Host "WARNING: gemma4:e4b not pulled — run: ollama pull gemma4:e4b"
    }
} catch {
    Write-Host "WARNING: ollama not found — install from https://ollama.com"
}

# 5. Verify
Write-Host "Running tests..."
python -m pytest -q

Write-Host ""
Write-Host "=== Setup complete ==="
Write-Host "Activate: .\.venv\Scripts\Activate.ps1"
Write-Host "Run demo: python demo.py"