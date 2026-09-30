"""Self-verification filter funnel: evaluate, filter, and control thought streams.

The funnel is the second/third stage of the unitary reasoner pipeline. It takes a
list of :data:`~funnel._types.Stream` dicts (produced by the core SVD
decomposition), scores each one, keeps the confident ones, and emits a single
:data:`~funnel._types.ControlSignal`.

The confidence of a stream is the product of three factors:

.. math::

    \\text{confidence} = \\sigma \\times \\text{consistency} \\times \\text{brevity}

* ``sigma`` — the stream's singular value (amplitude strength).
* ``consistency`` — agreement between the stream's ``amplitude_ratio`` and its
  singular value (how self-consistent the decomposition is).
* ``brevity`` — a penalty for overly complex / fragmented thought (fewer streams is
  better).

Three thresholds partition the confidence axis:

* ``>= accept_threshold``  → stream is **accepted** (kept).
* ``>= warn_threshold``    → stream is **warned** (kept but flagged).
* otherwise               → stream is **rejected** (dropped).

The aggregate funnel confidence and the strongest stream's status drive the control
signal:

* ``'continue'``  — proceed; at least one strong accepted stream.
* ``'measure'``   — results are borderline; re-measure before deciding.
* ``'backtrack'`` — everything rejected / too diffuse; rethink the branch.
* ``'delegate'``  — conflict or low confidence; hand off to another subsystem.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from ._types import ControlSignal, Stream, as_streams


class FilterFunnel:
    """Filter and score thought streams, emitting a control signal.

    Parameters
    ----------
    accept_threshold:
        Confidence at or above which a stream is accepted (default ``0.6``).
    warn_threshold:
        Confidence at or above which a stream is warned (default ``0.35``).
    reject_threshold:
        Confidence below which a stream is rejected (default ``0.15``).
    conflict_penalty:
        How much an existing conflict lowers the aggregate confidence (default ``0.2``).
    """

    def __init__(
        self,
        accept_threshold: float = 0.6,
        warn_threshold: float = 0.35,
        reject_threshold: float = 0.15,
        conflict_penalty: float = 0.2,
        delegate_threshold: int = 3,
    ) -> None:
        if not (reject_threshold <= warn_threshold <= accept_threshold):
            raise ValueError(
                "thresholds must satisfy reject <= warn <= accept, got "
                f"({reject_threshold}, {warn_threshold}, {accept_threshold})"
            )
        self.accept_threshold = float(accept_threshold)
        self.warn_threshold = float(warn_threshold)
        self.reject_threshold = float(reject_threshold)
        self.conflict_penalty = float(conflict_penalty)
        self.delegate_threshold = int(delegate_threshold)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def evaluate(
        self, streams: list[Stream]
    ) -> tuple[list[Stream], ControlSignal, float]:
        """Evaluate a list of streams and produce kept streams + control signal.

        Parameters
        ----------
        streams:
            List of stream dicts (keys ``singular_value``, ``amplitude_ratio``,
            ``state_A``, ``state_B``). May be empty.

        Returns
        -------
        kept_streams:
            The streams whose confidence is ``>= warn_threshold``, each augmented
            with ``confidence`` and ``status`` keys.
        control_signal:
            One of ``'continue' | 'measure' | 'backtrack' | 'delegate'``.
        confidence:
            Aggregate funnel confidence in ``[0, 1]``.
        """
        validated = as_streams(streams)
        if not validated:
            return [], "backtrack", 0.0

        scored = [self._score_stream(s, len(validated)) for s in validated]

        # Aggregate confidence = mean of accepted/warned confidences (0 if none).
        kept = [s for s in scored if s["status"] != "rejected"]
        if kept:
            aggregate = float(np.mean([s["confidence"] for s in kept]))
        else:
            aggregate = 0.0

        control = self._control_signal(scored, aggregate)
        return cast("list[Stream]", kept), control, float(np.clip(aggregate, 0.0, 1.0))

    # ------------------------------------------------------------------ #
    # Scoring
    # ------------------------------------------------------------------ #
    def _score_stream(self, stream: Stream, n_streams: int) -> dict[str, Any]:
        """Compute the confidence and status of a single stream."""
        sigma = abs(float(stream.get("singular_value", 0.0)))
        amp_ratio = float(stream.get("amplitude_ratio", 0.0))

        # sigma factor: normalise against a reference of 1.0 (clipped).
        sigma_factor = float(np.clip(sigma, 0.0, 1.0))

        # consistency: how well amplitude_ratio agrees with sigma.
        consistency = self._consistency(sigma, amp_ratio)

        # brevity: fewer streams => more focused => higher brevity.
        brevity = self._brevity(n_streams)

        confidence = sigma_factor * consistency * brevity
        confidence = float(np.clip(confidence, 0.0, 1.0))
        status = self._status(confidence)

        return {
            "singular_value": sigma,
            "amplitude_ratio": amp_ratio,
            "confidence": confidence,
            "status": status,
            "state_A": stream.get("state_A"),
            "state_B": stream.get("state_B"),
            "interpretation": stream.get("interpretation", ""),
        }

    @staticmethod
    def _consistency(sigma: float, amp_ratio: float) -> float:
        """Consistency between singular value and amplitude ratio.

        If the stream carries a large fraction of the amplitude (high ``amp_ratio``)
        but a small singular value (or vice versa) the decomposition is inconsistent.
        """
        if sigma <= 0.0:
            return 0.0
        # Both should be "large" together; use the harmonic-ish agreement.
        return float(np.clip(1.0 - abs(sigma - amp_ratio), 0.0, 1.0))

    @staticmethod
    def _brevity(n_streams: int) -> float:
        """Brevity factor: decays as the number of streams grows."""
        if n_streams <= 0:
            return 0.0
        return float(np.clip(1.0 / (1.0 + 0.5 * (n_streams - 1)), 0.0, 1.0))

    def _status(self, confidence: float) -> str:
        """Map a confidence to ``'accepted' | 'warned' | 'rejected'``."""
        if confidence >= self.accept_threshold:
            return "accepted"
        if confidence >= self.warn_threshold:
            return "warned"
        return "rejected"

    # ------------------------------------------------------------------ #
    # Control signal
    # ------------------------------------------------------------------ #
    def _control_signal(
        self, scored: list[dict[str, Any]], aggregate: float
    ) -> ControlSignal:
        """Derive the control signal from per-stream statuses and aggregate confidence."""
        n_accepted = sum(1 for s in scored if s["status"] == "accepted")
        n_warned = sum(1 for s in scored if s["status"] == "warned")

        # Everything rejected => rethink.
        if n_accepted == 0 and n_warned == 0:
            return "backtrack"

        # Strong accepted stream(s) with high aggregate => proceed.
        if n_accepted >= 1 and aggregate >= self.accept_threshold:
            return "continue"

        # Only warned streams, aggregate moderate => measure, unless thought is too
        # fragmented (many warned, none accepted) => delegate.
        if n_accepted == 0 and n_warned >= 1:
            if n_warned <= self.delegate_threshold:
                return "measure"
            return "delegate"

        # Accepted streams exist but aggregate pulled down (e.g. many rejected)
        # => delegate to another subsystem.
        return "delegate"

    def _apply_conflict_penalty(self, aggregate: float, has_conflict: bool) -> float:
        """Lower aggregate confidence when a conflict is present."""
        if not has_conflict:
            return aggregate
        return float(np.clip(aggregate - self.conflict_penalty, 0.0, 1.0))
