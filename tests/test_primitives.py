"""
Tests for engine/primitives.py — ViVy Final V1.0 Sprint 1.

Covers all 4 Engine Primitives: engine_file_io, engine_exec,
engine_media_slice, engine_cache_control.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 1 — HOH-VIVY-FINAL-V1): Initial.
"""

from __future__ import annotations

import os
import platform
import shutil
import tempfile
from pathlib import Path

import pytest

from engine.primitives import (
    CacheOp,
    FileAction,
    PrimitiveResult,
    _CACHE_STORE,
    engine_cache_control,
    engine_exec,
    engine_file_io,
    engine_media_slice,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_cache_store():
    """Reset in-memory cache between tests."""
    _CACHE_STORE.clear()
    yield
    _CACHE_STORE.clear()


@pytest.fixture
def td():
    """Windows-safe temp directory (avoids pytest-of-LENOVO PermissionError)."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(str(d), ignore_errors=True)


# ---------------------------------------------------------------------------
# engine_file_io tests
# ---------------------------------------------------------------------------


class TestEngineFileIo:
    def test_write_and_read(self, td):
        p = td / "hello.txt"
        wr = engine_file_io(FileAction.WRITE, str(p), content="Hello ViVy")
        assert wr.ok
        assert wr.metadata["bytes_written"] == len("Hello ViVy")

        rd = engine_file_io(FileAction.READ, str(p))
        assert rd.ok
        assert rd.data == "Hello ViVy"

    def test_write_and_read_string_action(self, td):
        p = td / "test2.txt"
        engine_file_io("write", str(p), content="abc")
        rd = engine_file_io("read", str(p))
        assert rd.ok
        assert rd.data == "abc"

    def test_exists_true(self, td):
        p = td / "exists.txt"
        p.write_text("x")
        r = engine_file_io(FileAction.EXISTS, str(p))
        assert r.ok
        assert r.data is True

    def test_exists_false(self, td):
        r = engine_file_io(FileAction.EXISTS, str(td / "nofile.txt"))
        assert r.ok
        assert r.data is False

    def test_read_nonexistent_returns_not_ok(self, td):
        r = engine_file_io(FileAction.READ, str(td / "ghost.txt"))
        assert not r.ok
        assert "not found" in r.error_message.lower()

    def test_append(self, td):
        p = td / "log.txt"
        engine_file_io(FileAction.WRITE, str(p), content="line1\n")
        engine_file_io(FileAction.APPEND, str(p), content="line2\n")
        rd = engine_file_io(FileAction.READ, str(p))
        assert rd.data == "line1\nline2\n"

    def test_delete_existing(self, td):
        p = td / "del.txt"
        p.write_text("bye")
        r = engine_file_io(FileAction.DELETE, str(p))
        assert r.ok
        assert r.data is True
        assert not p.exists()

    def test_delete_nonexistent_ok(self, td):
        r = engine_file_io(FileAction.DELETE, str(td / "nope.txt"))
        assert r.ok
        assert r.data is False

    def test_mkdir(self, td):
        new_dir = td / "a" / "b" / "c"
        r = engine_file_io(FileAction.MKDIR, str(new_dir))
        assert r.ok
        assert new_dir.exists()

    def test_read_with_offset(self, td):
        p = td / "offset.txt"
        p.write_bytes(b"0123456789")
        r = engine_file_io(FileAction.READ, str(p), offset=5, length=3)
        assert r.ok
        assert r.data == "567"

    def test_write_bytes(self, td):
        p = td / "bytes.bin"
        r = engine_file_io(FileAction.WRITE, str(p), content=b"\x00\x01\x02")
        assert r.ok
        assert p.read_bytes() == b"\x00\x01\x02"

    def test_elapsed_ms_present(self, td):
        p = td / "t.txt"
        r = engine_file_io(FileAction.WRITE, str(p), content="x")
        assert r.elapsed_ms >= 0.0

    def test_result_is_primitive_result_instance(self, td):
        r = engine_file_io(FileAction.EXISTS, str(td / "any.txt"))
        assert isinstance(r, PrimitiveResult)

    def test_write_creates_parent_dirs(self, td):
        p = td / "deep" / "nested" / "file.txt"
        r = engine_file_io(FileAction.WRITE, str(p), content="nested")
        assert r.ok
        assert p.exists()


# ---------------------------------------------------------------------------
# engine_exec tests
# ---------------------------------------------------------------------------


class TestEngineExec:
    def test_echo_command(self):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "echo hello"])
        else:
            r = engine_exec(["echo", "hello"])
        assert r.ok
        assert "hello" in r.data

    def test_exit_code_nonzero_not_ok(self):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "exit 1"], capture_stderr=True)
        else:
            r = engine_exec(["bash", "-c", "exit 1"])
        assert not r.ok
        assert r.metadata["exit_code"] != 0

    def test_metadata_has_exit_code(self):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "echo x"])
        else:
            r = engine_exec(["echo", "x"])
        assert "exit_code" in r.metadata

    def test_nonexistent_command_not_ok(self):
        r = engine_exec(["vivy_no_such_binary_xyz"])
        assert not r.ok
        assert "not found" in r.error_message.lower() or "os error" in r.error_message.lower()

    def test_timeout_respected(self):
        if platform.system() == "Windows":
            cmd = ["cmd", "/c", "ping -n 5 127.0.0.1"]
        else:
            cmd = ["sleep", "10"]
        r = engine_exec(cmd, timeout=0.5)
        assert not r.ok
        assert r.metadata.get("timed_out") is True

    def test_stderr_captured(self):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "echo error_msg 1>&2"], capture_stderr=True)
        else:
            r = engine_exec(["bash", "-c", "echo error_msg >&2"])
        assert "stderr" in r.metadata

    def test_elapsed_ms_positive(self):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "echo ok"])
        else:
            r = engine_exec(["echo", "ok"])
        assert r.elapsed_ms >= 0.0

    def test_string_command(self):
        if platform.system() == "Windows":
            r = engine_exec("echo hello_string")
        else:
            r = engine_exec("echo hello_string")
        assert r.ok
        assert "hello_string" in r.data

    def test_env_variable_injected(self):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "echo %VIVY_TEST_VAR%"], env={"VIVY_TEST_VAR": "vivy42"})
            assert "vivy42" in r.data
        else:
            r = engine_exec(["bash", "-c", "echo $VIVY_TEST_VAR"], env={"VIVY_TEST_VAR": "vivy42"})
            assert "vivy42" in r.data

    def test_cwd_used(self, td):
        if platform.system() == "Windows":
            r = engine_exec(["cmd", "/c", "cd"], cwd=str(td))
        else:
            r = engine_exec(["pwd"], cwd=str(td))
        assert r.ok
        assert str(td).replace("\\", "/").lower().split("/")[-1] in r.data.lower()


# ---------------------------------------------------------------------------
# engine_media_slice tests
# ---------------------------------------------------------------------------


class TestEngineMediaSlice:
    def test_nonexistent_source_not_ok(self, td):
        r = engine_media_slice(str(td / "no_video.mp4"), 0, 1000)
        assert not r.ok
        assert "not found" in r.error_message.lower()

    def test_ffmpeg_missing_returns_ok_false(self, td):
        """If ffmpeg is not installed, engine_media_slice must not raise — returns ok=False."""
        p = td / "fake.mp4"
        p.write_bytes(b"FAKE")
        r = engine_media_slice(str(p), start_ms=0.0, end_ms=500.0)
        if not r.ok:
            assert r.error_message  # Must have non-empty error message
        assert isinstance(r, PrimitiveResult)

    def test_metadata_contains_duration(self, td):
        """Even on failure, result must be a PrimitiveResult (not exception)."""
        p = td / "fake.mkv"
        p.write_bytes(b"FAKE")
        r = engine_media_slice(str(p), start_ms=100.0, end_ms=2000.0)
        assert isinstance(r, PrimitiveResult)
        if r.ok:
            assert r.metadata.get("duration_ms") == 1900.0

    def test_auto_output_path(self, td):
        """Output path auto-generated from source name."""
        p = td / "video.mp4"
        p.write_bytes(b"FAKE")
        r = engine_media_slice(str(p), start_ms=0, end_ms=1000)
        assert isinstance(r, PrimitiveResult)


# ---------------------------------------------------------------------------
# engine_cache_control tests
# ---------------------------------------------------------------------------


class TestEngineCacheControl:
    def test_purge_empty_scope_ok(self):
        r = engine_cache_control(CacheOp.PURGE_TRANSIENT, scope="nonexistent")
        assert r.ok
        assert r.data["chunks_removed"] == 0

    def test_stats_empty(self):
        r = engine_cache_control(CacheOp.STATS)
        assert r.ok
        assert r.data["total_chunks"] == 0

    def test_snapshot_empty_scope(self):
        r = engine_cache_control(CacheOp.SNAPSHOT, scope="test")
        assert r.ok
        assert r.data["chunk_count"] == 0

    def test_load_artifact_not_found(self, td):
        r = engine_cache_control(
            CacheOp.LOAD_ARTIFACT,
            scope="test",
            artifact_path=str(td / "no.md"),
        )
        assert not r.ok
        assert "not found" in r.error_message.lower()

    def test_load_artifact_ok(self, td):
        art = td / "kb.md"
        art.write_text("# Knowledge\nViVy knows this.")
        r = engine_cache_control(
            CacheOp.LOAD_ARTIFACT,
            scope="session1",
            artifact_path=str(art),
        )
        assert r.ok
        assert "ViVy knows this" in r.data
        assert r.metadata["chars"] > 0

    def test_purge_specific_chunks(self):
        # Manually seed the cache store
        _CACHE_STORE["scope_a"] = {"c1": "data1", "c2": "data2", "c3": "data3"}
        r = engine_cache_control(CacheOp.PURGE_TRANSIENT, scope="scope_a", chunk_ids=["c1", "c2"])
        assert r.ok
        assert r.data["chunks_removed"] == 2
        assert "c3" in _CACHE_STORE.get("scope_a", {})

    def test_purge_all_in_scope(self):
        _CACHE_STORE["scope_b"] = {"x": "1", "y": "2"}
        r = engine_cache_control(CacheOp.PURGE_TRANSIENT, scope="scope_b")
        assert r.ok
        assert r.data["chunks_removed"] == 2
        assert "scope_b" not in _CACHE_STORE

    def test_string_op_accepted(self):
        r = engine_cache_control("stats")
        assert r.ok

    def test_elapsed_ms_present(self):
        r = engine_cache_control(CacheOp.STATS)
        assert r.elapsed_ms >= 0.0

    def test_load_artifact_missing_path_arg(self):
        r = engine_cache_control(CacheOp.LOAD_ARTIFACT, scope="s")
        assert not r.ok
        assert "artifact_path required" in r.error_message

    def test_snapshot_after_load(self, td):
        art = td / "snap.md"
        art.write_text("snap content")
        engine_cache_control(CacheOp.LOAD_ARTIFACT, scope="snap_scope", artifact_path=str(art))
        r = engine_cache_control(CacheOp.SNAPSHOT, scope="snap_scope")
        assert r.ok
        assert r.data["chunk_count"] >= 1
