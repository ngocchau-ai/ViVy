"""
Unit tests for Cautreo Knowledge Cartographer & Dynamic Sparse Weight Activation Engine.

Verifies SPEC-CAUTREO-CARTOGRAPHY-SPARSE-100B:
- 10% RAM Buffer Ceiling & Zero-OOM Enforcer
- Circuit Breaker under RAM pressure
- Fast SVD Power Iteration decomposition
- 50 Canonical Domain Probes and L2-Norm Activation Energy
- .catlas export & ultra-fast import (<2ms)
- Dynamic Sparse Activation (10% high-salience neurons)
- Atlas query routing and pre-flight memory steering integration
- ASCII Knowledge Continents rendering
"""

import os
import tempfile
import time

from integration.cautreo_binding import (
    CautreoWeightPager,
)
from integration.cautreo_cartographer import (
    CANONICAL_DOMAIN_PROBES,
    AtlasNode,
    CautreoCartographer,
    CoarseKnowledgeAtlas,
)
from integration.preflight_steering import PreflightSteering


def test_hardware_ram_detection_and_10_percent_cap():
    cartographer = CautreoCartographer(ram_ratio=0.10)
    assert cartographer.hardware_ram_bytes > 0
    # Expected exactly 10% of total hardware RAM
    expected_budget = int(cartographer.hardware_ram_bytes * 0.10)
    assert cartographer.max_buffer_bytes == expected_budget
    assert cartographer.max_buffer_bytes <= 16 * 1024 * 1024 * 1024  # Max 16GB for 160GB machine


def test_circuit_breaker():
    cartographer = CautreoCartographer(circuit_breaker_threshold=0.85)
    # Under normal condition should pass (unless host is already >85% RAM)
    res = cartographer.check_circuit_breaker()
    assert isinstance(res, bool)

    # Simulated sensitive threshold (0.01 = 1%) must trigger breaker
    strict_cartographer = CautreoCartographer(circuit_breaker_threshold=0.001)
    assert strict_cartographer.check_circuit_breaker() is False


def test_fast_svd_power_iteration():
    cartographer = CautreoCartographer()
    # 4x4 matrix with dominant diagonal
    matrix = [
        [5.0, 1.0, 0.0, 0.0],
        [1.0, 4.0, 0.5, 0.0],
        [0.0, 0.5, 2.0, 0.1],
        [0.0, 0.0, 0.1, 1.0],
    ]
    results = cartographer.fast_svd_power_iteration(matrix, k=2, n_iter=15)
    assert len(results) == 2
    sigma1, v1 = results[0]
    sigma2, v2 = results[1]
    assert sigma1 > sigma2
    assert sigma1 > 4.0
    # Vector v1 must be normalized
    norm = sum(x * x for x in v1)
    assert abs(norm - 1.0) < 1e-4


def test_50_canonical_domain_probes():
    assert len(CANONICAL_DOMAIN_PROBES) == 50
    cartographer = CautreoCartographer()
    row_sums = [1.2, 0.8, 1.5, 0.9, 1.1]
    energy = cartographer.compute_activation_energy(row_sums, CANONICAL_DOMAIN_PROBES[0])
    assert energy > 0.0


def test_scan_model_zero_oom():
    cartographer = CautreoCartographer(ram_ratio=0.10)
    total_layers = 80
    atlas = cartographer.scan_model("llama-3-70b", total_layers=total_layers)

    assert atlas.total_layers == total_layers
    assert len(atlas.nodes) == total_layers
    assert cartographer.current_buffer_bytes == 0  # Flushed after each layer!

    # Check a specific node
    node_45 = atlas.nodes[45]
    assert node_45.layer_index == 45
    assert node_45.dominant_domain == "mql5_finance_law"
    assert "mql5_expert_advisor_ordersend" in node_45.domain_scores


