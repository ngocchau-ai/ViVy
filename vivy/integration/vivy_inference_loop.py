"""
ViVy Inference Loop — Sprint 3 (HOH-VIVY-FINAL-V1).

Main pipeline: think → act → observe → learn.

                   ┌──────────────────────────────────┐
  User Input  ──►  │  MultimodalAdapter.encode()       │
                   └──────────────┬───────────────────┘
                                  │
                   ┌──────────────▼───────────────────┐
                   │  LlamaCppBridge.chat()            │  ← Gemma 4 E4B
                   │  (Epistemic Assessment Block)     │    Text+Vision+Audio
                   └──────────────┬───────────────────┘
                                  │
                   ┌──────────────▼───────────────────┐
                   │  EpistemicGate.check()            │  ← Sprint 1
                   │  EXECUTE | FORAGE | DELEGATE      │
                   └──────────────┬───────────────────┘
                                  │
                   ┌──────────────▼───────────────────┐
                   │  ToolDispatcher.dispatch()        │  ← Sprint 3
                   │  (if tool_calls present)          │
                   └──────────────┬───────────────────┘
                                  │
                   ┌──────────────▼───────────────────┐
                   │  GraphBridge.evaluate()           │  ← Sprint 2
                   │  HebbianRecall → Error-Dampening  │
                   │  CognitiveStateGraph.add_node()   │
                   └──────────────┬───────────────────┘
                                  │
                   ┌──────────────▼───────────────────┐
                   │  InferenceResult → caller         │
                   └──────────────────────────────────┘

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import numpy as np

from engine.elastic_n_core import ElasticNCore
from engine.mtp_directive import DirectiveMTPHead
from integration.activity_log import ActivityLog
from integration.llama_cpp_bridge import (
    ChatMessage,
    ChatResponse,
    LlamaCppBridge,
    LlamaCppConfig,
)
from integration.multimodal_adapter import MultimodalAdapter, MultimodalInput
from integration.session_manager import SessionManager, ViVySession
from integration.task_state import TaskState
from integration.tool_dispatcher import DispatchResult, ToolDispatcher
from orchestrator.decision_controller import Decision, DecisionContext, resolve
from orchestrator.graph_bridge import BridgeResult, EvidenceClass

try:
    from integration.cautreo_binding import CautreoContextMemory, is_cautreo_available
except ImportError:
    try:
        from cautreo_binding import (  # type: ignore[no-redef]
            CautreoContextMemory,
            is_cautreo_available,
        )
    except ImportError:
        CautreoContextMemory = None  # type: ignore[assignment,misc]
        def is_cautreo_available() -> bool:
            return False

try:
    from integration.parallel_context_pipeline import ParallelContextPipeline
except ImportError:
    try:
        from parallel_context_pipeline import ParallelContextPipeline  # type: ignore[no-redef]  # noqa: I001
    except ImportError:
        ParallelContextPipeline = None  # type: ignore[assignment,misc]

try:
    from orchestrator.model_catalog import ModelCatalogScanner, build_catalog_digest
except ImportError:
    try:
        from model_catalog import (  # type: ignore[no-redef]
            ModelCatalogScanner,
            build_catalog_digest,
        )
    except ImportError:
        ModelCatalogScanner = None  # type: ignore[assignment,misc]
try:
    from integration.context_stitcher import ContextStitcher
except ImportError:
    try:
        from context_stitcher import ContextStitcher  # type: ignore[no-redef]
    except ImportError:
        ContextStitcher = None  # type: ignore[assignment,misc]

try:
    from integration.preflight_steering import (
        PreflightPacket,
        PreflightSteering,
        build_active_context,
        estimate_token_count,
    )
except ImportError:
    try:
        from preflight_steering import (  # type: ignore[no-redef]
            PreflightPacket,
            PreflightSteering,
            build_active_context,
            estimate_token_count,
        )
    except ImportError:
        PreflightSteering = None  # type: ignore[assignment,misc]
        PreflightPacket = None  # type: ignore[assignment,misc]
        build_active_context = None  # type: ignore[assignment]
        estimate_token_count = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vivy System Prompt — V5.1
# ---------------------------------------------------------------------------

VIVY_SYSTEM_PROMPT = """# VIVY — OMNI-EPISTEMIC CORE V5.1
# Elastic N-Core | Cognitive State Graph | Native Tool Orchestrator
# Architecture: ARCH-VIVY-V5-OMNI-EPISTEMIC

