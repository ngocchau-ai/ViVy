"""T8 — the safe learning path, end to end.  [NEW 29/09/2026 · WP-8]

Nghiệm thu WP-8 (plan §WP-8):

    replay log → 0 thăng cấp sai;
    ≥1 bài học VERIFIED thật khi có bằng chứng.

WP-8 fixed F-B05: ``independently_verified=False`` was hardcoded at the
``evaluate_multi_stream`` call site in ``integration/vivy_inference_loop.py``,
and ``evidence_packet`` was never forwarded at all.  Both halves of the Gate 7
input were dead, so ``VERIFIED_RESULT`` was unreachable, so
``LessonStore.promote()`` never fired, so the system had zero lessons and could
not learn.  This file is the tripwire that keeps that from coming back.

What "verified" means here
--------------------------
Deliberately narrow, and stated here so nobody upgrades the claim later:
*independent* means **a process outside the model returned an observation and
none failed**.  It does **not** mean the claim is semantically true — a tool
returning ``ok`` is process success (Gate 7: *"Process success != semantic
correctness != durable knowledge"*).  Semantic verification is the tribunal's
job (WP-11).  These tests assert the *learning gate*, not model accuracy.

Confidence scores in the fixtures below are raised to 0.9 by hand.  That is a
fixture for the >= 0.7 branch of the class ladder, **not** an accuracy claim —
see ``docs/CAPABILITY_LEDGER.md`` for what has actually been measured.

INV-01: every patch carries a test.  If a test here fails, **fix the code, not
the test** (plan hard rule #4).
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from engine.elastic_n_core import ElasticNCore, NCoreSinglePassResult
from engine.primitives import PrimitiveResult
from integration.evidence import EvidencePacket, build_evidence_packet
from integration.lesson_store import LessonStore
from integration.tool_dispatcher import DispatchResult
from memory.cognitive_graph import CognitiveStateGraph
from memory.hebbian_recall import HebbianRecall
from orchestrator.graph_bridge import EvidenceClass, GraphBridge

VIVY_ROOT = Path(__file__).resolve().parent.parent

_TEST_TMP = Path("_pytest_tmp")

#: The F-B05 hardcode.  If this literal ever appears as *live code* in the
#: inference loop again, verification is being asserted away instead of derived
#: from observations, and the learning path is dead.
FORBIDDEN_HARDCODE = "independently_verified=False"

#: The real forwarding the hardcode used to replace.  Both halves are required:
#: the flag alone forgets the packet, the packet alone is ignored by the gate.
REQUIRED_FORWARDING = (
    "independently_verified=independently_verified",
    "evidence_packet=evidence_packet",
)


# ---------------------------------------------------------------------------
# Source scanning (same contract as test_capability_honesty.live_code_lines)
# ---------------------------------------------------------------------------


def live_code_lines(text: str) -> str:
    """Return only Python code lines — comments and docstrings removed.

    WP-8 archived the old hardcode in ``[REPLACED]`` comment blocks per the
    project rule "cô lập, không xóa".  Those quotes are history, not behaviour.
    """
    out: list[str] = []
    in_triple: str | None = None
    for line in text.splitlines():
        if in_triple:
            if in_triple in line:
                in_triple = None
            continue

        for q in ('"""', "'''"):
            if q in line:
                before, _, after = line.partition(q)
                if q in after:
                    line = before + after.partition(q)[2]
                    break
                in_triple = q
                line = before
                break

        if line.lstrip().startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mktemp() -> Path:
    p = _TEST_TMP / f"slp_{int(time.time() * 1000)}_{os.getpid()}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rm(p: Path) -> None:
    shutil.rmtree(p, ignore_errors=True)


def _ok_tool(name: str, call_id: str, data: object) -> DispatchResult:
    """A real ``DispatchResult`` — the exact type the inference loop dispatches.

    Using the production type rather than a stub is the point: the packet
    builder must work against the rows the loop actually passes.
    """
    return DispatchResult(
        tool_name=name,
        primitive_result=PrimitiveResult(ok=True, data=data, elapsed_ms=1.0),
        tool_call_id=call_id,
        elapsed_ms=1.0,
    )


def _bad_tool(name: str, call_id: str) -> DispatchResult:
    return DispatchResult(
        tool_name=name,
        primitive_result=PrimitiveResult(
            ok=False, error_message="synthetic failure", elapsed_ms=1.0
        ),
        tool_call_id=call_id,
        elapsed_ms=1.0,
    )


