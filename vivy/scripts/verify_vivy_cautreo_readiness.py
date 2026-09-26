"""verify_vivy_cautreo_readiness.py

Comprehensive end-to-end verification of ViVy Final and Cautreo Engine:
1. Verification of Codex Findings Remediation (P1 & P2 fixes)
2. Cautreo C-ABI In-Process Memory & Score Graph
   # [ISOLATED 23/09/2026] prior: "0ms In-Process"
3. Parallel Decomposition & Compression Input Pipeline
4. ViVy Inference Loop Context Budget (2048 window) & Intuition Digest
5. ViVy Dream Engine (LUCID_STANDBY) Cycle
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the packaged Vivy Final core to path. The old unitary-reasoner path was
# a stale layout assumption and made this readiness entrypoint unusable.
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
# Compatibility bridge: the packaged Final track still imports the shared
# OpenAI-compatible LLM client from the active unitary-reasoner track.
sys.path.insert(0, str(WORKSPACE_ROOT.parent / "unitary-reasoner"))
sys.path.insert(0, str(WORKSPACE_ROOT / "core"))

from engine.dream_engine import VivyDreamEngine  # noqa: E402
from integration.cautreo_binding import (  # noqa: E402
    CautreoContextMemory,
    CautreoScoreGraph,
    is_cautreo_available,
)
from integration.multimodal_adapter import MultimodalInput  # noqa: E402
from integration.parallel_context_pipeline import ParallelContextPipeline  # noqa: E402
from integration.vivy_inference_loop import (  # noqa: E402
    ChatMessage,
    VivyInferenceLoop,
)


def verify_codex_remediations() -> dict[str, bool]:
    results = {}

    # Check 1: Qwen2.5-Coder model artifact presence
    coder_path = WORKSPACE_ROOT / "models" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    exists = coder_path.is_file()
    size_mb = (coder_path.stat().st_size / (1024 * 1024)) if exists else 0
    results["qwen_coder_artifact_present"] = exists and size_mb > 4000
    print(f"[CODEX-P1-1] Qwen2.5-Coder artifact: {'FOUND' if exists else 'MISSING'} ({size_mb:.1f} MB)")

    # Check 2: ElasticNCore audit boundary
    from engine.elastic_n_core import ElasticNCore
    n_core = ElasticNCore(n_min=2, n_max=4, hidden_dim=64)
    results["n_core_boundary_declared"] = hasattr(n_core, "_AUDIT_NOTICE")
    print(f"[CODEX-P1-2] ElasticNCore audit boundary: {'VERIFIED' if results['n_core_boundary_declared'] else 'MISSING'}")

    # Check 3: Cautreo DLL availability
    dll_available = is_cautreo_available()
    results["cautreo_dll_available"] = dll_available
    # [ISOLATED 23/09/2026] prior: 'YES (0ms RAM)' — Gate 9: no latency claim.
    print(f"[CODEX-P1-3] Cautreo C-ABI DLL available: {'YES (in-process)' if dll_available else 'FALLBACK'}")

    return results


def verify_cautreo_memory_and_digest() -> dict[str, bool]:
    results = {}
    with CautreoContextMemory() as mem:
        # [ISOLATED 23/09/2026] prior: "Error repeat rate must strictly remain 0%"
        mem.store_constraint("inv_epistemic", "Dampen repeated errors (VM-11)")
        mem.store_task("task_e2e", "Execute verification of ViVy and Cautreo readiness")
        mem.store_hard_fact("fact_cpu", "Running on local CPU with 2048 context window limit")

        digest = mem.build_intuition_digest()
        results["digest_generated"] = bool(digest and "VM-11" in digest and "Execute verification" in digest)
        print(f"[CAUTREO-MEM] Intuition Digest built:\n{digest}\n")

        # Test score graph
        from integration.cautreo_binding import CautreoScoreType
        graph = CautreoScoreGraph()
        graph.update(CautreoScoreType.TASK_PROGRESS, 0.95, 0.99)
        score = graph.get_score(CautreoScoreType.TASK_PROGRESS)
        results["score_graph_working"] = score > 0.50
        print(f"[CAUTREO-GRAPH] Score graph TASK_PROGRESS: {score:.2f}")

    return results


def verify_parallel_context_pipeline() -> dict[str, bool]:
    results = {}
    with CautreoContextMemory() as mem:
        pipeline = ParallelContextPipeline(
            activation_threshold_chars=800,
            max_segment_chars=600,
            context_memory=mem,
        )

        long_task = (
            "# COMPREHENSIVE ARCHITECTURE SPECIFICATION FOR TRADING AUTOMATION\n\n"
            "## OBJECTIVE\n"
            "Integrate multi-timeframe price action analysis with zero programmatic filter guards.\n\n"
            "## CONSTRAINTS\n"
            "- ViVy is the sole soul controlling execution\n"
            "- CPU inference window is strictly 2048 tokens\n"
            "- Do not add R:R guards in Python wrapper\n\n"
            "## DETAILED EXECUTION PLAN\n"
            + ("Step-by-step detailed operational checklist for the trading engine. " * 30)
            + "\n\n```python\ndef execute_order(symbol, action):\n    return mt5.order_send(symbol, action)\n```\n"
        )

        proc = pipeline.process(long_task, task_id="spec_verification_01")
        results["pipeline_active"] = proc.is_processed
        results["has_overview"] = bool(proc.compressed_digest)
        results["chunks_stored"] = proc.total_segments > 1
        results["fused_prompt_valid"] = "[PARALLEL_INPUT_PIPELINE" in proc.fused_prompt

        print(f"[PARALLEL-PIPELINE] Input length: {len(long_task)} chars")
        print(f"[PARALLEL-PIPELINE] Decomposed into: {proc.total_segments} chunks")
        print(f"[PARALLEL-PIPELINE] Overview preview:\n{proc.compressed_digest}\n")
        print(f"[PARALLEL-PIPELINE] Stored segment IDs: {proc.remaining_segment_ids}")

    return results


def verify_vivy_inference_loop_readiness() -> dict[str, bool]:
    results = {}
    from unittest.mock import MagicMock

    from integration.llama_cpp_bridge import LlamaCppBridge
    from integration.session_manager import SessionManager

    mock_bridge = MagicMock(spec=LlamaCppBridge)
    mock_sessions = MagicMock(spec=SessionManager)

    with CautreoContextMemory() as mem:
        mem.store_constraint("inv_readiness", "Verify all subsystems before declaring complete")
        pipeline = ParallelContextPipeline(
            activation_threshold_chars=800,
            max_segment_chars=600,
            context_memory=mem,
        )

        loop = VivyInferenceLoop(
            bridge=mock_bridge,
            session_manager=mock_sessions,
            context_memory=mem,
            parallel_pipeline=pipeline,
        )

        # Send a long input to trigger both decomposition & digest injection
        long_prompt = (
            "K\u1ebf ho\u1ea1ch tri\u1ec3n khai ki\u1ebfn tr\u00fac 91s:\n"
            "Y\u00eau c\u1ea7u x\u1eed l\u00fd to\u00e0n di\u1ec7n c\u00e1c module sau:\n"
            + ("Module ph\u00e2n t\u00edch th\u1ecb tr\u01b0\u1eddng k\u1ebft n\u1ed1i tr\u1ef1c ti\u1ebfp Cautreo DLL. " * 25)
        )

        messages = loop._build_messages(
            modal_input=MultimodalInput(text=long_prompt),
            history=[ChatMessage(role="user", content="hello"), ChatMessage(role="assistant", content="hi")],
        )

        sys_msg = messages[0].content
        user_msg = messages[-1].content

        results["digest_in_system_prompt"] = "## VIVY INTUITION DIGEST" in sys_msg
        results["fusion_in_user_prompt"] = "[PARALLEL_INPUT_PIPELINE" in user_msg

        print(f"[VIVY-LOOP] Digest in system prompt: {results['digest_in_system_prompt']}")
        print(f"[VIVY-LOOP] Parallel fusion in user prompt: {results['fusion_in_user_prompt']}")

    return results


def verify_vivy_dream_engine() -> dict[str, bool]:
    results = {}
    with CautreoContextMemory() as mem:
        mem.store_summary("summary_turn_1", "Hoàn thành phân tích kiến trúc 91s và kiểm thử Cautreo C-ABI")
        dream_engine = VivyDreamEngine(context_memory=mem)
        cycle = dream_engine.run_dream_cycle(
            task_id="verification_readiness",
            idle_duration_s=2.5,
        )

        results["dream_success"] = cycle.success
        results["standby_mode"] = cycle.status == "LUCID_STANDBY"
        results["digest_persisted"] = bool(mem.get_summary("vivy_intuition_digest_current"))
        results["synced_2brain"] = cycle.synced_2brain

        print(f"[DREAM-ENGINE] Cycle success: {cycle.success}")
        print(f"[DREAM-ENGINE] Standby mode: {cycle.status}")
        print(f"[DREAM-ENGINE] Invariants promoted: {cycle.invariants_promoted}")
        print(f"[DREAM-ENGINE] Digest persisted in Cautreo RAM: {results['digest_persisted']}")
        print(f"[DREAM-ENGINE] 2brain durable sync: {results['synced_2brain']}")

    return results


def main() -> int:
    print("=" * 60)
    print("VERIFICATION SUITE: VIVY FINAL & CAUTREO ENGINE READINESS")
    print("=" * 60)

    checks = []
    checks.append(("Codex Remediation Check", verify_codex_remediations()))
    checks.append(("Cautreo Memory & Score Graph Check", verify_cautreo_memory_and_digest()))
    checks.append(("Parallel Context Pipeline Check", verify_parallel_context_pipeline()))
    checks.append(("ViVy Inference Loop Check", verify_vivy_inference_loop_readiness()))
    checks.append(("ViVy Dream Engine Check", verify_vivy_dream_engine()))

    print("\n" + "=" * 60)
    print("SUMMARY RESULTS:")
    print("=" * 60)

    all_pass = True
    for name, sub_results in checks:
        passed = all(sub_results.values())
        if not passed:
            all_pass = False
        status_str = "PASS [ALL VERIFIED]" if passed else "FAIL"
        print(f"[{status_str}] {name}")
        for k, v in sub_results.items():
            print(f"   - {k}: {'PASS' if v else 'FAIL'}")

    print("=" * 60)
    if all_pass:
        print("OVERALL VERDICT: READINESS SUBSYSTEM CHECKS PASS; PRODUCT SEMANTIC PARITY REMAINS UNVERIFIED.")
        return 0
    else:
        print("OVERALL VERDICT: ONE OR MORE CHECKS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
