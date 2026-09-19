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

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np

from engine.elastic_n_core import ElasticNCore
from engine.mtp_directive import DirectiveMTPHead
from integration.llama_cpp_bridge import ChatMessage, ChatResponse, LlamaCppBridge, LlamaCppConfig
from integration.multimodal_adapter import MultimodalAdapter, MultimodalInput
from integration.session_manager import SessionManager, ViVySession
from integration.tool_dispatcher import DispatchResult, ToolDispatcher
from orchestrator.graph_bridge import BridgeResult

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
Target: self | engine_file_io | engine_exec | engine_media_slice | knowledge_forage
Action: <what will be executed>
Expected_Evidence: <measurable success criteria>
</vivy_thought>

## DECISION CRITERIA
- EXECUTE_DIRECTLY: Confidence HIGH, no Unknown_Entities → proceed immediately
- NEED_KNOWLEDGE_FORAGING: Any Unknown_Entity present → call knowledge_forage first
- DELEGATE_MODEL: Task requires specialist → structure and describe sub-task

## CONSTRAINTS
- NEVER answer without the <vivy_thought> block
- Report uncertainty when Confidence < HIGH
- Use tool calls for all filesystem/execution actions
- Prefer tool calls over generating code that describes what to do
- On tool failure: analyze error, adjust approach, do NOT retry blindly

## ERROR DAMPENING (VM-11)
When a tool call fails, analyze why before retrying. Same action with same
parameters will be suppressed (0% repeat rate enforced by CognitiveStateGraph).
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
    ) -> None:
        self._bridge = bridge
        self._sessions = session_manager
        self._adapter = adapter or MultimodalAdapter()
        self._n_core = n_core or ElasticNCore(n_min=2, n_max=4, hidden_dim=64)
        self._mtp = mtp_head or DirectiveMTPHead(hidden_dim=64)
        self._dispatcher = dispatcher or ToolDispatcher()
        self._max_rounds = max_agentic_rounds
        self._system_prompt = system_prompt

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

        # Normalize input
        if isinstance(user_input, str):
            modal_input = self._adapter.from_text(user_input)
        else:
            modal_input = user_input

        # Build initial messages
        messages = self._build_messages(modal_input, conversation_history)

        # Run inference pipeline
        try:
            result = self._run_pipeline(messages, session, mode)
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
        return result

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        modal_input: MultimodalInput,
        history: list[ChatMessage] | None,
    ) -> list[ChatMessage]:
        """Build message list for LLM call."""
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=self._system_prompt)
        ]

        # Add history
        if history:
            messages.extend(history)

        # Add current user message
        prompt_text = self._adapter.build_prompt_text(modal_input)
        user_msg = ChatMessage(
            role="user",
            content=prompt_text,
            images=[modal_input.image_b64] if modal_input.image_b64 else [],
        )
        messages.append(user_msg)
        return messages

    def _run_pipeline(
        self,
        messages: list[ChatMessage],
        session: ViVySession,
        mode: InferenceMode,
    ) -> InferenceResult:
        """Main pipeline: LLM → tool dispatch loop → graph update."""
        all_tool_results: list[DispatchResult] = []
        total_tokens = 0
        rounds = 0
        final_response = ""
        epistemic_decision = "UNKNOWN"

        # ViVy N-Core: evaluate action vector in parallel
        n_core_result = self._n_core.forward(n_override=2)
        action_vector = n_core_result.winner.action_vector

        # MTP directive (pre-compute before LLM call)
        directive = self._mtp.forward(action_vector)

        # Agentic loop
        max_rounds = self._max_rounds if mode == InferenceMode.AGENTIC else 1

        while rounds < max_rounds:
            rounds += 1

            # LLM call
            response: ChatResponse = self._bridge.chat(messages)
            total_tokens += response.prompt_tokens + response.completion_tokens

            # Parse epistemic decision from <vivy_thought> block
            if response.content:
                epistemic_decision = self._parse_epistemic_decision(response.content)

            # If no tool calls or CHAT mode, we're done
            if not response.has_tool_calls or mode == InferenceMode.CHAT:
                final_response = response.content
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
        bridge_result = session.bridge.evaluate(
            action_vector,
            session.graph,
            session.recall,
            task_context=epistemic_decision,
        )
        session.touch()

        return InferenceResult(
            response_text=final_response,
            tool_dispatch_results=all_tool_results,
            epistemic_decision=epistemic_decision,
            bridge_result=bridge_result,
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

    @classmethod
    def from_env(cls) -> "VivyInferenceLoop":
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
