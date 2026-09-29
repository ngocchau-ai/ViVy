"""Regression tests for WP-2 / O-03 — loop control (F-B01, F-B02, F-B03).

Pins the three findings the review measured in the activity log
(15/15 ``inference_end`` with ``rounds: 10`` and ``decision: DELEGATE``):

* **F-B01** a tool-free answer must not spin to ``max_rounds``;
* **F-B02** CHAT/BATCH must not report ``DELEGATE`` just because they run one round;
* **F-B03** a missing ``Epistemic_Decision`` field must fail closed, not become
  ``EXECUTE_DIRECTLY``.

Plus the ``resolve()`` contract that makes ``HALT`` reachable at all.
"""

from __future__ import annotations

from integration.llama_cpp_bridge import ChatResponse
from integration.session_manager import SessionManager
from integration.task_state import TaskState
from integration.vivy_inference_loop import InferenceMode, VivyInferenceLoop
from orchestrator.decision_controller import Decision, DecisionContext, resolve

# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


def _response(content: str, tool_calls: list | None = None, finish_reason: str = "stop") -> ChatResponse:
    return ChatResponse(
        content=content,
        tool_calls=list(tool_calls or []),
        finish_reason=finish_reason,
        prompt_tokens=10,
        completion_tokens=5,
        elapsed_ms=1.0,
        raw={},
    )


def _thought(decision: str, expected: str = "a typed tool result") -> str:
    return (
        f"<vivy_thought>\nEpistemic_Decision: {decision}\n"
        f"Expected_Evidence: {expected}\n</vivy_thought>\nanswer body"
    )