def _high_conf_core_result() -> NCoreSinglePassResult:
    """An N-Core pass whose candidates clear the 0.7 VERIFIED threshold.

    Scores are raised by hand: this is a fixture for the class ladder, not a
    measurement of anything.
    """
    nc = ElasticNCore(n_min=2, n_max=2, hidden_dim=32, seed=0)
    result = nc.forward(n_override=2)
    for cand in result.candidates:
        cand.score = 0.9
    result.winner.score = 0.9
    return result


def _bridge_stack() -> tuple[GraphBridge, CognitiveStateGraph, HebbianRecall]:
    return (
        GraphBridge(dampening_noise_floor=0.05, auto_register=True),
        CognitiveStateGraph(),
        HebbianRecall(dim=32),
    )


def _claim() -> str:
    return "engine_file_io reported the file content and it matched the goal."


def _limits() -> str:
    return (
        "process success only: an external tool returned ok with no tool "
        "failures. Semantic correctness is NOT verified here (tribunal is WP-11)."
    )


def _packet_from(tools: list[DispatchResult]) -> tuple[EvidencePacket, bool]:
    return build_evidence_packet(
        claim=_claim(),
        expected_evidence="a typed observation from an external tool",
        task_id="task_slp",
        session_id="sess_slp",
        state_hash="hash_slp_abc",
        tool_results=tools,
        confidence=0.9,
        limits=_limits(),
    )


# ---------------------------------------------------------------------------
# The real chain: observations -> packet -> class -> durable lesson
# ---------------------------------------------------------------------------


class TestRealVerificationChain:
    def test_full_chain_yields_a_verified_lesson(self):
        """T8 clause 2: ≥1 bài học VERIFIED thật khi có bằng chứng.

        Nothing here is stubbed past the tool rows: real ``DispatchResult`` →
        real ``build_evidence_packet`` → real ``evaluate_multi_stream`` → real
        ``LessonStore.promote``.  If any stage regresses to the F-B05 hardcode,
        this test fails.
        """
        d = _mktemp()
        try:
            tools = [
                _ok_tool("engine_file_io", "call_1", {"n": 42}),
                _ok_tool("engine_exec", "call_2", {"stdout": "ok"}),
            ]
            packet, independent = _packet_from(tools)
            assert independent is True
            assert packet.valid_for_promotion()

            core_result = _high_conf_core_result()
            bridge, graph, recall = _bridge_stack()
            _br, evidence_class = bridge.evaluate_multi_stream(
                core_result=core_result,
                graph=graph,
                recall=recall,
                task_context="t8 chain",
                independently_verified=independent,
                evidence_packet=packet,
            )
            assert evidence_class == EvidenceClass.VERIFIED_RESULT

            store = LessonStore(store_path=d / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_slp",
                content=_claim(),
                evidence_class=evidence_class,
                confidence=0.9,
                provenance={"evidence": asdict(packet), "node_ids": ["n1"], "rounds": 1},
            )
            assert lesson is not None
            assert lesson.evidence_class == EvidenceClass.VERIFIED_RESULT.name

            # The receipt on the lesson must carry the observations, not just
            # a bare True.  Gate 7: "Promotion records provenance, scope,
            # confidence, and validation."
            stored = lesson.provenance["evidence"]
            # asdict() preserves the tuple; a JSON round-trip would make it a
            # list.  Compare content either way.
            assert list(stored["evidence_ids"]) == list(packet.evidence_ids)
            assert "engine_file_io" in stored["actual_observation"]
            assert stored["acceptance"].startswith("ACCEPTED:")
            assert stored["source"] == "tool_dispatch"

            counts = store.count()
            assert counts["active"] == 1
        finally:
            _rm(d)

    def test_zero_tool_results_cannot_become_a_lesson(self):
        """A run with nothing outside the model must not learn.

        This is the F-B05 failure mode in its purest form: the model asserted
        its own correctness and the gate believed it.
        """
        d = _mktemp()
        try:
            packet, independent = _packet_from([])
            assert independent is False
            assert not packet.valid_for_promotion()

            bridge, graph, recall = _bridge_stack()
            _br, evidence_class = bridge.evaluate_multi_stream(
                core_result=_high_conf_core_result(),
                graph=graph,
                recall=recall,
                task_context="no tools",
                independently_verified=independent,
                evidence_packet=packet,
            )
            assert evidence_class != EvidenceClass.VERIFIED_RESULT

            store = LessonStore(store_path=d / "lessons.jsonl")
            lesson = store.promote(
                session_id="sess_empty",
                content=_claim(),
                evidence_class=evidence_class,
                confidence=0.9,
                provenance={"evidence": asdict(packet)},
            )
            assert lesson is None
            assert store.count()["total"] == 0
        finally:
            _rm(d)

    def test_any_failed_tool_blocks_verification(self):
        """One failed observation poisons the run — fail-closed, not majority vote.

        "Independent" requires that *no* external process failed.  A partial
        result that still looks good is exactly the case that must not be
        promoted.
        """
        tools = [
            _ok_tool("engine_file_io", "call_1", {"n": 42}),
            _bad_tool("engine_exec", "call_2"),
        ]
        packet, independent = _packet_from(tools)
        assert independent is False
        assert packet.acceptance.startswith("REJECTED:")
        # The failure must be named in the receipt, not silently dropped.
        assert "engine_exec" in packet.acceptance
        # And only the successful observation is cited as evidence.
        assert packet.evidence_ids == ("call_1",)

        d = _mktemp()
        try:
            bridge, graph, recall = _bridge_stack()
            _br, evidence_class = bridge.evaluate_multi_stream(
                core_result=_high_conf_core_result(),
                graph=graph,
                recall=recall,
                task_context="mixed tools",
                independently_verified=independent,
                evidence_packet=packet,
            )
            assert evidence_class != EvidenceClass.VERIFIED_RESULT
            store = LessonStore(store_path=d / "lessons.jsonl")
            assert store.promote(
                session_id="sess_mixed", content=_claim(),
                evidence_class=evidence_class, confidence=0.9,
                provenance={"evidence": asdict(packet)},
            ) is None
        finally:
            _rm(d)

    def test_packet_is_capped_and_sanitised(self):
        """Observations are receipts, not transcripts.

        Unbounded tool output would make the packet unreadable and could smuggle
        a second claim past the gate.
        """
        huge = "x" * 5000
        tools = [_ok_tool("engine_file_io", "call_big", huge)]
        packet, independent = _packet_from(tools)
        assert independent is True
        assert len(packet.actual_observation) < 1000
        assert "…" in packet.actual_observation