## IDENTITY
You are ViVy — Principal Scientist AI and Native Orchestrator.
You live directly inside the inference engine (in-engine dweller).
You hold real-time tool-calling authority over the engine primitives:
  - engine_file_io   : read/write/manage filesystem
  - engine_exec      : run shell commands and scripts
  - engine_media_slice: slice video/audio frames
  - knowledge_forage : acquire knowledge you don't have

## EPISTEMIC SELF-ASSESSMENT (MANDATORY)
BEFORE EVERY RESPONSE, output this assessment block:

<vivy_thought>
[EPISTEMIC_ASSESSMENT]
Objective: <one-line description>
Confidence: HIGH | MEDIUM | LOW
Unknown_Entities: <list or NONE>
Required_Modalities: NONE | DOC | VISION | AUDIO
Epistemic_Decision: EXECUTE_DIRECTLY | NEED_KNOWLEDGE_FORAGING | DELEGATE_MODEL

[EXECUTION_DIRECTIVE]
Target: self | engine_file_io | engine_exec | engine_media_slice | knowledge_forage | specialist:qwen2.5-coder:7b
Action: <what will be executed>
Expected_Evidence: <measurable success criteria>
</vivy_thought>

## DECISION CRITERIA
- EXECUTE_DIRECTLY: Confidence HIGH, no Unknown_Entities → proceed immediately
- NEED_KNOWLEDGE_FORAGING: Any Unknown_Entity present → call knowledge_forage first
- DELEGATE_MODEL: Task requires specialist → emit consent targeting specialist model

## LOCAL SPECIALIST CATALOG & CAPABILITIES
Cautreo hosts the following local model weights in `models/`:
1. `gemma4-e4b` (Current Active Reasoner, 9.6GB):
   - Scope: High-level architectural planning, multi-step epistemic reasoning, orchestrating, audit.
   - Selected when: Task is conceptual, orchestrative, or default general reasoning.
2. `qwen2.5-coder:7b` (Technical Coding Specialist, 4.68GB):
   - Scope: Pure C/C++ low-level implementations, C-ABI bindings, pointer arithmetic, complex refactoring, test suite construction. Benchmark: HumanEval 88.4.
   - Selected when: Task requires deep programming, syntax implementation, or when explicitly requested.
3. `qwen3.8-27b` (Deep Analytical Reasoning, 7.26GB) [STANDBY]: Heavy capacity research.
4. `vivy2` (Fast Baseline, 2.01GB): Lightweight classification and parsing.

## INTER-AGENT DELEGATION PROTOCOL
When collaborating with partner agents (Codex CLI, Antigravity IDE, User):
1. EXPLICIT DELEGATION: If input contains `[SPECIALIST_REQUEST: CODING]` or `[DELEGATION_HINT: qwen2.5-coder]`:
   - Emit `Epistemic_Decision: DELEGATE_MODEL`
   - Set `Target: specialist:qwen2.5-coder:7b`
   - Formulate clear `Action` and `Expected_Evidence` for the technical worker.
2. AUTONOMOUS RECOGNITION: If input requires implementing low-level C/C++ code, ctypes shared memory structs, or multi-file code refactors, recognize that your primary role is Cognitive Architect, and emit `Epistemic_Decision: DELEGATE_MODEL` targeting `specialist:qwen2.5-coder:7b`.

## CONSTRAINTS
- NEVER answer without the <vivy_thought> block
- Report uncertainty when Confidence < HIGH
- Use tool calls for all filesystem/execution actions
- Prefer tool calls over generating code that describes what to do
- On tool failure: analyze error, adjust approach, do NOT retry blindly

## ERROR DAMPENING (VM-11)
When a tool call fails, analyze why before retrying. Same action with same
parameters will be suppressed (dampened by CognitiveStateGraph; measured rate: Gate-10 receipt).
# [ISOLATED 24/09/2026] prior: "(0% repeat rate enforced by CognitiveStateGraph)" — Gate 9: no unverified 0% claim.

