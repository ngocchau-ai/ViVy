"""Tests for model_upgrade_protocol (Wave 4A — progressive scaling).

Changelog:
    25/09/2026 (Claude Code — Wave 4A): Initial.
"""
from __future__ import annotations

import unittest

from training.model_upgrade_protocol import MigrationReceipt, UpgradeProtocol
from training.weight_pager import WeightPager


def _make_ready_protocol(
    n_scores: int = 120,
    avg: float = 0.85,
) -> UpgradeProtocol:
    """Build a protocol that passes all readiness gates."""
    proto = UpgradeProtocol(memory_threshold=100, score_threshold=0.7)
    proto.set_hardware_available(True)
    proto.set_task_complexity("medium")
    for _ in range(n_scores):
        proto.add_experience(avg)
    return proto


class TestReadinessCheck(unittest.TestCase):
    def test_not_ready_no_experience(self) -> None:
        proto = UpgradeProtocol()
        report = proto.readiness_check()
        self.assertFalse(report.is_ready)
        self.assertGreater(len(report.blockers), 0)

    def test_not_ready_no_hardware(self) -> None:
        proto = UpgradeProtocol(memory_threshold=1, score_threshold=0.0)
        proto.add_experience(0.9)
        report = proto.readiness_check()
        self.assertFalse(report.is_ready)
        self.assertTrue(any("hardware" in b for b in report.blockers))

    def test_not_ready_low_score(self) -> None:
        proto = UpgradeProtocol(memory_threshold=1, score_threshold=0.7)
        proto.set_hardware_available(True)
        proto.add_experience(0.3)
        report = proto.readiness_check()
        self.assertFalse(report.is_ready)
        self.assertTrue(any("avg_decision_score" in b for b in report.blockers))

    def test_not_ready_low_memory(self) -> None:
        proto = UpgradeProtocol(memory_threshold=100, score_threshold=0.0)
        proto.set_hardware_available(True)
        proto.add_experience(0.9)
        report = proto.readiness_check()
        self.assertFalse(report.is_ready)
        self.assertTrue(any("memory_entries" in b for b in report.blockers))

    def test_ready(self) -> None:
        proto = _make_ready_protocol()
        report = proto.readiness_check()
        self.assertTrue(report.is_ready)
        self.assertEqual(report.blockers, [])

    def test_report_to_dict(self) -> None:
        proto = _make_ready_protocol()
        d = proto.readiness_check().to_dict()
        self.assertIn("is_ready", d)
        self.assertIn("blockers", d)
        self.assertIn("memory_entries", d)


class TestExperience(unittest.TestCase):
    def test_add_experience(self) -> None:
        proto = UpgradeProtocol()
        proto.add_experience(0.8)
        proto.add_experience(0.6)
        self.assertEqual(proto.memory_entries, 2)
        self.assertAlmostEqual(proto.avg_decision_score, 0.7)

    def test_invalid_score_raises(self) -> None:
        proto = UpgradeProtocol()
        with self.assertRaises(ValueError):
            proto.add_experience(1.5)

    def test_avg_empty(self) -> None:
        proto = UpgradeProtocol()
        self.assertEqual(proto.avg_decision_score, 0.0)

    def test_set_complexity_valid(self) -> None:
        proto = UpgradeProtocol()
        proto.set_task_complexity("high")
        report = proto.readiness_check()
        self.assertEqual(report.task_complexity, "high")

    def test_set_complexity_invalid(self) -> None:
        proto = UpgradeProtocol()
        with self.assertRaises(ValueError):
            proto.set_task_complexity("extreme")


