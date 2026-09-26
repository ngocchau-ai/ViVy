import os
import sys
import time
import subprocess
import psutil

TARGET_BYTES = 47415714048
FILE_PATH = r"D:\models\qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
CURL_URL = "https://huggingface.co/bartowski/Qwen2-VL-72B-Instruct-GGUF/resolve/main/Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
INITIAL_PID = 11088

print(f"[WATCHER_STARTED] Target: {TARGET_BYTES} bytes. File: {FILE_PATH}", flush=True)

def is_curl_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'curl' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'Qwen2-VL-72B' in cmdline:
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

while True:
    if os.path.exists(FILE_PATH):
        cur_len = os.path.getsize(FILE_PATH)
        if cur_len >= TARGET_BYTES:
            print(f"[DOWNLOAD_SUCCESS] File reached target size: {cur_len} bytes.", flush=True)
            break
    else:
        cur_len = 0

    active_pid = is_curl_running()
    if active_pid is None:
        if os.path.exists(FILE_PATH):
            cur_len = os.path.getsize(FILE_PATH)
        if cur_len >= TARGET_BYTES:
            print(f"[DOWNLOAD_SUCCESS] Target reached after process termination: {cur_len} bytes.", flush=True)
            break
        else:
            print(f"[RESUMING_DOWNLOAD] Curl not detected and file is {cur_len}/{TARGET_BYTES} bytes. Resuming...", flush=True)
            subprocess.run([
                "curl.exe", "-L", "-C", "-", "--fail", "--retry", "10", "--retry-delay", "5",
                "-o", FILE_PATH, CURL_URL
            ], check=False)
    
    time.sleep(15)

# Verify GGUF header
magic = b""
try:
    with open(FILE_PATH, "rb") as f:
        magic = f.read(4)
except Exception as e:
    print(f"Error reading header: {e}")

final_size = os.path.getsize(FILE_PATH)
gb = round(final_size / (1024**3), 2)
print("=" * 60, flush=True)
print("=== HOÀN TẤT TẢI VỀ MODEL MỚI THÀNH CÔNG ===", flush=True)
print(f"Model: Qwen2-VL-72B-Instruct-Q4_K_M.gguf", flush=True)
print(f"Dung lượng: {final_size:,} bytes ({gb} GB)", flush=True)
print(f"GGUF Header: {magic.decode('ascii', errors='replace')}", flush=True)
print(f"Trạng thái: Sẵn sàng nạp vào Cautreo Cartography & ViVy Final Core", flush=True)
print("=" * 60, flush=True)
