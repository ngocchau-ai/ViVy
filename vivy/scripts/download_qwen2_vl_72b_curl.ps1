# Resumable Downloader for Qwen2-VL-72B-Instruct GGUF using curl.exe
$targetDir = "D:\models\qwen2-vl-72b"
if (!(Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$baseUrl = "https://huggingface.co/bartowski/Qwen2-VL-72B-Instruct-GGUF/resolve/main"

$files = @(
    @{
        Name = "mmproj-Qwen2-VL-72B-Instruct-f16.gguf"
        Size = 1399840256
        Desc = "Multimodal Vision Projector (1.30 GB)"
    },
    @{
        Name = "Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
        Size = 47415714048
        Desc = "Core 72B Language & Cognitive Weights (44.16 GB)"
    }
)

Write-Host "============================================================"
Write-Host "  QWEN2-VL-72B-INSTRUCT CURL RESUMABLE DOWNLOADER"
Write-Host "  Destination: $targetDir"
Write-Host "============================================================"

foreach ($file in $files) {
    $outPath = Join-Path $targetDir $file.Name
    $url = "$baseUrl/$($file.Name)"
    $expected = $file.Size

    Write-Host "`n[*] Target: $($file.Name) [$($file.Desc)]"
    Write-Host "    Expected Bytes: $expected"

    $maxRetries = 30
    $retry = 0

    while ($retry -lt $maxRetries) {
        $curSize = 0
        if (Test-Path $outPath) {
            $curSize = (Get-Item $outPath).Length
        }

        if ($curSize -ge $expected) {
            Write-Host "  [COMPLETE] File matches expected size: $curSize bytes."
            break
        }

        Write-Host "  [START/RESUME] Current size: $([math]::round($curSize/1MB, 2)) MB / $([math]::round($expected/1MB, 2)) MB"
        
        # Execute curl with Resume (-C -), Follow redirects (-L), and retry
        & "C:\WINDOWS\system32\curl.exe" -L -C - --fail --retry 5 --retry-delay 3 -o $outPath $url

        if ($LASTEXITCODE -eq 0) {
            $finalSize = (Get-Item $outPath).Length
            if ($finalSize -ge $expected) {
                Write-Host "  [SUCCESS] Finished downloading $($file.Name)!"
                break
            }
        }

        $retry++
        Write-Host "  [RETRY $retry/$maxRetries] Curl exited with code $LASTEXITCODE. Retrying in 5 seconds..."
        Start-Sleep -Seconds 5
    }
}

Write-Host "`n============================================================"
Write-Host "  ALL MODEL FILES PROCESSED!"
Write-Host "============================================================"
