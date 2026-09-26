#!/usr/bin/env python3
r"""
download_qwen2_vl_72b.py — Resumable Downloader for Qwen2-VL-72B-Instruct GGUF.

Tải model Qwen2-VL-72B-Instruct Q4_K_M (44.16GB) và mmproj-f16 (1.30GB)
vào D:\models\qwen2-vl-72b\ với cơ chế:
- HTTP Range Header Resumable (tự động tiếp tục khi rớt mạng).
- Chunk Streaming (2MB buffers, flush tức thì).
- Periodic Logging (Tốc độ MB/s, % hoàn tất, ETA).
- Safe Retry Loop.
"""

import sys
import time
import urllib.request
from pathlib import Path

# Force unbuffered output so logs appear instantly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

DEST_DIR = Path(r"D:\models\qwen2-vl-72b")
BASE_URL = "https://huggingface.co/bartowski/Qwen2-VL-72B-Instruct-GGUF/resolve/main"

FILES = [
    {
        "filename": "mmproj-Qwen2-VL-72B-Instruct-f16.gguf",
        "expected_bytes": 1399840256,
        "description": "Multimodal Vision Projector (f16)"
    },
    {
        "filename": "Qwen2-VL-72B-Instruct-Q4_K_M.gguf",
        "expected_bytes": 47415714048,
        "description": "Core 72B Language & Cognitive Weights (Q4_K_M)"
    }
]

CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks for responsive streaming

def download_file_resumable(filename: str, expected_bytes: int, desc: str) -> bool:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    target_path = DEST_DIR / filename
    url = f"{BASE_URL}/{filename}"

    print("\n" + "=" * 65, flush=True)
    print(f"[*] Target: {filename} [{desc}]", flush=True)
    print(f"    Target Path: {target_path}", flush=True)
    print(f"    Expected Size: {expected_bytes / (1024**3):.2f} GB ({expected_bytes:,} bytes)", flush=True)
    print("=" * 65, flush=True)

    max_retries = 25
    retry_count = 0

    while retry_count < max_retries:
        current_size = target_path.stat().st_size if target_path.exists() else 0

        if current_size >= expected_bytes:
            print(f"  [ALREADY COMPLETE] File {filename} matches expected size: {current_size:,} bytes.", flush=True)
            return True

        headers = {"User-Agent": "Mozilla/5.0"}
        mode = "wb"
        if current_size > 0:
            headers["Range"] = f"bytes={current_size}-"
            mode = "ab"
            print(f"  [RESUME] Tiếp tục tải từ byte {current_size:,} ({current_size / (1024**3):.2f} GB)...", flush=True)

        req = urllib.request.Request(url, headers=headers)

        try:
            start_time = time.time()
            bytes_since_start = 0
            last_log_time = start_time

            with urllib.request.urlopen(req, timeout=60) as resp, open(target_path, mode) as f:
                status_code = resp.getcode()
                if mode == "ab" and status_code not in (206, 200):
                    print(f"  [WARN] Server không trả về 206 Partial (Status {status_code}). Bắt đầu lại từ đầu.", flush=True)
                    mode = "wb"
                    current_size = 0

                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    f.write(chunk)
                    f.flush()

                    chunk_len = len(chunk)
                    current_size += chunk_len
                    bytes_since_start += chunk_len

                    now = time.time()
                    if now - last_log_time >= 3.0 or current_size >= expected_bytes:
                        elapsed = now - start_time
                        speed_mb = (bytes_since_start / (1024 * 1024)) / max(elapsed, 0.001)
                        pct = (current_size / expected_bytes) * 100
                        remaining_bytes = max(0, expected_bytes - current_size)
                        eta_s = remaining_bytes / max(speed_mb * 1024 * 1024, 1)

                        print(f"  -> {pct:5.2f}% | {current_size / (1024**3):.2f}/{expected_bytes / (1024**3):.2f} GB | "
                              f"Speed: {speed_mb:5.1f} MB/s | ETA: {eta_s/60:.1f} min", flush=True)
                        last_log_time = now

            if current_size >= expected_bytes:
                print(f"  [SUCCESS] Hoàn tất tải {filename}! Tổng dung lượng: {current_size:,} bytes.", flush=True)
                return True

        except Exception as e:
            retry_count += 1
            print(f"  [RETRY {retry_count}/{max_retries}] Lỗi kết nối: {e}. Đang tạm dừng 3s rồi tải tiếp...", flush=True)
            time.sleep(3)

    print(f"  [FAILED] Không thể hoàn thành tải {filename} sau {max_retries} lần thử.", flush=True)
    return False

def main():
    print("=" * 65, flush=True)
    print("  QWEN2-VL-72B-INSTRUCT GGUF RESUMABLE DOWNLOADER", flush=True)
    print(f"  Destination: {DEST_DIR}", flush=True)
    print("=" * 65, flush=True)

    for item in FILES:
        ok = download_file_resumable(item["filename"], item["expected_bytes"], item["description"])
        if not ok:
            print(f"\n[ERROR] Tải thất bại tại file: {item['filename']}", flush=True)
            sys.exit(1)

    print("\n" + "=" * 65, flush=True)
    print("  [ALL COMPLETED] Toàn bộ model Qwen2-VL-72B-Instruct đã sẵn sàng!", flush=True)
    print("=" * 65, flush=True)

if __name__ == "__main__":
    main()