class _FakeBridge:
    """Deterministic LLM stand-in that counts how many rounds the loop ran."""

    def __init__(self, responses: list[ChatResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def chat_safe(self, messages, epistemic_decision=None):  # noqa: ANN001, ARG002
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return _response(_thought("EXECUTE_DIRECTLY"))


def _loop(responses: list[ChatResponse]) -> tuple[VivyInferenceLoop, _FakeBridge, object]:
    bridge = _FakeBridge(responses)
    loop = VivyInferenceLoop(  # type: ignore[arg-type]
        bridge=bridge,
        session_manager=SessionManager(hidden_dim=64),
        max_agentic_rounds=10,
    )
    session = loop._sessions.create_session()
    return loop, bridge, session  # type: ignore[return-value]


def _task() -> TaskState:
    return TaskState(task_id="t-wp2", goal="answer a simple question", observation="obs")


# ---------------------------------------------------------------------------
# F-B03 — parse is fail-closed
# ---------------------------------------------------------------------------


def test_parse_epistemic_decision_reads_known_values() -> None:
    parse = VivyInferenceLoop._parse_epistemic_decision
    assert parse(_thought("EXECUTE_DIRECTLY")) == "EXECUTE_DIRECTLY"
    assert parse(_thought("NEED_KNOWLEDGE_FORAGING")) == "NEED_KNOWLEDGE_FORAGING"
    assert parse(_thought("DELEGATE_MODEL")) == "DELEGATE_MODEL"


def test_parse_epistemic_decision_fails_closed_on_missing_field() -> None:
    """F-B03: a missing field used to return EXECUTE_DIRECTLY (fail-open)."""
    parse = VivyInferenceLoop._parse_epistemic_decision
    assert parse("just an answer, no thought block") == ""
    assert parse("") == ""
    assert parse("<vivy_thought>Epistemic_Decision: SOMETHING_ELSE</vivy_thought>") == ""


def test_unparsed_decision_maps_to_delegate_not_execute() -> None:
    """The caller's map default must be live and fail-closed."""
    requested = VivyInferenceLoop._parse_epistemic_decision("no thought block")
    requested_map = {
        "EXECUTE_DIRECTLY": Decision.CONTINUE,
        "NEED_KNOWLEDGE_FORAGING": Decision.FORAGE,
        "DELEGATE_MODEL": Decision.DELEGATE,
    }
    assert requested not in requested_map
    assert requested_map.get(requested, Decision.DELEGATE) is Decision.DELEGATE


# ---------------------------------------------------------------------------
# F-B01 — HALT is reachable; the tool-free loop must not spin
# ---------------------------------------------------------------------------


def test_resolve_halts_when_evidence_verified() -> None:
    """F-B01: HALT was unreachable because evidence_verified was never supplied."""
    ctx = DecisionContext(
        requested=Decision.CONTINUE,
        has_expected_evidence=True,
        evidence_verified=True,
    )
    assert resolve(ctx) is Decision.HALT


def test_resolve_safety_precedence_beats_verified_evidence() -> None:
    """A failed tool still blocks: INCIDENT/BACKTRACK outrank HALT."""
    assert resolve(
        DecisionContext(Decision.CONTINUE, True, evidence_verified=True, tool_failed=True)
    ) is Decision.INCIDENT
    assert resolve(
        DecisionContext(
            Decision.CONTINUE, True, evidence_verified=True,
            tool_failed=True, repeated_failure=True,
        )
    ) is Decision.BACKTRACK


def test_verified_evidence_does_not_override_a_request_for_more_work() -> None:
    """T4: 0/30 false-halt.  A model asking to FORAGE/DELEGATE is not finished.

    Overriding that request into HALT just because it named an Expected_Evidence
    target is a false-halt — the very failure T4 measures.  The provisional
    ``evidence_verified`` signal is narrow on purpose until WP-8 replaces it
    with a real EvidencePacket verdict.
    """
    for more_work in (Decision.FORAGE, Decision.DELEGATE, Decision.BACKTRACK):
        ctx = DecisionContext(
            requested=more_work,
            has_expected_evidence=True,
            evidence_verified=True,
        )
        assert resolve(ctx) is more_work, f"{more_work} was overridden into a false-halt"


def test_tool_free_answer_stops_after_one_round() -> None:
    """F-B01: a tool-free answer used to run to max_rounds (log: 15/15 rounds=10)."""
    loop, bridge, session = _loop([_response(_thought("EXECUTE_DIRECTLY"))])
    result = loop._run_pipeline(
        messages=[], session=session, mode=InferenceMode.AGENTIC, task_state=_task()
    )
    assert bridge.calls == 1, f"expected 1 LLM call, got {bridge.calls}"
    assert result.rounds == 1, f"expected rounds=1, got {result.rounds}"
    assert result.epistemic_decision in {Decision.HALT.value, Decision.CONTINUE.value}


def test_delegate_decision_does_not_reloop() -> None:
    """DELEGATE means hand off — it must not ask for 'the next bounded action'."""
    loop, bridge, session = _loop([_response(_thought("DELEGATE_MODEL"))])
    result = loop._run_pipeline(
        messages=[], session=session, mode=InferenceMode.AGENTIC, task_state=_task()
    )
    assert bridge.calls == 1
    assert result.rounds == 1


def test_forage_may_request_another_round() -> None:
    """FORAGE genuinely needs more work, so a second round is legitimate."""
    loop, bridge, session = _loop([
        _response(_thought("NEED_KNOWLEDGE_FORAGING")),
        _response(_thought("EXECUTE_DIRECTLY")),
    ])
    result = loop._run_pipeline(
        messages=[], session=session, mode=InferenceMode.AGENTIC, task_state=_task()
    )
    assert bridge.calls == 2
    assert result.rounds == 2


# ---------------------------------------------------------------------------
# F-B02 — single-round modes must not always report DELEGATE
# ---------------------------------------------------------------------------


def test_single_round_context_does_not_forced_delegate() -> None:
    """F-B02: rounds >= max_rounds fired on round 1 for CHAT/BATCH."""
    ctx = DecisionContext(
        requested=Decision.CONTINUE,
        has_expected_evidence=True,
        rounds=1,
        max_rounds=1,
        single_round=True,
    )
    assert resolve(ctx) is Decision.CONTINUE


def test_single_round_skips_missing_evidence_delegate() -> None:
    """A chat answer without an evidence contract is not a loop hand-off."""
    ctx = DecisionContext(
        requested=Decision.CONTINUE,
        has_expected_evidence=False,
        single_round=True,
    )
    assert resolve(ctx) is Decision.CONTINUE


def test_multi_round_still_honours_budget_and_evidence_contract() -> None:
    """The loop-governance rules still apply when single_round is False."""
    assert resolve(
        DecisionContext(Decision.CONTINUE, True, rounds=10, max_rounds=10)
    ) is Decision.DELEGATE
    assert resolve(DecisionContext(Decision.FORAGE, False)) is Decision.DELEGATE


def test_budget_exhausted_override_wins_over_rounds() -> None:
    """An explicit budget_exhausted=True hands off even with rounds remaining."""
    assert resolve(
        DecisionContext(
            Decision.CONTINUE, True, rounds=1, max_rounds=10, budget_exhausted=True
        )
    ) is Decision.DELEGATE
    assert resolve(
        DecisionContext(
            Decision.CONTINUE, True, rounds=10, max_rounds=10, budget_exhausted=False
        )
    ) is Decision.CONTINUE


def test_chat_mode_reports_model_request_not_delegate() -> None:
    """End-to-end: a CHAT round must report CONTINUE/HALT, never forced DELEGATE."""
    loop, bridge, session = _loop([_response(_thought("EXECUTE_DIRECTLY"))])
    result = loop._run_pipeline(
        messages=[], session=session, mode=InferenceMode.CHAT, task_state=_task()
    )
    assert bridge.calls == 1
    assert result.rounds == 1
    assert result.epistemic_decision != Decision.DELEGATE.value
