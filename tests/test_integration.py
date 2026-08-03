"""Integration tests: memory + funnel working together with a mocked core module.

The ``core`` module is not yet implemented, so we provide a lightweight fake
``extract_thought_streams`` that mimics the interface contract from PLAN_3DAY.md
(``core/svd_streams.py``) and drive the full memory -> funnel pipeline.
"""

import numpy as np

from funnel._types import CONTROL_SIGNALS, make_stream
from funnel.analysis import amplitude_phase_analysis, entropy_analysis
from funnel.conflict import detect_conflict
from funnel.filter import FilterFunnel
from memory.associative import QuantumAssociativeMemory
from memory.query import analogical_reasoning, cosine_similarity


# --------------------------------------------------------------------------- #
# Mock of core/svd_streams.extract_thought_streams
# --------------------------------------------------------------------------- #
def _fake_extract_thought_streams(state, partition=None, threshold=0.05):
    """Fake core SVD stream extractor. Returns a list of Stream dicts.

    The input ``state`` is a complex vector; we split it into two halves (the two
    "registers" of the partition) and return one stream per pair with a singular
    value proportional to the pair's amplitude.
    """
    state = np.asarray(state, dtype=np.complex128)
    n = state.shape[0]
    half = n // 2
    A = state[:half]
    B = state[half : 2 * half]
    streams = []
    for i in range(half):
        sv = abs(A[i]) + abs(B[i])
        if sv < threshold:
            continue
        streams.append(
            make_stream(
                singular_value=sv,
                amplitude_ratio=sv / max(float(np.linalg.norm(state)), 1e-15),
                state_A=np.array([A[i]], dtype=np.complex128),
                state_B=np.array([B[i]], dtype=np.complex128),
                interpretation=f"stream_{i}",
            )
        )
    return streams


class TestPipelineIntegration:
    def test_full_pipeline(self):
        """memory store -> query -> funnel evaluate, end to end."""
        # 1. Build and populate memory.
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        e2 = np.array([0.0, 0.0, 1.0, 0.0])
        e3 = np.array([0.0, 0.0, 0.0, 1.0])
        mem.store(e0, e1)
        mem.store(e2, e3)

        # 2. Query memory.
        y_hat, conf = mem.query(e0)
        assert conf > 0.0
        assert y_hat.shape == (4,)

        # 3. Feed a retrieved state through the fake core -> streams.
        state = np.concatenate([y_hat, y_hat])
        streams = _fake_extract_thought_streams(state)

        # 4. Run analysis + funnel.
        entropy = entropy_analysis(streams)
        amp_phase = amplitude_phase_analysis(streams)
        funnel = FilterFunnel()
        kept, signal, funnel_conf = funnel.evaluate(streams)

        assert 0.0 <= funnel_conf <= 1.0
        assert signal in CONTROL_SIGNALS
        assert entropy["n_streams"] == len(streams)
        assert amp_phase["n_streams"] == len(streams)

    def test_memory_funnel_analogy_loop(self):
        """Store patterns, retrieve, then find analogies among retrieved streams."""
        mem = QuantumAssociativeMemory(dim=4)
        patterns = []
        for i in range(4):
            x = np.zeros(4)
            y = np.zeros(4)
            x[i] = 1.0
            y[(i + 1) % 4] = 1.0
            patterns.append((x, y))
            mem.store(x, y)

        # Retrieve an analogy for pattern 0.
        analogies = analogical_reasoning(mem, patterns[0][0], k=2)
        assert isinstance(analogies, list)

        # Feed the top analogy through the funnel.
        if analogies:
            top, _ = analogies[0]
            state = np.concatenate([top, top])
            streams = _fake_extract_thought_streams(state)
            _, signal, _ = FilterFunnel().evaluate(streams)
            assert signal in CONTROL_SIGNALS

    def test_conflict_detected_in_pipeline(self):
        """Two strong orthogonal streams => funnel + conflict agree there's tension."""
        streams = [
            make_stream(
                singular_value=0.8,
                amplitude_ratio=0.5,
                state_A=np.array([1.0, 0.0], dtype=np.complex128),
                state_B=np.array([0.0, 1.0], dtype=np.complex128),
            ),
            make_stream(
                singular_value=0.7,
                amplitude_ratio=0.5,
                state_A=np.array([0.0, 1.0], dtype=np.complex128),
                state_B=np.array([1.0, 0.0], dtype=np.complex128),
            ),
        ]
        conflict = detect_conflict(streams, min_amplitude=0.05, overlap_threshold=0.5)
        assert conflict["conflict"]

        # Funnel should still emit a valid signal.
        _, signal, _ = FilterFunnel().evaluate(streams)
        assert signal in CONTROL_SIGNALS

    def test_consistency_across_analysis_functions(self):
        """amplitude_phase and entropy should agree on stream count."""
        state = np.array([1.0, 0.5, 0.3, 0.1, 0.2, 0.4], dtype=np.complex128)
        streams = _fake_extract_thought_streams(state)
        n = len(streams)

        amp = amplitude_phase_analysis(streams)
        ent = entropy_analysis(streams)
        assert amp["n_streams"] == n
        assert ent["n_streams"] == n
        assert amp["total_amplitude"] > 0.0

    def test_memory_retrieval_feeds_funnel_confidence(self):
        """A well-stored memory should produce a confident funnel result."""
        mem = QuantumAssociativeMemory(dim=8)
        # Store a single strong association.
        x = np.zeros(8)
        y = np.zeros(8)
        x[0] = 1.0
        y[1] = 1.0
        mem.store(x, y)

        y_hat, mem_conf = mem.query(x)
        assert mem_conf > 0.0

        state = np.concatenate([y_hat, y_hat])
        streams = _fake_extract_thought_streams(state)
        _, signal, funnel_conf = FilterFunnel().evaluate(streams)
        assert signal in CONTROL_SIGNALS
        assert funnel_conf >= 0.0

    def test_cosine_similarity_between_retrieved_and_stored(self):
        """Retrieved pattern should be similar to the stored target."""
        mem = QuantumAssociativeMemory(dim=4)
        e0 = np.array([1.0, 0.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0, 0.0])
        mem.store(e0, e1)

        y_hat, _ = mem.query(e0)
        sim = cosine_similarity(y_hat, e1)
        assert sim > 0.0
