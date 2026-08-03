"""Amplitude/phase, entropy, and interference analysis of thought streams.

These are the *measurement* primitives of the filter funnel's first stage. They
turn a list of :data:`~funnel._types.Stream` dicts into interpretable scalars:

* :func:`amplitude_phase_analysis` — dominant amplitudes and phases.
* :func:`entropy_analysis` — Shannon entropy of the amplitude distribution.
* :func:`interference_detection` — detect coherent interference between streams.

All arithmetic is ``numpy.complex128``.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ._types import Stream


def _amplitudes(streams: list[Stream]) -> NDArray[np.float64]:
    """Return the amplitude (magnitude) of each stream's singular value."""
    return np.asarray(
        [abs(float(s.get("singular_value", 0.0))) for s in streams], dtype=np.float64
    )


def amplitude_phase_analysis(
    streams: list[Stream], top_k: int = 3
) -> dict[str, Any]:
    """Analyse the amplitude and phase structure of the streams.

    Parameters
    ----------
    streams:
        List of stream dicts.
    top_k:
        Number of dominant streams to report in ``dominant``.

    Returns
    -------
    dict
        With keys:

        * ``total_amplitude`` — sum of stream amplitudes.
        * ``max_amplitude`` — largest amplitude.
        * ``mean_amplitude`` — mean amplitude (``0.0`` if empty).
        * ``n_streams`` — number of streams.
        * ``dominant`` — list of ``(index, amplitude, phase)`` for the top-``k``
          streams, sorted by amplitude descending. ``phase`` is the phase
          (in radians) of the stream's ``state_A`` at the largest-magnitude
          entry, or ``0.0`` if unavailable.
        * ``phase_spread`` — circular standard deviation of dominant phases.
    """
    amps = _amplitudes(streams)
    n = len(streams)
    total = float(amps.sum()) if n else 0.0
    max_amp = float(amps.max()) if n else 0.0
    mean_amp = float(amps.mean()) if n else 0.0

    dominant: list[tuple[int, float, float]] = []
    for idx in np.argsort(amps)[::-1][: max(0, top_k)]:
        phase = _stream_phase(streams[int(idx)])
        dominant.append((int(idx), float(amps[int(idx)]), phase))

    phases = [ph for (_i, _a, ph) in dominant]
    phase_spread = _circular_std(phases) if phases else 0.0

    return {
        "total_amplitude": total,
        "max_amplitude": max_amp,
        "mean_amplitude": mean_amp,
        "n_streams": n,
        "dominant": dominant,
        "phase_spread": phase_spread,
    }


def _stream_phase(stream: Stream) -> float:
    """Extract a representative phase from a stream's ``state_A`` vector."""
    a = stream.get("state_A")
    if a is None:
        return 0.0
    arr = np.asarray(a, dtype=np.complex128).ravel()
    if arr.size == 0:
        return 0.0
    # Phase of the largest-magnitude entry.
    idx = int(np.argmax(np.abs(arr)))
    return float(np.angle(arr[idx]))


def _circular_std(phases: list[float]) -> float:
    """Circular standard deviation of a list of phase angles (radians)."""
    if not phases:
        return 0.0
    p = np.asarray(phases, dtype=np.float64)
    R = float(np.hypot(np.mean(np.cos(p)), np.mean(np.sin(p))))
    R = min(1.0, max(0.0, R))
    return float(math.sqrt(-2.0 * math.log(R))) if R > 0.0 else math.pi


