# Script giám sát và tự phục hồi tải model Qwen2-VL-72B-Instruct
$targetBytes = 47415714048
$filePath = "D:\models\qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
$curlUrl = "https://huggingface.co/bartowski/Qwen2-VL-72B-Instruct-GGUF/resolve/main/Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
$initialPid = 11088

Write-Output "[WATCHER_STARTED] Target: $targetBytes bytes. File: $filePath"

while ($true) {
    if (Test-Path $filePath) {
        $curLen = (Get-Item $filePath).Length
        if ($curLen -ge $targetBytes) {
            Write-Output "[DOWNLOAD_SUCCESS] File reached target size: $curLen bytes."
            break
        }
    }
    
    # Check if curl is alive
    $proc = Get-Process -Id $initialPid -ErrorAction SilentlyContinue
    if (-not $proc) {
        # Check by process name and command line if restarted or ended
        $otherCurl = Get-CimInstance Win32_Process -Filter "Name = 'curl.exe'" | Where-Object { $_.CommandLine -match "Qwen2-VL-72B" }
        if (-not $otherCurl) {
            $curLen = if (Test-Path $filePath) { (Get-Item $filePath).Length } else { 0 }
            if ($curLen -ge $targetBytes) {
                Write-Output "[DOWNLOAD_SUCCESS] File verified complete at $curLen bytes."
                break
            } else {
                Write-Output "[RESUMING_DOWNLOAD] Curl stopped early at $curLen bytes. Resuming via curl -C - ..."
                & "C:\WINDOWS\system32\curl.exe" -L -C - --fail --retry 10 --retry-delay 5 -o $filePath $curlUrl
                $initialPid = $PID # avoid re-checking old pid
            }
        } else {
            $initialPid = $otherCurl.ProcessId
        }
    }

    Start-Sleep -Seconds 15
}

# Verify GGUF Magic Header
$stream = [System.IO.File]::OpenRead($filePath)
$bytes = New-Object byte[] 4
$read = $stream.Read($bytes, 0, 4)
$stream.Close()
$magic = [System.Text.Encoding]::ASCII.GetString($bytes)

$finalLen = (Get-Item $filePath).Length
$gb = [math]::Round($finalLen / 1GB, 2)
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Output "=== HOÀN TẤT TẢI VỀ MODEL MỚI THÀNH CÔNG ==="
Write-Output "Model: Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
Write-Output "Dung lượng: $finalLen bytes ($gb GB)"
Write-Output "GGUF Magic: $magic"
Write-Output "Timestamp: $now"
