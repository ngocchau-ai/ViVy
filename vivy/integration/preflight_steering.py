"""
Preflight Steering Engine — ViVy V6 & Cautreo Native Architecture.

Implements Pre-Actuation Memory Steering:
1. Extracts Hard Negative Constraints from CognitiveStateGraph (falsified nodes)
   to dampen VM-11 error repeats. Measured repeat rate is a Gate-10 metric and
   is NOT claimed here without a receipt.
2. Retrieves Intuition Anchors from Cautreo Native Memory (in-process C-ABI;
   latency is a measured benchmark, not asserted in copy).
3. Injects Directive Guidance from N-Core MTP Head directly into the model context
   BEFORE inference begins, eliminating "temporary amnesia".

Changelog:
    22/09/2026 (Antigravity IDE & Ngoc Chau — Sprint R1): Initial implementation.
    23/09/2026 (Claude Code — P0 Superority Truth Pass): Gate 9 scrub.
        [ISOLATED] prior docstring claim "VM-11 (Error repeat rate = 0%)";
        [ISOLATED] prior "(C-ABI 0ms RAM)" latency claim. Both lacked receipts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PreflightPacket:
    """Pre-actuation steering payload injected before model generation.

    Attributes
    ----------
    negative_constraints:
        List of forbidden patterns/mistakes extracted from past falsifications.
    intuition_anchors:
        List of relevant memory anchors or intuition digest from Cautreo.
    directive_summary:
        Formatted N-Core MTP directive (action code, flags, confidence).
    recommended_slot:
        Suggested weight/tool slot for task execution (e.g. 'code_py', 'reasoning').
    metadata:
        Additional provenance metadata.
    """

    negative_constraints: list[str] = field(default_factory=list)
    intuition_anchors: list[str] = field(default_factory=list)
    directive_summary: str | None = None
    recommended_slot: str | None = None
    atlas_guidance: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_system_injection(self) -> str:
        """Format the steering payload into a markdown block for the system prompt."""
        sections: list[str] = []

        # 1. Hard Negative Constraints (VM-11 Enforcer)
        if self.negative_constraints:
            constraints_text = "\n".join(
                f"- [FORBIDDEN / DO NOT REPEAT]: {rule}" for rule in self.negative_constraints
            )
            # [ISOLATED 23/09/2026] prior header claimed "(VM-11: REPEAT RATE = 0%)"
            # — Gate 9 forbids a 0% claim without a reproducible receipt.
            sections.append(
                "### PRE-FLIGHT HARD NEGATIVE CONSTRAINTS (VM-11 DAMPENER ACTIVE)\n"
                "The following actions/patterns previously FALSIFIED in this workspace and are STRICTLY FORBIDDEN:\n"
                f"{constraints_text}"
            )

        # 2. N-Core MTP Directive Guidance
        if self.directive_summary:
            sections.append(
                "### N-CORE MTP DIRECTIVE PRE-GUIDANCE\n"
                f"{self.directive_summary}"
            )

        # 3. Intuition Anchors
        if self.intuition_anchors:
            anchors_text = "\n".join(f"- {anchor}" for anchor in self.intuition_anchors)
            # [ISOLATED 23/09/2026] prior header claimed "(0ms RAM)" — latency
            # claims require a benchmark receipt under Gate 9.
            sections.append(
                "### CAUTREO NATIVE INTUITION ANCHORS (IN-PROCESS MEMORY)\n"
                f"{anchors_text}"
            )

        # 4. Cautreo Knowledge Atlas Guidance (Dynamic Sparse Activation)
        if self.atlas_guidance:
            sections.append(
                "### CAUTREO KNOWLEDGE ATLAS GUIDANCE (DYNAMIC SPARSE ACTIVATION)\n"
                f"{self.atlas_guidance}"
            )

        if not sections:
            return ""

        return (
            "\n\n## VIVY PRE-ACTUATION MEMORY STEERING (CAUTREO CORE)\n"
            + "\n\n".join(sections)
        )


class PreflightSteering:
    """Orchestrator for pre-flight memory retrieval and negative rule compilation."""

    @staticmethod
    def extract_negative_constraints(
        graph: Any | None,
        max_constraints: int = 5,
    ) -> list[str]:
        """Extract falsified nodes from CognitiveStateGraph as negative constraints."""
        if graph is None:
            return []

        negative_rules: list[str] = []
        seen: set[str] = set()

        try:
            # CognitiveStateGraph holds nodes in _nodes or nodes property
            nodes = getattr(graph, "nodes", None)
            if nodes is None:
                nodes = getattr(graph, "_nodes", {})
            for _node_id, node in nodes.items():
                if getattr(node, "is_dampened", lambda: False)():
                    # Check falsified reason in metadata or node content
                    metadata = getattr(node, "metadata", {})
                    reason = metadata.get("falsified_reason") or getattr(node, "content", "")
                    cleaned = str(reason).strip()
                    if cleaned and cleaned not in seen:
                        seen.add(cleaned)
                        negative_rules.append(cleaned)
                        if len(negative_rules) >= max_constraints:
                            break
        except Exception as e:
            logger.debug("extract_negative_constraints error: %s", e)

        return negative_rules

    @staticmethod
    def extract_atlas_guidance(atlas: Any, task_text: str, top_k: int = 2) -> str | None:
        """Query Knowledge Atlas for high-salience layer coordinates and sparsity recommendation."""
        if not atlas:
            return None
        try:
            matches = atlas.query(task_text, top_k=top_k)
            if not matches:
                return None
            lines = []
            for node, score in matches:
                if score > 0.15:
                    lines.append(
                        f"- Target Layer {node.layer_index:02d} ({node.block_name}): Domain='{node.dominant_domain}', "
                        f"Affinity={score:.2f}, Sparsity={node.sparsity_ratio*100:.0f}%, "
                        f"Active RAM={node.sparse_ram_mb:.1f}MB (Top-10% Neurons: {len(node.high_salience_neuron_indices)})"
                    )
            if not lines:
                return None
            return "\n".join(lines)
        except Exception as e:
            logger.debug("extract_atlas_guidance error: %s", e)
            return None

    @classmethod
    def compile_packet(
        cls,
        task_text: str,
        graph: Any | None = None,
        context_memory: Any | None = None,
        directive: Any | None = None,
        max_negative: int = 5,
        atlas: Any | None = None,
    ) -> PreflightPacket:
        """Compile complete PreflightPacket prior to LLM inference."""
        negative_rules = cls.extract_negative_constraints(graph, max_constraints=max_negative)
        intuition_anchors: list[str] = []
        directive_summary: str | None = None
        atlas_guidance: str | None = None

        # 1. Fetch intuition anchors from Cautreo context memory if available
        if context_memory is not None:
            try:
                # If memory has build_intuition_digest or get_summary
                if hasattr(context_memory, "get_summary"):
                    digest = context_memory.get_summary("vivy_intuition_digest_current")
                    if digest and digest.strip():
                        intuition_anchors.append(digest.strip())
                elif hasattr(context_memory, "build_intuition_digest"):
                    digest = context_memory.build_intuition_digest()
                    if digest and digest.strip():
                        intuition_anchors.append(digest.strip())
            except Exception as e:
                logger.debug("Failed to retrieve Cautreo memory digest: %s", e)

        # 2. Format MTP directive if provided
        if directive is not None:
            try:
                target_id = getattr(directive, "target_id", None)
                opcode = getattr(directive, "opcode", getattr(directive, "action_code", "UNKNOWN"))
                confidence = getattr(directive, "confidence", 1.0)
                if target_id:
                    directive_summary = (
                        f"Target Component: `{target_id}` | Opcode: `{opcode}` | "
                        f"Confidence: {confidence:.2f}\n"
                        f"Align immediate execution directly with this directive."
                    )
                else:
                    directive_summary = (
                        f"Action Directive: `{opcode}` | Confidence: {confidence:.2f}\n"
                        f"Align immediate execution directly with this directive."
                    )
            except Exception as e:
                logger.debug("Failed to format directive summary: %s", e)

        # 3. Detect weight slot recommendation based on task text keywords
        slot = "general_cognition"
        lower_task = task_text.lower()
        if any(w in lower_task for w in ["code", "script", "python", "mt5", "function", "bug"]):
            slot = "code_py_specialist"
        elif any(w in lower_task for w in ["math", "calculate", "quant", "formula"]):
            slot = "math_quant_specialist"

        # 4. Extract Knowledge Atlas Guidance if atlas available
        if atlas is not None:
            atlas_guidance = cls.extract_atlas_guidance(atlas, task_text, top_k=2)

        return PreflightPacket(
            negative_constraints=negative_rules,
            intuition_anchors=intuition_anchors,
            directive_summary=directive_summary,
            recommended_slot=slot,
            atlas_guidance=atlas_guidance,
            metadata={"task_length": len(task_text)},
        )


# ---------------------------------------------------------------------------
# Sliding Aperture — Active Context Builder  (Phase 3, PLAN-VIVY-SCORED-MINDMAP-DAG)
# ---------------------------------------------------------------------------


def build_active_context(
    current_node: Any,
    parent_node: Any | None = None,
    negative_constraints: list[tuple[str, str, float]] | None = None,
    expected_evidence: str = "",
) -> str:
    """Build a compact sliding-aperture prompt (~150-250 tokens).

    Injects ONLY four lean components into the context window:
      1. Active subtask ID + intent
      2. Parent intent (one line)
      3. Negative constraints from STOP branches
      4. Evidence contract

    Forbidden: stuffing full subtask history into the prompt.
    Budget: < 300 tokens (strict ceiling), leaving > 1800 tokens
    of the 2048 window free for Gemma 4 reasoning.

    Parameters
    ----------
    current_node:
        ScoredTaskNode currently IN_PROGRESS.
    parent_node:
        Optional parent ScoredTaskNode.
    negative_constraints:
        List of (task_id, constraint_text, score) from STOPPED branches.
    expected_evidence:
        Measurable success criteria for the active subtask.

    Returns
    -------
    str
        Compact markdown prompt block.
    """
    task_id = getattr(current_node, "task_id", "unknown")
    intent = getattr(current_node, "intent", "")
    parent_intent = getattr(parent_node, "intent", "") if parent_node else ""

    lines: list[str] = []
    lines.append(f"## NHIỆM VỤ HIỆN TẠI (ACTIVE SUBTASK): [ID: {task_id}]")
    lines.append(f"- Mục tiêu: {intent}")
    if parent_intent:
        lines.append(f"- Ngữ cảnh cha: {parent_intent}")

    if negative_constraints:
        lines.append("")
        lines.append(
            "## BÀI HỌC VÀ RÀNG BUỘC CẤM ĐOÁN "
            "(NEGATIVE CONSTRAINTS TỪ CÁC NHÁNH ĐÃ STOP):"
        )
        for cid, constraint, score in negative_constraints[:5]:
            lines.append(
                f"- ⛔ KHÔNG LẶP LẠI [{cid} - Điểm {score:.0f}/10]: {constraint}"
            )

    lines.append("")
    lines.append("## TIÊU CHÍ NGHIỆM THU (EVIDENCE CONTRACT):")
    lines.append(f"- {expected_evidence or 'Chưa xác định'}")

    return "\n".join(lines)


def estimate_token_count(text: str) -> int:
    """Rough token estimate (~4 chars per token for mixed EN/VI)."""
    return max(1, len(text) // 4)
