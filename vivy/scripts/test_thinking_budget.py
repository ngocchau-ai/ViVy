#!/usr/bin/env python3
"""P1 Dynamic Thinking Budget tests.

Maps EpistemicGate / directive decisions to a per-request thinking budget
(0 / 384 / 1024) instead of force-disabling thinking or relying on a single
static server-level hard cap.

Gate 9: these tests assert mapping and payload shape only. They do NOT claim
latency, quality, or accuracy gains from enabling thinking.

Changelog:
    23/09/2026 (Claude Code — P1 Dynamic Thinking Budget): Initial.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ResolveThinkingBudgetTests(unittest.TestCase):
    def test_execute_directly_maps_to_off(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_OFF,
            resolve_thinking_budget,
        )

        self.assertEqual(resolve_thinking_budget("EXECUTE_DIRECTLY"), THINKING_BUDGET_OFF)
        self.assertEqual(resolve_thinking_budget("EXECUTE"), THINKING_BUDGET_OFF)
        self.assertEqual(resolve_thinking_budget("HALT"), THINKING_BUDGET_OFF)

    def test_foraging_and_continue_map_to_standard(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_STANDARD,
            resolve_thinking_budget,
        )

        for decision in (
            "NEED_KNOWLEDGE_FORAGING",
            "NEED_INFO",
            "CONTINUE",
            "FORAGE",
            "UNKNOWN",
        ):
            self.assertEqual(
                resolve_thinking_budget(decision),
                THINKING_BUDGET_STANDARD,
                f"decision={decision}",
            )

    def test_delegate_maps_to_deep(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_DEEP,
            resolve_thinking_budget,
        )

        for decision in (
            "DELEGATE_MODEL",
            "DELEGATE_CODEX",
            "DELEGATE_CLAUDE",
            "DELEGATE",
            "BACKTRACK",
            "INCIDENT",
        ):
            self.assertEqual(
                resolve_thinking_budget(decision),
                THINKING_BUDGET_DEEP,
                f"decision={decision}",
            )

    def test_none_and_unknown_default_to_standard(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_STANDARD,
            resolve_thinking_budget,
        )

        self.assertEqual(resolve_thinking_budget(None), THINKING_BUDGET_STANDARD)
        self.assertEqual(resolve_thinking_budget("NOT_A_REAL_DECISION"), THINKING_BUDGET_STANDARD)
        self.assertEqual(resolve_thinking_budget(""), THINKING_BUDGET_STANDARD)

    def test_accepts_epistemic_decision_enum(self):
        from orchestrator.epistemic_gate import EpistemicDecision
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_DEEP,
            THINKING_BUDGET_OFF,
            THINKING_BUDGET_STANDARD,
            resolve_thinking_budget,
        )

        self.assertEqual(resolve_thinking_budget(EpistemicDecision.EXECUTE_DIRECTLY), THINKING_BUDGET_OFF)
        self.assertEqual(resolve_thinking_budget(EpistemicDecision.NEED_KNOWLEDGE_FORAGING), THINKING_BUDGET_STANDARD)
        self.assertEqual(resolve_thinking_budget(EpistemicDecision.DELEGATE_MODEL), THINKING_BUDGET_DEEP)

    def test_accepts_decision_controller_aliases(self):
        from orchestrator.decision_controller import Decision
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_DEEP,
            THINKING_BUDGET_OFF,
            THINKING_BUDGET_STANDARD,
            resolve_thinking_budget,
        )

        self.assertEqual(resolve_thinking_budget(Decision.CONTINUE), THINKING_BUDGET_STANDARD)
        self.assertEqual(resolve_thinking_budget(Decision.FORAGE), THINKING_BUDGET_STANDARD)
        self.assertEqual(resolve_thinking_budget(Decision.DELEGATE), THINKING_BUDGET_DEEP)
        self.assertEqual(resolve_thinking_budget(Decision.HALT), THINKING_BUDGET_OFF)

    def test_is_case_insensitive(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_OFF,
            resolve_thinking_budget,
        )

        self.assertEqual(resolve_thinking_budget("execute_directly"), THINKING_BUDGET_OFF)
        self.assertEqual(resolve_thinking_budget("Execute_Directly"), THINKING_BUDGET_OFF)


class ClampThinkingBudgetTests(unittest.TestCase):
    def test_clamp_bounds(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_CEILING,
            THINKING_BUDGET_OFF,
            clamp_thinking_budget,
        )

        self.assertEqual(clamp_thinking_budget(-5), THINKING_BUDGET_OFF)
        self.assertEqual(clamp_thinking_budget(0), 0)
        self.assertEqual(clamp_thinking_budget(384), 384)
        self.assertEqual(clamp_thinking_budget(THINKING_BUDGET_CEILING), THINKING_BUDGET_CEILING)
        self.assertEqual(clamp_thinking_budget(99_999), THINKING_BUDGET_CEILING)


class BuildChatTemplateKwargsTests(unittest.TestCase):
    def test_zero_budget_disables_thinking(self):
        from orchestrator.thinking_budget import build_chat_template_kwargs

        self.assertEqual(build_chat_template_kwargs(0), {"enable_thinking": False})

    def test_positive_budget_enables_thinking_with_budget(self):
        from orchestrator.thinking_budget import build_chat_template_kwargs

        self.assertEqual(
            build_chat_template_kwargs(384),
            {"enable_thinking": True, "thinking_budget": 384},
        )
        self.assertEqual(
            build_chat_template_kwargs(1024),
            {"enable_thinking": True, "thinking_budget": 1024},
        )

    def test_negative_budget_disables_thinking(self):
        from orchestrator.thinking_budget import build_chat_template_kwargs

        self.assertEqual(build_chat_template_kwargs(-1), {"enable_thinking": False})

    def test_budget_above_ceiling_is_clamped(self):
        from orchestrator.thinking_budget import (
            THINKING_BUDGET_CEILING,
            build_chat_template_kwargs,
        )

        kwargs = build_chat_template_kwargs(50_000)
        self.assertTrue(kwargs["enable_thinking"])
        self.assertEqual(kwargs["thinking_budget"], THINKING_BUDGET_CEILING)


class BuildThinkingPayloadFieldsTests(unittest.TestCase):
    def test_fields_keep_reasoning_format_none(self):
        from orchestrator.thinking_budget import build_thinking_payload_fields

        for budget in (0, 384, 1024):
            fields = build_thinking_payload_fields(budget)
            self.assertEqual(fields["reasoning_format"], "none", f"budget={budget}")
            self.assertIn("chat_template_kwargs", fields)

    def test_fields_toggle_enable_thinking_per_request(self):
        from orchestrator.thinking_budget import build_thinking_payload_fields

        off = build_thinking_payload_fields(0)
        on = build_thinking_payload_fields(384)
        self.assertFalse(off["chat_template_kwargs"]["enable_thinking"])
        self.assertTrue(on["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(on["chat_template_kwargs"]["thinking_budget"], 384)


class LlamaCppBridgePayloadTests(unittest.TestCase):
    def test_chat_accepts_thinking_budget_parameter(self):
        import inspect

        from integration.llama_cpp_bridge import LlamaCppBridge

        sig = inspect.signature(LlamaCppBridge.chat)
        self.assertIn("thinking_budget", sig.parameters)
        self.assertIn("epistemic_decision", sig.parameters)

    def test_chat_safe_forwards_thinking_budget_parameter(self):
        import inspect

        from integration.llama_cpp_bridge import LlamaCppBridge

        sig = inspect.signature(LlamaCppBridge.chat_safe)
        self.assertIn("thinking_budget", sig.parameters)
        self.assertIn("epistemic_decision", sig.parameters)

    def test_build_request_payload_applies_budget(self):
        from integration.llama_cpp_bridge import build_request_payload

        payload = build_request_payload(
            model="gemma4-e4b",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.15,
            top_p=0.9,
            max_tokens=768,
            thinking_budget=1024,
        )
        self.assertEqual(payload["reasoning_format"], "none")
        self.assertTrue(payload["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(payload["chat_template_kwargs"]["thinking_budget"], 1024)

    def test_build_request_payload_default_is_off(self):
        from integration.llama_cpp_bridge import build_request_payload

        payload = build_request_payload(
            model="gemma4-e4b",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.15,
            top_p=0.9,
            max_tokens=768,
        )
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])

    def test_build_request_payload_resolves_epistemic_decision(self):
        from integration.llama_cpp_bridge import build_request_payload

        payload = build_request_payload(
            model="gemma4-e4b",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.15,
            top_p=0.9,
            max_tokens=768,
            epistemic_decision="DELEGATE_MODEL",
        )
        self.assertTrue(payload["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(payload["chat_template_kwargs"]["thinking_budget"], 1024)

    def test_content_fallback_reads_reasoning_content(self):
        """When thinking is on, Gemma4 may route text into reasoning_content."""
        from integration.llama_cpp_bridge import _extract_content

        self.assertEqual(_extract_content({"content": "hello", "reasoning_content": "think"}), "hello")
        self.assertEqual(_extract_content({"content": "", "reasoning_content": "think"}), "think")
        self.assertEqual(_extract_content({"content": None, "reasoning_content": "think"}), "think")
        self.assertEqual(_extract_content({}), "")


class OllamaChatPayloadTests(unittest.TestCase):
    def _load_vivy_call(self):
        """Import vivy_call.py from the HoH skill tree."""
        import importlib.util
        from pathlib import Path

        repo = Path(__file__).resolve().parents[3]
        path = repo / ".agents" / "skills" / "hoh-vivy-default" / "scripts" / "vivy_call.py"
        spec = importlib.util.spec_from_file_location("vivy_call_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_build_ollama_payload_applies_budget(self):
        mod = self._load_vivy_call()
        payload = mod.build_ollama_payload(
            [{"role": "user", "content": "hi"}],
            thinking_budget=384,
        )
        self.assertEqual(payload["reasoning_format"], "none")
        self.assertTrue(payload["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(payload["chat_template_kwargs"]["thinking_budget"], 384)

    def test_build_ollama_payload_default_is_off(self):
        mod = self._load_vivy_call()
        payload = mod.build_ollama_payload([{"role": "user", "content": "hi"}])
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])

    def test_ollama_chat_accepts_thinking_budget(self):
        import inspect

        mod = self._load_vivy_call()
        sig = inspect.signature(mod.ollama_chat)
        self.assertIn("thinking_budget", sig.parameters)


class InferenceLoopBudgetWiringTests(unittest.TestCase):
    def test_pipeline_uses_resolve_thinking_budget_for_next_round(self):
        """Static check: _run_pipeline must consult resolve_thinking_budget."""
        import ast
        from pathlib import Path

        src_path = Path(__file__).resolve().parents[1] / "integration" / "vivy_inference_loop.py"
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        self.assertIn("resolve_thinking_budget", names)
        self.assertIn("thinking_budget", names)


if __name__ == "__main__":
    unittest.main()
