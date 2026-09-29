"""
cautreo_binding.py — ViVy Native In-Process C-ABI Binding for CAUTREO Engine.

Cung cấp kết nối trực tiếp (In-Process Direct Binding) giữa
ViVy Core (Python) và Cautreo Engine (C Native Shared Library `cautreo.dll`).
# [ISOLATED 23/09/2026] prior: "(Zero-Latency In-Process Direct Binding)" — latency: see P5 receipt

Kiến trúc:
    ViVy (Linh hồn / Bản ngã nhận thức)
        │
        ├── Direct Memory Access (ctypes / In-Process Pointer) [latency: benchmark]
        # [ISOLATED 23/09/2026] prior: "[0ms Latency]"
        ▼
    Cautreo (Cơ thể / Căn phòng sinh tồn)
        ├── src/context_memory: HARD_FACT, CONSTRAINT, TASK, SUMMARY
        ├── src/score: Runtime Score Graph (CONTEXT_EFFICIENCY, TASK_PROGRESS)
        └── src/context_chain: CCE Segment Decomposer & Priority Scoring

Changelog:
    21/09/2026 (Antigravity IDE, Phase 2): Initial C-ABI ctypes implementation.
    23/09/2026 (Claude Code — P5 Gate 9): Isolate unbenchmarked latency claim; point at P5 receipt.
"""

from __future__ import annotations

import ctypes
import logging
import os
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums matching C definitions
# ---------------------------------------------------------------------------


class CautreoMemoryKind(IntEnum):
    HARD_FACT = 0
    TASK = 1
    CONSTRAINT = 2
    SUMMARY = 3


class CautreoScoreType(IntEnum):
    MODEL_CAPABILITY = 0
    AGENT_FIT = 1
    TASK_PROGRESS = 2
    MEMORY_QUALITY = 3
    CONTEXT_EFFICIENCY = 4
    PRECISION_FIT = 5
    STREAM_EFFICIENCY = 6
    OUTCOME = 7


class CautreoMemoryStatus(IntEnum):
    OK = 0
    INVALID = -1
    NOMEM = -2
    IO = -3
    CORRUPT = -4
    CONFLICT = -5
    NOT_FOUND = -6


# ---------------------------------------------------------------------------
# Ctypes Struct Definitions
# ---------------------------------------------------------------------------

CT_MEMORY_ID_MAX = 96
CT_MEMORY_HASH_MAX = 96


class _CtMemoryProvenance(ctypes.Structure):
    _fields_ = [
        ("message_id", ctypes.c_char_p),
        ("tool_call_id", ctypes.c_char_p),
        ("source_offset", ctypes.c_uint64),
        ("source_length", ctypes.c_uint64),
        ("source_hash", ctypes.c_char_p),
    ]


class _CtMemoryPut(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char_p),
        ("kind", ctypes.c_int),
        ("content", ctypes.c_char_p),
        ("content_len", ctypes.c_size_t),
        ("provenance", _CtMemoryProvenance),
        ("created_at_ms", ctypes.c_uint64),
        ("expires_at_ms", ctypes.c_uint64),
    ]


class _CtMemoryItem(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char * CT_MEMORY_ID_MAX),
        ("kind", ctypes.c_int),
        ("content", ctypes.c_char_p),
        ("content_len", ctypes.c_size_t),
        ("message_id", ctypes.c_char * CT_MEMORY_ID_MAX),
        ("tool_call_id", ctypes.c_char * CT_MEMORY_ID_MAX),
        ("source_offset", ctypes.c_uint64),
        ("source_length", ctypes.c_uint64),
        ("source_hash", ctypes.c_char * CT_MEMORY_HASH_MAX),
        ("version", ctypes.c_uint64),
        ("created_at_ms", ctypes.c_uint64),
        ("updated_at_ms", ctypes.c_uint64),
        ("expires_at_ms", ctypes.c_uint64),
        ("deleted", ctypes.c_bool),
    ]


class _CtMemoryOptions(ctypes.Structure):
    _fields_ = [
        ("persistence", ctypes.c_int),
        ("cold_log_path", ctypes.c_char_p),
        ("max_items", ctypes.c_size_t),
    ]


# ---------------------------------------------------------------------------
# Library Loader
# ---------------------------------------------------------------------------


