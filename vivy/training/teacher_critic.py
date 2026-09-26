"""
Teacher Critic Engine — ViVy V6 & Cautreo Native Architecture (Sprint R3).

Implements the Online / Post-Session Teacher Evaluator (Critic):
1. Evaluates ViVy's generated directives and thinking blocks across 3 axes:
   - Syntax Score: Validity of <vivy_thought> formatting, Epistemic_Decision, Expected_Evidence.
   - Routing Score: Accuracy of target component / model slot selection.
   - Efficiency Score: Latency, token economy, absence of repeated falsifications.
2. Supports External Teacher LLM via MiMo API (model: mimo-v2.5-pro) with deep reasoning critique.
3. Computes composite reward score and updates Cautreo Score Graph (ct_score_graph) in RAM.
4. Feeds back into CognitiveStateGraph error dampening (VM-11).

Changelog:
    22/09/2026 (Antigravity IDE & Ngoc Chau — Sprint R3): Initial implementation.
    22/09/2026 (Antigravity IDE & Ngoc Chau — Sprint R3): Added External MiMo 2.5 Pro Teacher Critic integration.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CriticEvaluation:
    """Detailed evaluation score card from the Teacher Critic."""

    syntax_score: float
    routing_score: float
    efficiency_score: float
    composite_score: float
    feedback_notes: list[str] = field(default_factory=list)
    recommended_penalties: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True if composite score meets the acceptance threshold."""
        return self.composite_score >= 0.75 and self.syntax_score >= 0.8


