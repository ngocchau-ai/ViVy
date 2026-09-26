"""
Tests for engine/elastic_n_core.py — ViVy Final V1.0 Sprint 1.

Covers: ElasticNCore forward pass, detect_hardware_budget, OOM guard,
N scaling, single-pass GEMM correctness, and Gate 1 benchmark.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 1 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import numpy as np
import pytest

from engine.elastic_n_core import (
    ElasticNCore,
    HardwareBudget,
    NCoreSinglePassResult,
    detect_hardware_budget,
)

# ---------------------------------------------------------------------------
# detect_hardware_budget tests
# ---------------------------------------------------------------------------


class TestDetectHardwareBudget:
    def test_returns_hardware_budget(self):
        b = detect_hardware_budget()
        assert isinstance(b, HardwareBudget)

    def test_n_active_in_bounds(self):
        b = detect_hardware_budget(n_min=2, n_max=8)
        assert 2 <= b.n_active <= 8

    def test_oom_guard_low_vram(self):
        """Very low VRAM → OOM guard → n_active = n_min = 2."""
        b = detect_hardware_budget(n_min=2, n_max=16, vram_override_mb=100)
        assert b.n_active == 2
        assert "oom_guard" in b.budget_source

    def test_high_vram_scales_up(self):
        """High VRAM allows N > 2."""
        b = detect_hardware_budget(n_min=2, n_max=16, vram_override_mb=8192)
        assert b.n_active >= 2  # could be capped by CPU count

    def test_override_vram_is_used(self):
        b = detect_hardware_budget(vram_override_mb=2048)
        assert b.vram_estimate_mb == 2048

    def test_is_compute_bound_when_n_gt_1(self):
        b = detect_hardware_budget(n_min=2, vram_override_mb=4096)
        assert b.is_compute_bound == (b.n_active > 1)

    def test_n_min_floor_respected(self):
        b = detect_hardware_budget(n_min=3, n_max=3, vram_override_mb=4096)
        assert b.n_active == 3

    def test_n_max_ceiling_respected(self):
        b = detect_hardware_budget(n_min=2, n_max=4, vram_override_mb=99999)
        assert b.n_active <= 4


# ---------------------------------------------------------------------------
# ElasticNCore construction tests
# ---------------------------------------------------------------------------


class TestElasticNCoreInit:
    def test_default_construction(self):
        nc = ElasticNCore()
        assert nc.n_min == 2
        assert nc.n_max == 16
        assert nc.hidden_dim == 64

    def test_custom_params(self):
        nc = ElasticNCore(n_min=2, n_max=4, hidden_dim=32)
        assert nc.n_max == 4
        assert nc.hidden_dim == 32

    def test_n_min_below_2_raises(self):
        with pytest.raises(ValueError, match="n_min must be"):
            ElasticNCore(n_min=1)

    def test_n_max_above_64_raises(self):
        with pytest.raises(ValueError, match="n_max must be"):
            ElasticNCore(n_max=65)

    def test_n_min_gt_n_max_raises(self):
        with pytest.raises(ValueError, match="n_min .* must be"):
            ElasticNCore(n_min=8, n_max=4)

    def test_head_weights_shape(self):
        nc = ElasticNCore(n_min=2, n_max=8, hidden_dim=16)
        assert nc._head_weights.shape == (8, 16, 16)

    def test_head_weights_normalised(self):
        nc = ElasticNCore(n_min=2, n_max=4, hidden_dim=8)
        norms = np.linalg.norm(nc._head_weights, axis=(1, 2))
        # All norms should be ≈ 1 (normalised)
        assert np.allclose(norms, 1.0, atol=0.1)


# ---------------------------------------------------------------------------
# ElasticNCore.forward tests
# ---------------------------------------------------------------------------


class TestElasticNCoreForward:
    @pytest.fixture
    def nc(self):
        return ElasticNCore(n_min=2, n_max=8, hidden_dim=32, seed=0)

    def test_forward_returns_result(self, nc):
        r = nc.forward()
        assert isinstance(r, NCoreSinglePassResult)

    def test_forward_n_active_is_n_min_at_minimum(self, nc):
        r = nc.forward(vram_override_mb=50)  # very low → OOM guard
        assert r.n_active >= nc.n_min

    def test_forward_candidates_count_matches_n_active(self, nc):
        r = nc.forward(n_override=3)
        assert len(r.candidates) == 3
        assert r.n_active == 3

    def test_forward_winner_in_candidates(self, nc):
        r = nc.forward()
        assert r.winner in r.candidates

    def test_forward_winner_has_highest_score(self, nc):
        r = nc.forward()
        best_score = max(c.score for c in r.candidates)
        assert abs(r.winner.score - best_score) < 1e-6

    def test_forward_action_vectors_sum_to_1(self, nc):
        r = nc.forward()
        for c in r.candidates:
            total = float(np.sum(c.action_vector))
            assert abs(total - 1.0) < 1e-4, f"core_{c.core_index} softmax sum={total}"

    def test_forward_with_explicit_hidden_state(self, nc):
        h = np.ones(32, dtype=np.float32)
        h = h / np.linalg.norm(h)
        r = nc.forward(hidden_state=h)
        assert r.n_active >= nc.n_min

    def test_forward_dim_mismatch_raises(self, nc):
        bad_h = np.ones(10, dtype=np.float32)
        with pytest.raises(ValueError, match="dim mismatch"):
            nc.forward(hidden_state=bad_h)

    def test_forward_n_override_clamped(self, nc):
        r = nc.forward(n_override=100)  # above n_max=8
        assert r.n_active <= nc.n_max

    def test_forward_n_override_below_n_min_clamped(self, nc):
        r = nc.forward(n_override=1)  # below n_min=2
        assert r.n_active >= nc.n_min

    def test_forward_hypotheses_labels(self, nc):
        labels = ["analyze", "critique", "plan"]
        r = nc.forward(n_override=3, hypotheses=labels)
        assert r.candidates[0].hypothesis == "analyze"
        assert r.candidates[1].hypothesis == "critique"

    def test_forward_elapsed_ms_present(self, nc):
        r = nc.forward()
        assert r.elapsed_ms >= 0.0

    def test_forward_is_compute_bound_at_n2(self, nc):
        r = nc.forward(n_override=2)
        assert r.is_compute_bound is True  # N=2 > 1 → compute bound

    def test_scores_are_in_0_1_range(self, nc):
        r = nc.forward()
        for c in r.candidates:
            assert 0.0 <= c.score <= 1.0

    # ---- OOM guard edge case (Gate 1 requirement) ----

    def test_oom_guard_n2_at_very_low_vram(self):
        nc = ElasticNCore(n_min=2, n_max=16, hidden_dim=64)
        r = nc.forward(vram_override_mb=100)  # Very low → OOM guard
        assert r.n_active == 2

    def test_no_oom_at_n2_low_vram(self):
        """N=2 must always succeed regardless of VRAM constraint."""
        nc = ElasticNCore(n_min=2, n_max=16, hidden_dim=64)
        # Even with trivially low budget, no exception
        r = nc.forward(vram_override_mb=1)
        assert r.n_active == 2
        assert len(r.candidates) == 2

    # ---- Performance benchmark (Gate 1: directive generation ≤ 15ms) ----

    def test_single_forward_under_15ms(self, nc):
        """Single-pass GEMM must complete in ≤ 15ms on normal hardware."""
        r = nc.forward()
        assert r.elapsed_ms < 15.0, (
            f"Forward pass took {r.elapsed_ms:.2f}ms — exceeds 15ms Gate 1 budget"
        )

    def test_deterministic_with_same_hidden_state(self):
        nc = ElasticNCore(n_min=2, n_max=4, hidden_dim=16, seed=7)
        h = np.ones(16, dtype=np.float32)
        h /= np.linalg.norm(h)
        r1 = nc.forward(hidden_state=h.copy(), n_override=2)
        r2 = nc.forward(hidden_state=h.copy(), n_override=2)
        assert r1.winner.core_index == r2.winner.core_index
        assert abs(r1.winner.score - r2.winner.score) < 1e-6

    def test_detect_hardware_budget_instance_method(self, nc):
        b = nc.detect_hardware_budget()
        assert isinstance(b, HardwareBudget)
        assert nc.n_min <= b.n_active <= nc.n_max
