<#
.SYNOPSIS
  start_desktop.ps1 — Khởi chạy Cautreo Desktop Studio V1.0 (1-Click)
.DESCRIPTION
  Khởi động Backend API Server (port 8765) và mở Dedicated Desktop Window qua Edge Native Shell.
#>

param(
    [switch]$NoBrowser = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VivyFinalDir = Split-Path -Parent $ScriptDir
$DesktopDir = Join-Path $VivyFinalDir "desktop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  CAUTREO DESKTOP STUDIO V1.0 — 1-CLICK LAUNCHER" -ForegroundColor Cyan
Write-Host "  Living Room Interface for HoH x ViVy Core" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check if backend is already listening
$port = 8765
$isOpen = $false
try {
    $client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $port)
    $client.Close()
    $isOpen = $true
} catch {
    $isOpen = $false
}

if (-not $isOpen) {
    Write-Host "[+] Khởi động Cautreo Desktop Backend Server..." -ForegroundColor Yellow
    $backendScript = Join-Path $DesktopDir "backend\server.py"
    $job = Start-Process python -ArgumentList "`"$backendScript`"" -WorkingDirectory $DesktopDir -WindowStyle Hidden -PassThru
    Write-Host "[+] Backend Server PID: $($job.Id)" -ForegroundColor Green

    # Wait for ready
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 250
        try {
            $client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $port)
            $client.Close()
            $ready = $true
            break
        } catch { }
    }

    if ($ready) {
        Write-Host "[+] Backend Server đã sẵn sàng tại http://127.0.0.1:8765 !" -ForegroundColor Green
    } else {
        Write-Host "[-] Cảnh báo: Server chưa kịp phản hồi, tiếp tục mở giao diện..." -ForegroundColor Yellow
    }
} else {
    Write-Host "[+] Backend Server đã chạy sẵn sàng tại port $port." -ForegroundColor Green
}

# 2. Open Desktop Shell
if (-not $NoBrowser) {
    $edgePaths = @(
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    )
    $edge = $null
    foreach ($p in $edgePaths) {
        if (Test-Path $p) { $edge = $p; break }
    }

    $targetUrl = "http://127.0.0.1:8765"

    if ($edge) {
        Write-Host "[+] Mở Desktop Native App Window..." -ForegroundColor Cyan
        Start-Process $edge -ArgumentList "--app=`"$targetUrl`" --window-size=1320,840 --app-id=com.cautreo.studio"
    } else {
        Write-Host "[+] Mở trình duyệt mặc định..." -ForegroundColor Cyan
        Start-Process $targetUrl
    }
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Cautreo Studio V1.0 đang hoạt động!" -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:8765" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