def _find_cautreo_dll() -> str | None:
    """Locate cautreo.dll in known build directories."""
    candidates = [
        # 2026-09-26 repo layout: vivy/integration/ -> Vivy_final/engine/bin/
        Path(__file__).resolve().parent.parent.parent / "engine" / "bin" / "cautreo.dll",
        Path("D:/91s_Vivy/Vivy_final/engine/bin/cautreo.dll"),
        # [ISOLATED 26/09/2026] legacy relative from unitary-reasoner/integration/ — kept as fallback
        Path(__file__).parent.parent.parent / "Vivy_final" / "engine" / "bin" / "cautreo.dll",
        Path("D:/cautreov2/build/cautreo.dll"),
        Path(os.environ.get("CAUTREO_DLL_PATH", "")),
        Path(__file__).parent.parent.parent / "cautreov2" / "build" / "cautreo.dll",
    ]
    for p in candidates:
        if p and p.is_file():
            return str(p.resolve())
    return None


_CAUTREO_DLL_INSTANCE: ctypes.CDLL | None = None
_CAUTREO_LOAD_ERROR: str | None = None

dll_path = _find_cautreo_dll()
if dll_path:
    try:
        _CAUTREO_DLL_INSTANCE = ctypes.CDLL(dll_path)
        logger.info("Loaded native Cautreo C-ABI library: %s", dll_path)
    except Exception as exc:  # noqa: BLE001
        _CAUTREO_LOAD_ERROR = str(exc)
        logger.warning("Failed loading native Cautreo DLL at %s: %s", dll_path, exc)
else:
    _CAUTREO_LOAD_ERROR = "cautreo.dll not found in search paths"


def is_native_cautreo_available() -> bool:
    """Check if native Cautreo DLL is loaded and functional."""
    return _CAUTREO_DLL_INSTANCE is not None


is_cautreo_available = is_native_cautreo_available


def _find_pager_dll() -> str | None:
    """Locate cautreo_pager.dll in known build directories."""
    candidates = [
        # 2026-09-26 repo layout: vivy/integration/ -> Vivy_final/engine/bin/
        Path(__file__).resolve().parent.parent.parent / "engine" / "bin" / "cautreo_pager.dll",
        # [ISOLATED 26/09/2026] legacy relative from unitary-reasoner/integration/ — kept as fallback
        Path(__file__).parent.parent.parent / "Vivy_final" / "engine" / "bin" / "cautreo_pager.dll",
        Path(os.environ.get("CAUTREO_PAGER_DLL_PATH", "")),
    ]
    for p in candidates:
        if p and p.is_file():
            return str(p.resolve())
    return None


_CAUTREO_PAGER_DLL: ctypes.CDLL | None = None
_PAGER_LOAD_ERROR: str | None = None

_pager_dll_path = _find_pager_dll()
if _pager_dll_path:
    try:
        _CAUTREO_PAGER_DLL = ctypes.CDLL(_pager_dll_path)
        logger.info("Loaded native Cautreo Weight Pager: %s", _pager_dll_path)
    except Exception as exc:  # noqa: BLE001
        _PAGER_LOAD_ERROR = str(exc)
        logger.warning("Failed loading pager DLL at %s: %s", _pager_dll_path, exc)


def is_native_pager_available() -> bool:
    """Check if native Cautreo Weight Pager DLL is loaded."""
    return _CAUTREO_PAGER_DLL is not None


# ---------------------------------------------------------------------------
# High-level Python Wrappers
# ---------------------------------------------------------------------------


@dataclass
class CautreoMemoryItem:
    id: str
    kind: CautreoMemoryKind
    content: str
    version: int
    created_at_ms: int
    updated_at_ms: int