class MimoCriticClient:
    """Client for calling External Xiaomi MiMo API (mimo-v2.5-pro) as Teacher Critic."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("MIMO_API_KEY", "")
        self.model = model or os.getenv("MIMO_MODEL", "mimo-v2.5-pro")
        self.timeout = timeout

        # Determine endpoint: Token Plan keys (tp-*) use token-plan-sgp
        if api_base:
            self.api_base = api_base.rstrip("/")
        elif os.getenv("MIMO_API_BASE"):
            self.api_base = os.environ["MIMO_API_BASE"].rstrip("/")
        elif self.api_key.startswith("tp-"):
            self.api_base = "https://token-plan-sgp.xiaomimimo.com/v1"
        else:
            self.api_base = "https://api.xiaomimimo.com/v1"

    @property
    def is_available(self) -> bool:
        """Check if MiMo credentials are configured."""
        return bool(self.api_key.strip())

    def evaluate_with_teacher(
        self,
        task_text: str,
        output_text: str,
        tool_results: list[dict[str, Any]] | None = None,
        elapsed_ms: float = 50.0,
    ) -> CriticEvaluation:
        """Send prompt to MiMo 2.5 Pro Teacher Critic and parse evaluation."""
        if not self.is_available:
            raise ValueError("MIMO_API_KEY is not configured.")

        system_prompt = (
            "You are the Senior AI Teacher and Architecture Critic for ViVy Core.\n"
            "Evaluate ViVy's generated reasoning and execution directive strictly.\n"
            "Scoring Axes (0.0 to 1.0):\n"
            "- syntax_score: Has valid <vivy_thought> with Epistemic_Decision and Expected_Evidence.\n"
            "- routing_score: Accurate component delegation (e.g. coding tasks routed to code specialist or direct execute).\n"
            "- efficiency_score: Concise token usage, fast latency, no unnecessary foraging.\n"
            "Return ONLY a JSON object with this schema:\n"
            "{\n"
            '  "syntax_score": float,\n'
            '  "routing_score": float,\n'
            '  "efficiency_score": float,\n'
            '  "composite_score": float,\n'
            '  "feedback_notes": [string],\n'
            '  "recommended_penalties": [string],\n'
            '  "critique_summary": string\n'
            "}"
        )

        user_content = (
            f"Task: {task_text}\n\n"
            f"Execution Latency: {elapsed_ms:.1f}ms\n"
            f"Tool Results: {json.dumps(tool_results or [])}\n\n"
            f"ViVy Output to Evaluate:\n{output_text}\n"
        )

        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 1024,
            "temperature": 0.1,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]["message"]
                content = choice.get("content", "")
                reasoning = choice.get("reasoning_content", "")

                # Extract JSON from content
                json_match = re.search(r"\{[\s\S]*\}", content)
                if not json_match:
                    raise ValueError(f"Teacher response does not contain JSON: {content[:200]}")

                parsed = json.loads(json_match.group(0))

                return CriticEvaluation(
                    syntax_score=float(parsed.get("syntax_score", 0.0)),
                    routing_score=float(parsed.get("routing_score", 0.0)),
                    efficiency_score=float(parsed.get("efficiency_score", 0.0)),
                    composite_score=round(float(parsed.get("composite_score", 0.0)), 3),
                    feedback_notes=parsed.get("feedback_notes", []),
                    recommended_penalties=parsed.get("recommended_penalties", []),
                    metadata={
                        "teacher_model": self.model,
                        "teacher_reasoning": reasoning,
                        "critique_summary": parsed.get("critique_summary", ""),
                        "elapsed_ms": elapsed_ms,
                        "source": "mimo-2.5pro",
                    },
                )
        except Exception as e:
            logger.warning("MiMo Teacher Critic request failed: %s", e)
            raise


class TeacherCritic:
    """Evaluates ViVy actions using External MiMo 2.5 Pro API or Local Heuristics."""

    VIVY_THOUGHT_PATTERN = re.compile(
        r"<vivy_thought>([\s\S]*?)</vivy_thought>",
        re.IGNORECASE,
    )
    DECISION_PATTERN = re.compile(
        r"Epistemic_Decision\s*:\s*(EXECUTE_DIRECTLY|NEED_KNOWLEDGE_FORAGING|DELEGATE_MODEL)",
        re.IGNORECASE,
    )
    EVIDENCE_PATTERN = re.compile(
        r"Expected_Evidence\s*:\s*([^\n\r]+)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        weight_syntax: float = 0.3,
        weight_routing: float = 0.4,
        weight_efficiency: float = 0.3,
        use_mimo_api: bool = True,
        mimo_client: MimoCriticClient | None = None,
    ) -> None:
        self.w_syntax = weight_syntax
        self.w_routing = weight_routing
        self.w_efficiency = weight_efficiency
        self.use_mimo_api = use_mimo_api
        self.mimo_client = mimo_client or MimoCriticClient()

    def evaluate_output(
        self,
        task_text: str,
        output_text: str,
        tool_results: list[dict[str, Any]] | None = None,
        elapsed_ms: float = 50.0,
        force_local: bool = False,
    ) -> CriticEvaluation:
        """Evaluate a model output text across syntax, routing, and efficiency.

        Attempts external MiMo 2.5 Pro evaluation first if enabled and configured;
        falls back to deterministic local rule evaluation on failure or offline mode.
        """
        if self.use_mimo_api and not force_local and self.mimo_client.is_available:
            try:
                return self.mimo_client.evaluate_with_teacher(
                    task_text=task_text,
                    output_text=output_text,
                    tool_results=tool_results,
                    elapsed_ms=elapsed_ms,
                )
            except Exception as exc:
                logger.warning("Falling back to local TeacherCritic heuristics due to: %s", exc)

        return self._evaluate_local(task_text, output_text, tool_results, elapsed_ms)

    def _evaluate_local(
        self,
        task_text: str,
        output_text: str,
        tool_results: list[dict[str, Any]] | None = None,
        elapsed_ms: float = 50.0,
    ) -> CriticEvaluation:
        """Deterministic local rule-based evaluation."""
        notes: list[str] = []
        penalties: list[str] = []

        # 1. Evaluate Syntax
        syntax_score = 0.0
        thought_match = self.VIVY_THOUGHT_PATTERN.search(output_text)
        if thought_match:
            thought_body = thought_match.group(1)
            has_decision = bool(self.DECISION_PATTERN.search(thought_body))
            has_evidence = bool(self.EVIDENCE_PATTERN.search(thought_body))
            if has_decision and has_evidence:
                syntax_score = 1.0
                notes.append("Syntax: Valid <vivy_thought> with Decision and Evidence.")
            elif has_decision:
                syntax_score = 0.7
                notes.append("Syntax: Missing explicit Expected_Evidence.")
            else:
                syntax_score = 0.4
                notes.append("Syntax: Missing Epistemic_Decision.")
        else:
            syntax_score = 0.0
            notes.append("Syntax: No <vivy_thought> block found.")
            penalties.append("Missing <vivy_thought> block")

        # 2. Evaluate Routing
        routing_score = 0.8  # default baseline
        lower_task = task_text.lower()
        lower_out = output_text.lower()

        # Check if task is coding MT5/Python
        if any(k in lower_task for k in ["code", "script", "python", "mt5"]):
            if "code_py" in lower_out or "execute_directly" in lower_out or "delegate_model" in lower_out:
                routing_score = 1.0
                notes.append("Routing: Properly identified coding execution/delegation.")
            elif "forage" in lower_out:
                routing_score = 0.6
                notes.append("Routing: Unnecessary knowledge foraging for known coding task.")
            else:
                routing_score = 0.3
                penalties.append("Failed to route coding task to code specialist")

        # 3. Evaluate Efficiency
        efficiency_score = 1.0
        # Penalize if tools failed
        if tool_results:
            failed_count = sum(1 for tr in tool_results if not tr.get("ok", True))
            if failed_count > 0:
                penalty_ratio = failed_count / len(tool_results)
                efficiency_score = max(0.0, 1.0 - penalty_ratio)
                notes.append(f"Efficiency: {failed_count} tool call(s) failed.")
                penalties.append(f"Tool failure count: {failed_count}")

        # Penalize if latency is excessively high (>10s for single directive)
        if elapsed_ms > 10000.0:
            efficiency_score *= 0.7
            notes.append(f"Efficiency: High latency {elapsed_ms:.1f}ms.")

        composite = (
            self.w_syntax * syntax_score
            + self.w_routing * routing_score
            + self.w_efficiency * efficiency_score
        )

        return CriticEvaluation(
            syntax_score=syntax_score,
            routing_score=routing_score,
            efficiency_score=efficiency_score,
            composite_score=round(composite, 3),
            feedback_notes=notes,
            recommended_penalties=penalties,
            metadata={"elapsed_ms": elapsed_ms, "source": "local_heuristics"},
        )

    def sync_to_cautreo(
        self,
        evaluation: CriticEvaluation,
        cautreo_memory: Any | None = None,
        node_id: str | None = None,
    ) -> bool:
        """Sync evaluation result to Cautreo Score Graph and Context Memory."""
        if cautreo_memory is None:
            return False

        try:
            # If CautreoContextMemory has store_hard_fact or update_score
            if hasattr(cautreo_memory, "store_hard_fact") and node_id:
                score_str = f"score={evaluation.composite_score:.2f}|pass={evaluation.passed}|source={evaluation.metadata.get('source', 'local')}"
                cautreo_memory.store_hard_fact(f"eval_{node_id}", score_str)
                logger.info("Synced critic evaluation for node %s to Cautreo memory", node_id)
                return True
        except Exception as e:
            logger.debug("Cautreo sync skipped: %s", e)

        return False
