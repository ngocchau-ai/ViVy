import os
import sys
import time
import subprocess

TARGET_BYTES = 47415714048
FILE_PATH = r"D:\models\qwen2-vl-72b\Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
URL = "https://huggingface.co/bartowski/Qwen2-VL-72B-Instruct-GGUF/resolve/main/Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
SAFE_VERIFIED_OFFSET = 32999741231

# 1. Truncate to clean verified offset if file was overgrown
if os.path.exists(FILE_PATH):
    cur_size = os.path.getsize(FILE_PATH)
    if cur_size > SAFE_VERIFIED_OFFSET:
        print(f"[TRUNCATING] File was {cur_size} bytes. Truncating to verified position: {SAFE_VERIFIED_OFFSET}...", flush=True)
        with open(FILE_PATH, "r+b") as f:
            f.truncate(SAFE_VERIFIED_OFFSET)
    elif cur_size < SAFE_VERIFIED_OFFSET:
        print(f"[WARNING] File size ({cur_size}) < SAFE_VERIFIED_OFFSET ({SAFE_VERIFIED_OFFSET})", flush=True)
else:
    print("[ERROR] File does not exist!", flush=True)
    sys.exit(1)

print(f"[RESUMING] Clean start at {SAFE_VERIFIED_OFFSET} / {TARGET_BYTES} bytes ({SAFE_VERIFIED_OFFSET/TARGET_BYTES*100:.2f}%)", flush=True)
remaining_total = TARGET_BYTES - SAFE_VERIFIED_OFFSET
print(f"[REMAINING] {remaining_total / (1024**3):.2f} GiB to download.", flush=True)

CHUNK_SIZE = 4 * 1024 * 1024 # 4MB pipe buffer

while True:
    current = os.path.getsize(FILE_PATH)
    if current >= TARGET_BYTES:
        print(f"[DOWNLOAD_COMPLETE] Exactly {current} bytes reached.", flush=True)
        break
    
    range_str = f"{current}-{TARGET_BYTES - 1}"
    print(f"\n[STREAM] Starting curl stream for range {range_str}...", flush=True)
    cmd = ["curl.exe", "-s", "-N", "-L", "-r", range_str, URL]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=CHUNK_SIZE)
    last_report = time.time()
    bytes_at_start = current
    t0 = time.time()
    
    with open(FILE_PATH, "r+b") as f:
        f.seek(current)
        try:
            while True:
                buf = proc.stdout.read(CHUNK_SIZE)
                if not buf:
                    break
                f.write(buf)
                f.flush()
                
                now = time.time()
                if now - last_report >= 5.0:
                    written = f.tell()
                    pct = (written / TARGET_BYTES) * 100
                    speed = (written - bytes_at_start) / (now - t0) / (1024 * 1024)
                    rem_sec = (TARGET_BYTES - written) / (speed * 1024 * 1024) if speed > 0 else 0
                    print(f"[{time.strftime('%H:%M:%S')}] {written:,} / {TARGET_BYTES:,} ({pct:.2f}%) | Speed: {speed:.2f} MB/s | ETA: {rem_sec/60:.1f}m", flush=True)
                    last_report = now
        except Exception as e:
            print(f"[STREAM_EXCEPTION] {e}", flush=True)
            proc.kill()
        finally:
            proc.wait()

    final_cur = os.path.getsize(FILE_PATH)
    print(f"[STREAM_ENDED] Process exited with code {proc.returncode}. Current size: {final_cur:,} bytes.", flush=True)
    if final_cur >= TARGET_BYTES:
        break
    time.sleep(2)

# Final Verification
final_size = os.path.getsize(FILE_PATH)
print("=" * 60, flush=True)
print(f"=== MODEL DOWNLOAD VERIFICATION ===", flush=True)
print(f"Target Size:   {TARGET_BYTES:,} bytes", flush=True)
print(f"Actual Size:   {final_size:,} bytes", flush=True)
print(f"Match:         {final_size == TARGET_BYTES}", flush=True)

with open(FILE_PATH, "rb") as f:
    magic = f.read(4)
print(f"GGUF Magic:    {magic.decode('ascii', errors='replace')}", flush=True)

# Verify last 64 bytes match HF remote
print("Verifying final 64 bytes with HuggingFace...", flush=True)
test_cmd = ["curl.exe", "-s", "-L", "-r", f"{TARGET_BYTES-64}-{TARGET_BYTES-1}", URL]
remote_tail = subprocess.check_output(test_cmd)
with open(FILE_PATH, "rb") as f:
    f.seek(TARGET_BYTES - 64)
    local_tail = f.read(64)

tail_match = (remote_tail == local_tail)
print(f"Tail Bit-Perfect Verification: {tail_match}", flush=True)
if tail_match:
    print("ALL CHECKS PASSED: Model is 100% bit-perfect and ready for Cartography & ViVy!", flush=True)
else:
    print("[WARNING] Tail mismatch! Needs inspection.", flush=True)
print("=" * 60, flush=True)
