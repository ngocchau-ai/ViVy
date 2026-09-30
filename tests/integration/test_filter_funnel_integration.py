"""Integration test cho Phễu lọc Tự kiểm chứng + Memory Tương quan + Verification Tribunal."""

import pytest

from nps_core.evidence_assimilator import EvidencePacket, Reproducibility
from nps_core.filter_funnel import FilterFunnel, FunnelSignal
from nps_core.hypothesis_population import PopulationSnapshot
from nps_core.memory import QuantumAssociativeMemory
from nps_core.verification_tribunal import VerificationTribunal


def make_packet(eid: str, result: str) -> EvidencePacket:
    return EvidencePacket(
        evidence_id=eid,
        task_id="TASK-001",
        executor_id="EXECUTOR-001",
        claim="Claim verified",
        result=result,
        method="test",
        artifacts=(),
        confidence=0.9,
        limitations=(),
        failure_modes=(),
        reproducibility=Reproducibility(command="pytest", environment="local", seed=None),
        affected_hypotheses=("THOUGHT-001",),
        provenance=("runner",),
        content_hash="a" * 64,
    )


def test_end_to_end_filter_funnel_memory_tribunal():
    # 1. Khởi tạo Associative Memory và lưu 1 mẫu thành công
    memory = QuantumAssociativeMemory(dim_input=2, dim_output=2)
    memory.store([1.0, 0.0], [0.0, 1.0])

    # 2. Truy vấn trực giác 1-chạm
    match = memory.query([0.98, 0.02])
    assert match.confidence > 0.85

    # 3. Chạy pipeline FilterFunnel
    funnel = FilterFunnel()
    state_vec = [1.0, 0.0, 0.0, 0.0]  # Fully converged state

    # 4. Đánh giá Tribunal kết hợp FilterFunnel
    snapshot = PopulationSnapshot.empty()
    packet = make_packet("EV-001", "PASSED")

    conflicts, logs, funnel_res = VerificationTribunal.evaluate_with_filter_funnel(
        packets=[packet],
        snapshot=snapshot,
        state_vector=state_vec,
        partition=(1, 1),
        funnel=funnel,
    )

    assert len(conflicts) == 0
    assert len(logs) == 1
    assert logs[0].reproduced is True
    assert funnel_res.signal == FunnelSignal.MEASURE_AND_HALT
    assert funnel_res.extracted_pattern is not None

    # 5. Nạp pattern thu được vào Memory cho bài toán tiếp theo
    pattern = funnel_res.extracted_pattern
    if len(pattern.input_vector) == 2 and len(pattern.output_vector) == 2:
        memory.store(pattern.input_vector, pattern.output_vector)
        assert memory.pattern_count == 2
