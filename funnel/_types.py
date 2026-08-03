"""Shared type definitions for the filter funnel.

A :data:`Stream` is a single "thought stream" extracted from the core SVD
decomposition. It is a plain ``dict`` with the keys defined by the interface
contract (``core/svd_streams.py``):

* ``singular_value`` — the singular value of this stream.
* ``amplitude_ratio`` — fraction of total amplitude carried by this stream.
* ``state_A`` — the left (source) component state vector.
* ``state_B`` — the right (target) component state vector.
* ``interpretation`` — optional human/LLM-readable label.

The control signal produced by the funnel is one of the string literals in
:data:`ControlSignal`.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray


class Stream(TypedDict, total=False):
    """A single thought stream as produced by the core SVD decomposition."""

    singular_value: float
    amplitude_ratio: float
    state_A: NDArray[np.complex128]
    state_B: NDArray[np.complex128]
    interpretation: str


#: The four control signals the funnel can emit.
ControlSignal = Literal["continue", "measure", "backtrack", "delegate"]

#: All valid control signals (for validation).
CONTROL_SIGNALS: tuple[str, ...] = ("continue", "measure", "backtrack", "delegate")


def make_stream(
    singular_value: float,
    amplitude_ratio: float,
    state_A: NDArray[np.complex128],
    state_B: NDArray[np.complex128],
    interpretation: str = "",
) -> Stream:
    """Convenience constructor for a :data:`Stream` dict."""
    return {
        "singular_value": float(singular_value),
        "amplitude_ratio": float(amplitude_ratio),
        "state_A": np.asarray(state_A, dtype=np.complex128),
        "state_B": np.asarray(state_B, dtype=np.complex128),
        "interpretation": interpretation,
    }


def as_streams(raw: Any) -> list[Stream]:
    """Coerce a list of dicts into :data:`Stream` dicts (validates required keys).

    Parameters
    ----------
    raw:
        Iterable of dicts, each with at least the keys ``singular_value``,
        ``amplitude_ratio``, ``state_A``, ``state_B``.

    Returns
    -------
    list[Stream]
        Validated stream dicts.

    Raises
    ------
    TypeError
        If an element is not a mapping or a required key is missing.
    """
    required = ("singular_value", "amplitude_ratio", "state_A", "state_B")
    out: list[Stream] = []
    for item in raw:
        if not isinstance(item, dict):
            raise TypeError(f"stream must be a dict, got {type(item).__name__}")
        missing = [k for k in required if k not in item]
        if missing:
            raise TypeError(f"stream missing required keys: {missing}")
        out.append(Stream(**item))
    return out