class CautreoContextMemory:
    """Native Context Memory manager for ViVy within Cautreo.

    In-process C-memory access (latency: see P5 benchmark receipt).
    # [ISOLATED 23/09/2026] prior: "Zero-latency, in-process C-memory access."
    """

    def __init__(self, max_items: int = 1024, cold_log_path: str | None = None) -> None:
        self._dll = _CAUTREO_DLL_INSTANCE
        self._mem_ptr: ctypes.c_void_p | None = None
        self._fallback_store: dict[str, CautreoMemoryItem] = {}

        if self._dll:
            self._dll.ct_context_memory_open.argtypes = [
                ctypes.POINTER(_CtMemoryOptions),
                ctypes.POINTER(ctypes.c_void_p),
            ]
            self._dll.ct_context_memory_open.restype = ctypes.c_int

            self._dll.ct_context_memory_close.argtypes = [ctypes.c_void_p]
            self._dll.ct_context_memory_close.restype = None

            self._dll.ct_context_memory_put.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(_CtMemoryPut),
                ctypes.c_uint64,
                ctypes.POINTER(ctypes.c_uint64),
            ]
            self._dll.ct_context_memory_put.restype = ctypes.c_int

            self._dll.ct_context_memory_get.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_uint64,
            ]
            self._dll.ct_context_memory_get.restype = ctypes.POINTER(_CtMemoryItem)

            opts = _CtMemoryOptions(
                persistence=1 if cold_log_path else 0,
                cold_log_path=cold_log_path.encode("utf-8") if cold_log_path else None,
                max_items=max_items,
            )
            out_ptr = ctypes.c_void_p()
            ret = self._dll.ct_context_memory_open(
                ctypes.byref(opts), ctypes.byref(out_ptr)
            )
            if ret == 0:
                self._mem_ptr = out_ptr
            else:
                logger.warning(
                    "ct_context_memory_open failed with %d, using in-memory fallback", ret
                )

    def close(self) -> None:
        if self._dll and self._mem_ptr:
            self._dll.ct_context_memory_close(self._mem_ptr)
            self._mem_ptr = None

    def __enter__(self) -> CautreoContextMemory:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def put(
        self,
        item_id: str,
        kind: CautreoMemoryKind,
        content: str,
        expected_version: int = 0,
    ) -> int:
        """Put item into native Cautreo memory."""
        now_ms = int(time.time() * 1000)

        if self._dll and self._mem_ptr:
            prov = _CtMemoryProvenance(
                message_id=b"msg_vivy_core",
                tool_call_id=b"tool_in_process",
                source_offset=0,
                source_length=0,
                source_hash=b"sha256:vivy_core_native",
            )
            put_req = _CtMemoryPut(
                id=item_id.encode("utf-8"),
                kind=int(kind),
                content=content.encode("utf-8"),
                content_len=len(content.encode("utf-8")),
                provenance=prov,
                created_at_ms=now_ms,
                expires_at_ms=0,
            )
            out_ver = ctypes.c_uint64(0)
            ret = self._dll.ct_context_memory_put(
                self._mem_ptr, ctypes.byref(put_req), expected_version, ctypes.byref(out_ver)
            )
            if ret == 0:
                ver = out_ver.value
                self._fallback_store[item_id] = CautreoMemoryItem(
                    id=item_id,
                    kind=kind,
                    content=content,
                    version=ver,
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
                return ver
            return -1

        # Fallback
        ver = expected_version + 1
        self._fallback_store[item_id] = CautreoMemoryItem(
            id=item_id,
            kind=kind,
            content=content,
            version=ver,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        return ver

    def get(self, item_id: str) -> CautreoMemoryItem | None:
        """Get item from native Cautreo memory."""
        now_ms = int(time.time() * 1000)
        if self._dll and self._mem_ptr:
            self._dll.ct_context_memory_get.restype = ctypes.POINTER(_CtMemoryItem)
            item_ptr = self._dll.ct_context_memory_get(
                self._mem_ptr, item_id.encode("utf-8"), now_ms
            )
            if item_ptr:
                item = item_ptr.contents
                raw_content = item.content
                content_str = (
                    raw_content.decode("utf-8", errors="replace")
                    if raw_content
                    else ""
                )
                return CautreoMemoryItem(
                    id=item.id.decode("utf-8", errors="replace"),
                    kind=CautreoMemoryKind(item.kind),
                    content=content_str,
                    version=item.version,
                    created_at_ms=item.created_at_ms,
                    updated_at_ms=item.updated_at_ms,
                )
            return None

        return self._fallback_store.get(item_id)

    def get_all(self) -> list[CautreoMemoryItem]:
        """Return all tracked memory items."""
        return list(self._fallback_store.values())

    def store_hard_fact(self, fact_id: str, content: str) -> int:
        return self.put(fact_id, CautreoMemoryKind.HARD_FACT, content)

    def store_constraint(self, constraint_id: str, content: str) -> int:
        return self.put(constraint_id, CautreoMemoryKind.CONSTRAINT, content)

    def store_task(self, task_id: str, content: str) -> int:
        return self.put(task_id, CautreoMemoryKind.TASK, content)

    def store_summary(self, summary_id: str, content: str) -> int:
        return self.put(summary_id, CautreoMemoryKind.SUMMARY, content)

    def get_summary(self, summary_id: str) -> str | None:
        """Retrieve content of a summary or memory item by ID."""
        item = self.get(summary_id)
        return item.content if item else None

    def build_intuition_digest(self) -> str:
        """Build a compact ~150-token intuition header for context slots.

        Extracts active constraints, root task, and key hard facts.
        """
        parts = ["### [VIVY INTUITION DIGEST — NATIVE MEMORY]"]

        # Collect constraints and facts
        for _item_id, item in list(self._fallback_store.items()):
            if item.kind == CautreoMemoryKind.CONSTRAINT:
                parts.append(f"• INVARIANT: {item.content}")
            elif item.kind == CautreoMemoryKind.TASK:
                parts.append(f"• ACTIVE GOAL: {item.content}")
            elif item.kind == CautreoMemoryKind.HARD_FACT:
                parts.append(f"• FACT: {item.content}")

        if len(parts) == 1:
            # [ISOLATED 23/09/2026] prior fallback claimed "Error repeat rate = 0%"
            # — Gate 9: no 0% claim without a reproducible receipt.
            parts.append("• INVARIANT: Preserve epistemic rigor | Dampen falsified branches (VM-11)")
            parts.append("• ACTIVE GOAL: Execute task with zero drift")

        return "\n".join(parts)


class CautreoScoreGraph:
    """Native Runtime Score Graph wrapper for ViVy within Cautreo."""

    def __init__(self) -> None:
        self._dll = _CAUTREO_DLL_INSTANCE
        self._graph_ptr: ctypes.c_void_p | None = None
        self._fallback_scores: dict[int, tuple[float, float]] = {}

        if self._dll:
            self._dll.ct_score_graph_create.restype = ctypes.c_void_p
            self._dll.ct_score_graph_destroy.argtypes = [ctypes.c_void_p]
            self._dll.ct_score_graph_update.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_float,
                ctypes.c_float,
            ]
            self._dll.ct_score_graph_update.restype = ctypes.c_int
            self._dll.ct_score_graph_score.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._dll.ct_score_graph_score.restype = ctypes.c_float
            self._dll.ct_score_graph_confidence.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._dll.ct_score_graph_confidence.restype = ctypes.c_float

            self._graph_ptr = self._dll.ct_score_graph_create()

    def destroy(self) -> None:
        if self._dll and self._graph_ptr:
            self._dll.ct_score_graph_destroy(self._graph_ptr)
            self._graph_ptr = None

    def __enter__(self) -> CautreoScoreGraph:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.destroy()

    def update(
        self,
        score_type: CautreoScoreType,
        score: float,
        evidence_weight: float = 1.0,
    ) -> int:
        """Update a score in native score graph."""
        if self._dll and self._graph_ptr:
            return self._dll.ct_score_graph_update(
                self._graph_ptr,
                int(score_type),
                ctypes.c_float(score),
                ctypes.c_float(evidence_weight),
            )
        self._fallback_scores[int(score_type)] = (score, evidence_weight)
        return 0

    def get_score(self, score_type: CautreoScoreType) -> float:
        """Get current score value [0.0, 1.0]."""
        if self._dll and self._graph_ptr:
            return float(self._dll.ct_score_graph_score(self._graph_ptr, int(score_type)))
        return self._fallback_scores.get(int(score_type), (0.5, 0.0))[0]

    def get_confidence(self, score_type: CautreoScoreType) -> float:
        """Get current confidence value [0.0, 1.0]."""
        if self._dll and self._graph_ptr:
            return float(
                self._dll.ct_score_graph_confidence(self._graph_ptr, int(score_type))
            )
        return self._fallback_scores.get(int(score_type), (0.5, 0.0))[1]

    @property
    def context_efficiency(self) -> float:
        return self.get_score(CautreoScoreType.CONTEXT_EFFICIENCY)

    @property
    def task_progress(self) -> float:
        return self.get_score(CautreoScoreType.TASK_PROGRESS)

    @property
    def memory_quality(self) -> float:
        return self.get_score(CautreoScoreType.MEMORY_QUALITY)


# ---------------------------------------------------------------------------
# Sprint R4: Weight Paging & Task-Sequential Slicing (C-ABI)
# ---------------------------------------------------------------------------


class CtQuantType(IntEnum):
    FP32 = 0
    FP16 = 1
    Q8_0 = 2
    Q4_K_M = 3
    IQ2_XXS = 4
    CUSTOM_PROJECTION = 5


class CtSliceState(IntEnum):
    ON_DISK = 0
    PAGING_IN = 1
    RESIDENT = 2
    DIRTY = 3


@dataclass
class WeightSliceInfo:
    slice_name: str
    file_offset: int
    slice_size_bytes: int
    layer_index: int
    quant_type: CtQuantType = CtQuantType.Q4_K_M
    state: CtSliceState = CtSliceState.ON_DISK
    task_affinity_score: float = 0.5
    last_accessed_ms: int = 0
    n_dims: int = 1
    dims: tuple[int, ...] = ()


def _compute_ggml_type_size(type_id: int, n_elements: int) -> int:
    """Compute raw byte size for a GGML tensor type."""
    type_sizes: dict[int, float] = {
        0: 4.0, 1: 2.0, 7: 1.0, 8: 34.0 / 32, 9: 36.0 / 32,
        10: 2.0, 11: 4.0, 12: 8.0,
        2: 18.0 / 32, 3: 20.0 / 32, 6: 22.0 / 32,
        13: 84.0 / 256, 14: 110.0 / 256, 15: 144.0 / 256,
        16: 176.0 / 256, 17: 210.0 / 256, 18: 292.0 / 256,
        19: 18.0 / 32,
    }
    return int(n_elements * type_sizes.get(type_id, 4.0))


def _parse_gguf_tensor_infos(path: str) -> list[dict[str, Any]]:
    """Parse GGUF tensor metadata (names, shapes, types, offsets) from file."""
    import struct

    tensors: list[dict[str, Any]] = []
    with open(path, "rb") as f:
        magic = struct.unpack("<I", f.read(4))[0]
        if magic != 0x46554747:
            raise ValueError("Not a GGUF file")
        _version = struct.unpack("<I", f.read(4))[0]
        n_tensors = struct.unpack("<Q", f.read(8))[0]
        n_kv = struct.unpack("<Q", f.read(8))[0]

        def _read_str() -> str:
            slen = struct.unpack("<Q", f.read(8))[0]
            return f.read(slen).decode("utf-8", errors="replace")

        def _skip_value(vt: int) -> None:
            if vt in (0, 1, 7):
                f.seek(1, 1)
            elif vt in (2, 3):
                f.seek(2, 1)
            elif vt in (4, 5, 6):
                f.seek(4, 1)
            elif vt in (10, 11, 12):
                f.seek(8, 1)
            elif vt == 8:
                _read_str()
            elif vt == 9:
                at = struct.unpack("<I", f.read(4))[0]
                n = struct.unpack("<Q", f.read(8))[0]
                for _ in range(n):
                    _skip_value(at)
            else:
                raise ValueError(f"Unknown GGUF value type {vt}")

        for _ in range(n_kv):
            _read_str()
            vt = struct.unpack("<I", f.read(4))[0]
            _skip_value(vt)

        for _ in range(n_tensors):
            name = _read_str()
            n_dims = struct.unpack("<I", f.read(4))[0]
            dims = [struct.unpack("<Q", f.read(8))[0] for _ in range(n_dims)]
            dtype = struct.unpack("<I", f.read(4))[0]
            offset = struct.unpack("<Q", f.read(8))[0]

            n_elem = 1
            for d in dims:
                n_elem *= d
            size_bytes = _compute_ggml_type_size(dtype, n_elem)

            layer = 0
            blk_pos = name.find("blk.")
            if blk_pos >= 0:
                try:
                    layer = int(name[blk_pos + 4:].split(".")[0])
                except ValueError:
                    pass

            tensors.append({
                "name": name,
                "n_dims": n_dims,
                "dims": tuple(dims),
                "type": dtype,
                "offset": offset,
                "size_bytes": size_bytes,
                "layer": layer,
            })
    return tensors


class CautreoWeightPager:
    """Cautreo Weight Paging & Slicing Controller.

    Supports native C weight pager (cautreo_pager.dll) with real GGUF I/O
    and real matvec compute. Falls back to Python simulation when native
    is unavailable or no model_path is provided.
    """

    def __init__(
        self,
        model_id: str = "qwen2.5-coder-14b",
        model_path: str = "",
        max_ram_budget_bytes: int = 2 * 1024 * 1024 * 1024,
    ) -> None:
        self.model_id = model_id
        self.model_path = model_path
        self.max_ram_budget_bytes = max_ram_budget_bytes
        self._current_ram_bytes = 0
        self._slices: dict[str, WeightSliceInfo] = {}
        self._dll = _CAUTREO_DLL_INSTANCE
        self._pager_dll = _CAUTREO_PAGER_DLL
        self._registry_ptr: ctypes.c_void_p | None = None
        self._use_native = False

        if self._pager_dll is not None and model_path:
            self._init_native(model_path)

        if not self._use_native:
            self._init_default_coder_slices()

    def _init_native(self, model_path: str) -> None:
        """Initialize native weight pager registry from GGUF."""
        dll = self._pager_dll
        if dll is None:
            return

        self._declare_pager_argtypes(dll)

        out_ptr = ctypes.c_void_p()
        ret = dll.ct_weight_registry_init(
            model_path.encode("utf-8"),
            ctypes.c_uint64(self.max_ram_budget_bytes),
            ctypes.byref(out_ptr),
        )
        if ret != 0 or not out_ptr.value:
            logger.warning("ct_weight_registry_init failed: %d", ret)
            return

        self._registry_ptr = out_ptr
        n = dll.ct_weight_registry_build_from_gguf(self._registry_ptr)
        if n < 0:
            logger.warning("build_from_gguf failed: %d", n)
            dll.ct_weight_registry_free(self._registry_ptr)
            self._registry_ptr = None
            return

        self._use_native = True
        logger.info("Native weight pager: %d slices from %s", n, model_path)
        self._track_gguf_shapes(model_path)

    @staticmethod
    def _declare_pager_argtypes(dll: ctypes.CDLL) -> None:
        dll.ct_weight_registry_init.argtypes = [
            ctypes.c_char_p, ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        dll.ct_weight_registry_init.restype = ctypes.c_int
        dll.ct_weight_registry_free.argtypes = [ctypes.c_void_p]
        dll.ct_weight_registry_free.restype = None
        dll.ct_weight_registry_build_from_gguf.argtypes = [ctypes.c_void_p]
        dll.ct_weight_registry_build_from_gguf.restype = ctypes.c_int
        dll.ct_weight_registry_register_slice.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p,
            ctypes.c_uint64, ctypes.c_uint64,
            ctypes.c_uint32, ctypes.c_int,
        ]
        dll.ct_weight_registry_register_slice.restype = ctypes.c_int
        dll.ct_weight_slice_page_in.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        dll.ct_weight_slice_page_in.restype = ctypes.c_int
        dll.ct_weight_slice_page_out.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        dll.ct_weight_slice_page_out.restype = ctypes.c_int
        dll.ct_weight_slice_sparse_page_in.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_float,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        dll.ct_weight_slice_sparse_page_in.restype = ctypes.c_int
        dll.ct_weight_slice_stream_compute.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_float), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_float), ctypes.c_size_t,
        ]
        dll.ct_weight_slice_stream_compute.restype = ctypes.c_int
        dll.ct_weight_registry_ram_usage.argtypes = [ctypes.c_void_p]
        dll.ct_weight_registry_ram_usage.restype = ctypes.c_uint64
        dll.ct_weight_registry_resident_count.argtypes = [ctypes.c_void_p]
        dll.ct_weight_registry_resident_count.restype = ctypes.c_int
        dll.ct_weight_registry_slice_count.argtypes = [ctypes.c_void_p]
        dll.ct_weight_registry_slice_count.restype = ctypes.c_int
        dll.ct_weight_slice_state.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        dll.ct_weight_slice_state.restype = ctypes.c_int
        dll.ct_weight_slice_loaded_bytes.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        dll.ct_weight_slice_loaded_bytes.restype = ctypes.c_int

    def _track_gguf_shapes(self, model_path: str) -> None:
        """Parse GGUF tensor metadata for Python-side shape tracking."""
        try:
            for t in _parse_gguf_tensor_infos(model_path):
                self._slices[t["name"]] = WeightSliceInfo(
                    slice_name=t["name"],
                    file_offset=t["offset"],
                    slice_size_bytes=t["size_bytes"],
                    layer_index=t.get("layer", 0),
                    state=CtSliceState.ON_DISK,
                    n_dims=t["n_dims"],
                    dims=t["dims"],
                )
        except Exception as exc:
            logger.warning("Failed to parse GGUF shapes: %s", exc)

    def build_from_gguf(self) -> int:
        """Register weight slices from GGUF tensor index (native only)."""
        if self._use_native and self._registry_ptr and self._pager_dll:
            return self._pager_dll.ct_weight_registry_build_from_gguf(self._registry_ptr)
        return -1

    def _init_default_coder_slices(self) -> None:
        """Register structural layer slices for Qwen Coder (48 transformer layers)."""
        for l_idx in range(48):
            s_name = f"qwen.blk.{l_idx}.ffn"
            self.register_slice(
                slice_name=s_name,
                file_offset=l_idx * 125829120,
                slice_size_bytes=125829120,
                layer_index=l_idx,
                quant_type=CtQuantType.Q4_K_M,
            )

    def register_slice(
        self,
        slice_name: str,
        file_offset: int,
        slice_size_bytes: int,
        layer_index: int,
        quant_type: CtQuantType = CtQuantType.Q4_K_M,
    ) -> None:
        self._slices[slice_name] = WeightSliceInfo(
            slice_name=slice_name,
            file_offset=file_offset,
            slice_size_bytes=slice_size_bytes,
            layer_index=layer_index,
            quant_type=quant_type,
            state=CtSliceState.ON_DISK,
        )

    def page_in(self, slice_name: str) -> bool:
        if self._use_native and self._registry_ptr and self._pager_dll:
            buf = ctypes.c_void_p()
            ret = self._pager_dll.ct_weight_slice_page_in(
                self._registry_ptr,
                slice_name.encode("utf-8"),
                ctypes.byref(buf),
            )
            return ret == 0

        if slice_name not in self._slices:
            logger.warning("Slice %s not found in registry", slice_name)
            return False

        slice_info = self._slices[slice_name]
        if slice_info.state == CtSliceState.RESIDENT:
            slice_info.last_accessed_ms = int(time.time() * 1000)
            return True

        while (self._current_ram_bytes + slice_info.slice_size_bytes) > self.max_ram_budget_bytes:
            evicted = self._evict_lru_slice()
            if not evicted:
                logger.warning("Unable to evict any slice to fit %s", slice_name)
                break

        slice_info.state = CtSliceState.RESIDENT
        slice_info.last_accessed_ms = int(time.time() * 1000)
        self._current_ram_bytes += slice_info.slice_size_bytes
        return True

    def page_out(self, slice_name: str) -> bool:
        if self._use_native and self._registry_ptr and self._pager_dll:
            ret = self._pager_dll.ct_weight_slice_page_out(
                self._registry_ptr, slice_name.encode("utf-8")
            )
            return ret == 0

        if slice_name not in self._slices:
            return False
        slice_info = self._slices[slice_name]
        if slice_info.state == CtSliceState.RESIDENT:
            slice_info.state = CtSliceState.ON_DISK
            self._current_ram_bytes = max(0, self._current_ram_bytes - slice_info.slice_size_bytes)
            return True
        return False

    def _evict_lru_slice(self) -> bool:
        resident = [s for s in self._slices.values() if s.state == CtSliceState.RESIDENT]
        if not resident:
            return False
        resident.sort(key=lambda s: (s.task_affinity_score, s.last_accessed_ms))
        victim = resident[0]
        return self.page_out(victim.slice_name)

    def sparse_page_in(self, slice_name: str, top_k_ratio: float = 0.10) -> bool:
        if self._use_native and self._registry_ptr and self._pager_dll:
            buf = ctypes.c_void_p()
            ret = self._pager_dll.ct_weight_slice_sparse_page_in(
                self._registry_ptr,
                slice_name.encode("utf-8"),
                ctypes.c_float(top_k_ratio),
                ctypes.byref(buf),
            )
            return ret == 0

        if slice_name not in self._slices:
            logger.warning("Slice %s not found in registry", slice_name)
            return False

        slice_info = self._slices[slice_name]
        sparse_size_bytes = int(slice_info.slice_size_bytes * top_k_ratio)

        while (self._current_ram_bytes + sparse_size_bytes) > self.max_ram_budget_bytes:
            evicted = self._evict_lru_slice()
            if not evicted:
                logger.warning("Unable to evict any slice to fit sparse %s", slice_name)
                break

        slice_info.state = CtSliceState.RESIDENT
        slice_info.last_accessed_ms = int(time.time() * 1000)
        self._current_ram_bytes += sparse_size_bytes
        return True

    def stream_compute(self, slice_name: str, input_tensor: list[float]) -> list[float]:
        if self._use_native and self._registry_ptr and self._pager_dll:
            self.page_in(slice_name)

            n_in = len(input_tensor)
            info = self._slices.get(slice_name)
            if info and info.n_dims >= 2 and len(info.dims) >= 2:
                rows = int(info.dims[-2])
                cols = int(info.dims[-1])
            elif info and info.n_dims == 1 and len(info.dims) >= 1:
                rows = 1
                cols = int(info.dims[0])
            else:
                rows = cols = n_in

            in_arr = (ctypes.c_float * max(cols, 1))()
            for i in range(min(n_in, cols)):
                in_arr[i] = input_tensor[i]
            out_arr = (ctypes.c_float * max(rows, 1))()

            ret = self._pager_dll.ct_weight_slice_stream_compute(
                self._registry_ptr,
                slice_name.encode("utf-8"),
                in_arr, cols,
                out_arr, rows,
            )
            if ret == 0:
                return list(out_arr[:rows])
            logger.warning("Native stream_compute failed: %d for %s", ret, slice_name)

        self.page_in(slice_name)
        return [x * 1.05 + 0.01 for x in input_tensor]

    def get_ram_usage_mb(self) -> float:
        if self._use_native and self._registry_ptr and self._pager_dll:
            return self._pager_dll.ct_weight_registry_ram_usage(self._registry_ptr) / (1024 * 1024)
        return self._current_ram_bytes / (1024 * 1024)

    @property
    def resident_slice_count(self) -> int:
        if self._use_native and self._registry_ptr and self._pager_dll:
            return self._pager_dll.ct_weight_registry_resident_count(self._registry_ptr)
        return sum(1 for s in self._slices.values() if s.state == CtSliceState.RESIDENT)

    @property
    def total_slices(self) -> int:
        if self._use_native and self._registry_ptr and self._pager_dll:
            return self._pager_dll.ct_weight_registry_slice_count(self._registry_ptr)
        return len(self._slices)

    def close(self) -> None:
        if self._use_native and self._registry_ptr and self._pager_dll:
            self._pager_dll.ct_weight_registry_free(self._registry_ptr)
            self._registry_ptr = None
            self._use_native = False

    def __enter__(self) -> CautreoWeightPager:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Sprint R5: Re-export Cartographer & Dynamic Sparse Models
# ---------------------------------------------------------------------------
try:
    from integration.cautreo_cartographer import (
        CANONICAL_DOMAIN_PROBES,
        AtlasNode,
        CautreoCartographer,
        CoarseKnowledgeAtlas,
    )
except ImportError:
    from cautreo_cartographer import (  # type: ignore
        CANONICAL_DOMAIN_PROBES,
        AtlasNode,
        CautreoCartographer,
        CoarseKnowledgeAtlas,
    )

__all__ = [
    "AtlasNode",
    "CANONICAL_DOMAIN_PROBES",
    "CautreoCartographer",
    "CautreoContextMemory",
    "CautreoMemoryItem",
    "CautreoMemoryKind",
    "CautreoScoreGraph",
    "CautreoScoreType",
    "CautreoWeightPager",
    "CoarseKnowledgeAtlas",
    "CtQuantType",
    "CtSliceState",
    "WeightSliceInfo",
    "is_cautreo_available",
    "is_native_cautreo_available",
    "is_native_pager_available",
]

