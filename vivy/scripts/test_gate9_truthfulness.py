#!/usr/bin/env python3
"""Gate 9 truthfulness tests — P0 Superority Truth Pass.

Gate 9 (ACCEPTANCE_GATES.md): no `PRODUCTION-READY`, `0%`, `O(1)`, or latency
claim is accepted without a reproducible benchmark or receipt.

These tests assert that runtime-emitted strings (prompt injection, intuition
digest) do NOT carry unverified absolute claims. Prior claim text is preserved
in source comments as [ISOLATED], never deleted from history.

Changelog:
    23/09/2026 (Claude Code — P0 Superority Truth Pass): Initial.
"""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Absolute / unverified claim patterns Gate 9 forbids in runtime output.
FORBIDDEN_CLAIM = re.compile(
    r"(repeat\s*rate\s*=\s*0(\.0)?%|"
    r"error\s*rate\s*0%|"
    r"0\.00ms|"
    r"0ms\s*RAM|"
    r"latency\s*=\s*0|"
    r"PRODUCTION-READY|"
    r"0%\s*repeat|"
    r"0%\s*retry)",
    re.I,
)


class PreflightInjectionGate9Tests(unittest.TestCase):
    def test_injection_has_no_unverified_zero_claim(self):
        from integration.preflight_steering import PreflightPacket

        packet = PreflightPacket(
            negative_constraints=["do not retry falsified trade_buy"],
            intuition_anchors=["prior save succeeded"],
            directive_summary="mode=CONTINUE confidence=0.8",
        )
        text = packet.to_system_injection()
        self.assertTrue(text, "expected non-empty injection")
        match = FORBIDDEN_CLAIM.search(text)
        self.assertIsNone(
            match,
            f"Gate 9 violation in preflight injection: {match.group(0) if match else ''}",
        )

    def test_injection_still_marks_vm11_enforcement_without_rate_claim(self):
        from integration.preflight_steering import PreflightPacket

        packet = PreflightPacket(negative_constraints=["do not retry falsified trade_buy"])
        text = packet.to_system_injection()
        self.assertIn("VM-11", text)
        self.assertIn("FORBIDDEN", text)
        self.assertNotIn("0%", text)


class IntuitionDigestGate9Tests(unittest.TestCase):
    def test_fallback_digest_has_no_unverified_zero_claim(self):
        from integration.cautreo_binding import CautreoContextMemory

        mem = CautreoContextMemory(max_items=8)
        digest = mem.build_intuition_digest()
        match = FORBIDDEN_CLAIM.search(digest)
        self.assertIsNone(
            match,
            f"Gate 9 violation in intuition digest: {match.group(0) if match else ''}",
        )
        self.assertNotIn("0%", digest)


class DocstringGate9Tests(unittest.TestCase):
    def test_preflight_module_docstring_has_no_zero_percent_claim(self):
        import integration.preflight_steering as mod

        doc = mod.__doc__ or ""
        # [ISOLATED] changelog lines may quote prior claims — the project rule is
        # isolate, never delete. Live docstring prose must stay Gate-9 clean.
        live_lines = [
            line for line in doc.splitlines() if "[ISOLATED" not in line.upper()
        ]
        live = "\n".join(live_lines)
        match = FORBIDDEN_CLAIM.search(live)
        self.assertIsNone(
            match,
            f"Gate 9 violation in preflight docstring: {match.group(0) if match else ''}",
        )


class SystemPromptGate9Tests(unittest.TestCase):
    """VIVY_SYSTEM_PROMPT is emitted verbatim into every LLM call."""

    def test_system_prompt_has_no_unverified_zero_claim(self):
        from integration.vivy_inference_loop import VIVY_SYSTEM_PROMPT

        live_lines = [
            line
            for line in VIVY_SYSTEM_PROMPT.splitlines()
            if "[ISOLATED" not in line.upper()
        ]
        live = "\n".join(live_lines)
        match = FORBIDDEN_CLAIM.search(live)
        self.assertIsNone(
            match,
            f"Gate 9 violation in VIVY_SYSTEM_PROMPT: {match.group(0) if match else ''}",
        )
        self.assertNotIn("0ms RAM", live)
        self.assertNotIn("0% repeat", live.lower())

    def test_system_prompt_still_marks_vm11(self):
        from integration.vivy_inference_loop import VIVY_SYSTEM_PROMPT

        self.assertIn("VM-11", VIVY_SYSTEM_PROMPT)


class ParallelPipelineGate9Tests(unittest.TestCase):
    def test_fused_prompt_template_has_no_unverified_zero_claim(self):
        import ast
        import inspect

        import integration.parallel_context_pipeline as mod

        src = inspect.getsource(mod)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                live_lines = [
                    line
                    for line in node.value.splitlines()
                    if "[ISOLATED" not in line.upper()
                ]
                live = "\n".join(live_lines)
                match = FORBIDDEN_CLAIM.search(live)
                self.assertIsNone(
                    match,
                    f"Gate 9 violation in parallel_context_pipeline string: "
                    f"{match.group(0) if match else ''}",
                )


class DesktopBridgeGate9Tests(unittest.TestCase):
    """Seeded constraints and vitals invariants are shown in the Desktop UI."""

    def test_desktop_bridge_module_source_has_no_unverified_zero_claim(self):
        import ast
        from pathlib import Path

        candidates = [
            Path(__file__).resolve().parents[2]
            / "desktop"
            / "backend"
            / "bridge.py",
            Path(__file__).resolve().parents[2]
            / "desktop"
            / "backend"
            / "server.py",
            Path(__file__).resolve().parents[2]
            / "desktop"
            / "backend"
            / "sockets"
            / "harness_socket.py",
        ]
        for path in candidates:
            if not path.exists():
                continue
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    live_lines = [
                        line
                        for line in node.value.splitlines()
                        if "[ISOLATED" not in line.upper()
                    ]
                    live = "\n".join(live_lines)
                    match = FORBIDDEN_CLAIM.search(live)
                    self.assertIsNone(
                        match,
                        f"Gate 9 violation in {path.name}: "
                        f"{match.group(0) if match else ''}",
                    )


if __name__ == "__main__":
    unittest.main()
