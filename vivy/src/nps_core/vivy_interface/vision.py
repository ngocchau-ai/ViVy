"""ViVy Vision Encoder — Multimodal Visual Processing Module.

Handles image input payload validation, metadata extraction, and visual feature tokenization.
Standard-library only.

[REPLACED 29/09/2026 · WP-5 / O-12 / F-F01] — honest interfaces
=================================================================

WHAT THIS MODULE USED TO CLAIM
    ``VisionEncoder.from_file`` returned a fully populated ``ImagePayload`` —
    ``width=1024, height=1024`` — for **any** path, including paths that do not
    exist.  For a missing path the ``content_hash`` was ``sha256(str(path))``:
    a hash of the *filename*, presented as if it were a hash of the *image*.
    ``encode_visual_summary`` then printed that fabricated resolution into the
    prompt as ``Resolution=1024x1024``.

    Nothing in this module ever decoded a pixel.  The review called it F-F01.

WHAT IT ACTUALLY DOES NOW
    * **Real file:** hashes the **bytes**, reports ``width``/``height`` as
      ``None`` — because we still do not decode the image.  ``None`` means
      *unknown*, not zero and not 1024.
    * **Missing file:** raises ``FileNotFoundError``.  The old fabricating
      path is kept, but only behind an explicit ``allow_simulated=True``, and
      the payload it returns is flagged ``simulated=True`` so every downstream
      summary has to admit it.
    * ``mime_type`` is still **inferred from the file extension**, not sniffed.
      Marked in ``ImagePayload.mime_source``.

The fabricating branch is **[ISOLATED]**, not deleted — see the callout in
``from_file``.  See ``docs/CAPABILITY_LEDGER.md`` for what this module is
allowed to claim.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ImagePayload",
    "VisionEncoder",
]


@dataclass(frozen=True, slots=True)
class ImagePayload:
    """Frozen value object capturing image **metadata** for ViVy.

    This is a *receipt about a file*, not a decoded image.  ``width`` and
    ``height`` are ``None`` unless a caller supplies measured dimensions —
    this module never measures them.
    """

    image_id: str
    source_path: str | None
    mime_type: str
    width: int | None
    """Measured pixel width, or ``None`` when not decoded.  Never invented."""
    height: int | None
    """Measured pixel height, or ``None`` when not decoded.  Never invented."""
    content_hash: str
    """sha256 of the file **bytes**, or of the path string when ``simulated``."""
    simulated: bool = False
    """True when the pixels were never read (opt-in fabricating branch)."""
    mime_source: str = "extension"
    """``"extension"`` (inferred) — never ``"sniffed"``.  See module docstring."""

    @property
    def resolution_known(self) -> bool:
        return self.width is not None and self.height is not None

    @property
    def is_content_hash(self) -> bool:
        """True when ``content_hash`` hashes bytes rather than the path string."""
        return not self.simulated

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "source_path": self.source_path,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "content_hash": self.content_hash,
            "simulated": self.simulated,
            "mime_source": self.mime_source,
            "resolution_known": self.resolution_known,
        }


class VisionEncoder:
    """Builds image **payload receipts** for ViVy Multimodal Reasoning.

    Despite the historical name this class does **not** encode visual tokens.
    See the module docstring (F-F01).
    """

    @staticmethod
    def from_file(
        image_path: str | Path,
        *,
        allow_simulated: bool = False,
    ) -> ImagePayload:
        """Create an :class:`ImagePayload` from a file path.

        Parameters
        ----------
        image_path:
            Path to an image file.
        allow_simulated:
            Opt-in to the **[ISOLATED]** fabricating branch used when the path
            does not exist.  Default ``False``: a missing file raises, because
            a payload that pretends to describe an image nobody has is worse
            than an error.

        Raises
        ------
        FileNotFoundError
            If the path does not exist and ``allow_simulated`` is False.
        """
        path = Path(image_path)
        if not path.exists():
            # [ISOLATED 29/09/2026 · WP-5 / F-F01] this branch used to be the
            # *only* behaviour for a missing path, and it was silent.  It is
            # kept because "cô lập, không xóa", but it is now opt-in and the
            # payload it returns is flagged so no summary can dress it up as
            # real perception.
            if not allow_simulated:
                raise FileNotFoundError(
                    f"VisionEncoder.from_file: {path} does not exist. "
                    f"Pass allow_simulated=True if you deliberately want a "
                    f"SIMULATED payload (metadata only, no pixels were read)."
                )
            content_hash = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
            image_id = f"IMG-VIVY-{content_hash[:8]}"
            ext = path.suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return ImagePayload(
                image_id=image_id,
                source_path=str(path),
                mime_type=mime,
                # Unknown, and now allowed to be.  Was: 1024 x 1024, invented.
                width=None,
                height=None,
                content_hash=content_hash,
                simulated=True,
                mime_source="extension",
            )

        data = path.read_bytes()
        content_hash = hashlib.sha256(data).hexdigest()[:16]
        image_id = f"IMG-VIVY-{content_hash[:8]}"
        ext = path.suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"

        return ImagePayload(
            image_id=image_id,
            source_path=str(path),
            mime_type=mime,
            # Still not decoded — so still unknown.  Was: 1024 x 1024, invented.
            width=None,
            height=None,
            content_hash=content_hash,
            simulated=False,
            mime_source="extension",
        )

    @staticmethod
    def encode_visual_summary(image: ImagePayload) -> str:
        """Describe the payload for prompt context — honestly.

        The summary states what is known and, just as importantly, what is
        not.  It never prints a resolution that was not measured.
        """
        if image.resolution_known:
            resolution = f"{image.width}x{image.height}"
        else:
            resolution = "UNKNOWN (not decoded)"

        origin = "SIMULATED (no pixels read)" if image.simulated else "bytes-hashed"
        return (
            f"[Visual Payload: {image.image_id} | Path={image.source_path or 'memory'} | "
            f"Resolution={resolution} | Format={image.mime_type} "
            f"(mime inferred from extension) | Provenance={origin}]"
        )