def entropy_analysis(streams: list[Stream]) -> dict[str, float]:
    """Shannon entropy of the normalised amplitude distribution.

    A high entropy means the thought is spread across many comparable streams
    (diffuse / uncertain); a low entropy means one stream dominates (focused).

    Parameters
    ----------
    streams:
        List of stream dicts.

    Returns
    -------
    dict
        With keys:

        * ``entropy`` — Shannon entropy in nats (``0.0`` for empty or single).
        * ``max_entropy`` — ``log(n_streams)``, the maximum possible entropy.
        * ``normalized_entropy`` — ``entropy / max_entropy`` in ``[0, 1]``
          (``0.0`` if ``n_streams < 2``).
        * ``n_streams`` — number of streams.
    """
    amps = _amplitudes(streams)
    n = len(amps)
    if n == 0:
        return {"entropy": 0.0, "max_entropy": 0.0, "normalized_entropy": 0.0, "n_streams": 0}

    total = float(amps.sum())
    if total <= 0.0:
        return {"entropy": 0.0, "max_entropy": math.log(n), "normalized_entropy": 0.0, "n_streams": n}

    p = amps / total
    p = p[p > 0.0]
    entropy = float(-np.sum(p * np.log(p)))
    max_entropy = math.log(n)
    normalized = entropy / max_entropy if n > 1 else 0.0
    return {
        "entropy": entropy,
        "max_entropy": max_entropy,
        "normalized_entropy": float(np.clip(normalized, 0.0, 1.0)),
        "n_streams": n,
    }


def interference_detection(
    streams: list[Stream],
    phase_tol: float = 0.5,
    amp_ratio_tol: float = 0.1,
    min_amplitude: float = 0.05,
) -> dict[str, Any]:
    """Detect coherent interference between pairs of streams.

    Interference is measured via the normalised complex inner product (overlap)
    between the ``state_A`` vectors of two streams:

    * **Constructive** — overlap ``≥ cos(phase_tol)`` (states are nearly parallel).
    * **Destructive** — overlap ``≤ -cos(phase_tol)`` (states are nearly anti-parallel).

    Only pairs where both streams carry amplitude ``≥ min_amplitude`` and the
    weaker stream carries at least ``amp_ratio_tol`` of the stronger one are
    considered.

    Parameters
    ----------
    streams:
        List of stream dicts.
    phase_tol:
        Phase tolerance (radians). Overlap threshold for constructive/destructive
        is ``cos(phase_tol)``.
    amp_ratio_tol:
        Minimum ratio ``min(ai, aj) / max(ai, aj)`` for two streams to be
        considered comparable.
    min_amplitude:
        Minimum absolute amplitude for a stream to participate in interference
        (weak streams are ignored).

    Returns
    -------
    dict
        With keys:

        * ``interference`` — ``True`` if at least one interfering pair exists.
        * ``pairs`` — list of ``(i, j, kind, overlap, amp_ratio)``.
        * ``n_interfering_pairs`` — number of interfering pairs.
    """
    amps = _amplitudes(streams)
    n = len(streams)
    pairs: list[tuple[int, int, str, float, float]] = []
    overlap_thr = math.cos(phase_tol)

    if n < 2:
        return {"interference": False, "pairs": pairs, "n_interfering_pairs": 0}

    for i in range(n):
        for j in range(i + 1, n):
            ai, aj = amps[i], amps[j]
            if ai < min_amplitude or aj < min_amplitude:
                continue
            if ai <= 0.0 or aj <= 0.0:
                continue
            ratio = min(ai, aj) / max(ai, aj)
            if ratio < amp_ratio_tol:
                continue

            ov = _stream_overlap(streams[i], streams[j])
            if ov >= overlap_thr:
                pairs.append((i, j, "constructive", float(ov), float(ratio)))
            elif ov <= -overlap_thr:
                pairs.append((i, j, "destructive", float(ov), float(ratio)))

    return {
        "interference": len(pairs) > 0,
        "pairs": pairs,
        "n_interfering_pairs": len(pairs),
    }


def _stream_overlap(a: Stream, b: Stream) -> float:
    """Normalised real-part inner product between two streams' ``state_A``.

    Returns a value in ``[-1, 1]``.
    """
    av_raw = a.get("state_A")
    bv_raw = b.get("state_A")
    av = np.asarray([0] if av_raw is None else av_raw, dtype=np.complex128).ravel()
    bv = np.asarray([0] if bv_raw is None else bv_raw, dtype=np.complex128).ravel()
    if av.shape[0] != bv.shape[0] or av.shape[0] == 0:
        return 0.0
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    return float(np.clip(np.vdot(av, bv).real / (na * nb), -1.0, 1.0))
