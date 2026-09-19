"""Ollama Protocol HTTP Bridge Server for ViVy.

Provides a lightweight standard-library HTTP server implementing Ollama API endpoints:
- /api/tags (Lists installed models: vivy:latest)
- /api/show (Model details & Modelfile)
- /api/chat (Interactive chat endpoint)
- /api/generate (Generation endpoint)
- /api/version (Ollama version emulation)

Allows any Ollama client (Open-WebUI, Ollama CLI, LangChain, etc.) to talk to ViVy.
Standard-library only.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from nps_core.vivy_interface import MultimodalResponse, ViVyMultimodalEngine, VisionEncoder
from nps_core.vivy_ollama.exporter import OllamaModelExporter

__all__ = [
    "OllamaViVyBridgeHandler",
    "OllamaViVyBridgeServer",
]


class OllamaViVyBridgeHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler implementing Ollama API Protocol."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default verbose logging to stderr."""

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/api/tags", "/api/tags/"):
            self._send_json({
                "models": [
                    {
                        "name": "vivy:latest",
                        "model": "vivy:latest",
                        "modified_at": "2026-07-25T10:48:00Z",
                        "size": 2147483648,
                        "digest": "sha256:vivy1b00000000000000000000000000000000000000000000000000000000",
                        "details": {
                            "parent_model": "llama3.2:3b",
                            "format": "gguf",
                            "family": "llama",
                            "parameter_size": "1.15B",
                            "quantization_level": "Q4_K_M"
                        }
                    }
                ]
            })
        elif self.path in ("/api/version", "/api/version/"):
            self._send_json({"version": "0.3.14-vivy"})
        else:
            self._send_json({"status": "ViVy Ollama Protocol Bridge Online"}, status=200)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(raw_body)
        except json.JSONDecodeError:
            req_data = {}

        if self.path in ("/api/show", "/api/show/"):
            modelfile_str = OllamaModelExporter.generate_modelfile_content()
            self._send_json({
                "modelfile": modelfile_str,
                "parameters": "temperature 0.2\nstop \"<|im_end|>\"",
                "template": "{{ .System }}\n{{ .Prompt }}",
                "details": {"family": "llama", "parameter_size": "1.15B"}
            })
        elif self.path in ("/api/chat", "/api/chat/", "/api/generate", "/api/generate/"):
            prompt = ""
            if "messages" in req_data and isinstance(req_data["messages"], list) and len(req_data["messages"]) > 0:
                prompt = req_data["messages"][-1].get("content", "")
            else:
                prompt = req_data.get("prompt", "")

            res: MultimodalResponse = ViVyMultimodalEngine.process(prompt)

            self._send_json({
                "model": req_data.get("model", "vivy:latest"),
                "created_at": "2026-07-25T10:48:00Z",
                "message": {
                    "role": "assistant",
                    "content": res.response_text
                },
                "response": res.response_text,
                "done": True,
                "thought_chain": list(res.thought_chain),
                "detected_language": res.detected_language
            })
        else:
            self._send_json({"error": "endpoint not found"}, status=404)


class OllamaViVyBridgeServer:
    """Server manager for running Ollama ViVy protocol HTTP bridge."""

    def __init__(self, host: str = "127.0.0.1", port: int = 11434) -> None:
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None

    def start_in_background(self) -> None:
        """Initialize HTTP server instance."""
        self.server = HTTPServer((self.host, self.port), OllamaViVyBridgeHandler)

    def close(self) -> None:
        """Close server instance."""
        if self.server:
            self.server.server_close()
            self.server = None
