"""IO-guard tests — acceptance plan §2.11 (no input/receipt clobber on rerun)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from training.io_guard import RefuseOverwriteError, open_write, resolved


class IoGuardTests(unittest.TestCase):
    def test_refuses_to_overwrite_source(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text("x\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                open_write(src, protected=(src,))

    def test_refuses_to_overwrite_existing_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "receipt.json"
            out.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(RefuseOverwriteError):
                open_write(out)
            with open_write(out, allow_replace=True) as fh:
                fh.write("{}\n")

    def test_refuses_protected_alias_via_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "gold.jsonl"
            src.write_text("x\n", encoding="utf-8")
            alias = Path(d) / "sub" / ".." / "gold.jsonl"
            with self.assertRaises(RefuseOverwriteError):
                open_write(alias, protected=(src,))
            self.assertEqual(resolved(alias), resolved(src))

    def test_allows_new_path(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "new.jsonl"
            with open_write(out) as fh:
                fh.write("ok\n")
            self.assertEqual(out.read_text(encoding="utf-8"), "ok\n")


if __name__ == "__main__":
    unittest.main()
