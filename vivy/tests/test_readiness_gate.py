"""test_readiness_gate.py — Regression cho readiness gate OVERALL VERDICT.

[REGRESSION 27/09/2026] `verify_codex_remediations()` từng ghi
``results["qwen_coder_artifact_present"] = False`` cho một check đã bị
[ISOLATED 26/09/2026] (gguf qwen2.5-coder không tồn tại trên đĩa). Vì ``main()``
chấm bằng ``all(sub_results.values())``, key chết luôn False đó làm FAIL nhóm
Codex Remediation và OVERALL VERDICT vĩnh viễn dù mọi check thật đều xanh.

Test này bắt hai điều: check đã loại bỏ KHÔNG được quay lại phép chấm điểm, và
mọi check còn lại phải PASS — tức là readiness gate phải xanh được.
"""

from scripts.verify_vivy_cautreo_readiness import verify_codex_remediations

# Check đã [ISOLATED 26/09/2026] — không bao giờ được emit lại vào results.
RETIRED_CHECKS = frozenset({"qwen_coder_artifact_present"})


def test_retired_qwen_coder_check_is_not_scored():
    """Check đã bị loại bỏ thì không được nằm trong phép chấm điểm."""
    results = verify_codex_remediations()

    leaked = RETIRED_CHECKS.intersection(results)
    assert not leaked, (
        f"Check đã [ISOLATED 26/09/2026] vẫn còn trong results: {sorted(leaked)}. "
        "Key này luôn False nên sẽ làm FAIL OVERALL VERDICT vĩnh viễn — "
        "xem verify_codex_remediations() chú thích [FIXED 27/09/2026]."
    )


def test_codex_remediations_pass_with_live_checks_only():
    """Mọi check thật phải PASS — tất định gate xanh được nếu chỉ còn check thật."""
    results = verify_codex_remediations()

    assert results, "verify_codex_remediations() không trả về check nào"
    assert all(results.values()), (
        "Có check thật đang FAIL: "
        f"{sorted(k for k, v in results.items() if not v)}"
    )
    assert "n_core_boundary_declared" in results
    assert "cautreo_dll_available" in results
