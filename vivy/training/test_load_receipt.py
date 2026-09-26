"""Tests for load_receipt (AWL-5 — SHA256-chained load-decision log).

Changelog:
    25/09/2026 (Claude Code — AWL-5): Initial.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.cautreo_resource_monitor import ResourceBudget
from training.load_governor import LoadDecision
from training.load_receipt import LoadReceiptLog
from training.verify_receipt import GENESIS


def _decision(alias: str = "qwen-72b", complexity: float = 0.7) -> LoadDecision:
    return LoadDecision(
        alias=alias,
        complexity=complexity,
        current_fraction=0.0,
        target_fraction=0.35,
        target_layers=(0, 28),
        target_mb=280.0,
        action="load",
        reason="scale up to heavy band (0.35)",
        band_label="heavy",
    )


def _budget(headroom: float = 4644.0) -> ResourceBudget:
    return ResourceBudget(
        headroom_mb=headroom,
        max_loadable_mb=headroom,
        current_footprint_mb=2750.0,
        safety_margin_mb=1500.0,
        peak_footprint_mb=2750.0,
        per_model={"gemma4-e4b": 2700.0},
    )


class TestGenesis(unittest.TestCase):
    def test_first_receipt_is_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td, run_id="r1")
            sealed = log.record(_decision())
            self.assertEqual(sealed["prev_receipt_sha256"], GENESIS)
            self.assertEqual(log.last_sha256, sealed["self_sha256"])

    def test_empty_log_last_sha_is_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(LoadReceiptLog(td).last_sha256, GENESIS)


class TestChainLinks(unittest.TestCase):
    def test_chain_links(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td, run_id="r1")
            first = log.record(_decision(complexity=0.1))
            second = log.record(_decision(complexity=0.9))
            third = log.record(_decision(complexity=0.5))
            self.assertEqual(second["prev_receipt_sha256"], first["self_sha256"])
            self.assertEqual(third["prev_receipt_sha256"], second["self_sha256"])

    def test_filenames_sort_in_chain_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            for _ in range(3):
                log.record(_decision())
            names = sorted(p.name for p in Path(td).glob("*.json"))
            self.assertEqual(names[0].startswith("000001-"), True)
            self.assertEqual(names[1].startswith("000002-"), True)
            self.assertEqual(names[2].startswith("000003-"), True)


class TestVerify(unittest.TestCase):
    def test_intact_chain_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td, run_id="r1")
            for c in (0.1, 0.5, 0.9):
                log.record(_decision(complexity=c), budget=_budget())
            report = log.verify()
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["receipt_count"], 3)
            self.assertEqual(report["problems"], [])

    def test_tampered_byte_breaks_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td, run_id="r1")
            log.record(_decision(complexity=0.1))
            log.record(_decision(complexity=0.9))

            # Flip one byte inside the first receipt's stored complexity.
            target = min(Path(td).glob("*.json"))
            data = json.loads(target.read_text(encoding="utf-8"))
            data["decision"]["complexity"] = 0.11
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            report = log.verify()
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("self_sha256 mismatch" in p for p in report["problems"]))

    def test_reordered_receipts_break_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td, run_id="r1")
            log.record(_decision(complexity=0.1))
            log.record(_decision(complexity=0.2))
            log.record(_decision(complexity=0.3))

            # Swap names of receipt 1 and 3 so lexicographic order != chain order.
            files = sorted(Path(td).glob("*.json"))
            tmp = Path(td) / "swap.tmp"
            files[0].rename(tmp)
            files[2].rename(files[0])
            tmp.rename(files[2])

            report = log.verify()
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("chain break" in p for p in report["problems"]))

    def test_missing_prev_link_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            log.record(_decision())
            f = min(Path(td).glob("*.json"))
            data = json.loads(f.read_text(encoding="utf-8"))
            data["prev_receipt_sha256"] = "not-genesis"
            # Keep self_sha256 stale so this is a pure chain-link failure.
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            report = log.verify()
            self.assertEqual(report["status"], "FAIL")


class TestNoOverwrite(unittest.TestCase):
    def test_second_record_does_not_clobber_first(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            first = log.record(_decision(complexity=0.1))
            first_bytes = min(Path(td).glob("*.json")).read_bytes()
            log.record(_decision(complexity=0.9))
            files = sorted(Path(td).glob("*.json"))
            self.assertEqual(len(files), 2)
            self.assertEqual(files[0].read_bytes(), first_bytes)
            self.assertEqual(first["decision"]["complexity"], 0.1)


class TestPayload(unittest.TestCase):
    def test_record_carries_decision_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td, run_id="run-7")
            sealed = log.record(_decision(alias="gemma4-e4b", complexity=0.4), budget=_budget())
            self.assertEqual(sealed["kind"], "awl-load")
            self.assertEqual(sealed["run_id"], "run-7")
            self.assertEqual(sealed["decision"]["alias"], "gemma4-e4b")
            self.assertEqual(sealed["decision"]["complexity"], 0.4)
            self.assertEqual(sealed["decision"]["action"], "load")
            self.assertEqual(sealed["budget"]["headroom_mb"], 4644.0)
            self.assertIn("receipt_id", sealed)
            self.assertIn("self_sha256", sealed)

    def test_live_label_defaults_simulated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            sealed = log.record(_decision())
            self.assertEqual(sealed["live"], "SIMULATED_PROTOCOL")

    def test_live_label_honoured(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            sealed = log.record(_decision(), live="LIVE_MODEL_OBSERVATION")
            self.assertEqual(sealed["live"], "LIVE_MODEL_OBSERVATION")

    def test_budget_optional(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            sealed = log.record(_decision())
            self.assertIsNone(sealed["budget"])


class TestResume(unittest.TestCase):
    def test_chain_resumes_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            first = LoadReceiptLog(td, run_id="session-a")
            r1 = first.record(_decision(complexity=0.1))

            # New instance (process restart) must continue the chain.
            second = LoadReceiptLog(td, run_id="session-b")
            self.assertEqual(second.last_sha256, r1["self_sha256"])
            self.assertEqual(second.count(), 1)
            r2 = second.record(_decision(complexity=0.9))
            self.assertEqual(r2["prev_receipt_sha256"], r1["self_sha256"])
            self.assertEqual(second.verify()["status"], "PASS")

    def test_count_tracks_disk(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = LoadReceiptLog(td)
            self.assertEqual(log.count(), 0)
            log.record(_decision())
            log.record(_decision())
            self.assertEqual(log.count(), 2)


if __name__ == "__main__":
    unittest.main()
