"""Ollama API Client for ViVy AI Model.   [ISOLATED — not a real proxy]

[ISOLATED 29/09/2026 · WP-5 / O-12 / F-F04] — no model is ever called
======================================================================

The header claimed this *"Provides Ollama protocol payload formatting and API
communication methods."*  It formats payloads, yes.  It performs **no
communication**.  There is no ``urllib``/``socket``/``http`` call anywhere in
this file.  ``process_local_reasoning`` builds an **Ollama-shaped dict** from
``ViVyMultimodalEngine.process`` — which is a bilingual template (see
``vivy_interface/reasoning_engine.py``) — and returns it with the fields an
Ollama client expects (``model``, ``created_at``, ``message``, ``done``).

A caller reading that dict would conclude a model answered.  It did not.

STATUS (29/09/2026)
    * **`[ISOLATED]`** — kept for the research branch (D-2).  **Not a real
      Ollama proxy.**  To become one, it must actually speak HTTP to an
      Ollama server and record the model-id it got back.
    * Responses now carry ``model_call_made: False`` and
      ``simulated_response: True`` so no consumer can mistake this for model
      output.

Standard-library only.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from nps_core.vivy_interface import (
    MultimodalResponse,
    VisionEncoder,
    ViVyMultimodalEngine,
)

__all__ = [
    "OllamaViVyClient",
]


class OllamaViVyClient:
    """**ISOLATED** Ollama-shaped payload formatter.  Makes no HTTP calls.

    ``endpoint`` is stored and never contacted.  See the module docstring.
    """

    def __init__(self, endpoint: str = "http://localhost:11434", model_name: str = "vivy:latest") -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name

    def format_chat_payload(
        self,
        prompt: str,
        image_path: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Format request body according to Ollama /api/chat protocol."""
        msg: dict[str, Any] = {"role": "user", "content": prompt}
        if image_path and Path(image_path).exists():
            data = Path(image_path).read_bytes()
            b64_str = base64.b64encode(data).decode("utf-8")
            msg["images"] = [b64_str]

        return {
            "model": self.model_name,
            "messages": [msg],
            "stream": stream,
        }

    def process_local_reasoning(
        self,
        prompt: str,
        image_path: str | None = None,
        *,
        allow_simulated: bool = False,
    ) -> dict[str, Any]:
        """Build an Ollama-shaped dict from the **local template**.  No model call.

        [UPDATED 29/09/2026 · WP-5] the returned dict is explicitly marked
        ``model_call_made: False`` / ``simulated_response: True``.  A missing
        ``image_path`` raises unless ``allow_simulated=True``.
        """
        image_payload = (
            VisionEncoder.from_file(image_path, allow_simulated=allow_simulated)
            if image_path
            else None
        )
        res: MultimodalResponse = ViVyMultimodalEngine.process(prompt, image=image_payload)

        return {
            "model": self.model_name,
            "created_at": "2026-07-25T10:48:00Z",
            "message": {
                "role": "assistant",
                "content": res.response_text,
            },
            "done": True,
            "thought_chain": list(res.thought_chain),
            "detected_language": res.detected_language,
            "visual_summary": res.visual_summary,
            # [ADDED 29/09/2026 · WP-5] honesty flags — see module docstring.
            "model_call_made": False,
            "simulated_response": True,
            "note": (
                "[ISOLATED] Ollama-shaped template output. No model was called; "
                "self.endpoint was never contacted."
            ),
        }
