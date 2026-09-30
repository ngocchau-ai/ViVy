"""Conflict detection between thought streams.

A conflict occurs when two **strong** streams point in opposite directions — i.e. they
carry comparable amplitude but their component states are nearly anti-parallel (negative
inner-product overlap). This is the funnel's cue to stop and reconsider rather than
blindly continue.

The primary entry point is :func:`detect_conflict`, which returns a structured
report. A lightweight boolean wrapper :func:`has_conflict` is provided for callers
that only need a yes/no.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from ._types import Stream, as_streams


def _overlap(a: NDArray[np.complex128], b: NDArray[np.complex128]) -> float:
    """Normalised complex overlap magnitude in ``[0, 1]`` between two vectors."""
    av = np.asarray(a, dtype=np.complex128).ravel()
    bv = np.asarray(b, dtype=np.complex128).ravel()
    if av.shape[0] != bv.shape[0] or av.shape[0] == 0:
        return 0.0
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    return float(np.clip(abs(np.vdot(av, bv)) / (na * nb), 0.0, 1.0))


def detect_conflict(
    streams: list[Stream],
    min_amplitude: float = 0.05,
    overlap_threshold: float = 0.5,
) -> dict[str, Any]:
    """Detect pairs of strong, mutually contradictory streams.

    Two streams ``i`` and ``j`` are considered conflicting when:

    * both carry amplitude at least ``min_amplitude`` (they are both *strong*), and
    * their component states are nearly orthogonal or anti-parallel, i.e. the overlap
      between ``state_A`` of one and ``state_A`` of the other is below
      ``overlap_threshold``.

    Parameters
    ----------
    streams:
        List of stream dicts.
    min_amplitude:
        Minimum amplitude a stream must have to count as "strong".
    overlap_threshold:
        Maximum normalised overlap for two strong streams to be considered conflicting
        (lower overlap = more contradictory).

    Returns
    -------
    dict
        With keys:

        * ``conflict`` — ``True`` if at least one conflicting pair exists.
        * ``pairs`` — list of ``(i, j, amplitude_i, amplitude_j, overlap)``.
        * ``n_conflicts`` — number of conflicting pairs.
        * ``strong_indices`` — indices of the streams that are strong.
    """
    validated = as_streams(streams)
    n = len(validated)
    amps = np.asarray(
        [abs(float(s.get("singular_value", 0.0))) for s in validated], dtype=np.float64
    )

    strong = [i for i in range(n) if amps[i] >= min_amplitude]
    pairs: list[tuple[int, int, float, float, float]] = []

    for a in range(len(strong)):
        for b in range(a + 1, len(strong)):
            i, j = strong[a], strong[b]
            sa = validated[i]
            sb = validated[j]
            ov = _overlap(sa["state_A"], sb["state_A"])
            if ov < overlap_threshold:
                pairs.append((i, j, float(amps[i]), float(amps[j]), float(ov)))

    return {
        "conflict": len(pairs) > 0,
        "pairs": pairs,
        "n_conflicts": len(pairs),
        "strong_indices": strong,
    }


def has_conflict(
    streams: list[Stream],
    min_amplitude: float = 0.05,
    overlap_threshold: float = 0.5,
) -> bool:
    """Return ``True`` if the streams contain at least one conflicting pair."""
    return bool(
        detect_conflict(
            streams, min_amplitude=min_amplitude, overlap_threshold=overlap_threshold
        )["conflict"]
    )
