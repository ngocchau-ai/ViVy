"""Backend cho các handle năng lực.

Host sở hữu ba backend và **chỉ ba**: hệ file workspace, vài phép nội bộ, và một
máy khách HTTP tới endpoint model đã cấu hình.

`cautreo` thì host không có — host không biết Cautreo là gì (spec D3). Backend đó
do plugin runtime tự cắm vào qua `CallContext(_backends=...)`.

Về `model`: host không tự sinh câu trả lời nào. `ModelBackend` chỉ **chuyển tiếp**
prompt tới endpoint mà người dùng đã cấu hình (`--model-endpoint`) và trả về đúng
phản hồi của server. Không có endpoint, không có model backend; có endpoint nhưng
server chết thì lời gọi ném lỗi — bus biến thành `plugin_error`, **không có
`result` nào được sinh ra**. Tên model lấy từ phản hồi của server, không tự khai.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Kênh model dùng để viết lập luận trước khi ra câu trả lời. Đây là giao thức của
# template, không phải nội dung — nhưng nội dung BÊN TRONG vẫn là chữ của model
# và phải giữ lại cho người dùng xem khi họ muốn.
THINKING_CHANNELS = frozenset({"thought", "thinking", "reason", "reasoning", "analysis"})

# `<|channel>thought` mở kênh · `<channel|>` (hay `<|channel|>`) đóng kênh.
# Hai token này là giao thức nên bị loại khỏi phần hiển thị, nhưng `raw` giữ
# nguyên vẹn từng ký tự của đầu vào.
_CHANNEL_TOKEN = re.compile(r"<\|channel>([A-Za-z][A-Za-z0-9_-]*)|<\|?channel\|>")


def _resolve_channel_word(word: str) -> tuple[str, str]:
    """Tách tên kênh khỏi chữ của model khi hai thứ dính liền nhau.

    `<|channel>thoughtThinking Process` không có dấu cách ngăn giữa tên kênh
    (`thought`) và chữ bắt đầu (`Thinking`). Regex tham ăn sẽ bắt cả cụm
    `thoughtThinking` làm tên kênh và **ăn mất chữ của model**. Ở đây ta bóc
    phần dư trả lại — bất biến "không mất chữ" quan trọng hơn gọn gàng.

    Trả về `(tên kênh, chữ dư)`.
    """
    low = word.lower()
    if low in THINKING_CHANNELS:
        return low, ""
    for name in sorted(THINKING_CHANNELS, key=len, reverse=True):
        if low.startswith(name):
            return name, word[len(name) :]
    return low, ""


def split_model_channels(raw: Any) -> dict[str, Any]:
    """Tách lời model nói thành **câu trả lời** và **luồng tư duy**.

    Bất biến trung thực, kiểm bằng test:

    * `raw` trả về **nguyên vẹn** đúng chuỗi đầu vào — không mất chữ nào.
    * Không nhận diện được cấu trúc kênh thì **toàn bộ** nằm ở `answer`. Không
      bao giờ đẩy nội dung sang `thinking` rồi để đó cho người dùng không thấy.
    * `thinking` là danh sách từng đoạn, để giao diện bày **lần lượt** và mỗi
      khối tự thu gọn.

    Đây là **tách cấu trúc**, không phải viết lại lời model. Không có câu nào
    được tóm tắt, diễn giải hay thay thế.
    """
    if not isinstance(raw, str):
        return {"answer": "", "thinking": [], "raw": ""}

    segments: list[tuple[str | None, str]] = []
    channel: str | None = None
    buf = ""
    pos = 0
    for m in _CHANNEL_TOKEN.finditer(raw):
        buf += raw[pos : m.start()]
        if buf:
            segments.append((channel, buf))
        name = m.group(1)
        if name is None:
            # token đóng kênh — phần sau thuộc kênh mặc định
            channel, buf = None, ""
        else:
            # chữ dính liền tên kênh (`thoughtThinking`) được bóc trả lại `buf`
            channel, buf = _resolve_channel_word(name)
        pos = m.end()
    buf += raw[pos:]
    if buf:
        segments.append((channel, buf))

    def _is_thinking(name: str | None) -> bool:
        return name is not None and name in THINKING_CHANNELS

    thinking = [t.strip() for name, t in segments if _is_thinking(name) and t.strip()]
    answer = [t.strip() for name, t in segments if not _is_thinking(name) and t.strip()]
    return {
        "answer": "\n\n".join(answer),
        "thinking": thinking,
        "raw": raw,
    }


class FileSystemBackend:
    """Đọc/ghi trong workspace. Không có đường nào ra ngoài thư mục gốc."""

    name = "fs"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError(f"đường dẫn {path!r} nằm ngoài workspace") from exc
        return target

    def read(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8")

    def write(self, path: str, text: str) -> int:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return len(text)

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def list(self, path: str = "") -> list[str]:
        p = self._resolve(path or ".")
        if not p.is_dir():
            raise NotADirectoryError(path)
        return sorted(str(c.relative_to(self.root)) for c in p.iterdir())


class LocalBackend:
    """Vài phép nội bộ không cần model. Nhãn kết quả luôn là `tool-local`."""

    name = "local"

    def now(self) -> float:
        return time.time()

    def echo(self, text: Any) -> Any:
        return text

    def stat(self, path: str) -> dict[str, Any]:
        p = Path(path)
        return {"exists": p.exists(), "is_file": p.is_file(), "size": p.stat().st_size if p.is_file() else None}


class ModelBackend:
    """Máy khách HTTP tới một endpoint model tương thích OpenAI.

    Mỗi lời gọi là một chuyến đi thật. Backend này **không** có câu trả lời dự
    phòng, không có chuỗi "xin lỗi", không tự đặt tên model — mọi thứ trong kết
    quả đều lấy từ thân phản hồi của server, và mọi lỗi đều ném lên trên.
    """

    name = "model"

    def __init__(
        self,
        endpoint: str,
        *,
        model: str | None = None,
        timeout: float = 120.0,
        max_tokens: int = 512,
        system: str | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        # Chỉ dùng làm tham số `model` của request. Tên model **trong kết quả**
        # vẫn lấy từ phản hồi server.
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        # Bản đồ thân thể mà host nạp vào. Đây là **cửa duy nhất** model biết mình
        # là ai và đang có cơ quan nào — xem `bodymap.render_body_prompt()`.
        # Để None thì lời gọi đi ra vẫn là đúng một tin nhắn `user` như cũ.
        self.system = system

    def set_system(self, text: str | None) -> None:
        """Cập nhật system prompt. Host gọi sau mỗi lần registry đổi."""
        self.system = text if isinstance(text, str) and text.strip() else None

    # ---- nội bộ ----

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = self.endpoint + path
        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"model endpoint trả HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"không gọi được model endpoint {self.endpoint}: {exc}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"model endpoint trả về không phải JSON: {raw[:200]}") from exc

    # ---- API mà plugin chạm qua ctx.model ----

    def models(self) -> list[str]:
        """Danh sách model server đang phục vụ. Lấy từ server, không đoán."""
        data = self._request("/v1/models")
        out: list[str] = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            name = item.get("name") or item.get("id") if isinstance(item, dict) else None
            if isinstance(name, str) and name:
                out.append(name)
        return out

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Hỏi model một câu. Trả về đúng lời model nói, kèm siêu dữ liệu server.

        Dùng `/v1/chat/completions` vì server này áp chat template ở đó —
        `/v1/completions` sinh chữ lặp vô nghĩa (đã đo trên endpoint thật).
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt phải là chuỗi khác rỗng")
        messages: list[dict[str, str]] = []
        if self.system:
            # System prompt mang bản đồ thân thể (bodymap). Nó đi **trước** lời
            # người dùng — nhờ vậy model biết mình là ai trước khi trả lời.
            messages.append({"role": "system", "content": self.system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if self.model:
            payload["model"] = self.model
        if temperature is not None:
            payload["temperature"] = temperature

        data = self._request("/v1/chat/completions", payload)
        if not isinstance(data, dict):
            raise RuntimeError(f"model endpoint trả cấu trúc lạ: {type(data).__name__}")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("model endpoint không trả về choices nào")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str):
            raise RuntimeError("model endpoint không trả về nội dung lời nhắn")

        parts = split_model_channels(text)
        return {
            # `text` là NGUYÊN VĂN — không cắt, không sửa. `answer`/`thinking`
            # chỉ là cách xếp lại cho người đọc, và `split_model_channels` luôn
            # trả lại chính chuỗi này trong khoá `raw`.
            "text": text,
            "answer": parts["answer"],
            "thinking": parts["thinking"],
            # Tên model lấy từ phản hồi server — host không tự khai.
            "model": data.get("model"),
            "finish_reason": choices[0].get("finish_reason"),
            "usage": data.get("usage"),
        }

    def health(self) -> bool:
        try:
            data = self._request("/health")
        except Exception:  # noqa: BLE001 — health chỉ dò, không mang lỗi đi
            return False
        return bool(data) if not isinstance(data, dict) else data.get("status") == "ok"


def default_backends(
    workspace: str | Path, model_endpoint: str | None = None
) -> dict[str, Any]:
    """Backend host sở hữu.

    `model_endpoint` là đường dẫn host được cấu hình. **Không truyền** nghĩa là
    không có model nào — và khi đó `ctx.model.complete()` ném lỗi thật, không
    trả câu trả lời giả.
    """
    out: dict[str, Any] = {
        "fs": FileSystemBackend(workspace),
        "local": LocalBackend(),
    }
    if model_endpoint:
        out["model"] = ModelBackend(model_endpoint)
    return out
