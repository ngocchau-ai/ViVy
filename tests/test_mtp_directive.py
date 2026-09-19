"""
Tests for engine/mtp_directive.py — ViVy Final V1.0 Sprint 1.

Covers: DirectiveMTPHead forward pass, output format, HMAC signature
verification, opcode vocabulary, single-pass timing.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 1 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from engine.elastic_n_core import ElasticNCore
from engine.mtp_directive import (
    DirectiveExecutionTuple,
    DirectiveMTPHead,
    TargetComponent,
    _OPCODE_TABLE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mtp():
    return DirectiveMTPHead(hidden_dim=64, seed=0)


@pytest.fixture
def nc():
    return ElasticNCore(n_min=2, n_max=4, hidden_dim=64, seed=0)


@pytest.fixture
def action_vector():
    rng = np.random.default_rng(42)
    av = rng.standard_normal(64).astype(np.float32)
    av = av - av.max()
    av = np.exp(av)
    av = av / av.sum()
    return av


# ---------------------------------------------------------------------------
# DirectiveMTPHead construction
# ---------------------------------------------------------------------------


class TestDirectiveMTPHeadInit:
    def test_default_construction(self):
        head = DirectiveMTPHead()
        assert head.hidden_dim == 64

    def test_custom_hidden_dim(self):
        head = DirectiveMTPHead(hidden_dim=32)
        assert head.hidden_dim == 32

    def test_opcode_weight_shape(self):
        head = DirectiveMTPHead(hidden_dim=16)
        assert head._W_opcode.shape[1] == 16
        assert head._W_opcode.shape[0] == len(_OPCODE_TABLE)


# ---------------------------------------------------------------------------
# forward() output schema
# ---------------------------------------------------------------------------


class TestDirectiveMTPHeadForward:
    def test_returns_directive_execution_tuple(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.85)
        assert isinstance(d, DirectiveExecutionTuple)

    def test_target_id_is_valid_component(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.7)
        valid = {str(tc) for tc in TargetComponent}
        assert d.target_id in valid

    def test_opcode_is_non_empty_string(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.7)
        assert isinstance(d.opcode, str)
        assert len(d.opcode) > 0

    def test_payload_hash_is_sha256_hex(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.7)
        assert isinstance(d.payload_hash, str)
        assert len(d.payload_hash) == 64
        assert all(c in "0123456789abcdef" for c in d.payload_hash)

    def test_signature_is_sha256_hex(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.7)
        assert isinstance(d.signature, str)
        assert len(d.signature) == 64

    def test_confidence_preserved(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=1, confidence=0.923)
        assert abs(d.confidence - 0.923) < 1e-4

    def test_core_index_preserved(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=3, confidence=0.5)
        assert d.core_index == 3

    def test_payload_json_has_required_keys(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.8)
        for key in ("opcode", "target", "core_index", "confidence", "context"):
            assert key in d.payload_json, f"Missing key: {key}"

    def test_generation_ms_positive(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.8)
        assert d.generation_ms >= 0.0

    def test_context_hint_in_payload(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.8, context_hint="build vivy")
        assert "build vivy" in d.payload_json["context"]

    def test_context_hint_truncated_at_256(self, mtp, action_vector):
        long_ctx = "x" * 500
        d = mtp.forward(action_vector, core_index=0, confidence=0.5, context_hint=long_ctx)
        assert len(d.payload_json["context"]) <= 256

    def test_dim_mismatch_raises(self, mtp):
        bad_av = np.ones(10, dtype=np.float32)
        with pytest.raises(ValueError, match="dim mismatch"):
            mtp.forward(bad_av, core_index=0, confidence=0.5)

    def test_frozen_dataclass(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.9)
        with pytest.raises((AttributeError, TypeError)):
            d.opcode = "HACK"  # type: ignore

    def test_deterministic_output_same_input(self, action_vector):
        mtp = DirectiveMTPHead(hidden_dim=64, seed=7)
        d1 = mtp.forward(action_vector, core_index=0, confidence=0.5)
        d2 = mtp.forward(action_vector, core_index=0, confidence=0.5)
        assert d1.opcode == d2.opcode
        assert d1.payload_hash == d2.payload_hash
        assert d1.signature == d2.signature


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    def test_verify_valid_directive(self, mtp, action_vector):
        d = mtp.forward(action_vector, core_index=0, confidence=0.8)
        assert mtp.verify(d) is True

    def test_verify_tampered_opcode_fails(self, mtp, action_vector):
        import dataclasses
        d = mtp.forward(action_vector, core_index=0, confidence=0.8)
        tampered = dataclasses.replace(d, opcode="HACK_OPCODE")
        assert mtp.verify(tampered) is False

    def test_verify_tampered_target_fails(self, mtp, action_vector):
        import dataclasses
        d = mtp.forward(action_vector, core_index=0, confidence=0.8)
        tampered = dataclasses.replace(d, target_id="FAKE_TARGET")
        assert mtp.verify(tampered) is False

    def test_verify_tampered_payload_hash_fails(self, mtp, action_vector):
        import dataclasses
        d = mtp.forward(action_vector, core_index=0, confidence=0.8)
        tampered = dataclasses.replace(d, payload_hash="a" * 64)
        assert mtp.verify(tampered) is False


# ---------------------------------------------------------------------------
# Integration: ElasticNCore → DirectiveMTPHead pipeline
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    def test_ncore_to_mtp_pipeline(self, nc, mtp):
        """Full Sprint 1 pipeline: hidden_state → N-Core → MTP → DirectiveTuple."""
        h = np.ones(64, dtype=np.float32)
        h /= np.linalg.norm(h)

        core_result = nc.forward(hidden_state=h, n_override=2)
        winner = core_result.winner

        directive = mtp.forward(
            winner.action_vector,
            core_index=winner.core_index,
            confidence=winner.score,
            context_hint="test pipeline",
        )

        assert isinstance(directive, DirectiveExecutionTuple)
        assert mtp.verify(directive)
        assert directive.confidence == winner.score

    def test_pipeline_latency_under_15ms(self, nc, mtp):
        """Combined N-Core + MTP forward pass must be ≤ 15ms (Gate 1)."""
        t0 = time.perf_counter()

        core_result = nc.forward(n_override=2)
        directive = mtp.forward(
            core_result.winner.action_vector,
            core_index=core_result.winner.core_index,
            confidence=core_result.winner.score,
        )

        total_ms = (time.perf_counter() - t0) * 1000
        assert total_ms < 15.0, f"Pipeline took {total_ms:.2f}ms — exceeds 15ms Gate 1 budget"

    def test_different_hidden_states_may_produce_different_opcodes(self):
        """Different inputs and NC seeds should produce opcode diversity."""
        opcodes = set()
        rng = np.random.default_rng(0)
        # Use multiple NC seeds to ensure opcode diversity across the vocabulary
        for seed in range(5):
            nc_i = ElasticNCore(n_min=2, n_max=4, hidden_dim=64, seed=seed)
            mtp_i = DirectiveMTPHead(hidden_dim=64, seed=seed)
            for _ in range(8):
                h = rng.standard_normal(64).astype(np.float32)
                h /= np.linalg.norm(h)
                cr = nc_i.forward(hidden_state=h, n_override=2)
                d = mtp_i.forward(cr.winner.action_vector, core_index=0, confidence=cr.winner.score)
                opcodes.add(d.opcode)
        # At least 3 distinct opcodes from 40 runs with 5 different seeds
        assert len(opcodes) >= 3, f"Only {len(opcodes)} unique opcode(s) generated: {opcodes}"

    def test_opcode_is_from_vocabulary(self, nc, mtp):
        valid_opcodes = {op for _, op in _OPCODE_TABLE}
        cr = nc.forward()
        d = mtp.forward(cr.winner.action_vector, core_index=0, confidence=cr.winner.score)
        assert d.opcode in valid_opcodes
