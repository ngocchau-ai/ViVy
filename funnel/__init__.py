"""Unitary Reasoner — Filter Funnel module (analysis, filtering, conflict detection)."""

from ._types import CONTROL_SIGNALS, ControlSignal, Stream, as_streams, make_stream
from .analysis import amplitude_phase_analysis, entropy_analysis, interference_detection
from .conflict import detect_conflict, has_conflict
from .filter import FilterFunnel

__all__ = [
    "FilterFunnel",
    "Stream",
    "ControlSignal",
    "CONTROL_SIGNALS",
    "make_stream",
    "as_streams",
    "amplitude_phase_analysis",
    "entropy_analysis",
    "interference_detection",
    "detect_conflict",
    "has_conflict",
]
