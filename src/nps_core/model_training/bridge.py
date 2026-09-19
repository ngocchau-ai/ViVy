"""Bridge: converts NPS Core data structures to training examples.

Provides deterministic conversion from ThoughtState, PopulationSnapshot,
and ThoughtEcology into structured training examples suitable for
language model fine-tuning.  Standard-library only; no I/O.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from nps_core.evidence_assimilator.packet import EvidencePacket
from nps_core.hypothesis_population.lifecycle import PopulationSnapshot
from nps_core.hypothesis_population.thought_state import ThoughtState
from nps_core.model_training.errors import BridgeError
from nps_core.thought_ecology.index import ThoughtEcology

__all__ = [
    "TrainingExample",
    "BridgeConfig",
    "TASK_TYPES",
    "bridge_thought",
    "bridge_thought_reasoning",
    "bridge_thought_verification",
    "bridge_thought_critique",
    "bridge_thought_synthesis",
    "bridge_snapshot",
    "bridge_ecology",
    "bridge_evidence_packet",
    "examples_to_jsonl",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TASK_TYPES: tuple[str, ...] = (
    "reasoning",
    "verification",
    "critique",
    "synthesis",
    "ecology_analysis",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bridge_err(msg: str, **kwargs: Any) -> BridgeError:
    return BridgeError(msg, **kwargs)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# BridgeConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    """Configuration for the bridge conversion pipeline."""

    task_types: tuple[str, ...] = TASK_TYPES
    include_metadata: bool = True
    max_evidence_items: int = 10
    max_assumptions: int = 5
    max_graph_depth: int = 3
    system_prompt: str = (
        "You are a scientific reasoning assistant. "
        "Analyze the given evidence and produce well-structured hypotheses."
    )

    def __post_init__(self) -> None:
        valid = set(TASK_TYPES)
        for tt in self.task_types:
            if tt not in valid:
                raise _bridge_err(
                    f"unknown task_type: {tt!r}, must be one of {sorted(valid)}",
                    path="task_types",
                )


# ---------------------------------------------------------------------------
# TrainingExample
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrainingExample:
    """Immutable training example produced by the bridge.

    Fields:
    - task: The task type (reasoning, verification, etc.)
    - system: System prompt for instruction tuning
    - input: The input text (evidence, context)
    - output: The expected output (hypothesis, plan, etc.)
    - metadata: Optional provenance and quality metadata
    - content_hash: SHA-256 hex of input + output for deduplication
    """

    task: str
    system: str
    input: str
    output: str
    metadata: dict[str, Any]
    content_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.task, str) or not self.task:
            raise _bridge_err("task must be a non-empty string", path="task")
        if not isinstance(self.system, str):
            raise _bridge_err("system must be a string", path="system")
        if not isinstance(self.input, str) or not self.input:
            raise _bridge_err("input must be a non-empty string", path="input")
        if not isinstance(self.output, str) or not self.output:
            raise _bridge_err("output must be a non-empty string", path="output")
        if not isinstance(self.metadata, dict):
            raise _bridge_err("metadata must be a dict", path="metadata")
        expected_hash = _content_hash(self.input + self.output)
        if self.content_hash != expected_hash:
            object.__setattr__(self, "content_hash", expected_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "system": self.system,
            "input": self.input,
            "output": self.output,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainingExample:
        if not isinstance(data, dict):
            raise _bridge_err(f"expected dict, got {type(data).__name__}")
        required = {"task", "system", "input", "output", "metadata"}
        missing = required - data.keys()
        if missing:
            raise _bridge_err(f"missing keys: {sorted(missing)}")
        return cls(
            task=data["task"],
            system=data["system"],
            input=data["input"],
            output=data["output"],
            metadata=data["metadata"],
            content_hash="",
        )

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )


# ---------------------------------------------------------------------------
# Per-task bridge functions
# ---------------------------------------------------------------------------


def bridge_thought_reasoning(
    thought: ThoughtState,
    *,
    config: BridgeConfig,
    system_prompt: str | None = None,
) -> TrainingExample:
    """Convert a ThoughtState to a reasoning training example.

    Input: evidence + assumptions + context
    Output: hypothesis claim + predictions + falsification conditions
    """
    ev = thought.evidence
    evidence_lines: list[str] = []
    for bucket, label in [
        ("supporting", "Supporting"),
        ("opposing", "Opposing"),
        ("unresolved", "Unresolved"),
    ]:
        items = getattr(ev, bucket)
        for eid in items[: config.max_evidence_items]:
            evidence_lines.append(f"  [{label}] {eid}")

    assumption_lines: list[str] = []
    for a in thought.assumptions[: config.max_assumptions]:
        assumption_lines.append(
            f"  - {a.statement} (confidence: {a.confidence}, source: {a.source})"
        )

    input_parts = [
        f"Interpretation: {thought.interpretation.summary}",
        f"Scope: {thought.interpretation.scope}",
    ]
    if evidence_lines:
        input_parts.append("Evidence:")
        input_parts.extend(evidence_lines)
    if assumption_lines:
        input_parts.append("Assumptions:")
        input_parts.extend(assumption_lines)

    output_parts = [
        f"Hypothesis: {thought.hypothesis.claim}",
    ]
    if thought.hypothesis.predicted_observations:
        output_parts.append("Predicted observations:")
        for obs in thought.hypothesis.predicted_observations:
            output_parts.append(f"  - {obs}")
    if thought.hypothesis.falsification_conditions:
        output_parts.append("Falsification conditions:")
        for cond in thought.hypothesis.falsification_conditions:
            output_parts.append(f"  - {cond}")

    input_text = "\n".join(input_parts)
    output_text = "\n".join(output_parts)

    metadata: dict[str, Any] = {}
    if config.include_metadata:
        metadata = {
            "thought_id": thought.thought_id,
            "confidence": thought.metrics.confidence,
            "novelty": thought.metrics.novelty,
            "status": thought.status.state,
            "evidence_count": (
                len(ev.supporting) + len(ev.opposing) + len(ev.unresolved)
            ),
            "parent_ids": list(thought.parent_ids),
        }

    return TrainingExample(
        task="reasoning",
        system=system_prompt or config.system_prompt,
        input=input_text,
        output=output_text,
        metadata=metadata,
        content_hash="",
    )


def bridge_thought_verification(
    thought: ThoughtState,
    *,
    config: BridgeConfig,
    system_prompt: str | None = None,
) -> TrainingExample:
    """Convert a ThoughtState to a verification planning example.

    Input: hypothesis + evidence + metrics
    Output: verification plan
    """
    vp = thought.verification_plan

    input_parts = [
        f"Hypothesis: {thought.hypothesis.claim}",
        f"Confidence: {thought.metrics.confidence}",
        f"Risk if wrong: {thought.metrics.risk_if_wrong}",
    ]
    if vp.questions:
        input_parts.append("Questions to investigate:")
        for q in vp.questions:
            input_parts.append(f"  - {q}")

    output_parts = []
    if vp.required_experiments:
        output_parts.append("Required experiments:")
        for exp in vp.required_experiments:
            output_parts.append(f"  - {exp}")
    if vp.acceptable_evidence:
        output_parts.append("Acceptable evidence:")
        for ev_item in vp.acceptable_evidence:
            output_parts.append(f"  - {ev_item}")
    output_parts.append(f"Rejection threshold: {vp.rejection_threshold}")

    input_text = "\n".join(input_parts)
    output_text = "\n".join(output_parts)

    metadata: dict[str, Any] = {}
    if config.include_metadata:
        metadata = {
            "thought_id": thought.thought_id,
            "confidence": thought.metrics.confidence,
            "status": thought.status.state,
        }

    return TrainingExample(
        task="verification",
        system=system_prompt or config.system_prompt,
        input=input_text,
        output=output_text,
        metadata=metadata,
        content_hash="",
    )


def bridge_thought_critique(
    thought: ThoughtState,
    *,
    config: BridgeConfig,
    system_prompt: str | None = None,
) -> TrainingExample:
    """Convert a ThoughtState to a critique training example.

    Input: hypothesis + full evidence + metrics
    Output: structured assessment
    """
    ev = thought.evidence
    sup_count = len(ev.supporting)
    opp_count = len(ev.opposing)
    unr_count = len(ev.unresolved)
    total = sup_count + opp_count + unr_count

    input_parts = [
        f"Hypothesis: {thought.hypothesis.claim}",
        f"Current confidence: {thought.metrics.confidence}",
        f"Supporting evidence ({sup_count}): {list(ev.supporting)}",
        f"Opposing evidence ({opp_count}): {list(ev.opposing)}",
        f"Unresolved evidence ({unr_count}): {list(ev.unresolved)}",
    ]

    # Generate assessment
    support_ratio = sup_count / total if total > 0 else 0
    if total == 0:
        assessment = "Insufficient evidence to form a reliable assessment."
    elif support_ratio > 0.7:
        assessment = "Strong support: most evidence favors this hypothesis."
    elif support_ratio > 0.4:
        assessment = "Mixed evidence: hypothesis has both support and challenges."
    else:
        assessment = "Weak support: evidence predominantly challenges this hypothesis."

    output_parts = [
        f"Assessment: {assessment}",
        f"Evidence strength: {sup_count}/{total} supporting",
        f"Information need: {thought.metrics.information_need}",
        f"Expected value: {thought.metrics.expected_value}",
    ]

    input_text = "\n".join(input_parts)
    output_text = "\n".join(output_parts)

    metadata: dict[str, Any] = {}
    if config.include_metadata:
        metadata = {
            "thought_id": thought.thought_id,
            "confidence": thought.metrics.confidence,
            "evidence_total": total,
            "support_ratio": round(support_ratio, 3) if total > 0 else 0.0,
            "status": thought.status.state,
        }

    return TrainingExample(
        task="critique",
        system=system_prompt or config.system_prompt,
        input=input_text,
        output=output_text,
        metadata=metadata,
        content_hash="",
    )


def bridge_thought_synthesis(
    thought: ThoughtState,
    snapshot: PopulationSnapshot,
    *,
    config: BridgeConfig,
    system_prompt: str | None = None,
) -> TrainingExample:
    """Convert a ThoughtState with parents to a synthesis example.

    Input: parent hypotheses + evidence
    Output: child hypothesis (synthesis)
    """
    parent_thoughts: list[ThoughtState] = []
    for pid in thought.parent_ids:
        parent = snapshot.get(pid)
        if parent is not None:
            parent_thoughts.append(parent)

    input_parts: list[str] = []
    for i, pt in enumerate(parent_thoughts, 1):
        input_parts.append(f"Source {i}: {pt.hypothesis.claim}")
        ev = pt.evidence
        sup = len(ev.supporting)
        opp = len(ev.opposing)
        input_parts.append(f"  Evidence: {sup} supporting, {opp} opposing")
        input_parts.append(f"  Confidence: {pt.metrics.confidence}")

    output_parts = [
        f"Synthesized hypothesis: {thought.hypothesis.claim}",
        f"Confidence: {thought.metrics.confidence}",
    ]
    if thought.hypothesis.predicted_observations:
        output_parts.append("Combined predictions:")
        for obs in thought.hypothesis.predicted_observations:
            output_parts.append(f"  - {obs}")

    input_text = "\n".join(input_parts) if input_parts else "No parent thoughts available."
    output_text = "\n".join(output_parts)

    metadata: dict[str, Any] = {}
    if config.include_metadata:
        metadata = {
            "thought_id": thought.thought_id,
            "parent_ids": list(thought.parent_ids),
            "parent_count": len(parent_thoughts),
            "confidence": thought.metrics.confidence,
            "status": thought.status.state,
        }

    return TrainingExample(
        task="synthesis",
        system=system_prompt or config.system_prompt,
        input=input_text,
        output=output_text,
        metadata=metadata,
        content_hash="",
    )


# ---------------------------------------------------------------------------
# Aggregate bridge functions
# ---------------------------------------------------------------------------


def bridge_thought(
    thought: ThoughtState,
    snapshot: PopulationSnapshot | None = None,
    *,
    config: BridgeConfig | None = None,
) -> list[TrainingExample]:
    """Convert a single ThoughtState to all applicable training examples."""
    if config is None:
        config = BridgeConfig()

    examples: list[TrainingExample] = []

    for task_type in config.task_types:
        if task_type == "reasoning":
            examples.append(
                bridge_thought_reasoning(thought, config=config)
            )
        elif task_type == "verification":
            examples.append(
                bridge_thought_verification(thought, config=config)
            )
        elif task_type == "critique":
            examples.append(
                bridge_thought_critique(thought, config=config)
            )
        elif task_type == "synthesis":
            if thought.parent_ids and snapshot is not None:
                examples.append(
                    bridge_thought_synthesis(thought, snapshot, config=config)
                )
        elif task_type == "ecology_analysis":
            # Skip here; use bridge_ecology() separately
            pass

    return examples


def bridge_snapshot(
    snapshot: PopulationSnapshot,
    *,
    config: BridgeConfig | None = None,
) -> list[TrainingExample]:
    """Convert all thoughts in a PopulationSnapshot to training examples."""
    if config is None:
        config = BridgeConfig()

    all_examples: list[TrainingExample] = []
    for thought in snapshot.thoughts:
        all_examples.extend(
            bridge_thought(thought, snapshot, config=config)
        )
    return all_examples


def bridge_ecology(
    ecology: ThoughtEcology,
    snapshot: PopulationSnapshot,
    *,
    config: BridgeConfig | None = None,
) -> list[TrainingExample]:
    """Convert a ThoughtEcology to ecology analysis training examples."""
    if config is None:
        config = BridgeConfig()

    examples: list[TrainingExample] = []

    for tid in ecology.thought_ids:
        deps = ecology.dependencies_of(tid)
        contras = ecology.contradictions_of(tid)
        overlaps = ecology.overlaps_of(tid)
        assumptions = ecology.shared_assumptions_of(tid)

        # Skip isolated thoughts
        if not deps and not contras and not overlaps and not assumptions:
            continue

        thought = snapshot.get(tid)
        if thought is None:
            continue

        input_parts = [
            f"Thought: {tid}",
            f"Hypothesis: {thought.hypothesis.claim}",
        ]

        if deps:
            input_parts.append(f"Depends on: {[e.target_id for e in deps]}")
        if contras:
            contra_ids = []
            for e in contras:
                contra_ids.append(
                    e.second_id if e.first_id == tid else e.first_id
                )
            input_parts.append(f"Contradicts: {contra_ids}")
        if overlaps:
            overlap_ids = []
            for e in overlaps:
                overlap_ids.append(
                    e.second_id if e.first_id == tid else e.first_id
                )
            input_parts.append(f"Overlaps with: {overlap_ids}")
        if assumptions:
            input_parts.append(f"Shares assumptions: {len(assumptions)} links")

        output_parts = [f"Relationship analysis for {tid}:"]
        if deps:
            output_parts.append(f"  Dependencies: {len(deps)} upstream hypotheses")
        if contras:
            output_parts.append(f"  Contradictions: {len(contras)} conflicting hypotheses")
        if overlaps:
            output_parts.append(f"  Overlaps: {len(overlaps)} partially related hypotheses")
        if assumptions:
            output_parts.append(f"  Shared assumptions: {len(assumptions)} links")

        neighbors = ecology.neighborhood(tid)
        output_parts.append(f"  Total neighbors: {len(neighbors)}")

        input_text = "\n".join(input_parts)
        output_text = "\n".join(output_parts)

        metadata: dict[str, Any] = {}
        if config.include_metadata:
            metadata = {
                "thought_id": tid,
                "dependency_count": len(deps),
                "contradiction_count": len(contras),
                "overlap_count": len(overlaps),
                "assumption_link_count": len(assumptions),
                "neighbor_count": len(neighbors),
            }

        examples.append(
            TrainingExample(
                task="ecology_analysis",
                system=config.system_prompt,
                input=input_text,
                output=output_text,
                metadata=metadata,
                content_hash="",
            )
        )

    return examples


def bridge_evidence_packet(
    packet: EvidencePacket,
    *,
    config: BridgeConfig | None = None,
    system_prompt: str | None = None,
) -> TrainingExample:
    """Convert an EvidencePacket to a training example."""
    if config is None:
        config = BridgeConfig()

    input_parts = [
        f"Evidence ID: {packet.evidence_id}",
        f"Task: {packet.task_id}",
        f"Executor: {packet.executor_id}",
        f"Claim: {packet.claim}",
        f"Result: {packet.result}",
        f"Method: {packet.method}",
        f"Confidence: {packet.confidence}",
    ]
    if packet.limitations:
        input_parts.append(f"Limitations: {list(packet.limitations)}")
    if packet.failure_modes:
        input_parts.append(f"Failure modes: {list(packet.failure_modes)}")

    output_parts = [
        f"Evidence assessment for {packet.evidence_id}:",
        f"  Claim: {packet.claim}",
        f"  Confidence: {packet.confidence}",
        f"  Affected hypotheses: {list(packet.affected_hypotheses)}",
        f"  Provenance: {list(packet.provenance)}",
    ]

    input_text = "\n".join(input_parts)
    output_text = "\n".join(output_parts)

    metadata: dict[str, Any] = {}
    if config.include_metadata:
        metadata = {
            "evidence_id": packet.evidence_id,
            "task_id": packet.task_id,
            "confidence": packet.confidence,
            "affected_count": len(packet.affected_hypotheses),
        }

    return TrainingExample(
        task="evidence_assessment",
        system=system_prompt or config.system_prompt,
        input=input_text,
        output=output_text,
        metadata=metadata,
        content_hash="",
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def examples_to_jsonl(examples: list[TrainingExample]) -> str:
    """Serialize a list of TrainingExamples to JSONL format."""
    lines: list[str] = []
    for ex in examples:
        lines.append(ex.to_canonical_json())
    return "\n".join(lines) + "\n" if lines else ""
