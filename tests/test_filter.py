"""Unit tests for funnel/filter.py — FilterFunnel."""

import numpy as np
import pytest

from funnel._types import CONTROL_SIGNALS, make_stream
from funnel.filter import FilterFunnel


def _stream(sv: float, amp: float) -> dict:
    return make_stream(
        singular_value=sv,
        amplitude_ratio=amp,
        state_A=np.array([1.0, 0.0], dtype=np.complex128),
        state_B=np.array([0.0, 1.0], dtype=np.complex128),
    )


class TestFilterFunnelInit:
    def test_default_thresholds(self):
        f = FilterFunnel()
        assert f.accept_threshold == 0.6
        assert f.warn_threshold == 0.35
        assert f.reject_threshold == 0.15

    def test_custom_thresholds(self):
        f = FilterFunnel(accept_threshold=0.8, warn_threshold=0.5, reject_threshold=0.2)
        assert f.accept_threshold == 0.8
        assert f.warn_threshold == 0.5
        assert f.reject_threshold == 0.2

    def test_invalid_threshold_order_raises(self):
        with pytest.raises(ValueError):
            FilterFunnel(accept_threshold=0.3, warn_threshold=0.5, reject_threshold=0.6)

    def test_conflict_penalty_default(self):
        f = FilterFunnel()
        assert f.conflict_penalty == 0.2


class TestFilterFunnelEvaluate:
    def test_empty_streams_returns_backtrack(self):
        f = FilterFunnel()
        kept, signal, conf = f.evaluate([])
        assert kept == []
        assert signal == "backtrack"
        assert conf == 0.0

    def test_strong_single_stream_continue(self):
        f = FilterFunnel(accept_threshold=0.3, warn_threshold=0.15, reject_threshold=0.05)
        streams = [_stream(sv=0.9, amp=1.0)]
        kept, signal, conf = f.evaluate(streams)
        assert len(kept) >= 1
        assert signal == "continue"
        assert conf > 0.0

    def test_weak_stream_backtrack(self):
        f = FilterFunnel(accept_threshold=0.8, warn_threshold=0.6, reject_threshold=0.4)
        streams = [_stream(sv=0.1, amp=0.05)]
        kept, signal, conf = f.evaluate(streams)
        assert signal == "backtrack"
        assert conf == 0.0

    def test_borderline_measure(self):
        f = FilterFunnel(accept_threshold=0.8, warn_threshold=0.3, reject_threshold=0.1)
        streams = [_stream(sv=0.5, amp=0.5)]
        kept, signal, conf = f.evaluate(streams)
        assert signal == "measure"
        assert conf > 0.0

    def test_multiple_streams_mixed(self):
        f = FilterFunnel(accept_threshold=0.4, warn_threshold=0.2, reject_threshold=0.05)
        streams = [
            _stream(sv=0.9, amp=0.8),  # strong
            _stream(sv=0.5, amp=0.4),  # moderate
        ]
        kept, signal, conf = f.evaluate(streams)
        # At least one accepted => continue.
        assert signal == "continue"
        assert len(kept) >= 1
        assert conf > 0.0

    def test_all_rejected(self):
        f = FilterFunnel(accept_threshold=0.9, warn_threshold=0.8, reject_threshold=0.7)
        streams = [_stream(sv=0.1, amp=0.05), _stream(sv=0.2, amp=0.1)]
        kept, signal, conf = f.evaluate(streams)
        assert signal == "backtrack"
        assert len(kept) == 0

    def test_delegate_signal(self):
        """Many warned streams with no accepted => delegate (fragmented thought)."""
        f = FilterFunnel(accept_threshold=0.9, warn_threshold=0.3, reject_threshold=0.1)
        streams = [_stream(sv=1.0, amp=1.0) for _ in range(4)]
        kept, signal, conf = f.evaluate(streams)
        assert signal == "delegate"
        assert len(kept) == 4

    def test_confidence_in_range(self):
        f = FilterFunnel()
        streams = [_stream(sv=0.8, amp=0.7), _stream(sv=0.6, amp=0.5)]
        _, _, conf = f.evaluate(streams)
        assert 0.0 <= conf <= 1.0

    def test_control_signal_is_valid(self):
        f = FilterFunnel()
        for sv in [0.9, 0.5, 0.2, 0.05]:
            streams = [_stream(sv=sv, amp=sv)]
            _, signal, _ = f.evaluate(streams)
            assert signal in CONTROL_SIGNALS, f"Invalid signal {signal} for sv={sv}"


class TestFilterFunnelScoring:
    def test_status_accepted(self):
        f = FilterFunnel(accept_threshold=0.5, warn_threshold=0.3, reject_threshold=0.1)
        assert f._status(0.6) == "accepted"
        assert f._status(0.5) == "accepted"

    def test_status_warned(self):
        f = FilterFunnel(accept_threshold=0.5, warn_threshold=0.3, reject_threshold=0.1)
        assert f._status(0.4) == "warned"
        assert f._status(0.3) == "warned"

    def test_status_rejected(self):
        f = FilterFunnel(accept_threshold=0.5, warn_threshold=0.3, reject_threshold=0.1)
        assert f._status(0.2) == "rejected"
        assert f._status(0.05) == "rejected"

    def test_consistency_perfect(self):
        assert FilterFunnel._consistency(0.8, 0.8) == 1.0

    def test_consistency_zero_sigma(self):
        assert FilterFunnel._consistency(0.0, 0.5) == 0.0

    def test_brevity_single(self):
        assert FilterFunnel._brevity(1) == 1.0

    def test_brevity_many(self):
        b2 = FilterFunnel._brevity(2)
        b5 = FilterFunnel._brevity(5)
        assert b2 > b5

    def test_brevity_zero(self):
        assert FilterFunnel._brevity(0) == 0.0

    def test_conflict_penalty(self):
        f = FilterFunnel(conflict_penalty=0.3)
        assert f._apply_conflict_penalty(0.8, False) == 0.8
        assert abs(f._apply_conflict_penalty(0.8, True) - 0.5) < 1e-12
        assert f._apply_conflict_penalty(0.1, True) == 0.0


class TestFilterFunnelEdgeCases:
    def test_single_stream_exact_threshold(self):
        f = FilterFunnel(accept_threshold=0.5, warn_threshold=0.3, reject_threshold=0.1)
        # A stream with confidence exactly at accept_threshold.
        streams = [_stream(sv=1.0, amp=1.0)]
        kept, signal, _ = f.evaluate(streams)
        assert signal == "continue"
        assert len(kept) == 1

    def test_many_streams_low_brevity(self):
        f = FilterFunnel(accept_threshold=0.3, warn_threshold=0.15, reject_threshold=0.05)
        streams = [_stream(sv=0.5, amp=0.5) for _ in range(20)]
        _, signal, conf = f.evaluate(streams)
        # Many streams => brevity penalty lowers confidence.
        assert conf < 0.5

    def test_stream_without_optional_keys(self):
        """Streams without interpretation should still work."""
        f = FilterFunnel()
        stream = {
            "singular_value": 0.8,
            "amplitude_ratio": 0.7,
            "state_A": np.array([1.0, 0.0], dtype=np.complex128),
            "state_B": np.array([0.0, 1.0], dtype=np.complex128),
        }
        kept, signal, conf = f.evaluate([stream])
        assert signal in CONTROL_SIGNALS
        assert conf > 0.0