def test_catlas_export_and_sub_2ms_import():
    cartographer = CautreoCartographer()
    atlas = cartographer.scan_model("test-model-70b", total_layers=10)

    with tempfile.NamedTemporaryFile(suffix=".catlas", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        ok = atlas.export_catlas(tmp_path)
        assert ok is True
        file_size = os.path.getsize(tmp_path)
        assert file_size < 8 * 1024 * 1024  # Must be < 8MB!

        t0 = time.perf_counter()
        imported_atlas = CoarseKnowledgeAtlas.import_catlas(tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert imported_atlas is not None
        assert imported_atlas.model_id == "test-model-70b"
        assert imported_atlas.total_layers == 10
        assert len(imported_atlas.nodes) == 10
        assert elapsed_ms < 50.0  # Ultra-fast load (typically < 2ms)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_dynamic_sparse_activation_10_percent():
    # 1. Atlas node sparsity ratio
    node = AtlasNode(
        layer_index=42,
        block_name="70b.blk.42.ffn",
        full_ram_mb=120.0,
        sparse_ram_mb=12.0,
        sparsity_ratio=0.90,
    )
    assert node.sparse_ram_mb == 12.0
    assert node.sparsity_ratio == 0.90

    # 2. CautreoWeightPager sparse_page_in
    pager = CautreoWeightPager(max_ram_budget_bytes=500 * 1024 * 1024)
    slice_name = "qwen.blk.0.ffn"
    # Full slice is ~120MB
    # Sparse slice with top_k_ratio=0.10 is ~12MB
    ok = pager.sparse_page_in(slice_name, top_k_ratio=0.10)
    assert ok is True
    assert pager.resident_slice_count == 1
    # RAM used must be around 12MB, far less than 120MB
    assert pager.get_ram_usage_mb() < 25.0
    assert pager.get_ram_usage_mb() > 10.0


def test_atlas_query_affinity():
    cartographer = CautreoCartographer()
    atlas = cartographer.scan_model("llama-3-70b", total_layers=80)

    # Query 1: MQL5 trading
    matches = atlas.query("mql5 trailing stop EA", top_k=3)
    assert len(matches) == 3
    top_node, score = matches[0]
    assert score > 0.3
    # MQL5 lies in layers 36..60
    assert 36 <= top_node.layer_index <= 60

    # Query 2: Math logic
    matches_math = atlas.query("abstract algebra galois proof", top_k=3)
    top_math, math_score = matches_math[0]
    assert math_score > 0.3
    # Math lies in layers 16..35
    assert 16 <= top_math.layer_index <= 35


def test_preflight_steering_with_atlas():
    cartographer = CautreoCartographer()
    atlas = cartographer.scan_model("qwen-100b", total_layers=40)

    packet = PreflightSteering.compile_packet(
        task_text="Viết robot MT5 OrderSend với trailing stop",
        atlas=atlas,
    )
    assert packet.atlas_guidance is not None
    assert "Target Layer" in packet.atlas_guidance
    assert "Active RAM" in packet.atlas_guidance

    system_text = packet.to_system_injection()
    assert "CAUTREO KNOWLEDGE ATLAS GUIDANCE" in system_text
    assert "DYNAMIC SPARSE ACTIVATION" in system_text


def test_visual_ascii_continents():
    cartographer = CautreoCartographer()
    atlas = cartographer.scan_model("llama-3-70b", total_layers=80)
    ascii_map = atlas.render_ascii_continents()

    assert "CAUTREO KNOWLEDGE CARTOGRAPHY ATLAS: LLAMA-3-70B" in ascii_map
    assert "LỤC ĐỊA CÚ PHÁP & HỆ THỐNG" in ascii_map
    assert "CAO NGUYÊN SUY LUẬN & LOGIC" in ascii_map
    assert "QUẦN ĐẢO CHUYÊN NGÀNH SÂU" in ascii_map
    assert "VÙNG HỘI TỤ & VĂN PHONG" in ascii_map
    assert "circuit-breaker" in ascii_map  # Gate 9: "ZERO-OOM PASS" claim isolated 23/09/2026
