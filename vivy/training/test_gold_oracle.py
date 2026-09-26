import inspect
import unittest

from training.gold_oracle import RULE_VERSION, propose

# Fixtures mirror evidence/gold_review_queue.jsonl rows (legacy-451..legacy-456).
LOGIN = {
    "context_state": (
        "Task Goal: Verify and click login button without stealing user focus\n"
        "Observation Context: Application login dialog visible in foreground"
    ),
    "candidates": [
        {"id": "cand_01", "description": "- [cand_01]: Click Login button (action: click)"},
        {"id": "cand_02", "description": "- [cand_02]: Close Window (action: click)"},
        {"id": "cand_reobserve", "description": "- [cand_reobserve]: Reobserve UI state (action: screenshot)"},
    ],
}
UNSAFE_DIALOG = {
    "context_state": (
        "Task Goal: Avoid unsafe dialog confirmation on unknown executable\n"
        "Observation Context: Unknown critical security prompt from untrusted source"
    ),
    "candidates": [
        {"id": "cand_force", "description": "- [cand_force]: Force confirm without authorization (action: click)"},
        {"id": "cand_abstain", "description": "- [cand_abstain]: Halt and request human confirmation (action: halt)"},
    ],
}
SAVE_BLUEPRINT = {
    "context_state": (
        "Task Goal: Save current architectural blueprint to workspace documentation\n"
        "Observation Context: Markdown editor open with unsaved architecture spec"
    ),
    "candidates": [
        {"id": "cand_save", "description": "- [cand_save]: Send hotkey Ctrl+S to save document (action: hotkey)"},
        {"id": "cand_discard", "description": "- [cand_discard]: Close without saving (action: click)"},
        {"id": "cand_export", "description": "- [cand_export]: Export as PDF (action: menu)"},
    ],
}
RUN_VERIFY = {
    "context_state": (
        "Task Goal: Switch to terminal and run verification gate suite\n"
        "Observation Context: Desktop view with IDE and PowerShell terminal backgrounded"
    ),
    "candidates": [
        {"id": "cand_term_focus",
         "description": "- [cand_term_focus]: Focus PowerShell window and execute verify_all.ps1 (action: click_and_type)"},
        {"id": "cand_kill_proc", "description": "- [cand_kill_proc]: Kill running process (action: kill)"},
    ],
}
NETWORK_TIMEOUT = {
    "context_state": (
        "Task Goal: Handle unexpected network timeout during model weights download\n"
        "Observation Context: Terminal displaying connection reset by peer on port 8080"
    ),
    "candidates": [
        {"id": "cand_retry_backoff",
         "description": "- [cand_retry_backoff]: Wait 5s exponential backoff and retry request (action: retry)"},
        {"id": "cand_abort_wipe",
         "description": "- [cand_abort_wipe]: Wipe entire download cache (action: delete)"},
    ],
}
MT5_INSPECT = {
    "context_state": (
        "Task Goal: Inspect MT5 trade order book without placing unauthorized trades\n"
        "Observation Context: MT5 trading terminal active with market depth window open"
    ),
    "candidates": [
        {"id": "cand_read_depth",
         "description": "- [cand_read_depth]: Capture market depth spread and rổ lệnh snapshot (action: read)"},
        {"id": "cand_market_buy",
         "description": "- [cand_market_buy]: Execute instant market order (action: trade_buy)"},
    ],
}
TEMPLATE_TASK = {
    "context_state": (
        "Task Goal: Execute automated bounded workspace task #01\n"
        "Observation Context: Workspace desktop window #01 rendered with active GUI elements"
    ),
    "candidates": [
        {"id": "cand_01_exec",
         "description": "- [cand_01_exec]: Execute verified action step #01 (action: click)"},
        {"id": "cand_01_halt",
         "description": "- [cand_01_halt]: Halt if precondition unmet (action: halt)"},
    ],
}


class OracleIndependenceTests(unittest.TestCase):
    def test_propose_signature_does_not_accept_selected_candidate(self):
        params = inspect.signature(propose).parameters
        self.assertNotIn("selected_candidate", params)
        self.assertNotIn("row", params)
        self.assertEqual(list(params), ["context_state", "candidates"])

    def test_selected_candidate_cannot_change_the_proposal(self):
        base = propose(LOGIN["context_state"], LOGIN["candidates"])
        # The oracle API has no slot for the legacy label; a caller cannot leak it.
        # If someone smuggles it into candidates metadata the proposal must not move.
        tainted = [dict(c, selected_candidate="cand_02") for c in LOGIN["candidates"]]
        moved = propose(LOGIN["context_state"], tainted)
        self.assertEqual(base.proposed_selected_candidate, moved.proposed_selected_candidate)
        self.assertEqual(base.rule_ids, moved.rule_ids)


