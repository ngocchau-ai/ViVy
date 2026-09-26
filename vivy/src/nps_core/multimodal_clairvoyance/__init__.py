"""ViVy Multimodal Clairvoyance Core Package.

Provides native direct perception for 2D/3D images, 4D temporal video frames,
and audio spectrogram matrices without external standalone converters.
"""

from nps_core.multimodal_clairvoyance.audio_video_perception import (
    AudioPayload,
    AudioVideoEncoder,
    VideoPayload,
)
from nps_core.multimodal_clairvoyance.clairvoyance_engine import (
    ClairvoyanceEngine,
    ClairvoyanceResponse,
    ClairvoyanceState,
    SVDMultimodalDecomposer,
)

__all__ = [
    "AudioPayload",
    "VideoPayload",
    "AudioVideoEncoder",
    "ClairvoyanceState",
    "SVDMultimodalDecomposer",
    "ClairvoyanceEngine",
    "ClairvoyanceResponse",
]
