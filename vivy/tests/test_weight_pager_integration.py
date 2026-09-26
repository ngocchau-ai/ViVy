"""
Integration tests for Cautreo Weight Pager — real 72B GGUF slices.

Skips when the Qwen2-VL-72B GGUF file is not present on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from integration.cautreo_binding import (
    CautreoWeightPager,
    is_native_pager_available,
)

MODEL_72B = Path("D:/models/qwen2-vl-72b/Qwen2-VL-72B-Instruct-Q4_K_M.gguf")
GEMMA_4B = Path("D:/models/gemma4-e4b/vivy-gemma-e4b-q4km.gguf")

pytestmark = [
    pytest.mark.skipif(not is_native_pager_available(), reason="cautreo_pager.dll missing"),
]


def _require_file(p: Path) -> None:
    if not p.is_file():
        pytest.skip(f"Model file not found: {p}")


def test_page_in_real_72b_slice() -> None:
    _require_file(MODEL_72B)

    with CautreoWeightPager(model_path=str(MODEL_72B)) as pager:
        assert pager._use_native is True
        assert pager.total_slices > 0

        # Find first FFN-like slice name
        slice_names = list(pager._slices.keys())
        first = slice_names[0]
        assert pager.page_in(first) is True
        assert pager.resident_slice_count >= 1
        pager.page_out(first)


def test_ram_never_exceeds_budget_72b() -> None:
    _require_file(MODEL_72B)
    budget = 2 * 1024 * 1024 * 1024  # 2GB

    with CautreoWeightPager(model_path=str(MODEL_72B), max_ram_budget_bytes=budget) as pager:
        names = list(pager._slices.keys())[:80]
        for name in names:
            pager.page_in(name)
            ram = pager.get_ram_usage_mb() * 1024 * 1024
            assert ram <= budget + 1024, f"RAM {ram} exceeded budget {budget}"


def test_sparse_activation_72b() -> None:
    _require_file(MODEL_72B)

    with CautreoWeightPager(model_path=str(MODEL_72B)) as pager:
        names = list(pager._slices.keys())
        assert names
        assert pager.sparse_page_in(names[0], 0.05) is True


def test_gemma4_e4b_slices() -> None:
    _require_file(GEMMA_4B)

    with CautreoWeightPager(model_path=str(GEMMA_4B)) as pager:
        assert pager._use_native is True
        assert pager.total_slices > 0

        names = list(pager._slices.keys())[:5]
        for name in names:
            pager.page_in(name)
        assert pager.resident_slice_count >= 1


def test_full_pipeline_sparse_compute() -> None:
    _require_file(GEMMA_4B)

    with CautreoWeightPager(model_path=str(GEMMA_4B)) as pager:
        names = list(pager._slices.keys())
        assert names

        # Sparse page-in first slice
        first = names[0]
        pager.sparse_page_in(first, 0.10)

        # Get shape info
        info = pager._slices[first]
        if info.n_dims >= 2 and len(info.dims) >= 2:
            cols = int(info.dims[-1])
            input_vec = [1.0] * min(cols, 64)
            out = pager.stream_compute(first, input_vec)
            assert isinstance(out, list)
            assert len(out) > 0
