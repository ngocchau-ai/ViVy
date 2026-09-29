"""WP-7 / O-02 — T2 eval set, programmatic checker, and A/B/C harness.

Three things are pinned here:

1. the checker never scores by substring, and never accepts a fabricated
   concrete answer on an adversarial item;
2. the generator is deterministic and has exactly the shape the plan names
   (120 = 4 domains x 30, 8 dev / 22 held-out each, 30 adversarial at 8/8/7/7);
3. D-7 holds — held-out never lands inside ``Vivy_final/``, the harness fails
   closed without the owner-supplied file, and a substituted file is refused.

Changelog:
    29/09/2026 (Claude Code — WP-7/O-02): Initial.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from benchmarks.checker import (
    VERDICT_TOKENS,
    check_answer,
    eval_expression,
    extract_declared,
)
from benchmarks.eval_set.generate import (
    ADVERSARIAL_PER_DOMAIN,
    DEV_PER_DOMAIN,
    HELDOUT_PER_DOMAIN,
    ITEMS_PER_DOMAIN,
    build_all,
)
from benchmarks.eval_set.generate import (
    main as generate_main,
)
from benchmarks.eval_set.schema import (
    DOMAINS,
    INSUFFICIENT,
    EvalItem,
    sha256_item,
    write_jsonl,
)
from benchmarks.harness import (
    HANG_CEILING_S,
    ArmReply,
    HeldOutError,
    PlainModelArm,
    load_dev_items,
    load_heldout_items,
    load_manifest,
    mcnemar_exact,
    run_eval,
    run_with_ceiling,
    t2_verdict,
    verify_heldout_items,
    write_receipt,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_item(**overrides) -> EvalItem:
    payload = {
        "id": "math-x-000",
        "domain": "math",
        "split": "dev",
        "kind": "answerable",
        "prompt": "What is 2 + 3?\n\nEnd with ANSWER:",
        "expected": "5",
        "expected_kind": "number",
    }
    payload.update(overrides)
    item = EvalItem(**payload)
    item.validate()
    return item


class StubArm:
    """A scoring arm that never touches a model."""

    def __init__(self, name: str, text: str = "", *, correct: bool = False,
                 error: str | None = None, delay_s: float = 0.0) -> None:
        self.name = name
        self.text = text
        self.correct = correct
        self.error = error
        self.delay_s = delay_s

    def run(self, item: EvalItem) -> ArmReply:
        if self.delay_s:
            time.sleep(self.delay_s)
        return ArmReply(
            text=self.text,
            latency_ms=self.delay_s * 1000.0,
            completion_tokens=0,
            model_call_made=False if self.error is None else None,
            error=self.error,
        )


# ---------------------------------------------------------------------------
# 1. Checker — programmatic, never substring
# ---------------------------------------------------------------------------


class TestCheckerNumbers:
    def test_exact_integer(self):
        item = make_item(expected="42", expected_kind="number")
        result = check_answer(item, "Reasoning.\nANSWER: 42")
        assert result.correct is True
        assert result.reason == "number_within_tolerance"

    def test_within_tolerance(self):
        item = make_item(expected="0.5", expected_kind="number", tolerate=1e-6)
        assert check_answer(item, "ANSWER: 0.5000004").correct is True

    def test_outside_tolerance_is_wrong(self):
        item = make_item(expected="0.5", expected_kind="number", tolerate=1e-6)
        result = check_answer(item, "ANSWER: 0.5001")
        assert result.correct is False
        assert "outside_tolerance" in result.reason

    def test_integer_item_has_zero_tolerance(self):
        item = make_item(expected="42", expected_kind="number")
        assert item.tolerate == 0.0
        assert check_answer(item, "ANSWER: 42.5").correct is False

    def test_fraction_and_thousands_separators_parse(self):
        item = make_item(expected="0.75", expected_kind="number")
        assert check_answer(item, "ANSWER: 3/4").correct is True
        item2 = make_item(expected="1234", expected_kind="number")
        assert check_answer(item2, "ANSWER: 1,234").correct is True

    def test_unparsable_number_is_wrong(self):
        item = make_item(expected="42", expected_kind="number")
        result = check_answer(item, "ANSWER: forty-two")
        assert result.correct is False
        assert result.reason == "unparsable_number"


class TestCheckerSets:
    def test_exact_match_ignores_order_and_spacing(self):
        item = make_item(expected="{1,2,3}", expected_kind="set")
        assert check_answer(item, "ANSWER: {3, 1, 2}").correct is True
        assert check_answer(item, "ANSWER: 1, 2, 3").correct is True

    def test_extra_member_is_wrong(self):
        item = make_item(expected="{1,2}", expected_kind="set")
        result = check_answer(item, "ANSWER: {1, 2, 3}")
        assert result.correct is False
        assert "extra=" in result.reason

    def test_missing_member_is_wrong(self):
        item = make_item(expected="{1,2,3}", expected_kind="set")
        result = check_answer(item, "ANSWER: {1, 2}")
        assert result.correct is False
        assert "missing=" in result.reason

    def test_partial_overlap_reports_both(self):
        item = make_item(expected="{1,2}", expected_kind="set")
        result = check_answer(item, "ANSWER: {2, 9}")
        assert result.correct is False
        assert "missing=" in result.reason and "extra=" in result.reason


class TestCheckerExpressions:
    def test_arithmetic_value_equality(self):
        item = make_item(expected="5", expected_kind="expression")
        assert check_answer(item, "ANSWER: 2 + 3").correct is True
        assert check_answer(item, "ANSWER: 3+2").correct is True
        assert check_answer(item, "ANSWER: 5.0").correct is True

    def test_wrong_value(self):
        item = make_item(expected="5", expected_kind="expression")
        result = check_answer(item, "ANSWER: 2 * 3")
        assert result.correct is False
        assert result.reason == "expression_value_differs"

    def test_unicode_operators_normalise(self):
        item = make_item(expected="6", expected_kind="expression")
        assert check_answer(item, "ANSWER: 2 × 3").correct is True
        assert eval_expression("8 ÷ 2") == 4.0

    def test_refuses_calls_and_names(self):
        # A safe evaluator must not execute anything.
        assert eval_expression("__import__('os')") is None
        assert eval_expression("open('/etc/passwd')") is None

    def test_refuses_exploding_pow(self):
        assert eval_expression("10 ** 100") is None
        assert eval_expression("2 ** 99") is None


class TestCheckerText:
    def test_exact_after_normalisation(self):
        item = make_item(expected="x + 3", expected_kind="text")
        assert check_answer(item, "ANSWER: x+3").correct is True
        assert check_answer(item, "ANSWER: X + 3.").correct is True

    def test_matrix_whitespace_is_not_significant(self):
        item = make_item(expected="[[0, -1], [1, 0]]", expected_kind="text")
        assert check_answer(item, "ANSWER: [[0,-1],[1,0]]").correct is True

    def test_leading_token_concession_for_yes_no(self):
        item = make_item(expected="yes", expected_kind="text")
        assert check_answer(item, "ANSWER: Yes, it is a tree.").correct is True
        assert check_answer(item, "ANSWER: no").correct is False

    def test_no_substring_matching(self):
        item = make_item(expected="42", expected_kind="text")
        result = check_answer(item, "ANSWER: the answer is 42 of course")
        assert result.correct is False


class TestCheckerInsufficient:
    def _adversarial(self, **kw) -> EvalItem:
        payload = {
            "id": "graph-x-001",
            "domain": "graph",
            "split": "dev",
            "kind": "adversarial",
            "prompt": "A graph has 12 vertices, each of degree >= 3. How many edges?",
            "expected": INSUFFICIENT,
            "expected_kind": "insufficient",
            "missing_data": True,
        }
        payload.update(kw)
        item = EvalItem(**payload)
        item.validate()
        return item

    @pytest.mark.parametrize("token", sorted(VERDICT_TOKENS))
    def test_every_allowlisted_verdict_passes(self, token):
        item = self._adversarial()
        assert check_answer(item, f"VERDICT: {token}").correct is True

    def test_fabricated_answer_on_adversarial_fails(self):
        item = self._adversarial()
        result = check_answer(item, "I cannot be sure, but ANSWER: 24")
        assert result.correct is False
        assert result.reason == "fabricated_concrete_answer_on_unanswerable_item"

    def test_verdict_with_a_concrete_value_fails(self):
        item = self._adversarial()
        result = check_answer(item, "VERDICT: INSUFFICIENT_EVIDENCE, but ANSWER: 24")
        # The last declared line wins, and that one is a concrete ANSWER.
        assert result.correct is False
        assert result.reason == "fabricated_concrete_answer_on_unanswerable_item"

    def test_verdict_outside_allowlist_fails(self):
        item = self._adversarial()
        result = check_answer(item, "VERDICT: TRUST_ME")
        assert result.correct is False
        assert result.reason == "verdict_token_not_in_allowlist"

    def test_no_declared_line_is_wrong_for_every_kind(self):
        for item in (make_item(), self._adversarial()):
            result = check_answer(item, "I think the answer is probably five.")
            assert result.correct is False
            assert result.reason == "no_declared_answer"


class TestCheckerDeclaration:
    def test_last_declared_line_wins(self):
        item = make_item(expected="5", expected_kind="number")
        declared = extract_declared("ANSWER: 3\n\nANSWER: 5")
        assert declared is not None
        assert declared.value == "5"
        assert check_answer(item, "ANSWER: 3\nANSWER: 5").correct is True

    def test_verdict_instead_of_answer_is_wrong_on_answerable(self):
        item = make_item(expected="5", expected_kind="number")
        result = check_answer(item, "VERDICT: INSUFFICIENT_EVIDENCE")
        assert result.correct is False
        assert result.reason == "declared_VERDICT_instead_of_ANSWER"

    def test_answer_line_is_a_declared_line_not_a_substring(self):
        # "ANSWER: 5" buried in prose is not a declared line start... actually
        # it IS at a line start here.  What must fail is a value that only
        # contains the expected text somewhere.
        item = make_item(expected="5", expected_kind="number")
        assert check_answer(item, "the final ANSWER: 5").correct is False


# ---------------------------------------------------------------------------
# 2. Generator — shape and determinism
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def all_items() -> list[EvalItem]:
    return build_all()


class TestGeneratorShape:
    def test_total_is_120(self, all_items):
        assert len(all_items) == 120

    def test_four_domains_of_thirty(self, all_items):
        for domain in DOMAINS:
            n = sum(1 for i in all_items if i.domain == domain)
            assert n == ITEMS_PER_DOMAIN, f"{domain}: {n}"

    def test_dev_and_heldout_per_domain(self, all_items):
        for domain in DOMAINS:
            subset = [i for i in all_items if i.domain == domain]
            n_dev = sum(1 for i in subset if i.split == "dev")
            n_held = sum(1 for i in subset if i.split == "heldout")
            assert n_dev == DEV_PER_DOMAIN
            assert n_held == HELDOUT_PER_DOMAIN

    def test_adversarial_count_and_distribution(self, all_items):
        adv = [i for i in all_items if i.kind == "adversarial"]
        assert len(adv) == 30
        for domain, expected in ADVERSARIAL_PER_DOMAIN.items():
            got = sum(1 for i in adv if i.domain == domain)
            assert got == expected, f"{domain}: {got} != {expected}"

    def test_adversarial_are_stratified_across_splits(self, all_items):
        # No domain may put every adversarial item in one split.
        for domain in DOMAINS:
            subset = [i for i in all_items if i.domain == domain and i.kind == "adversarial"]
            splits = {i.split for i in subset}
            assert splits == {"dev", "heldout"}, f"{domain}: {splits}"

    def test_ids_are_unique(self, all_items):
        ids = [i.id for i in all_items]
        assert len(set(ids)) == len(ids)

    def test_determinism(self):
        first = [sha256_item(i) for i in build_all()]
        second = [sha256_item(i) for i in build_all()]
        assert first == second

    def test_every_item_carries_the_answer_line_instruction(self, all_items):
        for item in all_items:
            assert "ANSWER:" in item.prompt
            assert INSUFFICIENT in item.prompt


class TestGeneratorAnswersAreComputable:
    def test_every_answerable_item_self_scores(self, all_items):
        bad = []
        for item in all_items:
            if item.kind != "answerable":
                continue
            result = check_answer(item, f"ANSWER: {item.expected}")
            if not result.correct:
                bad.append((item.id, result.reason, item.expected))
        assert bad == [], bad

    def test_every_adversarial_item_self_scores(self, all_items):
        bad = []
        for item in all_items:
            if item.kind != "adversarial":
                continue
            result = check_answer(item, f"VERDICT: {INSUFFICIENT}")
            if not result.correct:
                bad.append((item.id, result.reason))
        assert bad == [], bad

    def test_adversarial_iff_insufficient(self, all_items):
        for item in all_items:
            assert (item.kind == "adversarial") == (item.expected_kind == "insufficient")

    def test_committed_manifest_leaks_nothing(self):
        from benchmarks.eval_set.generate import MANIFEST_PATH

        if not MANIFEST_PATH.exists():
            pytest.skip("manifest not generated in this checkout")
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        rows = payload["items"]
        assert len(rows) == 88
        for row in rows:
            assert set(row) == {"id", "domain", "split", "kind", "expected_kind", "sha256"}
            assert "prompt" not in row
            assert "expected" not in row


# ---------------------------------------------------------------------------
# 3. D-7 — held-out stays outside the repo
# ---------------------------------------------------------------------------


class TestD7HeldoutIsolation:
    def test_generator_refuses_in_repo_heldout_target(self, tmp_path, capsys):
        inside = Path(__file__).resolve().parents[1] / "benchmarks" / "eval_set" / "SNEAK.jsonl"
        code = generate_main(["--split", "heldout", "--out", str(inside)])
        assert code == 2
        assert not inside.exists()
        err = capsys.readouterr().err
        assert "REFUSED" in err and "D-7" in err

    def test_generator_writes_heldout_outside_the_repo(self):
        # NOTE: pytest's ``tmp_path`` lives under ``vivy/_pytest_tmp`` — which is
        # *inside* the repo, so the generator would rightly refuse it.  This
        # case needs a directory that is genuinely outside ``Vivy_final/``.
        outside = Path(tempfile.mkdtemp(prefix="vivy_t2_heldout_")) / "heldout_set.jsonl"
        code = generate_main(["--split", "heldout", "--out", str(outside)])
        assert code == 0
        assert outside.exists()
        lines = [line for line in outside.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 88

    def test_dev_writes_into_the_repo(self):
        # The dev half is deliberately committed.
        dev = load_dev_items()
        assert len(dev) == 32
        assert {i.split for i in dev} == {"dev"}


class TestHeldoutAuthentication:
    def _write(self, path: Path, items: list[EvalItem]) -> None:
        write_jsonl(str(path), items)

    def test_missing_file_is_not_a_silent_default(self, monkeypatch):
        monkeypatch.delenv("VIVY_HELDOUT_PATH", raising=False)
        with pytest.raises(HeldOutError, match="D-7"):
            load_heldout_items(None)

    def test_env_var_is_honoured(self, tmp_path, monkeypatch):
        items = [i for i in build_all() if i.split == "heldout"]
        self._write(tmp_path / "h.jsonl", items)
        monkeypatch.setenv("VIVY_HELDOUT_PATH", str(tmp_path / "h.jsonl"))
        loaded = load_heldout_items(None)
        assert len(loaded) == 88

    def test_substituted_file_is_refused(self, tmp_path):
        items = [i for i in build_all() if i.split == "heldout"]
        # Tamper with one item's answer without changing its id.
        tampered = []
        for item in items:
            if item.expected_kind == "number":
                replacement = EvalItem(
                    id=item.id, domain=item.domain, split=item.split, kind=item.kind,
                    prompt=item.prompt, expected="999999",
                    expected_kind=item.expected_kind, tolerate=item.tolerate,
                    missing_data=item.missing_data, notes=item.notes, tags=item.tags,
                )
                tampered.append(replacement)
            else:
                tampered.append(item)
        path = tmp_path / "h.jsonl"
        self._write(path, tampered)
        with pytest.raises(HeldOutError, match="sha256 mismatch|substituted"):
            load_heldout_items(path)

    def test_incomplete_file_is_refused(self, tmp_path):
        items = [i for i in build_all() if i.split == "heldout"][:10]
        path = tmp_path / "h.jsonl"
        self._write(path, items)
        with pytest.raises(HeldOutError, match="incomplete"):
            load_heldout_items(path)

    def test_unknown_id_is_refused(self, tmp_path):
        items = [i for i in build_all() if i.split == "heldout"]
        items.append(make_item(id="math-x-999", split="heldout"))
        path = tmp_path / "h.jsonl"
        self._write(path, items)
        problems = verify_heldout_items(items, load_manifest())
        assert any("not in the committed held-out manifest" in p for p in problems)


# ---------------------------------------------------------------------------
# 4. Harness plumbing (stub arms — no model)
# ---------------------------------------------------------------------------


class TestT2Verdict:
    def test_pass_at_minus_two(self):
        assert t2_verdict(0.50, 0.48)["status"] == "PASS"

    def test_stop_below_minus_five(self):
        verdict = t2_verdict(0.50, 0.449)
        assert verdict["status"] == "STOP_REDESIGN"
        assert "stop" in verdict["note"].lower()

    def test_grey_band_is_marginal(self):
        assert t2_verdict(0.50, 0.47)["status"] == "MARGINAL"

    def test_improvement_passes(self):
        assert t2_verdict(0.50, 0.60)["status"] == "PASS"


class TestMcNemar:
    def test_symmetric_pairs_give_p_one(self):
        assert mcnemar_exact(3, 3) == 1.0

    def test_no_discordant_pairs_give_p_one(self):
        assert mcnemar_exact(0, 0) == 1.0

    def test_strong_imbalance_is_significant(self):
        assert mcnemar_exact(0, 15) < 0.05

    def test_matches_the_binomial_tail(self):
        # b=1, c=5 -> n=6, k=1, p = 2*(C(6,0)+C(6,1))/64 = 2*7/64
        assert abs(mcnemar_exact(1, 5) - 2 * 7 / 64) < 1e-12

    def test_same_function_as_the_checker_module_is_not_required(self):
        # Keep the harness's own copy of the maths independently pinned.
        assert mcnemar_exact(2, 8) <= 1.0


class TestRunEval:
    def _items(self) -> list[EvalItem]:
        return [
            make_item(id="math-x-000", expected="5", expected_kind="number"),
            make_item(id="math-x-001", expected="7", expected_kind="number"),
            make_item(
                id="graph-x-002", domain="graph", kind="adversarial",
                prompt="underdetermined", expected=INSUFFICIENT,
                expected_kind="insufficient", missing_data=True,
            ),
        ]

    def test_receipt_has_arms_and_verdict(self, tmp_path):
        items = self._items()
        arms = [
            StubArm("baseline", "ANSWER: 5"),
            StubArm("pipeline", "ANSWER: 5"),
        ]
        payload = run_eval(items, arms, run_id="T2-test", split="dev")
        assert payload["n_items"] == 3
        assert set(payload["arms"]) == {"baseline", "pipeline"}
        assert payload["arms"]["baseline"]["n_items"] == 3
        assert "t2_verdict" in payload
        assert payload["per_item"] and len(payload["per_item"]) == 3

    def test_per_item_rows_carry_model_call_honesty(self):
        items = self._items()
        arms = [
            StubArm("baseline", "ANSWER: 5"),
            StubArm("pipeline", "ANSWER: 5", error="boom"),
        ]
        payload = run_eval(items, arms, run_id="T2-test", split="dev")
        for row in payload["per_item"]:
            assert row["arms"]["baseline"]["model_call_made"] is False
            # An arm that errored reports unknown, not "no call".
            assert row["arms"]["pipeline"]["model_call_made"] is None
            assert row["arms"]["pipeline"]["error"] == "boom"

    def test_accuracy_is_computed_not_asserted(self):
        items = self._items()
        # baseline: 1 of 3 right (only the first ANSWER: 5 matches)
        arms = [StubArm("baseline", "ANSWER: 5"), StubArm("pipeline", "ANSWER: 9")]
        payload = run_eval(items, arms, run_id="T2-test", split="dev")
        assert payload["arms"]["baseline"]["n_correct"] == 1
        assert payload["arms"]["pipeline"]["n_correct"] == 0

    def test_receipt_file_round_trips(self, tmp_path):
        items = self._items()
        payload = run_eval(items, [StubArm("baseline", "ANSWER: 5")],
                           run_id="T2-roundtrip", split="dev")
        path = write_receipt(payload, tmp_path)
        assert path.name == "T2-roundtrip.json"
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        assert on_disk["run_id"] == "T2-roundtrip"
        assert on_disk["hang_ceiling_s"] == HANG_CEILING_S

    def test_latency_note_declares_the_budget_is_unmeasured(self):
        items = self._items()
        payload = run_eval(items, [StubArm("baseline", "ANSWER: 5")],
                           run_id="T2-note", split="dev")
        assert "UNMEASURED" in payload["latency_note"]

    def test_ceiling_hits_are_censored_not_scored_as_wrong(self):
        """A ceiling hit is a censored observation, not a wrong answer.

        D-8 set 120 s to catch hangs.  When the model is merely slow, folding
        the miss into ``accuracy`` would make T2 measure "who finished in
        time" rather than "who was right", so both numbers are reported.
        """

        class CensorLastArm:
            """Answers the first two items, then hits the ceiling on the third."""

            name = "baseline"

            def run(self, item: EvalItem) -> ArmReply:
                if item.kind == "adversarial":
                    return ArmReply(text="", model_call_made=None,
                                    error="timeout_after_120s")
                return ArmReply(text="ANSWER: 5", model_call_made=True)

        items = self._items()
        arms = [CensorLastArm(), StubArm("pipeline", "ANSWER: 5")]
        payload = run_eval(items, arms, run_id="T2-censor", split="dev")
        base = payload["arms"]["baseline"]
        assert base["n_ceiling_hits"] == 1
        assert base["n_uncensored"] == 2
        # Strict accuracy counts the censored item as wrong: 1/3.
        assert base["n_correct"] == 1
        assert base["accuracy"] == pytest.approx(1 / 3)
        # Uncensored accuracy drops the observation entirely: 1/2.
        assert base["n_correct_uncensored"] == 1
        assert base["accuracy_uncensored"] == pytest.approx(0.5)
        # An arm with no censored items reports the two as equal.
        pipe = payload["arms"]["pipeline"]
        assert pipe["n_ceiling_hits"] == 0
        assert pipe["accuracy_uncensored"] == pipe["accuracy"]


class TestHangCeiling:
    def test_timeout_reports_unknown_call_not_no_call(self):
        def slow(item: EvalItem) -> ArmReply:
            time.sleep(2.0)
            return ArmReply(text="ANSWER: 1", model_call_made=True)

        item = make_item()
        reply = run_with_ceiling(slow, item, ceiling_s=0.2)
        assert reply.error is not None and "timeout" in reply.error
        assert reply.model_call_made is None

    def test_ceiling_actually_returns_rather_than_waiting_out_the_arm(self):
        """Regression: the first implementation used ``with ThreadPoolExecutor``,
        whose ``shutdown(wait=True)`` blocked until the hung arm finished.  The
        reply was correctly labelled a timeout, but the *run* still waited the
        full sleep — so the hang ceiling was decorative (D-8).  A 30 s arm under
        a 0.2 s ceiling must return in about 0.2 s, not 30 s.
        """

        def glacial(item: EvalItem) -> ArmReply:
            time.sleep(30.0)
            return ArmReply(text="ANSWER: 1", model_call_made=True)

        started = time.perf_counter()
        reply = run_with_ceiling(glacial, make_item(), ceiling_s=0.2)
        elapsed = time.perf_counter() - started
        assert reply.error is not None and "timeout" in reply.error
        assert elapsed < 2.0, f"ceiling did not abandon the arm (waited {elapsed:.1f}s)"

    def test_fast_path_returns_the_reply(self):
        def quick(item: EvalItem) -> ArmReply:
            return ArmReply(text="ANSWER: 5", model_call_made=True, latency_ms=1.0)

        reply = run_with_ceiling(quick, make_item(), ceiling_s=5.0)
        assert reply.text == "ANSWER: 5"
        assert reply.error is None
        assert reply.model_call_made is True

    def test_arm_exception_is_a_scored_miss_not_a_crash(self):
        def boom(item: EvalItem) -> ArmReply:
            raise RuntimeError("engine went away")

        reply = run_with_ceiling(boom, make_item(), ceiling_s=5.0)
        assert reply.error is not None and "RuntimeError" in reply.error
        assert reply.model_call_made is None

    def test_default_ceiling_is_the_d8_value(self):
        assert HANG_CEILING_S == 120.0


class TestFreshClientPerCall:
    """Regression: a shared ``LLMClient`` across ``asyncio.run`` calls dies on
    the second call with ``Event loop is closed``, and the item was scored wrong
    for a plumbing reason.  The baseline arm must build a client per call."""

    def test_baseline_arm_builds_a_client_per_call(self, monkeypatch):
        built: list[object] = []

        class FakeClient:
            async def chat(self, prompt, **kwargs):
                return "ANSWER: 5"

        def fake_fresh():
            client = FakeClient()
            built.append(client)
            return client

        monkeypatch.setattr("benchmarks.harness.fresh_client", fake_fresh)
        arm = PlainModelArm(model="m")
        item = make_item(expected="5", expected_kind="number")

        for _ in range(3):
            reply = arm.run(item)
            assert reply.error is None
            assert reply.model_call_made is True

        assert len(built) == 3
        assert len(set(id(c) for c in built)) == 3

    def test_three_sequential_calls_all_answer(self, monkeypatch):
        class FakeClient:
            async def chat(self, prompt, **kwargs):
                return "ANSWER: 5"

        monkeypatch.setattr("benchmarks.harness.fresh_client", lambda: FakeClient())
        arm = PlainModelArm(model="m")
        item = make_item(expected="5", expected_kind="number")
        texts = [arm.run(item).text for _ in range(3)]
        assert texts == ["ANSWER: 5"] * 3