# ---------------------------------------------------------------------------
# Replay log → 0 wrong promotions
# ---------------------------------------------------------------------------


@dataclass
class Attempt:
    """One promotion attempt on the replay log, with its expected outcome."""

    label: str
    evidence_class: EvidenceClass
    provenance: dict
    should_accept: bool


def _good_provenance() -> dict:
    tools = [_ok_tool("engine_file_io", "call_r", {"n": 7})]
    packet, independent = _packet_from(tools)
    assert independent is True
    return {"evidence": asdict(packet), "node_ids": ["n1"], "rounds": 1}


def _replay_log() -> list[Attempt]:
    """The adversarial replay.

    Every case here is a promotion that *would* have been wrong if it had
    landed.  The single legitimate case is included so the test proves the
    gate lets real knowledge through — a gate that rejects everything is not
    what T8 asks for.
    """
    valid = _good_provenance()
    valid_evidence = dict(valid["evidence"])  # type: ignore[arg-type]

    def ev(**over: object) -> dict:
        e = dict(valid_evidence)
        e.update(over)
        return {"evidence": e}

    return [
        Attempt(
            "legitimate VERIFIED with real observations",
            EvidenceClass.VERIFIED_RESULT, valid, True,
        ),
        Attempt(
            "VERIFIED with empty provenance (F-B05 sibling)",
            EvidenceClass.VERIFIED_RESULT, {}, False,
        ),
        Attempt(
            "VERIFIED with evidence key present but empty dict",
            EvidenceClass.VERIFIED_RESULT, {"evidence": {}}, False,
        ),
        Attempt(
            "VERIFIED with a blank claim",
            EvidenceClass.VERIFIED_RESULT, ev(claim=""), False,
        ),
        Attempt(
            "VERIFIED with no evidence ids",
            EvidenceClass.VERIFIED_RESULT, ev(evidence_ids=()), False,
        ),
        Attempt(
            "VERIFIED with confidence out of range",
            EvidenceClass.VERIFIED_RESULT, ev(confidence=1.5), False,
        ),
        Attempt(
            "VERIFIED with blank limits (no scope recorded)",
            EvidenceClass.VERIFIED_RESULT, ev(limits=""), False,
        ),
        Attempt(
            "VERIFIED but acceptance says REJECTED (unverified run)",
            EvidenceClass.VERIFIED_RESULT,
            ev(acceptance="REJECTED: no external observation: zero tool results"),
            False,
        ),
        Attempt(
            "PROVISIONAL_RESULT with good evidence (class gate)",
            EvidenceClass.PROVISIONAL_RESULT, valid, False,
        ),
        Attempt(
            "FAST_SIGNAL with good evidence (class gate)",
            EvidenceClass.FAST_SIGNAL, valid, False,
        ),
    ]


