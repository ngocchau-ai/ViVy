from orchestrator.decision_controller import Decision, DecisionContext, resolve


def test_halt_requires_independent_evidence():
    assert resolve(DecisionContext(Decision.HALT, True)) is Decision.CONTINUE
    assert resolve(DecisionContext(Decision.HALT, True, evidence_verified=True)) is Decision.HALT


def test_failures_escalate_then_backtrack():
    assert resolve(DecisionContext(Decision.CONTINUE, True, tool_failed=True)) is Decision.INCIDENT
    assert resolve(DecisionContext(Decision.CONTINUE, True, tool_failed=True, repeated_failure=True)) is Decision.BACKTRACK


def test_missing_evidence_and_budget_are_bounded():
    assert resolve(DecisionContext(Decision.FORAGE, False)) is Decision.DELEGATE
    assert resolve(DecisionContext(Decision.CONTINUE, True, rounds=10, max_rounds=10)) is Decision.DELEGATE
