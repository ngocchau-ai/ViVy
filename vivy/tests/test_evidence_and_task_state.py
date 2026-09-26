from integration.evidence import evidence_from_mapping
from integration.task_state import TaskState


def test_task_state_hash_is_stable_and_task_bound():
    a = TaskState("t1", "goal", "obs")
    b = TaskState("t1", "goal", "obs")
    c = TaskState("t2", "goal", "obs")
    assert a.state_hash == b.state_hash
    assert a.state_hash != c.state_hash


def test_incomplete_evidence_cannot_be_promoted():
    packet = evidence_from_mapping({"claim": "answer", "confidence": 1.0})
    assert not packet.valid_for_promotion()


def test_complete_evidence_is_promotable():
    packet = evidence_from_mapping({
        "claim": "answer", "evidence_ids": ["e1"], "source": "verifier",
        "expected_evidence": "4", "actual_observation": "4", "acceptance": "PASS",
        "confidence": 0.9, "limits": "arithmetic only", "task_id": "t1",
        "session_id": "s1", "state_hash": "abc",
    })
    assert packet.valid_for_promotion()
