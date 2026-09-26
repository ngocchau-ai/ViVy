"""Unit tests for ViVy Native Multimodal Clairvoyance Perception Core."""

from __future__ import annotations

import pytest

from nps_core.multimodal_clairvoyance import (
    AudioPayload,
    AudioVideoEncoder,
    ClairvoyanceEngine,
    ClairvoyanceState,
    SVDMultimodalDecomposer,
    VideoPayload,
)


def test_audio_video_encoders():
    audio = AudioVideoEncoder.encode_audio_file("sample.wav")
    assert isinstance(audio, AudioPayload)
    assert audio.sample_rate == 16000
    assert len(audio.spectrogram_matrix) == 16
    assert len(audio.spectrogram_matrix[0]) == 32

    video = AudioVideoEncoder.encode_video_file("sample.mp4")
    assert isinstance(video, VideoPayload)
    assert video.frame_count == 24
    assert len(video.temporal_frames) == 24


def test_clairvoyance_state_normalization():
    state = ClairvoyanceState(dim=4, amplitudes=[complex(1, 1), complex(2, -1), complex(0, 3), complex(-1, 0)])
    state.normalize()
    assert pytest.approx(state.norm, abs=1e-5) == 1.0


def test_svd_multimodal_decomposer():
    state = ClairvoyanceState(
        dim=4,
        amplitudes=[complex(1, 0)] * 4,
        spatial_features=[0.8, 0.6, 0.4, 0.2],
        spectral_features=[0.9, 0.7, 0.5, 0.3],
    )
    sigmas, score = SVDMultimodalDecomposer.decompose_multimodal_tensor(state)
    assert len(sigmas) == 4
    assert sigmas[0] >= sigmas[1]
    assert 0.0 <= score <= 1.0


def test_clairvoyance_engine_full_processing():
    res = ClairvoyanceEngine.process_multimodal_clairvoyance(
        prompt="Test direct perception",
        image_path="test_img.png",
        video_path="test_vid.mp4",
        audio_path="test_aud.wav",
    )
    assert res.text_prompt == "Test direct perception"
    assert res.image_payload is not None
    assert res.video_payload is not None
    assert res.audio_payload is not None
    assert res.state_norm == 1.0
    assert res.cross_modal_alignment_score > 0.0
    assert "VISION_2D_3D" in res.clairvoyance_perception_summary
    assert "AUDIO_SPECTROGRAM" in res.clairvoyance_perception_summary
