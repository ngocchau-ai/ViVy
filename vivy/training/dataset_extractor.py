"""
Dataset Extractor — ViVy V6 & Cautreo Native Architecture (Sprint R3).

Ingests and normalizes training examples for ViVy Tiny Cognitive Brain (0.5B - 1.5B):
1. Cautreo Native Activity Logs (.vivy_activity.jsonl) -> Real verified execution traces.
2. Verdict 2.0 / openJev -> Decision state to acceptance gate & reward classification pairs.
3. LLaVA Multimodal Traces -> Multimodal alignment & instruction-to-directive pairs.

Exports to ChatML / ShareGPT formatted JSONL ready for Unsloth / LoRA fine-tuning.

Changelog:
    22/09/2026 (Antigravity IDE & Ngoc Chau — Sprint R3): Initial implementation.
    29/09/2026 (Claude Code — WP-6/O-10/F-H01…F-H04): removed fabricated
        hard-evidence labels.  See the [ISOLATED] block at the end of this file
        for the exact strings that used to be written into every sample.

[REPLACED 29/09/2026 · WP-6 / F-H01] — what changed and why
===========================================================
The pre-WP-6 extractor asserted, as if measured:

    Expected_Evidence: AST_VALID_AND_TEST_PASS          (activity-log path)
    Expected_Evidence: MULTIMODAL_GROUNDING_VERIFIED    (LLaVA path)
    Expected_Evidence: COGNITIVE_CONSENSUS_VERIFIED     (2Brain path)
    capture_id_matched: True                            (CUA path)

None of those is a real gate in a real system and none was ever verified.  A
model trained on them learns to *claim* verification.  Reward had the same
defect: ``1.0 if status != "ERROR"`` paid full reward for any run that merely
did not crash.

Rules now enforced (T9):
  * ``Expected_Evidence`` is copied from a field the source record actually
    carries, or it says ``UNVERIFIED``.  Never a constant invented here.
  * A sample is emitted only with an ``evidence_receipt_id``.  Without one it
    is dropped and counted — "mọi mẫu có evidence_receipt_id hoặc bị loại".
  * Reward is 0.0 without a receipt.  A run that did not crash is not a run
    that was verified.
  * ``export_jsonl`` runs ``training.dataset_audit.assert_exportable`` before
    writing, so a regression in an ingest path cannot reach an SFT file.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Mapping

from training.dataset_audit import (
    UNVERIFIED_EVIDENCE,
    assert_exportable,
    find_fabricated_labels,
)

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
    # [NEW 29/09/2026 · WP-6] the receipt that backs this sample.  None means
    # the sample is not exportable — see DatasetExtractor.is_exportable().
    evidence_receipt_id: str | None = None

    def to_chatml(self) -> dict[str, Any]:
        """Format as OpenAI / ChatML messages format."""
        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.user_prompt},
                {"role": "assistant", "content": self.assistant_response},
            ],
            "source": self.source,
            "reward": self.reward_score,
        }
        if self.evidence_receipt_id is not None:
            payload["evidence_receipt_id"] = self.evidence_receipt_id
        return payload

    def to_sharegpt(self) -> dict[str, Any]:
        """Format as ShareGPT format (conversations list)."""
        payload: dict[str, Any] = {
            "conversations": [
                {"from": "system", "value": self.system_prompt},
                {"from": "human", "value": self.user_prompt},
                {"from": "gpt", "value": self.assistant_response},
            ],
            "source": self.source,
            "reward": self.reward_score,
        }
        if self.evidence_receipt_id is not None:
            payload["evidence_receipt_id"] = self.evidence_receipt_id
        return payload


def _receipt_id(record: Mapping[str, Any]) -> str | None:
    """Pull a backing receipt id out of a source record, or None.

    Accepts the three spellings that actually occur in the wild.  Returns None
    rather than inventing an id — a missing receipt is a dropped sample, not a
    placeholder.
    """
    for key in ("evidence_receipt_id", "receipt_id"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    provenance = record.get("provenance")
    if isinstance(provenance, Mapping):
        value = provenance.get("receipt_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _evidence_from_record(record: Mapping[str, Any], key: str = "expected_evidence") -> str:
    """Copy ``Expected_Evidence`` from the record, or say UNVERIFIED.

    A non-empty *string* field is the record's own claim and is copied through
    verbatim.  Anything else — missing, a bool, a number — is not evidence, so
    the sample says so instead of borrowing a constant.
    """
    value = record.get(key)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if not find_fabricated_labels(text):
            return text
        logger.warning(
            "record carries a fabricated evidence label (%r); marking UNVERIFIED",
            text,
        )
    return UNVERIFIED_EVIDENCE


def _check_line(record: Mapping[str, Any], key: str) -> str:
    """Render a boolean check from the record, or admit it was not checked.

    ``capture_id_matched: True`` used to be written unconditionally.  Now it is
    written only when the record reports the check, and otherwise says so.
    """
    value = record.get(key)
    if value is None:
        return f"{key}: NOT_CHECKED"
    return f"{key}: {bool(value)}"


class DatasetExtractor:
    """Extracts, filters, and formats training data from multiple epistemic sources."""

    DEFAULT_SYSTEM_TEMPLATE = (
        "You are ViVy, the Executive Cognitive Operating System for the 91s workspace.\n"
        "Your role: think, decompose, and emit structured Action Directives within milliseconds.\n"
        "Format output with <vivy_thought> containing Epistemic_Decision and Expected_Evidence."
    )

    # --- T9 gate ------------------------------------------------------------
    @staticmethod
    def is_exportable(sample: TrainingSample) -> tuple[bool, str]:
        """(ok, reason). A sample exports only when it is receipt-backed and clean."""
        if not sample.evidence_receipt_id:
            return False, "missing_evidence_receipt_id"
        found = find_fabricated_labels(sample.assistant_response)
        if found:
            return False, "fabricated_evidence_label:" + ",".join(found)
        found = find_fabricated_labels(sample.user_prompt)
        if found:
            return False, "fabricated_evidence_label_in_prompt:" + ",".join(found)
        return True, "ok"

    @classmethod
    def _emit(
        cls,
        samples: list[TrainingSample],
        *,
        system_prompt: str,
        user_prompt: str,
        assistant_response: str,
        source: str,
        reward_score: float,
        metadata: dict[str, Any],
        evidence_receipt_id: str | None,
        dropped: dict[str, int],
    ) -> None:
        sample = TrainingSample(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            source=source,
            reward_score=reward_score,
            metadata=metadata,
            evidence_receipt_id=evidence_receipt_id,
        )
        ok, reason = cls.is_exportable(sample)
        if not ok:
            dropped[reason] = dropped.get(reason, 0) + 1
            logger.info("dropped %s sample (%s)", source, reason)
            return
        samples.append(sample)

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
        dropped: dict[str, int] = {}

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
                        receipt = _receipt_id(record)

                        # [REPLACED 29/09/2026 · WP-6] was:
                        #   reward = 1.0 if status != "ERROR" else 0.0
                        # Not crashing is not being verified.  Reward is paid
                        # only against a receipt that backs the run.
                        reward = 1.0 if (receipt and status != "ERROR") else 0.0
                        if reward >= min_reward and session_id in current_session:
                            user_prompt = f"Task Execution: {session_id}"
                            assistant_response = (
                                f"<vivy_thought>\n"
                                f"Epistemic_Decision: {decision}\n"
                                f"Expected_Evidence: {_evidence_from_record(record)}\n"
                                f"</vivy_thought>\n"
                                f"Directive: COMPLETED_WITH_{decision} in {rounds} rounds."
                            )
                            cls._emit(
                                samples,
                                system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                                user_prompt=user_prompt,
                                assistant_response=assistant_response,
                                source="cautreo_activity",
                                reward_score=reward,
                                metadata={"session_id": session_id, "rounds": rounds},
                                evidence_receipt_id=receipt,
                                dropped=dropped,
                            )
                            current_session.pop(session_id, None)
        except Exception as e:
            logger.error("Error reading activity log: %s", e)

        if dropped:
            logger.info("extract_from_activity_log dropped %s", dropped)
        return samples

    @classmethod
    def ingest_verdict_pairs(
        cls,
        verdict_records: list[dict[str, Any]],
    ) -> list[TrainingSample]:
        """Ingest Verdict 2.0 / openJev verification pairs."""
        samples: list[TrainingSample] = []
        dropped: dict[str, int] = {}

        for item in verdict_records:
            state = item.get("context_state", "")
            action = item.get("proposed_action", "")
            verdict = item.get("verdict", "PASS")
            score = float(item.get("score", 1.0 if verdict == "PASS" else 0.0))
            # The gate name is the record's own field; when absent we say so
            # rather than defaulting to DETERMINISTIC_PASS and calling it proof.
            acceptance_gate = _evidence_from_record(item, "acceptance_gate")
            receipt = _receipt_id(item)

            # High-scoring actions become positive SFT samples
            if score >= 0.7:
                assistant_response = (
                    f"<vivy_thought>\n"
                    f"Epistemic_Decision: EXECUTE_DIRECTLY\n"
                    f"Expected_Evidence: {acceptance_gate}\n"
                    f"</vivy_thought>\n"
                    f"ACTION_DIRECTIVE: {action}"
                )
                cls._emit(
                    samples,
                    system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                    user_prompt=f"Given state: {state}\nFormulate bounded action directive.",
                    assistant_response=assistant_response,
                    source="verdict_2.0",
                    reward_score=score if receipt else 0.0,
                    metadata={"acceptance_gate": acceptance_gate},
                    evidence_receipt_id=receipt,
                    dropped=dropped,
                )

        if dropped:
            logger.info("ingest_verdict_pairs dropped %s", dropped)
        return samples

    @classmethod
    def ingest_llava_traces(
        cls,
        llava_records: list[dict[str, Any]],
    ) -> list[TrainingSample]:
        """Ingest LLaVA multimodal instruction-to-directive traces."""
        samples: list[TrainingSample] = []
        dropped: dict[str, int] = {}

        for item in llava_records:
            instruction = item.get("instruction", item.get("prompt", ""))
            response = item.get("response", item.get("output", ""))
            modality = item.get("modality", "multimodal_vision")

            if not instruction or not response:
                continue

            receipt = _receipt_id(item)
            # [REPLACED 29/09/2026 · WP-6] was the constant
            # MULTIMODAL_GROUNDING_VERIFIED.  A LLaVA trace carries no
            # grounding-verification field, so the sample says UNVERIFIED.
            evidence = _evidence_from_record(item, "grounding_verified_as")
            assistant_response = (
                f"<vivy_thought>\n"
                f"Epistemic_Decision: EXECUTE_DIRECTLY\n"
                f"Expected_Evidence: {evidence}\n"
                f"</vivy_thought>\n"
                f"{response}"
            )

            cls._emit(
                samples,
                system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                user_prompt=instruction,
                assistant_response=assistant_response,
                source="llava_multimodal",
                reward_score=1.0 if receipt else 0.0,
                metadata={"modality": modality, "expected_evidence": evidence},
                evidence_receipt_id=receipt,
                dropped=dropped,
            )

        if dropped:
            logger.info("ingest_llava_traces dropped %s", dropped)
        return samples

    @classmethod
    def ingest_cua_trajectories(
        cls,
        cua_records: list[dict[str, Any]],
        min_reward: float = 0.7,
    ) -> list[TrainingSample]:
        """Ingest CUA (Computer-Use Agent) bounded candidate trajectories."""
        samples: list[TrainingSample] = []
        dropped: dict[str, int] = {}

        for record in cua_records:
            goal = record.get("goal", "Execute desktop task safely")
            screen_context = record.get("screen_context", "")
            candidates = record.get("candidates", [])
            selected_id = record.get("selected_id", "")
            postcondition = record.get("postcondition", "UI state transitioned successfully")
            postcondition_passed = record.get("postcondition_passed", True)
            # [REPLACED 29/09/2026 · WP-6] was:
            #   reward = float(record.get("reward", 1.0 if postcondition_passed else 0.0))
            # A record with no reward and no receipt is not a verified 1.0.
            receipt = _receipt_id(record)
            if "reward" in record:
                reward = float(record["reward"])
            elif receipt is not None and postcondition_passed:
                reward = 1.0
            else:
                reward = 0.0

            if reward < min_reward or not selected_id or not candidates:
                dropped["below_min_reward_or_incomplete"] = (
                    dropped.get("below_min_reward_or_incomplete", 0) + 1
                )
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
                f"  - {_check_line(record, 'capture_id_matched')}\n"
                f"  - postcondition: {postcondition}\n"
                f"</vivy_thought>\n"
                f"EXECUTE_CANDIDATE: {selected_id}"
            )

            cls._emit(
                samples,
                system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                source="cua_bounded_trajectory",
                reward_score=reward,
                metadata={
                    "selected_id": selected_id,
                    "candidate_count": len(candidates),
                    "postcondition": postcondition,
                    "capture_id_matched": record.get("capture_id_matched"),
                },
                evidence_receipt_id=receipt,
                dropped=dropped,
            )

        if dropped:
            logger.info("ingest_cua_trajectories dropped %s", dropped)
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
        dropped: dict[str, int] = {}
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

                    receipt = _receipt_id(item)
                    user_prompt = f"Problem: {prob}\n"
                    if hypotheses:
                        user_prompt += "Hypotheses:\n" + "\n".join(f"- H{i+1}: {h}" for i, h in enumerate(hypotheses)) + "\n"
                    if evidence:
                        user_prompt += "Evidence:\n" + "\n".join(f"- {e}" for e in evidence)

                    # [REPLACED 29/09/2026 · WP-6] was the constant
                    # COGNITIVE_CONSENSUS_VERIFIED.  The 2Brain trace records a
                    # decision and a confidence, not a verified consensus.
                    expected = _evidence_from_record(item, "consensus_verified_as")
                    assistant_response = (
                        f"<vivy_thought>\n"
                        f"Target: UNITARY_REASONER\n"
                        f"Epistemic_Decision: EXECUTE_DIRECTLY\n"
                        f"Confidence: {conf}\n"
                        f"Expected_Evidence: {expected}\n"
                        f"</vivy_thought>\n"
                        f"DECISION: {decision}"
                    )

                    cls._emit(
                        samples,
                        system_prompt=cls.DEFAULT_SYSTEM_TEMPLATE,
                        user_prompt=user_prompt.strip(),
                        assistant_response=assistant_response,
                        source="2brain_vicy_reasoning",
                        reward_score=conf if receipt else 0.0,
                        metadata={
                            "domain": domain,
                            "complexity": item.get("complexity", "standard"),
                            "expected_evidence": expected,
                        },
                        evidence_receipt_id=receipt,
                        dropped=dropped,
                    )
        except Exception as e:
            logger.error("Error reading 2Brain reasoning dataset: %s", e)

        if dropped:
            logger.info("ingest_2brain_reasoning dropped %s", dropped)
        return samples

    @staticmethod
    def export_jsonl(samples: list[TrainingSample], output_path: str, format_type: str = "chatml") -> int:
        """Export samples to JSONL file. Returns count of exported items.

        Raises :class:`training.dataset_audit.FabricatedLabelError` when any row
        asserts a hard-evidence label without a receipt, or carries no receipt
        at all (T9).  The gate runs on the *serialized* rows, so it also covers
        a caller that built TrainingSample by hand.
        """
        rows = [s.to_chatml() if format_type == "chatml" else s.to_sharegpt() for s in samples]
        assert_exportable(rows)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        count = 0

        with open(output_path, "w", encoding="utf-8") as f:
            for payload in rows:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                count += 1

        logger.info("Exported %d training samples to %s", count, output_path)
        return count


# [ISOLATED 29/09/2026 · WP-6 / F-H01] — the fabricated labels this file used to
# write into every sample, preserved verbatim per "cô lập, không xóa".  They are
# quoted here in a comment block on purpose: a comment is history, not behaviour.
# None of these may return to a live f-string or string literal.
#
#   extract_from_activity_log:
#       f"Expected_Evidence: AST_VALID_AND_TEST_PASS\n"
#       reward = 1.0 if status != "ERROR" else 0.0
#
#   ingest_llava_traces:
#       f"Expected_Evidence: MULTIMODAL_GROUNDING_VERIFIED\n"
#       reward_score=1.0                      (no receipt required)
#
#   ingest_2brain_reasoning:
#       f"Expected_Evidence: COGNITIVE_CONSENSUS_VERIFIED\n"
#
#   ingest_cua_trajectories:
#       f"  - capture_id_matched: True\n"     (written whether or not it matched)
#       reward = float(record.get("reward", 1.0 if postcondition_passed else 0.0))
#
#   ingest_verdict_pairs:
#       acceptance_gate = item.get("acceptance_gate", "DETERMINISTIC_PASS")
#       (a missing gate was silently called a deterministic pass)
#
# Enforcement: training/dataset_audit.py::FABRICATED_EVIDENCE_LABELS, and
# training/test_no_fabricated_labels.py.  If a test there fails, fix this file.
