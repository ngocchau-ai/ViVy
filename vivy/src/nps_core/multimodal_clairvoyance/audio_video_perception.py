"""Audio & Video Payload Receipts for ViVy Clairvoyance Engine.

[REPLACED 29/09/2026 · WP-5 / O-12 / F-F03] — honest interfaces
=================================================================

WHAT THIS MODULE USED TO CLAIM
    The header said it *"Processes audio waveforms/spectrogram matrices and
    video frame temporal sequences directly without external standalone
    converters."*  In practice, for **any** path — existing or not — it:

    * hashed the **path string** and presented it as a content hash
    * invented ``sample_rate=16000``, ``channels=1``, ``duration_sec=5.0``
    * built a "spectrogram" from ``sin(f)*cos(t)`` of loop indices
    * invented ``frame_count=24``, ``fps=30.0``, ``width=1920``, ``height=1080``
    * emitted frame labels ``FRAME-000-<hash>`` and called them a video sequence

    No sample was ever read.  No frame was ever decoded.  This is the
    audio/video twin of ``vision.py``'s F-F01.

WHAT IT ACTUALLY DOES NOW
    * **Real file:** hashes the **bytes**.  Duration, sample rate, channels,
      fps and pixel dimensions are reported as ``None`` — unknown, because
      this module still does not decode media.
    * **Missing file:** raises ``FileNotFoundError`` unless the caller opts in
      with ``allow_simulated=True``, in which case the payload is flagged
      ``simulated=True``.
    * The "spectrogram matrix" is still generated from formulas, and is now
      flagged ``spectrogram_is_synthetic=True`` so nothing can present it as
      measured signal.  Frame labels are still labels, and ``frames_read`` is
      ``False`` always.

The old behaviour is **[ISOLATED]** at the call sites rather than deleted.
See ``docs/CAPABILITY_LEDGER.md``.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "AudioPayload",
    "VideoPayload",
    "AudioVideoEncoder",
]


@dataclass(frozen=True, slots=True)
class AudioPayload:
    """A **receipt about an audio file**, not a decoded waveform.

    Measurement fields are ``None`` when unknown.  This module never measures
    them; it only records that a file was named.
    """

    audio_id: str
    source_path: str | None
    duration_sec: float | None
    """Measured duration, or ``None``.  Was hardcoded ``5.0`` (invented)."""
    sample_rate: int | None
    """Measured sample rate, or ``None``.  Was hardcoded ``16000`` (invented)."""
    channels: int | None
    """Measured channel count, or ``None``.  Was hardcoded ``1`` (invented)."""
    content_hash: str
    """sha256 of the file **bytes**, or of the path string when ``simulated``."""
    spectrogram_matrix: tuple[tuple[float, ...], ...]
    #: [ADDED 29/09/2026] The matrix is generated from formulas, not from audio.
    spectrogram_is_synthetic: bool = True
    simulated: bool = False
    samples_read: bool = False
    """Always False.  This module never reads a sample."""

    @property
    def is_content_hash(self) -> bool:
        return not self.simulated

    def to_dict(self) -> dict[str, Any]:
        matrix = self.spectrogram_matrix
        return {
            "audio_id": self.audio_id,
            "source_path": self.source_path,
            "duration_sec": self.duration_sec,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "content_hash": self.content_hash,
            "matrix_shape": f"{len(matrix)}x{len(matrix[0]) if matrix else 0}",
            "spectrogram_is_synthetic": self.spectrogram_is_synthetic,
            "simulated": self.simulated,
            "samples_read": self.samples_read,
        }


@dataclass(frozen=True, slots=True)
class VideoPayload:
    """A **receipt about a video file**, not a decoded frame sequence.

    ``frame_count``, ``fps``, ``width`` and ``height`` are ``None`` unless a
    caller supplies measured values.  This module never measures them.
    """

    video_id: str
    source_path: str | None
    frame_count: int | None
    """Measured frame count, or ``None``.  Was hardcoded ``24`` (invented)."""
    fps: float | None
    """Measured frames-per-second, or ``None``.  Was hardcoded ``30.0``."""
    width: int | None
    """Measured width, or ``None``.  Was hardcoded ``1920`` (invented)."""
    height: int | None
    """Measured height, or ``None``.  Was hardcoded ``1080`` (invented)."""
    content_hash: str
    """sha256 of the file **bytes**, or of the path string when ``simulated``."""
    temporal_frames: tuple[str, ...]
    """Frame *labels*.  Never frame data.  See ``frames_read``."""
    simulated: bool = False
    frames_read: bool = False
    """Always False.  This module never decodes a frame."""

    @property
    def is_content_hash(self) -> bool:
        return not self.simulated

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "source_path": self.source_path,
            "frame_count": self.frame_count,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "content_hash": self.content_hash,
            "frame_label_count": len(self.temporal_frames),
            "frames_read": self.frames_read,
            "simulated": self.simulated,
        }


def _synthetic_spectrogram(num_freq_bins: int = 16, num_time_steps: int = 32):
    """Generate a formula-driven matrix.  SIMULATED — never signal-derived.

    [ISOLATED 29/09/2026 · WP-5] kept because "cô lập, không xóa"; the point of
    this helper is that its output depends on ``(f, t)`` alone, so two
    different audio files produce identical matrices.
    """
    spectrogram = []
    for f in range(num_freq_bins):
        row = []
        for t in range(num_time_steps):
            freq_val = math.sin((f + 1) * 0.5) * math.cos((t + 1) * 0.3)
            row.append(round(abs(freq_val), 4))
        spectrogram.append(tuple(row))
    return tuple(spectrogram)


class AudioVideoEncoder:
    """Builds audio/video **payload receipts**.  Decodes nothing.

    Despite the historical name this class does not encode waveforms or frame
    sequences.  See the module docstring (F-F03).
    """

    @staticmethod
    def encode_audio_file(
        audio_path: str | Path,
        duration_sec: float | None = None,
        *,
        allow_simulated: bool = False,
    ) -> AudioPayload:
        """Create an :class:`AudioPayload` receipt from a path.

        Parameters
        ----------
        audio_path:
            Path to an audio file.
        duration_sec:
            A **caller-supplied** duration.  It is recorded as given and
            attributed to the caller — this module does not measure it.  Pass
            ``None`` (the default) to record "unknown".
        allow_simulated:
            Opt-in to the fabricating branch when the path does not exist.

        Raises
        ------
        FileNotFoundError
            If the path does not exist and ``allow_simulated`` is False.
        """
        path = Path(audio_path)
        if not path.exists():
            if not allow_simulated:
                raise FileNotFoundError(
                    f"AudioVideoEncoder.encode_audio_file: {path} does not exist. "
                    f"Pass allow_simulated=True for a SIMULATED payload."
                )
            content_hash = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
            simulated = True
        else:
            data = path.read_bytes()
            content_hash = hashlib.sha256(data).hexdigest()[:16]
            simulated = False

        audio_id = f"AUD-VIVY-{content_hash[:8]}"
        # [ISOLATED] sample_rate=16000 and channels=1 used to be hardcoded here
        # and presented as measured.  They are now None = unknown.

        return AudioPayload(
            audio_id=audio_id,
            source_path=str(path),
            duration_sec=duration_sec,
            sample_rate=None,
            channels=None,
            content_hash=content_hash,
            spectrogram_matrix=_synthetic_spectrogram(),
            spectrogram_is_synthetic=True,
            simulated=simulated,
            samples_read=False,
        )

    @staticmethod
    def encode_video_file(
        video_path: str | Path,
        frame_count: int | None = None,
        fps: float | None = None,
        *,
        allow_simulated: bool = False,
    ) -> VideoPayload:
        """Create a :class:`VideoPayload` receipt from a path.

        ``frame_count`` and ``fps`` are **caller-supplied** and recorded as
        given; this module does not measure them.  Width and height are always
        ``None`` — they used to be invented as 1920x1080.

        Raises
        ------
        FileNotFoundError
            If the path does not exist and ``allow_simulated`` is False.
        """
        path = Path(video_path)
        if not path.exists():
            if not allow_simulated:
                raise FileNotFoundError(
                    f"AudioVideoEncoder.encode_video_file: {path} does not exist. "
                    f"Pass allow_simulated=True for a SIMULATED payload."
                )
            content_hash = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
            simulated = True
        else:
            data = path.read_bytes()
            content_hash = hashlib.sha256(data).hexdigest()[:16]
            simulated = False

        video_id = f"VID-VIVY-{content_hash[:8]}"

        # [ISOLATED] frames are labels, not data.  Kept as labels; the field
        # is now documented as such and ``frames_read`` stays False.
        n = frame_count if frame_count is not None else 0
        frames = tuple(f"FRAME-{t:03d}-{content_hash[:6]}" for t in range(n))

        return VideoPayload(
            video_id=video_id,
            source_path=str(path),
            frame_count=frame_count,
            fps=fps,
            width=None,
            height=None,
            content_hash=content_hash,
            temporal_frames=frames,
            simulated=simulated,
            frames_read=False,
        )