class TestMigrate(unittest.TestCase):
    def test_migrate_creates_receipt(self) -> None:
        proto = _make_ready_protocol()
        receipt = proto.migrate("gemma4-e4b", "qwen-70b", timestamp="2026-09-25")
        self.assertEqual(receipt.old_alias, "gemma4-e4b")
        self.assertEqual(receipt.new_alias, "qwen-70b")
        self.assertEqual(receipt.label, "PROVISIONAL_RESULT")

    def test_migrate_not_ready_raises(self) -> None:
        proto = UpgradeProtocol()
        with self.assertRaises(ValueError) as ctx:
            proto.migrate("a", "b")
        self.assertIn("blocked", str(ctx.exception))

    def test_migrate_same_alias_raises(self) -> None:
        proto = _make_ready_protocol()
        with self.assertRaises(ValueError):
            proto.migrate("m", "m")

    def test_migrate_genesis_receipt(self) -> None:
        proto = _make_ready_protocol()
        r = proto.migrate("a", "b")
        self.assertTrue(r.is_genesis)
        self.assertEqual(r.prev_sha256, "GENESIS")

    def test_migrate_chain(self) -> None:
        proto = _make_ready_protocol()
        r1 = proto.migrate("a", "b")
        r2 = proto.migrate("b", "c")
        self.assertEqual(r2.prev_sha256, r1.self_sha256)
        self.assertFalse(r2.is_genesis)

    def test_migrate_registers_inherited_weights(self) -> None:
        pager = WeightPager()
        pager.register_model("gemma4", "/m.gguf", "gguf", total_layers=28)
        proto2 = UpgradeProtocol(weight_pager=pager)
        proto2.set_hardware_available(True)
        for _ in range(120):
            proto2.add_experience(0.85)
        proto2.migrate("gemma4", "qwen-70b")
        entry = proto2.get_inherited_weights("gemma4")
        assert entry is not None
        self.assertEqual(entry["status"], "REGISTERED_FOR_CALLBACK")


class TestInheritWeights(unittest.TestCase):
    def test_inherit_registered_model(self) -> None:
        pager = WeightPager()
        pager.register_model("old", "/old.gguf", "gguf", total_layers=20)
        proto = UpgradeProtocol(weight_pager=pager)
        entry = proto.inherit_weights("old")
        self.assertEqual(entry["alias"], "old")
        self.assertEqual(entry["total_layers"], 20)
        self.assertEqual(entry["status"], "REGISTERED_FOR_CALLBACK")

    def test_inherit_unregistered_minimal(self) -> None:
        proto = UpgradeProtocol()
        entry = proto.inherit_weights("ghost")
        self.assertEqual(entry["status"], "MINIMAL_ENTRY")
        self.assertEqual(entry["alias"], "ghost")

    def test_get_inherited_weights(self) -> None:
        proto = UpgradeProtocol()
        proto.inherit_weights("m")
        self.assertIsNotNone(proto.get_inherited_weights("m"))
        self.assertIsNone(proto.get_inherited_weights("other"))

    def test_inherited_count(self) -> None:
        proto = UpgradeProtocol()
        proto.inherit_weights("a")
        proto.inherit_weights("b")
        self.assertEqual(proto.inherited_count, 2)


class TestChainVerification(unittest.TestCase):
    def test_empty_chain_ok(self) -> None:
        proto = UpgradeProtocol()
        self.assertTrue(proto.verify_chain())

    def test_valid_chain(self) -> None:
        proto = _make_ready_protocol()
        proto.migrate("a", "b")
        proto.migrate("b", "c")
        proto.migrate("c", "d")
        self.assertTrue(proto.verify_chain())

    def test_receipt_count(self) -> None:
        proto = _make_ready_protocol()
        proto.migrate("a", "b")
        self.assertEqual(proto.receipt_count, 1)


class TestSerialization(unittest.TestCase):
    def test_round_trip(self) -> None:
        proto = _make_ready_protocol()
        proto.migrate("a", "b", timestamp="2026-09-25")
        d = proto.to_dict()
        proto2 = UpgradeProtocol.from_dict(d)
        self.assertEqual(proto2.memory_entries, 120)
        self.assertEqual(proto2.receipt_count, 1)
        self.assertTrue(proto2.verify_chain())

    def test_round_trip_weight_registry(self) -> None:
        proto = UpgradeProtocol()
        proto.inherit_weights("old")
        d = proto.to_dict()
        proto2 = UpgradeProtocol.from_dict(d)
        self.assertIsNotNone(proto2.get_inherited_weights("old"))

    def test_empty_round_trip(self) -> None:
        proto = UpgradeProtocol()
        proto2 = UpgradeProtocol.from_dict(proto.to_dict())
        self.assertEqual(proto2.memory_entries, 0)
        self.assertEqual(proto2.receipt_count, 0)


class TestMigrationReceipt(unittest.TestCase):
    def test_to_dict(self) -> None:
        r = MigrationReceipt(
            receipt_id="m1", old_alias="a", new_alias="b",
            timestamp="t", prev_sha256="GENESIS", self_sha256="abc",
        )
        d = r.to_dict()
        self.assertEqual(d["receipt_id"], "m1")
        self.assertEqual(d["label"], "PROVISIONAL_RESULT")


if __name__ == "__main__":
    unittest.main()
