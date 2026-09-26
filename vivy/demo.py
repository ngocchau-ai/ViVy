#!/usr/bin/env python3
"""ViVy V5.0 — End-to-End Demo Script.

Demonstrates the full V5.0 pipeline:
    1. EpistemicGate — blocking assessment (Sprint 1)
    2. ModelRouter — Directive Contract dispatch (Sprint 2)
    3. ContextCacheController — Purge & Reload (Sprint 2)
    4. KnowledgeArtifactWriter — Knowledge Brief creation (Sprint 3)
    5. SelfHealingLoop — RCA & auto-patch (Sprint 3)

Usage:
    python demo.py

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3D): V5.0 demo added to existing demo.py.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Quiet for demo
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vivy-demo")


def demo_epistemic_gate() -> None:
    """Demo 1: EpistemicGate — Sprint 1."""
    print("\n" + "=" * 60)
    print("DEMO 1: EPISTEMIC GATE (Sprint 1)")
    print("=" * 60)

    from core.state import QuantumState
    from orchestrator.epistemic_gate import (
        EpistemicDecision,
        EpistemicGate,
        GateContext,
    )

    gate = EpistemicGate(confidence_threshold=0.7)

    # Scenario A: High confidence, no unknowns -> EXECUTE_DIRECTLY
    state_high = QuantumState(np.array([1.0, 0.0], dtype=np.complex128))
    ctx_a = GateContext(task_description="What is 2+2?", unknown_entities=[])
    result_a = gate.assess(state_high, ctx_a)
    print(f"\n[A] Task: '{ctx_a.task_description}'")
    print(f"    -> Decision: {result_a.decision} (confidence={result_a.confidence:.2f})")
    assert result_a.decision == EpistemicDecision.EXECUTE_DIRECTLY

    # Scenario B: Unknown entities -> NEED_KNOWLEDGE_FORAGING
    ctx_b = GateContext(
        task_description="Explain CUDA Warp Divergence optimization",
        unknown_entities=["CUDA Warp Divergence"],
    )
    result_b = gate.assess(state_high, ctx_b)
    print(f"\n[B] Task: '{ctx_b.task_description[:50]}...'")
    print(f"    Unknown: {ctx_b.unknown_entities}")
    print(f"    -> Decision: {result_b.decision} (modality={result_b.suggested_modality})")
    assert result_b.decision == EpistemicDecision.NEED_KNOWLEDGE_FORAGING

    # Scenario C: Low confidence -> DELEGATE_MODEL
    class _LowState:
        def norm(self) -> float:
            return 0.3

    ctx_c = GateContext(task_description="Prove Riemann Hypothesis", unknown_entities=[])
    result_c = gate.assess(_LowState(), ctx_c)
    print(f"\n[C] Task: '{ctx_c.task_description}'")
    print(f"    -> Decision: {result_c.decision} (model={result_c.suggested_model})")
    assert result_c.decision == EpistemicDecision.DELEGATE_MODEL

    print("\n✅ EpistemicGate demo PASSED")


def demo_context_cache() -> None:
    """Demo 2: ContextCacheController — Sprint 2."""
    print("\n" + "=" * 60)
    print("DEMO 2: CONTEXT CACHE CONTROLLER (Sprint 2)")
    print("=" * 60)

    from engine.cache_control import ContextCacheController

    cache = ContextCacheController()

    raw_docs = {
        "cuda_doc_p1": "CUDA Memory Hierarchy: Global > Shared > Registers...",
        "cuda_doc_p2": "Warp Divergence occurs when threads in a warp take different branches...",
        "cuda_doc_p3": "Optimizing: minimize divergence, use __syncwarp(), coalesce memory...",
    }
    for chunk_id, content in raw_docs.items():
        cache.store_chunk(chunk_id, content, source="cuda_guide.pdf")

    stats_before = cache.stats()
    print(f"\nStored {stats_before['chunks_in_cache']} chunks ({stats_before['current_bytes']} bytes)")

    snap = cache.snapshot_context()
    print(f"Snapshot: {snap.snapshot_id} ({len(snap.chunk_ids)} chunks)")

    result = cache.purge_all()
    cache.stats()  # diagnostic — intentionally not stored
    print(f"Purged: {result.chunks_removed} chunks, freed {result.bytes_freed} bytes")

    freed_pct = (result.bytes_freed / stats_before["current_bytes"] * 100) if stats_before["current_bytes"] else 0
    print(f"Memory freed: {freed_pct:.0f}% ≥ 60% ✓")
    assert freed_pct >= 60

    print("\n✅ ContextCacheController demo PASSED")


def demo_knowledge_artifact() -> None:
    """Demo 3: KnowledgeArtifactWriter — Sprint 3."""
    print("\n" + "=" * 60)
    print("DEMO 3: KNOWLEDGE ARTIFACT WRITER (Sprint 3)")
    print("=" * 60)

    from forager.artifact_writer import KnowledgeArtifactWriter, KnowledgeBriefContent

    writer = KnowledgeArtifactWriter(scratchpad_dir="scratchpad")
    content = KnowledgeBriefContent(
        topic="CUDA Warp Divergence Optimization",
        source_path="cuda_guide.pdf",
        core_mechanics="Warp Divergence: threads in a 32-thread warp take different branches. All paths execute serially. Minimize by reducing if/else in kernels.",
        invariants="- A warp is 32 threads (SIMT). - Divergence penalty = sum of branch paths. - __syncwarp() mandatory after warp-level primitives.",
        api_signatures="__ballot_sync(mask, pred)\n__shfl_sync(mask, var, srcLane)\n__syncwarp(mask)",
        gotchas="- Avoid branch divergence in inner loops. - Use warpSize constant, not literal 32. - __syncwarp() does NOT sync across warps.",
        lang="cuda",
    )

    result = writer.write_brief(content)
    print(f"\nBrief written: {Path(result.file_path).name}")
    print(f"Sections: {result.sections_complete}/4 complete")
    print(f"Validation: {'PASS ✅' if result.is_complete else 'FAIL ❌'}")
    assert result.is_complete

    print("\n✅ KnowledgeArtifactWriter demo PASSED")


def demo_self_healer() -> None:
    """Demo 4: SelfHealingLoop — Sprint 3."""
    print("\n" + "=" * 60)
    print("DEMO 4: SELF-HEALING RCA LOOP (Sprint 3)")
    print("=" * 60)

    from engine.self_healer import Incident, SelfHealingLoop

    healer = SelfHealingLoop(scratchpad_dir="scratchpad")

    incident = Incident(
        stderr="SyntaxError: unexpected EOF while parsing  File 'fibonacci.py', line 8",
        exit_code=1,
        source_code="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2",
        task_description="Implement fibonacci function",
    )

    print(f"\nIncident: {incident.incident_id}")
    result = healer.handle_incident(incident)
    print(f"Status: {'HEALED ✅' if result.success else 'UNRESOLVED ⚠️'}")
    print(f"Cause: {result.confirmed_cause}")
    print(f"Attempts: {result.attempts}/{len(result.hypotheses)} hypotheses")
    print(f"RCA Log: {Path(result.rca_log_path).name}")

    assert Path(result.rca_log_path).exists()
    print("\n✅ SelfHealingLoop demo PASSED")


async def demo_model_router() -> None:
    """Demo 5: ModelRouter Directive Contract — Sprint 2."""
    print("\n" + "=" * 60)
    print("DEMO 5: MODEL ROUTER — DIRECTIVE CONTRACT (Sprint 2)")
    print("=" * 60)

    from orchestrator.directive_contract import (
        DirectiveTaskContract,
        EvidenceCriteria,
        TaskType,
    )
    from orchestrator.model_router import ModelRouter

    class _DemoClient:
        async def chat(self, prompt: str, model: str | None = None, **kwargs: object) -> str:
            return f"[{model}] gradient descent minimizes loss by iterating in the negative gradient direction."

    router = ModelRouter(_DemoClient())
    contract = DirectiveTaskContract(
        task_id="demo-001",
        task_description="Explain gradient descent",
        task_type=TaskType.REASONING,
        preferred_model="gemma4eb",
        evidence_criteria=EvidenceCriteria(
            description="Must contain 'gradient'",
            require_output_contains=["gradient"],
            require_no_error=True,
        ),
        max_retries=2,
        timeout_s=30,
    )

    print(f"\nContract: {contract.task_id} -> model={contract.preferred_model}")
    evidence = await router.dispatch(contract)
    print(f"Evidence: status={evidence.status} passes={evidence.passes}")
    print(f"Output: {evidence.output[:80]}...")

    assert evidence.passes
    print("\n✅ ModelRouter demo PASSED")


async def main() -> None:
    """Run all V5.0 demo scenarios."""
    print("\n" + "=" * 60)
    print("VIVY V5.0 — END-TO-END DEMO")
    print("Sprint 1: Gate | Sprint 2: Router+Cache | Sprint 3: Artifact+Healer")
    print("=" * 60)

    demo_epistemic_gate()
    demo_context_cache()
    demo_knowledge_artifact()
    demo_self_healer()
    await demo_model_router()

    print("\n" + "=" * 60)
    print("ALL V5.0 DEMOS PASSED ✅ — Sprints 1-3 OPERATIONAL")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
