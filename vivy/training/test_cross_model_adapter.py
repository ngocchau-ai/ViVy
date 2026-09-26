"""Tests for cross_model_adapter (Wave 2B — routing + output composition).

Changelog:
    25/09/2026 (Claude Code — Wave 2B): Initial.
"""
from __future__ import annotations

import unittest

from training.cross_model_adapter import Coupling, CrossModelAdapter
from training.weight_pager import WeightPager


class TestCoupling(unittest.TestCase):
    def test_matches_any_when_no_tags(self) -> None:
        c = Coupling(primary="a", secondary="b")
        self.assertTrue(c.matches_task("anything"))

    def test_matches_tagged(self) -> None:
        c = Coupling(primary="a", secondary="b", task_tags=("code", "refactor"))
        self.assertTrue(c.matches_task("code"))
        self.assertFalse(c.matches_task("chat"))

    def test_to_dict(self) -> None:
        c = Coupling(primary="a", secondary="b", task_tags=("t",), blend_ratio=0.3)
        d = c.to_dict()
        self.assertEqual(d["primary"], "a")
        self.assertEqual(d["blend_ratio"], 0.3)


class TestCrossModelCouple(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = CrossModelAdapter()

    def test_couple_creates(self) -> None:
        c = self.adapter.couple("gemma4", "qwen70b")
        self.assertEqual(c.primary, "gemma4")
        self.assertEqual(self.adapter.coupling_count, 1)

    def test_same_alias_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.couple("m", "m")

    def test_invalid_blend_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.couple("a", "b", blend_ratio=1.5)

    def test_list_couplings(self) -> None:
        self.adapter.couple("a", "b", task_tags=("x",))
        entries = self.adapter.list_couplings()
        self.assertEqual(len(entries), 1)
        self.assertIn("x", entries[0]["task_tags"])


class TestCrossModelRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = CrossModelAdapter()

    def test_explicit_rule_wins(self) -> None:
        self.adapter.couple("gemma4", "qwen70b")
        self.adapter.set_route("code", "coder7b")
        r = self.adapter.route("code")
        self.assertEqual(r.model_alias, "coder7b")
        self.assertIn("explicit_rule", r.reason)

    def test_coupling_route_low_complexity_primary(self) -> None:
        self.adapter.couple("gemma4", "qwen70b", blend_ratio=0.7)
        r = self.adapter.route("reasoning", {"complexity": 0.2})
        self.assertEqual(r.model_alias, "gemma4")

    def test_coupling_route_high_complexity_secondary(self) -> None:
        self.adapter.couple("gemma4", "qwen70b", blend_ratio=0.3)
        r = self.adapter.route("reasoning", {"complexity": 0.9})
        self.assertEqual(r.model_alias, "qwen70b")

    def test_fallback_when_no_match(self) -> None:
        self.adapter.set_fallback("gemma4")
        r = self.adapter.route("unknown_task")
        self.assertEqual(r.model_alias, "gemma4")
        self.assertEqual(r.reason, "fallback")

    def test_no_route_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.route("no_match_task")


class TestCrossModelCombine(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = CrossModelAdapter()

    def test_blend_zero_returns_primary(self) -> None:
        out = self.adapter.combine_outputs("PRIMARY", "SECOND", blend_ratio=0.0)
        self.assertEqual(out, "PRIMARY")

    def test_blend_one_returns_secondary(self) -> None:
        out = self.adapter.combine_outputs("PRIMARY", "SECOND", blend_ratio=1.0)
        self.assertEqual(out, "SECOND")

    def test_blend_half_interleaves(self) -> None:
        out = self.adapter.combine_outputs("AAAABBBB", "CCCCDDDD", blend_ratio=0.5)
        self.assertIn("AAAA", out)
        self.assertIn("CCCC", out)

    def test_invalid_blend_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.combine_outputs("a", "b", blend_ratio=2.0)

    def test_custom_separator(self) -> None:
        out = self.adapter.combine_outputs("ABC", "XYZ", blend_ratio=0.5, separator="|")
        self.assertIn("|", out)


class TestCrossModelCallbackWeights(unittest.TestCase):
    def setUp(self) -> None:
        self.pager = WeightPager()
        self.pager.register_model("gemma4", "/m.gguf", "gguf", total_layers=20)
        self.adapter = CrossModelAdapter(weight_pager=self.pager)

    def test_callback_returns_slice(self) -> None:
        s = self.adapter.callback_weights("gemma4", "special_reasoning")
        assert s is not None
        self.assertEqual(s.alias, "gemma4")
        self.assertEqual(s.layer_range, (0, 5))  # 20 // 4

    def test_callback_unregistered_returns_none(self) -> None:
        self.assertIsNone(self.adapter.callback_weights("ghost", "task"))

    def test_callback_default_when_no_layers(self) -> None:
        self.pager.register_model("small", "/s.gguf", "gguf", total_layers=0)
        s = self.adapter.callback_weights("small", "t")
        assert s is not None
        self.assertEqual(s.layer_range, (0, 4))  # 16 // 4 (default total)


class TestCrossModelCouplingForTask(unittest.TestCase):
    def test_finds_matching_coupling(self) -> None:
        adapter = CrossModelAdapter()
        adapter.couple("a", "b", task_tags=("code",))
        adapter.couple("c", "d", task_tags=("chat",))
        found = adapter.coupling_for_task("chat")
        assert found is not None
        self.assertEqual(found.primary, "c")

    def test_returns_none_when_no_match(self) -> None:
        adapter = CrossModelAdapter()
        adapter.couple("a", "b", task_tags=("code",))
        self.assertIsNone(adapter.coupling_for_task("chat"))


if __name__ == "__main__":
    unittest.main()