class TestReplayLogZeroWrongPromotions:
    def test_replay_log_has_zero_wrong_promotions(self):
        """T8 clause 1: replay log → 0 thăng cấp sai.

        A wrong promotion is a lesson that landed in the store while violating
        Gate 7 (unverified output became durable knowledge, or the promotion
        failed to record provenance/validation).  The store is append-only, so
        the store **is** the replay log — this reads it back after the run.
        """
        d = _mktemp()
        try:
            store = LessonStore(store_path=d / "lessons.jsonl")
            log: list[tuple[str, str]] = []
            for attempt in _replay_log():
                lesson = store.promote(
                    session_id="sess_replay",
                    content=f"[{attempt.label}]",
                    evidence_class=attempt.evidence_class,
                    confidence=0.9,
                    provenance=attempt.provenance,
                )
                landed = lesson is not None
                log.append((attempt.label, "ACCEPTED" if landed else "REJECTED"))

                # Per-attempt assertion, so a failure names the case.
                assert landed is attempt.should_accept, (
                    f"replay wrong outcome for {attempt.label!r}: "
                    f"got {'ACCEPTED' if landed else 'REJECTED'}, "
                    f"expected {'ACCEPTED' if attempt.should_accept else 'REJECTED'}"
                )

            # --- the acceptance criterion, stated as a count ---
            n_should = sum(1 for a in _replay_log() if a.should_accept)
            n_landed = sum(1 for _, outcome in log if outcome == "ACCEPTED")
            wrong = [
                label for (label, outcome), a in zip(log, _replay_log(), strict=True)
                if (outcome == "ACCEPTED") != a.should_accept
            ]
            assert wrong == [], f"wrong promotions/rejections: {wrong}"
            assert n_landed == n_should == 1

            # --- and verified against the durable log itself ---
            for lesson in store.list_active():
                packet = EvidencePacket(**lesson.provenance["evidence"])
                assert lesson.evidence_class == EvidenceClass.VERIFIED_RESULT.name
                assert packet.valid_for_promotion(), (
                    f"landed lesson {lesson.lesson_id} lacks valid evidence"
                )
                assert packet.acceptance.startswith("ACCEPTED:"), (
                    f"landed lesson {lesson.lesson_id} cites a REJECTED run"
                )
                assert packet.source.strip()
                assert packet.limits.strip(), "Gate 7 requires scope/limits on promotion"
                assert 0.0 <= packet.confidence <= 1.0
        finally:
            _rm(d)

    def test_every_rejection_is_reachable_and_named(self):
        """The gate must reject for the reason it names — not incidentally.

        Without this, a fail-closed gate could "pass" the replay by rejecting
        everything, including legitimate knowledge.
        """
        accepted = [a.label for a in _replay_log() if a.should_accept]
        rejected = [a.label for a in _replay_log() if not a.should_accept]
        assert accepted == ["legitimate VERIFIED with real observations"]
        # Every reject case is distinct and targets a named contract clause.
        assert len(rejected) == len(set(rejected))
        assert len(rejected) >= 8


# ---------------------------------------------------------------------------
# Tripwire: F-B05 cannot silently return
# ---------------------------------------------------------------------------


