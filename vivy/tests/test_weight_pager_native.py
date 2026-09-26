"""
Native C Weight Pager tests — real GGUF I/O, real matvec compute.

Requires cautreo_pager.dll. Skips when unavailable.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from integration.cautreo_binding import (
    CautreoWeightPager,
    is_native_pager_available,
)

pytestmark = pytest.mark.skipif(
    not is_native_pager_available(),
    reason="cautreo_pager.dll not available",
)


# ---------------------------------------------------------------------------
# Helpers: write synthetic GGUF fixtures
# ---------------------------------------------------------------------------


def _write_u32(f, v: int) -> None:
    f.write(struct.pack("<I", v))


def _write_u64(f, v: int) -> None:
    f.write(struct.pack("<Q", v))


def _write_string_v2(f, s: str) -> None:
    b = s.encode("utf-8")
    _write_u64(f, len(b))
    f.write(b)


def _write_gguf_f32(
    path: Path, tensors: list[tuple[str, tuple[int, ...], list[float]]]
) -> None:
    """Write a minimal GGUF v2 file with F32 tensors."""
    with open(path, "wb") as f:
        _write_u32(f, 0x46554747)
        _write_u32(f, 2)
        _write_u64(f, len(tensors))
        _write_u64(f, 0)

        data_offset = 0
        for name, dims, _data in tensors:
            _write_string_v2(f, name)
            _write_u32(f, len(dims))
            for d in dims:
                _write_u64(f, d)
            _write_u32(f, 0)  # CT_GGML_F32
            _write_u64(f, data_offset)
            n_el = 1
            for d in dims:
                n_el *= d
            data_offset += n_el * 4

        cur = f.tell()
        aligned = (cur + 31) // 32 * 32
        for _ in range(cur, aligned):
            f.write(b"\x00")

        for _, dims, data in tensors:
            n_el = 1
            for d in dims:
                n_el *= d
            f.write(struct.pack(f"<{n_el}f", *data[:n_el]))


def _write_gguf_q8_0(path: Path) -> None:
    """Write a GGUF with a single Q8_0 tensor (32 elements, scale=1.0, qs=1)."""
    block = struct.pack("<e", 1.0) + bytes([1] * 32)  # f16 scale + 32 int8
    with open(path, "wb") as f:
        _write_u32(f, 0x46554747)
        _write_u32(f, 2)
        _write_u64(f, 1)
        _write_u64(f, 0)
        _write_string_v2(f, "q8t")
        _write_u32(f, 1)
        _write_u64(f, 32)
        _write_u32(f, 8)  # CT_GGML_Q8_0
        _write_u64(f, 0)
        cur = f.tell()
        aligned = (cur + 31) // 32 * 32
        for _ in range(cur, aligned):
            f.write(b"\x00")
        f.write(block)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_registry_init_and_free(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("t", (2, 2), [1.0, 2.0, 3.0, 4.0])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        assert pager._use_native is True
        assert pager.total_slices == 1


def test_build_from_gguf_small_fixture(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(
        gguf,
        [
            ("blk.0.ffn_gate", (2, 2), [1, 2, 3, 4]),
            ("blk.0.ffn_up", (3, 2), [5, 6, 7, 8, 9, 10]),
        ],
    )

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        assert pager.total_slices == 2
        assert "blk.0.ffn_gate" in pager._slices
        assert "blk.0.ffn_up" in pager._slices


def test_page_in_reads_real_bytes(tmp_path: Path) -> None:
    data = [1.5, -2.5, 3.75, 0.25]
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("test_tensor", (2, 2), data)])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        assert pager.page_in("test_tensor") is True
        assert pager.resident_slice_count == 1
        assert pager.get_ram_usage_mb() > 0


def test_page_in_ram_budget_enforcement(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(
        gguf,
        [
            ("a", (4, 4), [0.0] * 16),
            ("b", (4, 4), [0.0] * 16),
            ("c", (4, 4), [0.0] * 16),
        ],
    )

    with CautreoWeightPager(model_path=str(gguf), max_ram_budget_bytes=150) as pager:
        pager.page_in("a")
        pager.page_in("b")
        assert pager.resident_slice_count <= 2
        assert pager.get_ram_usage_mb() * 1024 * 1024 <= 150

        pager.page_in("c")
        assert pager.resident_slice_count <= 2
        assert pager.get_ram_usage_mb() * 1024 * 1024 <= 150


def test_page_out_frees_memory(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("t", (2, 2), [1, 2, 3, 4])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        pager.page_in("t")
        assert pager.get_ram_usage_mb() > 0
        assert pager.page_out("t") is True
        assert pager.get_ram_usage_mb() == 0
        assert pager.resident_slice_count == 0


def test_sparse_page_in_topk_ratio(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("t", (4, 2), [1, 2, 3, 4, 5, 6, 7, 8])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        assert pager.sparse_page_in("t", 0.5) is True
        assert pager.resident_slice_count == 1
        assert pager.get_ram_usage_mb() > 0


def test_stream_compute_matvec(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("W", (2, 3), [1, 2, 3, 4, 5, 6])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        out = pager.stream_compute("W", [1.0, 1.0, 1.0])
        assert len(out) == 2
        assert abs(out[0] - 6.0) < 1e-4
        assert abs(out[1] - 15.0) < 1e-4


def test_stream_compute_quantized_q8_0(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_q8_0(gguf)

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        out = pager.stream_compute("q8t", [1.0] * 32)
        assert len(out) == 1
        assert abs(out[0] - 32.0) < 1.0


def test_double_page_in_idempotent(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("t", (2, 2), [1, 2, 3, 4])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        pager.page_in("t")
        ram1 = pager.get_ram_usage_mb()
        pager.page_in("t")
        ram2 = pager.get_ram_usage_mb()
        assert ram1 == ram2
        assert pager.resident_slice_count == 1


def test_invalid_slice_name_returns_error(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("t", (2, 2), [1, 2, 3, 4])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        assert pager.page_in("nonexistent") is False


def test_corrupt_gguf_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.gguf"
    bad.write_bytes(struct.pack("<I", 0xDEADBEEF) + b"\x00" * 20)

    pager = CautreoWeightPager(model_path=str(bad))
    assert pager._use_native is False


def test_sequential_page_in_cycle(tmp_path: Path) -> None:
    gguf = tmp_path / "t.gguf"
    _write_gguf_f32(gguf, [("t", (4, 4), [float(i) for i in range(16)])])

    with CautreoWeightPager(model_path=str(gguf)) as pager:
        for _ in range(10):
            pager.page_in("t")
            ram_in = pager.get_ram_usage_mb()
            assert ram_in > 0
            pager.page_out("t")
            assert pager.get_ram_usage_mb() == 0
