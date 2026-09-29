"""test_model_catalog.py — Unit tests for autonomous model discovery & task archetype classification."""

from orchestrator.model_catalog import (
    ModelCatalogScanner,
    TaskArchetype,
    build_catalog_digest,
    classify_task_archetype,
)


def test_model_catalog_scanner():
    # Scan models directory
    scanner = ModelCatalogScanner()
    catalog = scanner.scan()

    assert catalog.orchestrator_core == "gemma4-e4b"
    assert "gemma4-e4b" in catalog.models
    assert "qwen2.5-coder-7b-instruct" in catalog.models or "qwen2.5-coder:7b" in catalog.models

    # Test archetype mapping
    # [REROUTED 26/09/2026] coding archetype now targets a model that exists on disk
    # (qwen2.5-coder gguf was never present). See model_manifest.json
    # task_archetype_mapping_note_2026-09-26.
    coding_model = catalog.get_specialist_for_task(TaskArchetype.NATIVE_SYSTEM_CODING)
    assert coding_model == "gemma4-e4b"


def test_classify_task_archetype_explicit_signals():
    scanner = ModelCatalogScanner()
    catalog = scanner.scan()

    # Explicit C-ABI signal
    p1 = "[TASK: C_ABI] Xây dựng struct ct_context_memory"
    arch1, model1, exp1 = classify_task_archetype(p1, catalog)
    assert arch1 == TaskArchetype.NATIVE_SYSTEM_CODING
    assert model1 == "gemma4-e4b"

    # Explicit Plan signal
    p2 = "[TASK: PLAN] Thiết kế kiến trúc phân rã 91s"
    arch2, model2, exp2 = classify_task_archetype(p2, catalog)
    assert arch2 == TaskArchetype.ARCH_SPEC_AND_PLAN
    assert model2 == "gemma4-e4b"


def test_classify_task_archetype_implicit_context():
    scanner = ModelCatalogScanner()
    catalog = scanner.scan()

    # Implicit low-level coding
    p1 = "Cần viết C-ABI và ctypes bindings cho cautreo.dll thao tác con trỏ pointer malloc"
    arch1, model1, exp1 = classify_task_archetype(p1, catalog)
    assert arch1 == TaskArchetype.NATIVE_SYSTEM_CODING
    assert model1 == "gemma4-e4b"

    # Implicit general cognitive plan
    p2 = "Phân tích và đánh giá rủi ro chiến lược sản phẩm"
    arch2, model2, exp2 = classify_task_archetype(p2, catalog)
    assert arch2 == TaskArchetype.ARCH_SPEC_AND_PLAN
    assert model2 == "gemma4-e4b"


def test_build_catalog_digest():
    scanner = ModelCatalogScanner()
    catalog = scanner.scan()
    digest = build_catalog_digest(catalog)

    assert "[VIVY LOCAL MODEL REPOSITORY" in digest
    assert "COGNITIVE SOUL" in digest
    assert "SPECIALIST" in digest
