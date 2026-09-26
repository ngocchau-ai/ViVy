import urllib.request
import json
import time

payload = {
    "model": "gemma4-e4b",
    "messages": [
        {"role": "system", "content": "You are ViVy, the Executive Cognitive OS. Format output with <vivy_thought> containing Epistemic_Decision and Expected_Evidence. Then provide a concise directive."},
        {"role": "user", "content": "Phat directive cho task tiep theo ve cau truc he thong."}
    ],
    "max_tokens": 512,
    "temperature": 0.2
}

print("=== Sending Standard Direct OpenAI-Compatible API Request ===")
t0 = time.time()
req = urllib.request.Request(
    "http://127.0.0.1:8080/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0
        print(f"Elapsed: {elapsed:.2f}s")
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content")
        print(f"Content Length: {len(content)}")
        print(f"Reasoning Content: {reasoning}")
        print("\n--- CONTENT PREVIEW ---")
        print(content[:500])
        if len(content) > 0:
            print("\n>>> TEST PASS: content is fully populated for standard OpenAI clients! <<<")
        else:
            print("\n>>> TEST FAIL: content is empty! <<<")
except Exception as e:
    print("Error:", e)