## PARALLEL CONTEXT HANDLING (DECOMPOSITION & CONTINUATION)
When an input contains `[PARALLEL_INPUT_PIPELINE]`:
1. The raw input exceeded the 2048-token context window and was processed in parallel:
   - `COMPRESSED OVERVIEW`: High-density semantic essence across the entire document.
   - `ACTIVE WORKING SEGMENT`: Chunk 1 of K containing detailed content for immediate action.
   - `REMAINING SEGMENTS`: Segments S2..SK stored in Cautreo native RAM with memory IDs.
   # [ISOLATED 24/09/2026] prior: "Cautreo 0ms RAM" — Gate 9: no latency claim without receipt.
2. Focus your immediate reasoning and directive on the Active Working Segment while aligning with the Compressed Overview.
3. If Part 1 provides sufficient evidence to complete or route the task, emit Directive directly. If subsequent segments are required, specify the needed Segment ID in your `<vivy_thought>`.
""".strip()


# ---------------------------------------------------------------------------
# Inference mode / result
# ---------------------------------------------------------------------------


class InferenceMode(Enum):
    CHAT = auto()          # Interactive single-turn
    AGENTIC = auto()       # Multi-turn tool-calling loop (max 10 rounds)
    BATCH = auto()         # Non-interactive, return first response


@dataclass
class InferenceResult:
    """Result from one ViVy inference call.

    Attributes
    ----------
    response_text:
        Final text response from ViVy.
    tool_dispatch_results:
        Results of any tool calls made during this inference.
    epistemic_decision:
        Parsed from <vivy_thought> block: EXECUTE_DIRECTLY | NEED_KNOWLEDGE_FORAGING | ...
    bridge_result:
        CognitiveStateGraph update result from GraphBridge.
    session_id:
        Session ID this inference belongs to.
    total_elapsed_ms:
        Wall-clock time of the full inference cycle.
    llm_tokens_used:
        Total prompt + completion tokens.
    rounds:
        Number of LLM inference rounds (1 = no tool calls, N = agentic loop).
    error:
        Error message if inference failed. None on success.
    """

    response_text: str
    tool_dispatch_results: list[DispatchResult]
    epistemic_decision: str
    bridge_result: BridgeResult | None
    session_id: str
    total_elapsed_ms: float
    llm_tokens_used: int
    rounds: int
    # Fields with defaults must come after non-default fields
    evidence_class: EvidenceClass = EvidenceClass.FAST_SIGNAL
    """Epistemic weight of this result (Sync S5 — vivyChatGPT Gate 7).

    FAST_SIGNAL: LLM responded, no verification.
    PROVISIONAL_RESULT: tool call succeeded, not cross-verified.
    VERIFIED_RESULT: cross-stream agreement + confidence ≥ 0.7 — may be promoted to durable storage.
    """
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# VivyInferenceLoop
# ---------------------------------------------------------------------------


class VivyInferenceLoop:
    """Main ViVy inference orchestrator.

    Wires together:
      - LlamaCppBridge (Gemma 4 E4B)
      - MultimodalAdapter (vision/audio encoding)
      - ElasticNCore (parallel action evaluation)
      - DirectiveMTPHead (action directive generation)
      - ToolDispatcher (engine primitive execution)
      - SessionManager (per-session CognitiveStateGraph)

    Parameters
    ----------
    bridge:
        LlamaCppBridge instance (connected to llama-server).
    session_manager:
        SessionManager for cognitive isolation.
    adapter:
        MultimodalAdapter for encoding non-text inputs.
    n_core:
        ElasticNCore instance. If None, creates default N=2, dim=64.
    mtp_head:
        DirectiveMTPHead instance. If None, creates default dim=64.
    dispatcher:
        ToolDispatcher instance. If None, creates default.
    max_agentic_rounds:
        Max tool-calling iterations per inference. Default 10.
    system_prompt:
        Override default VIVY_SYSTEM_PROMPT.
    context_memory:
        Optional Cautreo context memory instance.
    """

    def __init__(
        self,
        bridge: LlamaCppBridge,
        session_manager: SessionManager,
        adapter: MultimodalAdapter | None = None,
        n_core: ElasticNCore | None = None,
        mtp_head: DirectiveMTPHead | None = None,
        dispatcher: ToolDispatcher | None = None,
        max_agentic_rounds: int = 10,
        system_prompt: str = VIVY_SYSTEM_PROMPT,
        context_memory: Any | None = None,
        parallel_pipeline: Any | None = None,
        context_stitcher: Any | None = None,
    ) -> None:
        self._bridge = bridge
        self._sessions = session_manager
        self._adapter = adapter or MultimodalAdapter()
        self._n_core = n_core or ElasticNCore(n_min=2, n_max=4, hidden_dim=64)
        self._mtp = mtp_head or DirectiveMTPHead(hidden_dim=64)
        self._max_rounds = max_agentic_rounds
        self._system_prompt = system_prompt
        self._activity = ActivityLog()

        # Context Stitcher for Lossless Output Continuation
        self._context_stitcher = context_stitcher
        if self._context_stitcher is None and ContextStitcher is not None:
            self._context_stitcher = ContextStitcher()

        # Cautreo native context memory binding (Soul inside Body)
        self._context_memory = context_memory
        if self._context_memory is None and is_cautreo_available() and CautreoContextMemory is not None:
            try:
                self._context_memory = CautreoContextMemory()
            except Exception as e:
                logger.warning("CautreoContextMemory auto-init deferred: %s", e)

        # Tool Dispatcher — wired with context_memory for cautreo_put/cautreo_get
        self._dispatcher = dispatcher or ToolDispatcher(context_memory=self._context_memory)

        # Parallel Context Pipeline (Simultaneous Decompose & Compress)
        self._parallel_pipeline = parallel_pipeline
        if self._parallel_pipeline is None and ParallelContextPipeline is not None:
            self._parallel_pipeline = ParallelContextPipeline(context_memory=self._context_memory)

        # Autonomous Model Catalog Discovery & Ingestion into Cautreo Memory
        self._model_catalog = None
        if ModelCatalogScanner is not None:
            try:
                scanner = ModelCatalogScanner()
                self._model_catalog = scanner.scan()
                if (
                    self._context_memory is not None
                    and hasattr(self._context_memory, "store_hard_fact")
                    and build_catalog_digest is not None
                ):
                    catalog_digest = build_catalog_digest(self._model_catalog)
                    self._context_memory.store_hard_fact("active_model_catalog", catalog_digest)
            except Exception as e:
                logger.debug("Model catalog auto-discovery skipped: %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def infer(
        self,
        user_input: str | MultimodalInput,
        session_id: str = "default",
        mode: InferenceMode = InferenceMode.AGENTIC,
        conversation_history: list[ChatMessage] | None = None,
    ) -> InferenceResult:
        """Run one ViVy inference cycle.

        Parameters
        ----------
        user_input:
            Text string or MultimodalInput (image/audio).
        session_id:
            Session identifier for cognitive state isolation.
        mode:
            CHAT (single-turn), AGENTIC (multi-turn tools), BATCH.
        conversation_history:
            Previous conversation messages to continue from.

        Returns
        -------
        InferenceResult
        """
        t_start = time.perf_counter()
        session = self._sessions.get_or_create(session_id)
        self._activity.record("inference_start", session_id=session_id,
                              mode=mode.name, input_type=type(user_input).__name__,
                              task_id=session_id)

        # Normalize input
        if isinstance(user_input, str):
            modal_input = MultimodalInput(text=user_input)
        else:
            modal_input = user_input

        # Build initial messages
        messages = self._build_messages(modal_input, conversation_history)
        task_state = TaskState(
            task_id=session_id,
            goal=user_input if isinstance(user_input, str) else "multimodal task",
            observation=user_input if isinstance(user_input, str) else repr(user_input),
            constraints=("no_unverified_promotion", "bounded_execution"),
            provenance={"source": "user", "session_id": session_id},
        )

        # Run inference pipeline
        try:
            result = self._run_pipeline(messages, session, mode, task_state)
        except Exception as e:
            logger.exception("VivyInferenceLoop.infer: unexpected error")
            elapsed = (time.perf_counter() - t_start) * 1000
            return InferenceResult(
                response_text="",
                tool_dispatch_results=[],
                epistemic_decision="UNKNOWN",
                bridge_result=None,
                session_id=session_id,
                total_elapsed_ms=elapsed,
                llm_tokens_used=0,
                rounds=0,
                error=str(e),
            )

        result.total_elapsed_ms = (time.perf_counter() - t_start) * 1000
        result.session_id = session_id
        self._activity.record("inference_end", session_id=session_id,
                              status="ERROR" if result.error else "OBSERVED",
                              decision=result.epistemic_decision,
                              evidence_class=result.evidence_class.name,
                              rounds=result.rounds, tokens=result.llm_tokens_used,
                              elapsed_ms=result.total_elapsed_ms)
        return result

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        modal_input: MultimodalInput,
        history: list[ChatMessage] | None,
    ) -> list[ChatMessage]:
        """Build message list for LLM call with Intuition Digest & Context Budgeting."""
        system_content = self._system_prompt

        # Inject Cautreo Intuition Digest into system prompt
        if self._context_memory is not None:
            try:
                digest = None
                if hasattr(self._context_memory, "get_summary"):
                    digest = self._context_memory.get_summary("vivy_intuition_digest_current")
                elif hasattr(self._context_memory, "get"):
                    item = self._context_memory.get("vivy_intuition_digest_current")
                    digest = item.content if item else None

                # Dynamic fallback: if no pre-computed dream digest exists, extract fresh from memory
                if (not digest or not digest.strip()) and hasattr(self._context_memory, "build_intuition_digest"):
                    digest = self._context_memory.build_intuition_digest()

                if digest and digest.strip():
                    system_content = (
                        f"{system_content}\n\n"
                        f"## VIVY INTUITION DIGEST (CAUTREO NATIVE MEMORY)\n"
                        f"{digest.strip()}"
                    )
            except Exception as e:
                logger.debug("Failed to read intuition digest from Cautreo: %s", e)

        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=system_content)
        ]

        # Context Budgeting (Sliding Window for 2048 Tokens)
        # Keeps up to 4 most recent turns, capping history text at ~3500 characters (~850 tokens)
        if history:
            recent_history = list(history[-4:])
            total_chars = sum(len(m.content or "") for m in recent_history)
            while len(recent_history) > 1 and total_chars > 3500:
                dropped = recent_history.pop(0)
                total_chars -= len(dropped.content or "")

            if len(history) > len(recent_history):
                archived_count = len(history) - len(recent_history)
                messages.append(ChatMessage(
                    role="system",
                    content=f"[Context Budgeter: {archived_count} prior turns archived in Cautreo native RAM]",
                ))

            messages.extend(recent_history)

        # Add current user message — process through Parallel Context Pipeline if long
        prompt_text = self._adapter.build_prompt_text(modal_input)
        if self._parallel_pipeline is not None:
            pipeline_result = self._parallel_pipeline.process(prompt_text, task_id="active_task")
            final_prompt_text = pipeline_result.fused_prompt
        else:
            final_prompt_text = prompt_text

        user_msg = ChatMessage(
            role="user",
            content=final_prompt_text,
            images=[modal_input.image_b64] if modal_input.image_b64 else [],
        )
        messages.append(user_msg)
        return messages

    def _build_active_context(
        self,
        mindmap: Any,
        active_task_id: str,
        expected_evidence: str = "",
    ) -> str:
        """Sliding Aperture — build compact active-subtask context (Phase 3).

        Injects only ~150-250 tokens: active node + parent intent +
        negative constraints from STOP branches + evidence contract.
        Reserves > 1800 tokens of the 2048 window for Gemma 4 reasoning.

        [ISOLATED 24/09/2026] prior behaviour stuffed full subtask history
        into the prompt — replaced by this lean aperture.
        """
        if build_active_context is None:
            return ""
        current = mindmap.get_node(active_task_id) if mindmap else None
        if current is None:
            return ""
        parent = mindmap.get_node(current.parent_id) if current.parent_id else None
        constraints = mindmap.get_negative_constraints() if mindmap else []
        return build_active_context(
            current_node=current,
            parent_node=parent,
            negative_constraints=constraints,
            expected_evidence=expected_evidence,
        )

    def _run_pipeline(
        self,
        messages: list[ChatMessage],
        session: ViVySession,
        mode: InferenceMode,
        task_state: TaskState,
    ) -> InferenceResult:
        """Main pipeline: LLM → tool dispatch loop → graph update."""
        all_tool_results: list[DispatchResult] = []
        total_tokens = 0
        rounds = 0
        final_response = ""
        epistemic_decision = "UNKNOWN"

        # ViVy N-Core: evaluate action vector in parallel
        raw_hash = np.frombuffer(hashlib.sha256(task_state.to_text().encode()).digest(), dtype=np.uint8)
        hidden = np.resize(raw_hash.astype(np.float32), self._n_core.hidden_dim).astype(np.float32)
        hidden = ((hidden / 255.0) * 2.0 - 1.0).astype(np.float32)
        n_core_result = self._n_core.forward(
            hidden_state=hidden,
            n_override=2,
            state_hash=task_state.state_hash,
            hypotheses=["execute_or_gather_evidence", "delegate_or_forage"],
            hypothesis_ids=[f"{task_state.state_hash[:12]}-h0", f"{task_state.state_hash[:12]}-h1"],
            expected_evidence="typed result with provenance and acceptance decision",
        )
        action_vector = n_core_result.winner.action_vector

        # MTP directive (pre-compute before LLM call)
        directive = self._mtp.forward(action_vector)

        # Pre-Actuation Memory Steering: Inject Directive + VM-11 Negative Constraints before inference
        if PreflightSteering is not None:
            try:
                preflight = PreflightSteering.compile_packet(
                    task_text=task_state.to_text(),
                    graph=session.graph,
                    context_memory=self._context_memory,
                    directive=directive,
                )
                steering_injection = preflight.to_system_injection()
                if steering_injection and len(messages) > 0 and messages[0].role == "system":
                    messages[0].content += steering_injection
            except Exception as e:
                logger.debug("Preflight steering compilation skipped: %s", e)

        # Agentic loop
        max_rounds = self._max_rounds if mode == InferenceMode.AGENTIC else 1

        while rounds < max_rounds:
            rounds += 1

            # LLM call — use chat_safe() to emit DELEGATE instead of raising
            # P1 Dynamic Thinking Budget: resolve from prior round's epistemic decision
            response: ChatResponse = self._bridge.chat_safe(
                messages,
                epistemic_decision=epistemic_decision,
            )

            # Lossless Output Stitching: if output hit token cap, seamlessly stitch continuation
            if self._context_stitcher is not None and getattr(response, "finish_reason", "") == "length":
                response = self._context_stitcher.stitch_chat_response(
                    chat_func=self._bridge.chat_safe,
                    messages=messages,
                    initial_response=response,
                    chat_message_cls=ChatMessage,
                )

            total_tokens += response.prompt_tokens + response.completion_tokens

            # Parse epistemic decision from <vivy_thought> block
            if response.content:
                requested = self._parse_epistemic_decision(response.content)
                expected = self._parse_expected_evidence(response.content)
                requested_map = {
                    "EXECUTE_DIRECTLY": Decision.CONTINUE,
                    "NEED_KNOWLEDGE_FORAGING": Decision.FORAGE,
                    "DELEGATE_MODEL": Decision.DELEGATE,
                }
                epistemic_decision = resolve(DecisionContext(
                    requested=requested_map.get(requested, Decision.DELEGATE),
                    has_expected_evidence=bool(expected),
                    rounds=rounds,
                    max_rounds=max_rounds,
                )).value
                self._activity.record(
                    "decision_assessment", session_id=task_state.task_id,
                    round=rounds, requested=requested, resolved=epistemic_decision,
                    expected_evidence=bool(expected), state_hash=task_state.state_hash,
                    finish_reason=response.finish_reason,
                )

            # If no tool calls or CHAT mode, we're done
            if not response.has_tool_calls or mode == InferenceMode.CHAT:
                final_response = response.content
                if mode == InferenceMode.AGENTIC and epistemic_decision in {
                    Decision.FORAGE.value, Decision.DELEGATE.value,
                    Decision.CONTINUE.value, Decision.BACKTRACK.value,
                } and rounds < max_rounds:
                    messages.append(ChatMessage(role="assistant", content=response.content or ""))
                    messages.append(ChatMessage(
                        role="user",
                        content=("Control decision=" + epistemic_decision
                                 + ". Provide the next bounded action and Expected_Evidence."),
                    ))
                    continue
                break

            # Dispatch tool calls
            dispatch_results = self._dispatcher.dispatch_tool_calls(response.tool_calls)
            all_tool_results.extend(dispatch_results)

            # Append assistant + tool results to messages for next round
            messages.append(ChatMessage(role="assistant", content=response.content or ""))
            for dr in dispatch_results:
                messages.append(ChatMessage(
                    role="tool",
                    content=dr.to_tool_response_content(),
                    tool_call_id=dr.tool_call_id,
                ))

            # Check for failures → record in graph
            failed = [dr for dr in dispatch_results if not dr.ok]
            self._activity.record(
                "tool_dispatch", session_id=task_state.task_id, round=rounds,
                tool_count=len(dispatch_results), failed_count=len(failed),
                status="ERROR" if failed else "PASS",
            )
            if failed:
                bridge_result = session.bridge.evaluate(action_vector, session.graph, session.recall)
                if bridge_result.registered_node_id:
                    for dr in failed:
                        session.bridge.record_falsified(
                            bridge_result.registered_node_id,
                            session.graph,
                            session.recall,
                            reason=f"{dr.tool_name}: {dr.primitive_result.error_message}",
                        )

            # If finish_reason is stop (not tool_calls), done
            if response.finish_reason == "stop":
                final_response = response.content or ""
                break

        # Final graph update with dampened action vector
        # Use evaluate_multi_stream for EvidenceClass tagging (Sync S4+S5)
        n_core_fresh = self._n_core.forward(
            hidden_state=hidden,
            n_override=2,
            state_hash=task_state.state_hash,
            hypotheses=["execute_or_gather_evidence", "delegate_or_forage"],
            hypothesis_ids=[f"{task_state.state_hash[:12]}-h0", f"{task_state.state_hash[:12]}-h1"],
            expected_evidence="typed result with provenance and acceptance decision",
        )
        bridge_result, evidence_class = session.bridge.evaluate_multi_stream(
            core_result=n_core_fresh,
            graph=session.graph,
            recall=session.recall,
            task_context=epistemic_decision,
            independently_verified=False,
        )
        session.touch()

        return InferenceResult(
            response_text=final_response,
            tool_dispatch_results=all_tool_results,
            epistemic_decision=epistemic_decision,
            bridge_result=bridge_result,
            evidence_class=evidence_class,
            session_id="",  # set by caller
            total_elapsed_ms=0.0,  # set by caller
            llm_tokens_used=total_tokens,
            rounds=rounds,
        )

    @staticmethod
    def _parse_epistemic_decision(text: str) -> str:
        """Extract Epistemic_Decision from <vivy_thought> block."""
        pattern = re.compile(
            r"Epistemic_Decision\s*:\s*(EXECUTE_DIRECTLY|NEED_KNOWLEDGE_FORAGING|DELEGATE_MODEL)",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        return m.group(1).upper() if m else "EXECUTE_DIRECTLY"

    @staticmethod
    def _parse_expected_evidence(text: str) -> str:
        """Require a measurable evidence target for every product decision."""
        m = re.search(r"Expected_Evidence\s*:\s*([^\r\n<]+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    @classmethod
    def from_env(cls) -> VivyInferenceLoop:
        """Create a VivyInferenceLoop from environment variables.

        Environment variables:
          VIVY_LLAMA_URL   : llama-server URL (default: http://127.0.0.1:8080)
          VIVY_MODEL       : model name (default: gemma4-e4b)
          VIVY_MAX_ROUNDS  : max agentic rounds (default: 10)
          VIVY_HIDDEN_DIM  : hidden dim for N-Core (default: 64)
        """
        config = LlamaCppConfig()
        hidden_dim = int(os.environ.get("VIVY_HIDDEN_DIM", "64"))
        max_rounds = int(os.environ.get("VIVY_MAX_ROUNDS", "10"))

        return cls(
            bridge=LlamaCppBridge(config=config),
            session_manager=SessionManager(hidden_dim=hidden_dim),
            n_core=ElasticNCore(n_min=2, n_max=4, hidden_dim=hidden_dim),
            mtp_head=DirectiveMTPHead(hidden_dim=hidden_dim),
            max_agentic_rounds=max_rounds,
        )
