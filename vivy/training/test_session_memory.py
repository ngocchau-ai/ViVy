"""C10 tests — session-isolated memory correctness (put/get/delete, TTL, restart)."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from training.session_memory import (
    MemoryConflict,
    MemoryItem,
    MemoryNotFound,
    SessionMemory,
    SessionMemoryHub,
)


class PutGetDeleteTests(unittest.TestCase):
    def test_put_get_roundtrip(self):
        mem = SessionMemory(session_id="s1")
        ver = mem.put("k1", kind="HARD_FACT", content="hello")
        self.assertEqual(ver, 1)
        item = mem.get("k1")
        self.assertIsNotNone(item)
        self.assertEqual(item.content, "hello")
        self.assertEqual(item.kind, "HARD_FACT")
        self.assertEqual(item.version, 1)

    def test_unicode_and_long_values(self):
        mem = SessionMemory(session_id="s1")
        uni = "Tiếng Việt 🌟 newline\nđộ phức tạp O(n)"
        mem.put("uni", kind="SUMMARY", content=uni)
        self.assertEqual(mem.get("uni").content, uni)

        long_val = "x" * 200_000
        mem.put("long", kind="TASK", content=long_val)
        self.assertEqual(mem.get("long").content, long_val)
        self.assertEqual(len(mem.get("long").content), 200_000)

    def test_overwrite_requires_matching_version(self):
        mem = SessionMemory(session_id="s1")
        mem.put("k", kind="TASK", content="v1")
        ver2 = mem.put("k", kind="TASK", content="v2", expected_version=1)
        self.assertEqual(ver2, 2)
        self.assertEqual(mem.get("k").content, "v2")

        with self.assertRaises(MemoryConflict):
            mem.put("k", kind="TASK", content="v3", expected_version=1)

    def test_delete_isolation_and_version(self):
        mem = SessionMemory(session_id="s1")
        mem.put("k", kind="TASK", content="v1")
        mem.delete("k", expected_version=1)
        self.assertIsNone(mem.get("k"))

        with self.assertRaises(MemoryNotFound):
            mem.delete("k", expected_version=1)

        mem.put("k2", kind="TASK", content="a")
        with self.assertRaises(MemoryConflict):
            mem.delete("k2", expected_version=99)

    def test_content_over_limit_refused(self):
        mem = SessionMemory(session_id="s1")
        with self.assertRaises(ValueError):
            mem.put("big", kind="SUMMARY", content="y" * (1024 * 1024 + 1))


class SessionIsolationTests(unittest.TestCase):
    def test_no_cross_session_leak(self):
        hub = SessionMemoryHub()
        a = hub.for_session("session-a")
        b = hub.for_session("session-b")
        a.put("secret", kind="HARD_FACT", content="only-a")
        self.assertIsNone(b.get("secret"))
        self.assertEqual(a.count(), 1)
        self.assertEqual(b.count(), 0)

    def test_delete_in_one_session_leaves_other(self):
        hub = SessionMemoryHub()
        a = hub.for_session("session-a")
        b = hub.for_session("session-b")
        a.put("k", kind="TASK", content="a-val")
        b.put("k", kind="TASK", content="b-val")
        a.delete("k", expected_version=1)
        self.assertIsNone(a.get("k"))
        self.assertEqual(b.get("k").content, "b-val")

    def test_same_id_different_sessions_are_independent_versions(self):
        hub = SessionMemoryHub()
        a = hub.for_session("s-a")
        b = hub.for_session("s-b")
        self.assertEqual(a.put("k", kind="TASK", content="a1"), 1)
        self.assertEqual(b.put("k", kind="TASK", content="b1"), 1)
        self.assertEqual(a.put("k", kind="TASK", content="a2", expected_version=1), 2)
        self.assertEqual(b.get("k").version, 1)


class TtlTests(unittest.TestCase):
    def test_expired_item_is_not_returned(self):
        mem = SessionMemory(session_id="s1")
        mem.put("stale", kind="SUMMARY", content="old", ttl_ms=1000, now_ms=0)
        self.assertIsNotNone(mem.get("stale", now_ms=500))
        self.assertIsNone(mem.get("stale", now_ms=1500))

    def test_zero_ttl_means_no_expiry(self):
        mem = SessionMemory(session_id="s1")
        mem.put("forever", kind="HARD_FACT", content="keep", ttl_ms=0, now_ms=0)
        self.assertIsNotNone(mem.get("forever", now_ms=10**12))


class RestartAndConcurrencyTests(unittest.TestCase):
    def test_restart_restores_items_and_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mem.jsonl"
            a = SessionMemory(session_id="s1", persist_path=path)
            a.put("k", kind="TASK", content="persisted")
            a.put("k", kind="TASK", content="updated", expected_version=1)
            a.checkpoint()

            b = SessionMemory(session_id="s1", persist_path=path)
            item = b.get("k")
            self.assertIsNotNone(item)
            self.assertEqual(item.content, "updated")
            self.assertEqual(item.version, 2)

    def test_concurrent_puts_do_not_corrupt_store(self):
        mem = SessionMemory(session_id="s1")
        errors: list[BaseException] = []

        def worker(idx: int) -> None:
            try:
                for i in range(20):
                    mem.put(f"k-{idx}-{i}", kind="TASK", content=f"v-{idx}-{i}")
                    got = mem.get(f"k-{idx}-{i}")
                    if got is None or got.content != f"v-{idx}-{i}":
                        raise AssertionError(f"corrupt read {idx}/{i}")
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(mem.count(), 8 * 20)


class ItemSchemaTests(unittest.TestCase):
    def test_item_carries_provenance_and_timestamp_kinds(self):
        mem = SessionMemory(session_id="s1")
        mem.put(
            "p",
            kind="HARD_FACT",
            content="c",
            provenance={"source_hash": "sha256:abc", "message_id": "m1"},
        )
        item = mem.get("p")
        self.assertEqual(item.provenance["source_hash"], "sha256:abc")
        self.assertEqual(item.session_id, "s1")
        self.assertIsInstance(item, MemoryItem)
        self.assertGreater(item.created_at_ms, 0)
        self.assertGreaterEqual(item.updated_at_ms, item.created_at_ms)


if __name__ == "__main__":
    unittest.main()
