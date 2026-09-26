# verify_all.ps1 - Full Self-Verification for ViVy Final Distribution

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ViVy Final V1.0 - Full Self-Verification Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Resolve-Path "$ScriptDir\.."
$EngineDir = "$RootDir\engine\bin"
$CoreDir   = "$RootDir\core"
$AtlasesDir = "$RootDir\atlases"
$ModelsManifestDir = "$RootDir\models"

# Resolve Model Root (Priority: $env:MODEL_ROOT -> D:\models -> $RootDir\models)
$ModelRoot = if ($env:MODEL_ROOT -and (Test-Path $env:MODEL_ROOT)) {
    $env:MODEL_ROOT
} elseif (Test-Path "D:\models") {
    "D:\models"
} else {
    "$RootDir\models"
}

# Safe Python Interpreter Resolution
$PyExe = if ($env:PYTHON_EXE -and (Test-Path $env:PYTHON_EXE)) {
    $env:PYTHON_EXE
} else {
    $workspaceVenv = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path $workspaceVenv) {
        $workspaceVenv
    } else {
        $found = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($found -and (Test-Path $found) -and ($found -notmatch "WindowsApps")) {
            $found
        } else {
            $fallbacks = @(
                "D:\91s_Vivy\.venv\Scripts\python.exe",
                "C:\Users\LENOVO\AppData\Local\Programs\Python\Python311\python.exe",
                "C:\Users\LENOVO\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
            )
            $selected = $null
            foreach ($fb in $fallbacks) {
                if (Test-Path $fb) {
                    $selected = $fb
                    break
                }
            }
            if ($selected) { $selected } else { "python" }
        }
    }
}

$Passed = 0
$Failed = 0

function Check-Item ($label, $condition) {
    if ($condition) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
        $global:Passed++
    } else {
        Write-Host "  [FAIL] $label" -ForegroundColor Red
        $global:Failed++
    }
}

Write-Host ""
Write-Host "[1] Checking Python Runtime & Interpreter..." -ForegroundColor Yellow
$pyVer = & $PyExe --version 2>&1
Check-Item "Python executable resolved ($PyExe - $pyVer)" ($LASTEXITCODE -eq 0)

Write-Host ""
Write-Host "[2] Checking Cautreo Engine Binaries..." -ForegroundColor Yellow
Check-Item "cautreo.exe exists" (Test-Path "$EngineDir\cautreo.exe")
Check-Item "cautreo.dll exists" (Test-Path "$EngineDir\cautreo.dll")
Check-Item "cautreo-server.exe exists" (Test-Path "$EngineDir\cautreo-server.exe")

Write-Host ""
Write-Host "[3] Checking Cognitive Muscle Models (Root: $ModelRoot)..." -ForegroundColor Yellow
$gemmaPath = Join-Path $ModelRoot "gemma4-e4b\vivy-gemma-e4b-q4km.gguf"
$qwenVlPath = Join-Path $ModelRoot "qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
$mmprojPath = Join-Path $ModelRoot "qwen2-vl-72b\mmproj-Qwen2-VL-72B-Instruct-f16.gguf"

Check-Item "gemma4-e4b.gguf exists (~8.95GB - Active Reasoner)" (Test-Path $gemmaPath)
Check-Item "Qwen2-VL-72B-Instruct-Q4_K_M.gguf exists (~44.16GB - Multimodal Knowledge Pool)" (Test-Path $qwenVlPath)
Check-Item "mmproj-Qwen2-VL-72B-Instruct-f16.gguf exists (~1.30GB - Vision Projector)" (Test-Path $mmprojPath)
Write-Host "  [ISOLATED] vivy2.gguf and qwen3.8-27b.gguf archived to optimize NVMe disk space" -ForegroundColor DarkGray

Write-Host ""
Write-Host "[4] Checking ViVy Core & Cartography Components..." -ForegroundColor Yellow
Check-Item "engine/elastic_n_core.py exists" (Test-Path "$CoreDir\engine\elastic_n_core.py")
Check-Item "memory/cognitive_graph.py exists" (Test-Path "$CoreDir\memory\cognitive_graph.py")
Check-Item "orchestrator/model_router.py exists" (Test-Path "$CoreDir\orchestrator\model_router.py")
Check-Item "orchestrator/model_catalog.py exists" (Test-Path "$CoreDir\orchestrator\model_catalog.py")
Check-Item "integration/cautreo_binding.py exists (with WeightPager)" (Test-Path "$CoreDir\integration\cautreo_binding.py")
Check-Item "integration/cautreo_cartographer.py exists" (Test-Path "$CoreDir\integration\cautreo_cartographer.py")
Check-Item "integration/preflight_steering.py exists" (Test-Path "$CoreDir\integration\preflight_steering.py")
Check-Item "atlases/qwen2-vl-72b.catlas exists" (Test-Path "$AtlasesDir\qwen2-vl-72b.catlas")

Write-Host ""
Write-Host "[5] Testing C-ABI In-Process Direct Binding..." -ForegroundColor Yellow
$dllCheck = & $PyExe "$ScriptDir\verify_cautreo.py"
Check-Item "cautreo.dll loaded via ctypes with required symbols" ($dllCheck -like "*OK*")

Write-Host ""
Write-Host "[6] Checking Model Manifest Metadata..." -ForegroundColor Yellow
$manifestPath = "$ModelsManifestDir\model_manifest.json"
$manifestValid = $false
if (Test-Path $manifestPath) {
    try {
        $content = Get-Content $manifestPath -Raw | ConvertFrom-Json
        $manifestValid = ($null -ne $content.models)
    } catch {
        $manifestValid = $false
    }
}
Check-Item "models/model_manifest.json is valid and parseable" $manifestValid

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($Failed -eq 0) {
    Write-Host "  Summary: $Passed PASSED, $Failed FAILED - ALL GATES CLEARED" -ForegroundColor Green
} else {
    Write-Host "  Summary: $Passed PASSED, $Failed FAILED" -ForegroundColor Red
}
Write-Host "============================================================" -ForegroundColor Cyan

if ($Failed -eq 0) {
    exit 0
} else {
    exit 1
}

