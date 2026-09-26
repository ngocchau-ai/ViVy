"""
Multimodal Adapter — ViVy Sprint 3.

Encode text, image, và audio thành format Gemma 4 E4B hiểu được.
Không dùng thư viện nặng — chỉ stdlib + Pillow (optional) + base64.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InputModality(Enum):
    TEXT = auto()
    IMAGE = auto()
    AUDIO = auto()
    VIDEO_FRAME = auto()   # single frame extracted from video


@dataclass
class MultimodalInput:
    """Structured input for ViVy inference.

    Attributes
    ----------
    text:
        Text component of the input.
    modality:
        Primary modality of this input.
    image_b64:
        Base64-encoded PNG/JPEG image (if modality is IMAGE or VIDEO_FRAME).
    audio_transcript:
        Transcribed text of audio input (if modality is AUDIO).
    audio_path:
        Path to raw audio file (if modality is AUDIO and whisper not available).
    source_metadata:
        Optional metadata (filename, timecode, etc.)
    """

    text: str
    modality: InputModality = InputModality.TEXT
    image_b64: str | None = None
    audio_transcript: str | None = None
    audio_path: str | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MultimodalAdapter
# ---------------------------------------------------------------------------


class MultimodalAdapter:
    """Encode various input types for Gemma 4 E4B.

    Gemma 4 E4B accepts:
      - text: plain string
      - image: base64 data URI (PNG/JPEG)
      - audio: native audio tokens (if model supports) OR whisper transcript fallback

    This adapter handles the encoding and returns MultimodalInput objects
    ready to be passed to LlamaCppBridge.chat().

    Parameters
    ----------
    max_image_dim:
        Resize images to this max dimension (width or height) before encoding.
        Default 1024px. Reduces token usage.
    whisper_model:
        Path to whisper.cpp executable or "whisper" if on PATH.
        If None, audio is passed as [AUDIO TRANSCRIPT NOT AVAILABLE] placeholder.
    """

    def __init__(
        self,
        max_image_dim: int = 1024,
        whisper_model: str | None = None,
    ) -> None:
        self._max_dim = max_image_dim
        self._whisper = whisper_model
        self._pillow_available = self._check_pillow()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def from_text(self, text: str) -> MultimodalInput:
        """Wrap plain text input."""
        return MultimodalInput(text=text, modality=InputModality.TEXT)

    def from_image_path(self, path: str, caption: str = "") -> MultimodalInput:
        """Encode an image file as base64 for Gemma 4 E4B.

        Parameters
        ----------
        path:
            Path to image file (PNG, JPEG, WebP, etc.)
        caption:
            Optional text prompt to accompany the image.
        """
        img_b64 = self._encode_image_path(path)
        text = caption or f"[Image: {Path(path).name}]"
        return MultimodalInput(
            text=text,
            modality=InputModality.IMAGE,
            image_b64=img_b64,
            source_metadata={"source_path": path},
        )

    def from_image_bytes(self, data: bytes, caption: str = "", fmt: str = "png") -> MultimodalInput:
        """Encode raw image bytes as base64."""
        img_b64 = self._encode_image_bytes(data, fmt)
        return MultimodalInput(
            text=caption or "[Image input]",
            modality=InputModality.IMAGE,
            image_b64=img_b64,
        )

    def from_video_frame(self, video_path: str, time_ms: float = 0.0) -> MultimodalInput:
        """Extract a single frame from a video at time_ms and encode it.

        Uses ffmpeg. If not available, returns TEXT fallback.

        Parameters
        ----------
        video_path:
            Path to video file.
        time_ms:
            Time offset in milliseconds to extract frame.
        """
        frame_bytes = self._extract_video_frame(video_path, time_ms)
        if frame_bytes is None:
            logger.warning("MultimodalAdapter: ffmpeg unavailable, returning text fallback")
            return MultimodalInput(
                text=f"[Video frame at {time_ms}ms — ffmpeg unavailable]",
                modality=InputModality.TEXT,
                source_metadata={"video_path": video_path, "time_ms": time_ms},
            )

        img_b64 = base64.b64encode(frame_bytes).decode("utf-8")
        return MultimodalInput(
            text=f"[Video frame at {time_ms:.0f}ms from {Path(video_path).name}]",
            modality=InputModality.VIDEO_FRAME,
            image_b64=img_b64,
            source_metadata={"video_path": video_path, "time_ms": time_ms},
        )

    def from_audio_path(self, path: str) -> MultimodalInput:
        """Transcribe audio to text via whisper.cpp, or return placeholder.

        Parameters
        ----------
        path:
            Path to audio file (.wav, .mp3, .ogg, etc.)
        """
        transcript = self._transcribe_audio(path)
        if transcript:
            text = f"[Audio transcript]: {transcript}"
            modality = InputModality.AUDIO
        else:
            text = f"[Audio file: {Path(path).name} — transcription unavailable]"
            modality = InputModality.TEXT

        return MultimodalInput(
            text=text,
            modality=modality,
            audio_transcript=transcript,
            audio_path=path,
            source_metadata={"source_path": path},
        )

    def build_prompt_text(self, inp: MultimodalInput) -> str:
        """Build the text portion of the prompt from a MultimodalInput.

        For images, the image itself is passed separately via image_b64.
        This method returns the text prompt component only.
        """
        if inp.modality == InputModality.AUDIO and inp.audio_transcript:
            return f"<audio_input>\n{inp.audio_transcript}\n</audio_input>\n\n{inp.text}"
        return inp.text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_pillow() -> bool:
        try:
            import PIL  # noqa: F401
            return True
        except ImportError:
            return False

    def _encode_image_path(self, path: str) -> str:
        """Read image from disk and return base64 string."""
        if self._pillow_available:
            return self._encode_image_pillow(path)
        # Fallback: read raw bytes without resize
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _encode_image_pillow(self, path: str) -> str:
        """Resize image to max_image_dim and encode as PNG base64."""
        from PIL import Image as PILImage

        img = PILImage.open(path).convert("RGB")

        # Resize if needed
        w, h = img.size
        if max(w, h) > self._max_dim:
            ratio = self._max_dim / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), PILImage.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _encode_image_bytes(self, data: bytes, fmt: str = "png") -> str:
        """Encode raw bytes to base64."""
        if self._pillow_available and fmt.lower() not in ("png",):
            from PIL import Image as PILImage
            img = PILImage.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()
        return base64.b64encode(data).decode("utf-8")

    def _extract_video_frame(self, video_path: str, time_ms: float) -> bytes | None:
        """Extract single video frame using ffmpeg. Returns PNG bytes or None."""
        try:
            time_s = time_ms / 1000.0
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(time_s),
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",
                    tmp_path,
                ],
                capture_output=True,
                check=True,
                timeout=15,
            )
            with open(tmp_path, "rb") as f:
                return f.read()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug("MultimodalAdapter._extract_video_frame: %s", e)
            return None
        finally:
            if "tmp_path" in dir() and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _transcribe_audio(self, audio_path: str) -> str | None:
        """Transcribe audio using whisper.cpp if available."""
        if not self._whisper:
            return None
        try:
            result = subprocess.run(
                [self._whisper, "-m", "models/ggml-base.en.bin", "-f", audio_path, "--output-txt", "-"],
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning("MultimodalAdapter._transcribe_audio: %s", e)
            return None
