"""Integration tests for ViVy Native Multimodal Clairvoyance Pipeline."""

from __future__ import annotations

from pathlib import Path
import pytest

from nps_core.multimodal_clairvoyance import ClairvoyanceEngine


def test_clairvoyance_pipeline_integration():
    repo_root = Path(__file__).resolve().parents[2]
    image_path = repo_root / "docs" / "tower.png"
    video_path = repo_root / "docs" / "tower.mp4"
    audio_path = repo_root / "docs" / "ambient.wav"

    res = ClairvoyanceEngine.process_multimodal_clairvoyance(
        prompt="Integration pipeline thấu thị trực tiếp",
        image_path=image_path,
        video_path=video_path,
        audio_path=audio_path,
    )

    assert res.control_signal in ("CONTINUE_EVOLUTION", "MEASURE_AND_HALT")
    assert res.entropy_shannon >= 0.0
    assert len(res.singular_values) == 4
