"""
Dataset Extractor — ViVy V6 & Cautreo Native Architecture (Sprint R3).

Ingests and normalizes training examples for ViVy Tiny Cognitive Brain (0.5B - 1.5B):
1. Cautreo Native Activity Logs (.vivy_activity.jsonl) -> Real verified execution traces.
2. Verdict 2.0 / openJev -> Decision state to acceptance gate & reward classification pairs.
3. LLaVA Multimodal Traces -> Multimodal alignment & instruction-to-directive pairs.

Exports to ChatML / ShareGPT formatted JSONL ready for Unsloth / LoRA fine-tuning.

Changelog:
    22/09/2026 (Antigravity IDE & Ngoc Chau — Sprint R3): Initial implementation.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TrainingSample:
    """A single normalized training sample for ViVy Tiny Brain."""

    system_prompt: str
    user_prompt: str
    assistant_response: str
    source: str = "cautreo_activity"
    reward_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_chatml(self) -> dict[str, Any]:
        """Format as OpenAI / ChatML messages format."""
        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.user_prompt},
                {"role": "assistant", "content": self.assistant_response},
            ],
            "source": self.source,
            "reward": self.reward_score,
        }

    def to_sharegpt(self) -> dict[str, Any]:
        """Format as ShareGPT format (conversations list)."""
        return {
            "conversations": [
                {"from": "system", "value": self.system_prompt},
                {"from": "human", "value": self.user_prompt},
                {"from": "gpt", "value": self.assistant_response},
            ],
            "source": self.source,
            "reward": self.reward_score,
        }


class DatasetExtractor:
    """Extracts, filters, and formats training data from multiple epistemic sources."""

    DEFAULT_SYSTEM_TEMPLATE = (
        "You are ViVy, the Executive Cognitive Operating System for the 91s workspace.\n"
        "Your role: think, decompose, and emit structured Action Directives within milliseconds.\n"
        "Format output with <vivy_thought> containing Epistemic_Decision and Expected_Evidence."
    )

    @classmethod
    def extract_from_activity_log(
        cls,
        log_path: str,
        min_reward: float = 0.5,
    ) -> list[TrainingSample]:
        """Extract verified decision traces from Cautreo ActivityLog JSONL."""
        if not os.path.exists(log_path):
            logger.warning("Activity log not found: %s", log_path)
            return []

        samples: list[TrainingSample] = []
        current_session: dict[str, Any] = {}

        try:
            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    event = record.get("event")
                    session_id = record.get("session_id", "default")

                    if event == "inference_start":
                        current_session[session_id] = {
                            "task_id": record.get("task_id", session_id),
                            "input_type": record.get("input_type", "str"),
                            "decisions": [],
                        }
                    elif event == "decision_assessment":
                        if session_id in current_session:
                            current_session[session_id]["decisions"].append({
                                "requested": record.get("requested", "EXECUTE_DIRECTLY"),
                                "resolved": record.get("resolved", "CONTINUE"),
                                "expected_evidence": record.get("expected_evidence", True),
                            })
                    elif event == "inference_end":
                        status = record.get("status", "OBSERVED")
                        decision = record.get("decision", "EXECUTE_DIRECTLY")
                        rounds = record.get("rounds", 1)

                        reward = 1.0 if status != "ERROR" else 0.0
                        if reward >= min_reward and session_id in current_session:
                            user_prompt = f"Task Execution: {session_id}"
                            assistant_response = (
                                f"<vivy_thought>\n"
                                f"Epistemic_Decision: {decision}\n"
                                f"Expected_Evidence: AST_VALID_AND_TEST_PASS\n"
                                f"</vivy_thought>\n"
                                f"Directive: COMPLETED_WITH_{decision} in {rounds} rounds."
                            )
                            samples.append(TrainingSample(
                                system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                                user_prompt=user_prompt,
                                assistant_response=assistant_response,
                                source="cautreo_activity",
                                reward_score=reward,
                                metadata={"session_id": session_id, "rounds": rounds},
                            ))
                            current_session.pop(session_id, None)
        except Exception as e:
            logger.error("Error reading activity log: %s", e)

        return samples

    @classmethod
    def ingest_verdict_pairs(
        cls,
        verdict_records: list[dict[str, Any]],
    ) -> list[TrainingSample]:
        """Ingest Verdict 2.0 / openJev verification pairs."""
        samples: list[TrainingSample] = []

        for item in verdict_records:
            state = item.get("context_state", "")
            action = item.get("proposed_action", "")
            verdict = item.get("verdict", "PASS")
            score = float(item.get("score", 1.0 if verdict == "PASS" else 0.0))
            acceptance_gate = item.get("acceptance_gate", "DETERMINISTIC_PASS")

            # High-scoring actions become positive SFT samples
            if score >= 0.7:
                assistant_response = (
                    f"<vivy_thought>\n"
                    f"Epistemic_Decision: EXECUTE_DIRECTLY\n"
                    f"Expected_Evidence: {acceptance_gate}\n"
                    f"</vivy_thought>\n"
                    f"ACTION_DIRECTIVE: {action}"
                )
                samples.append(TrainingSample(
                    system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                    user_prompt=f"Given state: {state}\nFormulate bounded action directive.",
                    assistant_response=assistant_response,
                    source="verdict_2.0",
                    reward_score=score,
                    metadata={"acceptance_gate": acceptance_gate},
                ))

        return samples

    @classmethod
    def ingest_llava_traces(
        cls,
        llava_records: list[dict[str, Any]],
    ) -> list[TrainingSample]:
        """Ingest LLaVA multimodal instruction-to-directive traces."""
        samples: list[TrainingSample] = []

        for item in llava_records:
            instruction = item.get("instruction", item.get("prompt", ""))
            response = item.get("response", item.get("output", ""))
            modality = item.get("modality", "multimodal_vision")

            if not instruction or not response:
                continue

            assistant_response = (
                f"<vivy_thought>\n"
                f"Epistemic_Decision: EXECUTE_DIRECTLY\n"
                f"Expected_Evidence: MULTIMODAL_GROUNDING_VERIFIED\n"
                f"</vivy_thought>\n"
                f"{response}"
            )

            samples.append(TrainingSample(
                system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                user_prompt=instruction,
                assistant_response=assistant_response,
                source="llava_multimodal",
                reward_score=1.0,
                metadata={"modality": modality},
            ))

        return samples

    @classmethod
    def ingest_cua_trajectories(
        cls,
        cua_records: list[dict[str, Any]],
        min_reward: float = 0.7,
    ) -> list[TrainingSample]:
        """Ingest CUA (Computer-Use Agent) bounded candidate trajectories."""
        samples: list[TrainingSample] = []

        for record in cua_records:
            goal = record.get("goal", "Execute desktop task safely")
            screen_context = record.get("screen_context", "")
            candidates = record.get("candidates", [])
            selected_id = record.get("selected_id", "")
            postcondition = record.get("postcondition", "UI state transitioned successfully")
            postcondition_passed = record.get("postcondition_passed", True)
            reward = float(record.get("reward", 1.0 if postcondition_passed else 0.0))

            if reward < min_reward or not selected_id or not candidates:
                continue

            candidates_text = "\n".join(
                f"- [{c.get('id')}]: {c.get('description')} (action: {c.get('action')})"
                for c in candidates
            )

            user_prompt = (
                f"Task Goal: {goal}\n"
                f"Observation Context: {screen_context}\n"
                f"Bounded Candidate Table:\n{candidates_text}\n"
                f"Select the safest and most accurate candidate ID."
            )

            assistant_response = (
                f"<vivy_thought>\n"
                f"Target: CUA\n"
                f"Epistemic_Decision: BOUNDED_SELECTION\n"
                f"Selected_Candidate_ID: {selected_id}\n"
                f"Expected_Evidence:\n"
                f"  - capture_id_matched: True\n"
                f"  - postcondition: {postcondition}\n"
                f"</vivy_thought>\n"
                f"EXECUTE_CANDIDATE: {selected_id}"
            )

            samples.append(TrainingSample(
                system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                source="cua_bounded_trajectory",
                reward_score=reward,
                metadata={
                    "selected_id": selected_id,
                    "candidate_count": len(candidates),
                    "postcondition": postcondition,
                },
            ))

        return samples

    @classmethod
    def ingest_2brain_reasoning(
        cls,
        jsonl_path: str,
        limit: int = 400,
        min_confidence: float = 0.5,
    ) -> list[TrainingSample]:
        """Ingest structured cognitive reasoning traces from 2Brain vicy_v1 dataset."""
        if not os.path.exists(jsonl_path):
            logger.warning("2Brain reasoning dataset not found: %s", jsonl_path)
            return []

        samples: list[TrainingSample] = []
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    if len(samples) >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    conf = float(item.get("confidence", 0.8))
                    if conf < min_confidence:
                        continue

                    prob = item.get("problem", "")
                    hypotheses = item.get("hypotheses", [])
                    evidence = item.get("evidence", [])
                    decision = item.get("decision", "")
                    domain = item.get("domain", "cognitive_reasoning")

                    if not prob or not decision:
                        continue

                    user_prompt = f"Problem: {prob}\n"
                    if hypotheses:
                        user_prompt += "Hypotheses:\n" + "\n".join(f"- H{i+1}: {h}" for i, h in enumerate(hypotheses)) + "\n"
                    if evidence:
                        user_prompt += "Evidence:\n" + "\n".join(f"- {e}" for e in evidence)

                    assistant_response = (
                        f"<vivy_thought>\n"
                        f"Target: UNITARY_REASONER\n"
                        f"Epistemic_Decision: EXECUTE_DIRECTLY\n"
                        f"Confidence: {conf}\n"
                        f"Expected_Evidence: COGNITIVE_CONSENSUS_VERIFIED\n"
                        f"</vivy_thought>\n"
                        f"DECISION: {decision}"
                    )

                    samples.append(TrainingSample(
                        system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                        user_prompt=user_prompt.strip(),
                        assistant_response=assistant_response,
                        source="2brain_vicy_reasoning",
                        reward_score=conf,
                        metadata={"domain": domain, "complexity": item.get("complexity", "standard")},
                    ))
        except Exception as e:
            logger.error("Error reading 2Brain reasoning dataset: %s", e)

        return samples


    @staticmethod
    def export_jsonl(samples: list[TrainingSample], output_path: str, format_type: str = "chatml") -> int:
        """Export samples to JSONL file. Returns count of exported items."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        count = 0

        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                payload = sample.to_chatml() if format_type == "chatml" else sample.to_sharegpt()
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                count += 1

        logger.info("Exported %d training samples to %s", count, output_path)
        return count
