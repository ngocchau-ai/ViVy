"""
Unit tests for Cautreo Weight Paging & Slicing Controller (Sprint R4).
"""

from integration.cautreo_binding import (
    CautreoWeightPager,
    CtSliceState,
)


def test_weight_pager_init_and_default_slices():
    pager = CautreoWeightPager(model_id="qwen2.5-coder-14b")
    assert pager.total_slices == 48
    assert pager.resident_slice_count == 0
    assert pager.get_ram_usage_mb() == 0.0


def test_weight_pager_page_in_and_out():
    pager = CautreoWeightPager(max_ram_budget_bytes=500 * 1024 * 1024)
    slice_name = "qwen.blk.0.ffn"

    # Page in
    ok = pager.page_in(slice_name)
    assert ok is True
    assert pager.resident_slice_count == 1
    assert pager.get_ram_usage_mb() > 100.0

    # Page out
    ok_out = pager.page_out(slice_name)
    assert ok_out is True
    assert pager.resident_slice_count == 0
    assert pager.get_ram_usage_mb() == 0.0


def test_weight_pager_ram_budget_eviction():
    # Set tight RAM budget: 250MB (each slice is ~120MB, so max 2 slices fit)
    pager = CautreoWeightPager(max_ram_budget_bytes=250 * 1024 * 1024)

    pager.page_in("qwen.blk.0.ffn")
    pager.page_in("qwen.blk.1.ffn")
    assert pager.resident_slice_count == 2
    assert pager.get_ram_usage_mb() <= 250.0

    # Paging in a 3rd slice must evict the LRU slice (blk.0)
    pager.page_in("qwen.blk.2.ffn")
    assert pager.resident_slice_count == 2
    assert pager.get_ram_usage_mb() <= 250.0
    assert pager._slices["qwen.blk.0.ffn"].state == CtSliceState.ON_DISK
    assert pager._slices["qwen.blk.2.ffn"].state == CtSliceState.RESIDENT


def test_weight_pager_stream_compute():
    pager = CautreoWeightPager()
    input_vector = [1.0, 2.0, 3.0]
    output_vector = pager.stream_compute("qwen.blk.10.ffn", input_vector)

    assert len(output_vector) == 3
    assert output_vector[0] > input_vector[0]
    assert pager._slices["qwen.blk.10.ffn"].state == CtSliceState.RESIDENT