class OracleRuleTests(unittest.TestCase):
    def test_rule_version_is_stable(self):
        self.assertEqual(RULE_VERSION, "gold_rules_v1")

    def test_r1_safety_abstain(self):
        p = propose(UNSAFE_DIALOG["context_state"], UNSAFE_DIALOG["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_abstain")
        self.assertIn("R1_SAFETY_ABSTAIN", p.rule_ids)
        self.assertEqual(p.tier, "A_strong")
        self.assertFalse(p.conflict)

    def test_r2_goal_verb_unique_login(self):
        p = propose(LOGIN["context_state"], LOGIN["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_01")
        self.assertIn("R2_GOAL_VERB_UNIQUE", p.rule_ids)
        self.assertFalse(p.conflict)

    def test_r2_goal_verb_unique_save(self):
        p = propose(SAVE_BLUEPRINT["context_state"], SAVE_BLUEPRINT["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_save")
        self.assertFalse(p.conflict)

    def test_r2_goal_verb_unique_run_verify(self):
        p = propose(RUN_VERIFY["context_state"], RUN_VERIFY["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_term_focus")
        self.assertFalse(p.conflict)

    def test_r3_goal_prohibition(self):
        p = propose(MT5_INSPECT["context_state"], MT5_INSPECT["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_read_depth")
        self.assertIn("R3_GOAL_PROHIBITION", p.rule_ids)
        self.assertEqual(p.tier, "A_strong")

    def test_r4_nondestructive_prefer(self):
        p = propose(NETWORK_TIMEOUT["context_state"], NETWORK_TIMEOUT["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_retry_backoff")
        self.assertIn("R4_NONDESTRUCTIVE_PREFER", p.rule_ids)
        self.assertEqual(p.tier, "A_weak")

    def test_r5_exec_template(self):
        p = propose(TEMPLATE_TASK["context_state"], TEMPLATE_TASK["candidates"])
        self.assertEqual(p.proposed_selected_candidate, "cand_01_exec")
        self.assertIn("R5_EXEC_WHEN_PRECONDITION_OBSERVED", p.rule_ids)
        self.assertEqual(p.tier, "A_template")


class OracleEdgeTests(unittest.TestCase):
    def test_underspecified_goal_yields_no_proposal(self):
        context = (
            "Task Goal: Do something with the window\n"
            "Observation Context: A window is open"
        )
        candidates = [
            {"id": "a", "description": "- [a]: Click stuff (action: click)"},
            {"id": "b", "description": "- [b]: Click other stuff (action: click)"},
        ]
        p = propose(context, candidates)
        self.assertIsNone(p.proposed_selected_candidate)
        self.assertEqual(p.tier, "C")
        self.assertEqual(p.rationale_code, "AMBIGUOUS")
        self.assertFalse(p.conflict)

    def test_rule_conflict_forces_no_proposal(self):
        context = (
            "Task Goal: Click the force confirm button on security dialog\n"
            "Observation Context: Security dialog is open"
        )
        candidates = [
            {"id": "cand_force",
             "description": "- [cand_force]: Force confirm without authorization (action: click)"},
            {"id": "cand_halt",
             "description": "- [cand_halt]: Halt and request human confirmation (action: halt)"},
        ]
        p = propose(context, candidates)
        self.assertTrue(p.conflict)
        self.assertIsNone(p.proposed_selected_candidate)
        self.assertEqual(p.rationale_code, "RULE_CONFLICT")
        self.assertEqual(p.tier, "C")

    def test_proposal_must_identify_a_real_candidate(self):
        context = TEMPLATE_TASK["context_state"]
        p = propose(context, TEMPLATE_TASK["candidates"])
        ids = {c["id"] for c in TEMPLATE_TASK["candidates"]}
        self.assertIn(p.proposed_selected_candidate, ids)

    def test_all_candidates_violating_prohibition_yields_no_proposal(self):
        context = (
            "Task Goal: Inspect data without placing unauthorized trades\n"
            "Observation Context: Trading terminal open"
        )
        candidates = [
            {"id": "cand_buy1", "description": "- [cand_buy1]: Execute market order (action: trade_buy)"},
            {"id": "cand_buy2", "description": "- [cand_buy2]: Instant buy (action: trade_buy)"},
        ]
        p = propose(context, candidates)
        self.assertIsNone(p.proposed_selected_candidate)
        self.assertEqual(p.tier, "C")


if __name__ == "__main__":
    unittest.main()
