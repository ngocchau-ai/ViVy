"""
Unit tests for ViVy Training Pipeline — Dataset Extractor & Teacher Critic (Sprint R3).
"""

import json
import os
from unittest.mock import MagicMock

import pytest

from training.dataset_extractor import DatasetExtractor, TrainingSample
from training.teacher_critic import CriticEvaluation, TeacherCritic


def test_training_sample_formats():
    sample = TrainingSample(
        system_prompt="Base prompt",
        user_prompt="Write MT5 connector",
        assistant_response="<vivy_thought>Done</vivy_thought>",
        source="test_source",
        reward_score=0.9,
    )
    chatml = sample.to_chatml()
    assert len(chatml["messages"]) == 3
    assert chatml["messages"][0]["role"] == "system"
    assert chatml["reward"] == 0.9

    sharegpt = sample.to_sharegpt()
    assert len(sharegpt["conversations"]) == 3
    assert sharegpt["conversations"][1]["from"] == "human"


def test_dataset_extractor_from_activity_log(tmp_path):
    """[REWRITTEN 29/09/2026 · WP-6/F-H01 · hard rule #4 receipt]

    Receipt for the rewrite: these tests used to pin the *fabrication*.  The
    old fixture produced one sample whose ``Expected_Evidence`` was the
    hardcoded ``AST_VALID_AND_TEST_PASS`` and whose reward was ``1.0 if status
    != "ERROR"`` — i.e. it asserted that a run with no receipt and no evidence
    field was a fully-verified positive sample.  That is exactly the F-H01
    defect the plan removes, and the old assertion is not a spec any more.
    New spec (plan WP-6 acceptance / T9): a record with no ``evidence_receipt_id``
    yields **no** sample; adding a receipt yields one, whose evidence text comes
    from the record (or says ``UNVERIFIED``) and is never a constant.
    """
    log_file = tmp_path / "activity.jsonl"
    records = [
        {"event": "inference_start", "session_id": "s1", "input_type": "str"},
        {"event": "decision_assessment", "session_id": "s1", "requested": "EXECUTE_DIRECTLY", "expected_evidence": True},
        {"event": "inference_end", "session_id": "s1", "status": "OBSERVED", "decision": "EXECUTE_DIRECTLY", "rounds": 1},
    ]
    with open(log_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # No receipt -> nothing to train on.  Not crashing is not being verified.
    assert DatasetExtractor.extract_from_activity_log(str(log_file)) == []

    records[-1]["evidence_receipt_id"] = "oracle-deadbeefcafe"
    records[-1]["expected_evidence"] = "pytest passed (42 tests)"
    with open(log_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    samples = DatasetExtractor.extract_from_activity_log(str(log_file))
    assert len(samples) == 1
    assert samples[0].source == "cautreo_activity"
    assert samples[0].evidence_receipt_id == "oracle-deadbeefcafe"
    assert "EXECUTE_DIRECTLY" in samples[0].assistant_response
    assert "pytest passed (42 tests)" in samples[0].assistant_response
    assert "AST_VALID_AND_TEST_PASS" not in samples[0].assistant_response


def test_dataset_extractor_verdict_and_llava():
    """[REWRITTEN 29/09/2026 · WP-6/F-H01 · hard rule #4 receipt]

    Receipt: the old form asserted one sample per path with no receipt at all,
    and the LLaVA sample's evidence was the hardcoded
    ``MULTIMODAL_GROUNDING_VERIFIED``.  New spec (T9): no receipt -> dropped;
    with a receipt the gate name is the record's own field and a missing one
    says ``UNVERIFIED`` instead of defaulting to a constant.
    """
    verdict_data = [
        {
            "context_state": "MT5 script syntax error in OnTick()",
            "proposed_action": "Fix variable scope in OnTick() handler",
            "verdict": "PASS",
            "score": 0.95,
            "acceptance_gate": "MQL5_COMPILER_PASS",
            "evidence_receipt_id": "oracle-deadbeefcafe",
        },
        {
            "context_state": "Unknown state",
            "proposed_action": "Do random action",
            "verdict": "FAIL",
            "score": 0.2,
            "evidence_receipt_id": "oracle-deadbeefcafe",
        },
        {
            "context_state": "MT5 script syntax error in OnTick()",
            "proposed_action": "Fix variable scope in OnTick() handler",
            "verdict": "PASS",
            "score": 0.95,
            "acceptance_gate": "MQL5_COMPILER_PASS",
            # no receipt -> dropped
        },
    ]
    samples = DatasetExtractor.ingest_verdict_pairs(verdict_data)
    assert len(samples) == 1  # high score AND receipt backed
    assert samples[0].source == "verdict_2.0"
    assert samples[0].evidence_receipt_id == "oracle-deadbeefcafe"
    assert "MQL5_COMPILER_PASS" in samples[0].assistant_response

    llava_data = [
        {"instruction": "Analyze this chart snapshot", "response": "Action: Bullish breakout on M15",
         "evidence_receipt_id": "oracle-deadbeefcafe"},
        {"instruction": "No receipt here", "response": "should be dropped"},
    ]
    llava_samples = DatasetExtractor.ingest_llava_traces(llava_data)
    assert len(llava_samples) == 1
    assert llava_samples[0].source == "llava_multimodal"
    assert llava_samples[0].evidence_receipt_id == "oracle-deadbeefcafe"
    assert "MULTIMODAL_GROUNDING_VERIFIED" not in llava_samples[0].assistant_response
    assert "UNVERIFIED" in llava_samples[0].assistant_response


def test_dataset_extractor_cua_trajectories():
    """[REWRITTEN 29/09/2026 · WP-6/F-H01 · hard rule #4 receipt]

    Receipt: the old form asserted a CUA sample whose ``Expected_Evidence``
    carried the hardcoded ``capture_id_matched: True`` even though the record
    never ran that check.  New spec (T9): a trajectory with no receipt is
    dropped whatever its ``reward`` says, and a check the record did not report
    is written as ``NOT_CHECKED``, not as a pass.
    """
    cua_records = [
        {
            "goal": "Click submit button on checkout form",
            "screen_context": "Checkout page loaded, submit button visible at bottom",
            "candidates": [
                {"id": "cand_01", "description": "Click Submit button", "action": "click"},
                {"id": "cand_02", "description": "Click Cancel button", "action": "click"},
            ],
            "selected_id": "cand_01",
            "postcondition": "Order confirmed and receipt displayed",
            "postcondition_passed": True,
            "reward": 0.95,
            "evidence_receipt_id": "oracle-deadbeefcafe",
        },
        {
            "goal": "Unsafe action",
            "candidates": [{"id": "cand_01", "description": "Do unsafe"}],
            "selected_id": "cand_01",
            "reward": 0.2,  # Should be filtered out (< 0.7)
            "evidence_receipt_id": "oracle-deadbeefcafe",
        },
        {
            "goal": "High reward but unbacked",
            "candidates": [{"id": "cand_01", "description": "do it", "action": "click"}],
            "selected_id": "cand_01",
            "postcondition": "done",
            "postcondition_passed": True,
            "reward": 0.95,  # no receipt -> dropped
        },
    ]

    samples = DatasetExtractor.ingest_cua_trajectories(cua_records)
    assert len(samples) == 1
    assert samples[0].source == "cua_bounded_trajectory"
    assert samples[0].evidence_receipt_id == "oracle-deadbeefcafe"
    assert "BOUNDED_SELECTION" in samples[0].assistant_response
    assert "cand_01" in samples[0].assistant_response
    assert "Order confirmed" in samples[0].assistant_response
    assert "capture_id_matched: True" not in samples[0].assistant_response
    assert "capture_id_matched: NOT_CHECKED" in samples[0].assistant_response


def test_dataset_extractor_cua_reports_a_real_capture_result(tmp_path):
    """A record that actually reports the check keeps its own value."""
    cua_records = [
        {
            "goal": "g",
            "screen_context": "s",
            "candidates": [{"id": "cand_01", "description": "d", "action": "click"}],
            "selected_id": "cand_01",
            "postcondition": "done",
            "reward": 0.95,
            "capture_id_matched": False,
            "evidence_receipt_id": "oracle-deadbeefcafe",
        },
    ]
    samples = DatasetExtractor.ingest_cua_trajectories(cua_records)
    assert len(samples) == 1
    assert "capture_id_matched: False" in samples[0].assistant_response


def test_dataset_extractor_export(tmp_path):
    """[REWRITTEN 29/09/2026 · WP-6/F-H01 · hard rule #4 receipt]

    Receipt: the old form exported a hand-built ``TrainingSample`` with no
    receipt and asserted ``count == 1``.  New spec (T9): ``export_jsonl`` runs
    ``assert_exportable`` on the serialized rows and refuses anything that is
    not receipt-backed, so a hand-built sample cannot reach an SFT file.
    """
    sample = TrainingSample(
        system_prompt="sys",
        user_prompt="usr",
        assistant_response="ast",
    )
    out_file = tmp_path / "out.jsonl"
    with pytest.raises(Exception, match="evidence_receipt_id"):
        DatasetExtractor.export_jsonl([sample], str(out_file))
    assert not out_file.exists()

    backed = TrainingSample(
        system_prompt="sys",
        user_prompt="usr",
        assistant_response="Expected_Evidence: UNVERIFIED",
        evidence_receipt_id="oracle-deadbeefcafe",
    )
    count = DatasetExtractor.export_jsonl([backed], str(out_file))
    assert count == 1
    assert os.path.exists(out_file)


def test_teacher_critic_evaluation():
    critic = TeacherCritic()

    # Valid output
    valid_output = (
        "<vivy_thought>\n"
        "Epistemic_Decision: EXECUTE_DIRECTLY\n"
        "Expected_Evidence: AST_PASS\n"
        "</vivy_thought>\n"
        "Executing code_py MT5 bridge connector."
    )
    eval_result = critic.evaluate_output(
        task_text="Write a python script for MT5",
        output_text=valid_output,
        elapsed_ms=45.0,
        force_local=True,
    )
    assert eval_result.syntax_score == 1.0
    assert eval_result.routing_score == 1.0
    assert eval_result.efficiency_score == 1.0
    assert eval_result.composite_score >= 0.9
    assert eval_result.passed is True

    # Output missing thought block
    bad_output = "Just standard text without vivy thought block."
    bad_eval = critic.evaluate_output(
        task_text="Write python code",
        output_text=bad_output,
        force_local=True,
    )
    assert bad_eval.syntax_score == 0.0
    assert bad_eval.passed is False
    assert "Missing <vivy_thought> block" in bad_eval.recommended_penalties


def test_teacher_critic_sync_cautreo():
    critic = TeacherCritic()
    mock_memory = MagicMock()
    eval_result = CriticEvaluation(
        syntax_score=1.0,
        routing_score=1.0,
        efficiency_score=1.0,
        composite_score=1.0,
    )
    synced = critic.sync_to_cautreo(eval_result, cautreo_memory=mock_memory, node_id="node_123")
    assert synced is True
    mock_memory.store_hard_fact.assert_called_once()


def test_mimo_critic_endpoint_selection():
    from training.teacher_critic import MimoCriticClient

    client_tp = MimoCriticClient(api_key="tp-123456")
    assert client_tp.api_base == "https://token-plan-sgp.xiaomimimo.com/v1"

    client_sk = MimoCriticClient(api_key="sk-123456")
    assert client_sk.api_base == "https://api.xiaomimimo.com/v1"

    client_custom = MimoCriticClient(api_key="tp-123", api_base="https://my.custom.endpoint/v1")
    assert client_custom.api_base == "https://my.custom.endpoint/v1"


def test_mimo_critic_client_mock(monkeypatch):
    from unittest.mock import MagicMock

    from training.teacher_critic import MimoCriticClient

    mock_resp_json = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '```json\n{\n  "syntax_score": 0.95,\n  "routing_score": 0.9,\n  "efficiency_score": 0.85,\n  "composite_score": 0.90,\n  "feedback_notes": ["Good formatting"],\n  "recommended_penalties": [],\n  "critique_summary": "Passed"\n}\n```',
                    "reasoning_content": "Detailed thinking critique from MiMo 2.5 Pro.",
                }
            }
        ]
    }

    mock_urlopen = MagicMock()
    mock_cm = MagicMock()
    mock_cm.read.return_value = json.dumps(mock_resp_json).encode("utf-8")
    mock_cm.__enter__.return_value = mock_cm
    mock_urlopen.return_value = mock_cm

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = MimoCriticClient(api_key="tp-test-token")
    eval_res = client.evaluate_with_teacher(
        task_text="Test Task",
        output_text="<vivy_thought>Test</vivy_thought>",
    )

    assert eval_res.syntax_score == 0.95
    assert eval_res.composite_score == 0.90
    assert eval_res.metadata["teacher_reasoning"] == "Detailed thinking critique from MiMo 2.5 Pro."
    assert eval_res.metadata["source"] == "mimo-2.5pro"


def test_teacher_critic_fallback_to_local(monkeypatch):
    from training.teacher_critic import MimoCriticClient, TeacherCritic

    def failing_urlopen(*args, **kwargs):
        raise ConnectionError("Network offline")

    monkeypatch.setattr("urllib.request.urlopen", failing_urlopen)

    client = MimoCriticClient(api_key="tp-test-token")
    critic = TeacherCritic(mimo_client=client)

    # Output should fallback to local evaluation without crashing
    valid_output = (
        "<vivy_thought>\n"
        "Epistemic_Decision: EXECUTE_DIRECTLY\n"
        "Expected_Evidence: AST_PASS\n"
        "</vivy_thought>\n"
        "Executing code."
    )
    res = critic.evaluate_output("Some task", valid_output)
    assert res.metadata["source"] == "local_heuristics"
    assert res.syntax_score == 1.0