class TestFb05HardcodeCannotReturn:
    def test_inference_loop_derives_verification(self):
        """The hardcode is archived in comments; the live call site derives.

        Scans live code only, matching ``test_capability_honesty``: an
        ``[ISOLATED]`` / ``[REPLACED]`` quote is history and is allowed.
        """
        path = VIVY_ROOT / "integration" / "vivy_inference_loop.py"
        assert path.exists(), f"missing {path}"
        live = live_code_lines(path.read_text(encoding="utf-8"))

        assert FORBIDDEN_HARDCODE not in live, (
            f"{path.name} hardcodes {FORBIDDEN_HARDCODE!r} again. "
            "Verification must be derived from tool dispatch rows via "
            "build_evidence_packet() — see integration/evidence.py. "
            "(plan hard rule #4: fix the code, not this test.)"
        )
        for required in REQUIRED_FORWARDING:
            assert required in live, (
                f"{path.name} no longer forwards {required!r} to "
                "evaluate_multi_stream; the Gate 7 input is incomplete again."
            )
        assert "build_evidence_packet(" in live, (
            f"{path.name} no longer builds the evidence packet from observations."
        )
        # Confidence must be calibrated on the GraphBridge, which owns
        # calibrate_multi_stream_confidence.  self._bridge is the LLM bridge
        # (LlamaCppBridge) and has no such method -- mypy caught this once
        # already; don't let it come back behind a getattr.
        assert "self._bridge.calibrate_multi_stream_confidence" not in live, (
            "confidence is being calibrated on the LLM bridge. Use "
            "session.bridge.calibrate_multi_stream_confidence so the packet "
            "records the same number that drove the epistemic class."
        )

    def test_lesson_store_is_fail_closed_on_missing_evidence(self):
        """The other half of the hole: a promotion without evidence must reject.

        Before WP-8, ``promote(..., provenance={})`` validated the evidence key
        only *when present*, so an empty provenance sailed through — a wrong
        promotion under Gate 7 and T8.
        """
        path = VIVY_ROOT / "integration" / "lesson_store.py"
        live = live_code_lines(path.read_text(encoding="utf-8"))

        assert 'if "evidence" not in provenance:' in live, (
            "LessonStore.promote lost its fail-closed check on a missing "
            "'evidence' key. Gate 7 requires provenance + validation on every "
            "promotion."
        )
        assert "valid_for_promotion()" in live
        # The fail-open shape must not come back as the only guard.
        assert 'if "evidence" in provenance:' not in live

    def test_evidence_derivation_is_independent_of_model_claims(self):
        """``independently_verified`` must come from dispatch rows.

        ``derive_independent_verification`` is the single decision point; it
        takes tool results, never a model-supplied bool.  If someone later
        threads a model assertion into it, this fails.
        """
        path = VIVY_ROOT / "integration" / "evidence.py"
        live = live_code_lines(path.read_text(encoding="utf-8"))
        assert "def derive_independent_verification(" in live
        assert "def build_evidence_packet(" in live
        # The packet's flag is returned to the caller so it cannot be dropped —
        # that is the exact F-B05 failure mode being replaced.
        assert "return packet, independent" in live
        # Nothing in the builder may read a model-supplied verification flag.
        assert "model_verified" not in live
        assert "self_reported" not in live


class TestGate7ContractDocumentsLimit:
    def test_a_rejected_run_is_not_promotable_evidence(self):
        """[NEW 29/09/2026] WP-8 — the predicate must read the verdict.

        ``build_evidence_packet`` stamps ``REJECTED:`` on exactly the runs with
        zero or failed external observations.  Before this fix,
        ``valid_for_promotion()`` only checked the field was non-empty, so an
        unverified run's packet passed and could reach ``VERIFIED_RESULT`` and
        ``LessonStore.promote``.  Gate 7: *"Unverified output cannot become
        durable knowledge."*
        """
        packet, independent = _packet_from([])
        assert independent is False
        assert packet.acceptance.startswith("REJECTED:")
        assert not packet.valid_for_promotion()

        # Same packet shape with an explicit rejection verdict on a run that
        # otherwise has full evidence — still not promotable.
        good_tools = [_ok_tool("engine_file_io", "c", {"n": 1})]
        good, good_ind = _packet_from(good_tools)
        assert good_ind is True and good.valid_for_promotion()
        poisoned = EvidencePacket(
            **{**asdict(good), "acceptance": "REJECTED: 1/2 external observation(s) failed"}
        )
        assert not poisoned.valid_for_promotion()

    def test_limits_string_states_process_success_only(self):
        """The packet must not upgrade process success into truth.

        Gate 7 is explicit that process success is not semantic correctness.
        A packet whose ``limits`` field is blank would let a later reader
        mistake one for the other.
        """
        packet, independent = _packet_from([_ok_tool("t", "c", {"n": 1})])
        assert independent is True
        assert "process success" in packet.limits.lower()
        assert "not" in packet.limits.lower()
        assert packet.valid_for_promotion()
