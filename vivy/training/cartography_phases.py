"""C12 — Cartography phase split + RSS-vs-buffer + 100B / vision claim guards.

Five phases must stay distinct: atlas_load, weight_bytes_paged, resident_ram,
forward_execution, semantic_accuracy. RAM savings are never inferred from an
allocated buffer alone. 100B stays UNVERIFIED without real weights. Vision
needs real image bytes + reference labels — text descriptions do not count.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
from typing import Any, Sequence


PHASES = (
    "atlas_load",
    "weight_bytes_paged",
    "resident_ram",
    "forward_execution",
    "semantic_accuracy",
)

LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"


@dataclass(frozen=True)
class PhaseMeasurement:
    phase: str
    value: float | int | None
    unit: str
    source: str  # measured | config_math | not_run


def _phase(phase: str, value, unit: str, source: str = "measured") -> PhaseMeasurement:
    return PhaseMeasurement(phase=phase, value=value, unit=unit, source=source)


def measure_phases(
    *,
    atlas_bytes: int,
    atlas_load_ms: float,
    weight_bytes_paged: int,
    resident_rss_bytes: int,
    forward_ms: float,
    semantic_correct: int,
    semantic_total: int,
) -> dict[str, Any]:
    """Return one measurement per phase. Never collapses into a single score."""
    acc = (semantic_correct / semantic_total) if semantic_total else None
    phases = {
        "atlas_load": asdict(_phase("atlas_load", atlas_load_ms, "ms")),
        "weight_bytes_paged": asdict(_phase("weight_bytes_paged", weight_bytes_paged, "bytes")),
        "resident_ram": asdict(_phase("resident_ram", resident_rss_bytes, "bytes")),
        "forward_execution": asdict(_phase("forward_execution", forward_ms, "ms")),
        "semantic_accuracy": asdict(_phase("semantic_accuracy", acc, "accuracy")),
    }
    return {
        "phases": phases,
        "atlas_bytes_on_disk": atlas_bytes,
        "collapsed_to_single_score": False,
        "latency_claim": LATENCY_CLAIM,
        "note": (
            "atlas_load / weight_bytes_paged / resident_ram / forward_execution / "
            "semantic_accuracy are independent. Do not infer RAM savings from "
            "allocated_buffer_bytes. Do not treat atlas_load as forward latency."
        ),
    }


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _windows_memory_counters() -> dict[str, int] | None:
    if not hasattr(ctypes, "windll"):
        return None
    try:
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            return None
        return {
            "rss_bytes": int(counters.WorkingSetSize),
            "private_working_set_bytes": int(counters.WorkingSetSize),  # closest public field
            "page_faults": int(counters.PageFaultCount),
            "pagefile_usage_bytes": int(counters.PagefileUsage),
            "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        }
    except Exception:
        return None


def sample_process_memory(*, allocated_buffer_bytes: int) -> dict[str, Any]:
    """Report OS-level RSS/working-set/page-faults separately from an allocated buffer.

    `ram_savings_inferred_from_buffer` is always False — a smaller buffer is not
    proof of lower resident RAM.
    """
    os_sample = _windows_memory_counters()
    sample: dict[str, Any] = {
        "allocated_buffer_bytes": allocated_buffer_bytes,
        "rss_bytes": os_sample["rss_bytes"] if os_sample else None,
        "private_working_set_bytes": os_sample["private_working_set_bytes"] if os_sample else None,
        "page_faults": os_sample["page_faults"] if os_sample else None,
        "pagefile_usage_bytes": os_sample.get("pagefile_usage_bytes") if os_sample else None,
        "peak_working_set_bytes": os_sample.get("peak_working_set_bytes") if os_sample else None,
        "os_probe": "windows_psapi" if os_sample else "NOT_RUN",
        "ram_savings_inferred_from_buffer": False,
    }
    return sample


def check_100b_claim(
    *,
    claimed_parameter_count: int,
    weights_present: bool,
    weights_bytes: int,
    nearest_artifact: str = "",
) -> dict[str, Any]:
    """100B claims stay UNVERIFIED without real 100B weights. Never extrapolate from a smaller artifact."""
    has_real = bool(weights_present and weights_bytes > 0 and claimed_parameter_count >= 100_000_000_000)
    # Even with bytes on disk, a .catlas index is not model weights.
    is_catlas = nearest_artifact.endswith(".catlas")
    if not weights_present or is_catlas:
        return {
            "status": "UNVERIFIED",
            "claimed_parameter_count": claimed_parameter_count,
            "weights_present": weights_present,
            "weights_bytes": weights_bytes,
            "nearest_artifact": nearest_artifact,
            "extrapolated_from_smaller_artifact": False,
            "note": (
                f"No real 100B weights on host. Nearest artifact {nearest_artifact or 'none'} "
                "must not be extrapolated to a 100B measured claim (72b artifact ≠ 100B measured)."
            ),
        }
    return {
        "status": "MEASURABLE_IF_BENCHMARKED",
        "claimed_parameter_count": claimed_parameter_count,
        "weights_present": weights_present,
        "weights_bytes": weights_bytes,
        "nearest_artifact": nearest_artifact,
        "extrapolated_from_smaller_artifact": False,
        "note": "Real weights present. Still requires an actual inference benchmark before any latency/RAM claim.",
    }


def check_vision_claim(
    *,
    images: Sequence,
    reference_labels: Sequence,
    source: str = "text_description",
) -> dict[str, Any]:
    """Vision grounding requires real image payloads + reference labels.

    Text that describes an image is NOT multimodal grounding.
    """
    has_real_images = bool(images) and source == "image_bytes" and all(
        isinstance(img, (bytes, bytearray, memoryview)) and len(img) > 0 for img in images
    )
    has_reference_labels = bool(reference_labels) and all(
        isinstance(lbl, str) and lbl.strip() for lbl in reference_labels
    )
    counts = has_real_images and has_reference_labels
    return {
        "status": "READY_FOR_TEST" if counts else "NOT_RUN",
        "has_real_images": has_real_images,
        "has_reference_labels": has_reference_labels,
        "counts_as_multimodal_grounding": counts,
        "source": source,
        "n_images": len(images),
        "n_labels": len(reference_labels),
        "note": (
            "Real image bytes + non-empty reference labels required. "
            "Text descriptions of images are NOT multimodal grounding."
        ),
    }
