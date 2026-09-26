"""
Tests for VivyHost — Cautreo C11 Runtime Bridge.

Sprint: VIVY-HOST-001 (DD-11)
Coverage target: ≥ 20 tests, all scenarios including graceful degradation.

Changelog:
    20/09/2026 (Antigravity IDE — Sprint VIVY-HOST-001):
        Initial test suite — 25 tests covering all public methods.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integration.vivy_host import (
    DREAM_TRIGGER_ERROR_RATE,
    CautreoStatus,
    RoomStatus,
    VivyHost,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def host_offline() -> VivyHost:
    """VivyHost pointing to a non-existent binary → always offline."""
    return VivyHost(cautreo_exe=Path(r"C:\does_not_exist\cautreo.exe"))


@pytest.fixture
def host_mocked() -> tuple[VivyHost, MagicMock]:
    """VivyHost with _run_cli patched for full control."""
    h = VivyHost(cautreo_exe=Path(r"D:\cautreov2\91sCT\build\cautreo.exe"))
    h._available = True   # Force available without file-system check
    return h


# ---------------------------------------------------------------------------
# 1. Availability & init
# ---------------------------------------------------------------------------


class TestAvailability:
    def test_offline_when_binary_missing(self, host_offline: VivyHost) -> None:
        assert host_offline.available is False

    def test_repr_includes_status(self, host_offline: VivyHost) -> None:
        r = repr(host_offline)
        assert "OFFLINE" in r

    def test_env_var_overrides_path(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake_exe = Path(tmp) / "cautreo.exe"
            fake_exe.touch()
            with patch.dict("os.environ", {"CAUTREO_EXE": str(fake_exe)}):
                h = VivyHost()
                assert h._exe == fake_exe

    def test_reset_availability_cache(self, host_offline: VivyHost) -> None:
        assert host_offline.available is False
        host_offline.reset_availability_cache()
        assert host_offline._available is None


# ---------------------------------------------------------------------------
# 2. RoomStatus parsing
# ---------------------------------------------------------------------------


class TestRoomStatusParsing:
    def test_parse_json_healthy(self) -> None:
        raw = json.dumps({
            "status": "healthy",
            "ssd_tier1": True,
            "ssd_tier2": True,
            "brain_mounted": True,
            "knowledge_entries": 42,
        })
        s = RoomStatus.from_raw(raw)
        assert s.status == CautreoStatus.HEALTHY
        assert s.ssd_tier1_ok is True
        assert s.knowledge_entries == 42

    def test_parse_json_degraded(self) -> None:
        raw = json.dumps({"status": "degraded"})
        s = RoomStatus.from_raw(raw)
        assert s.status == CautreoStatus.DEGRADED

    def test_parse_keyword_ok(self) -> None:
        s = RoomStatus.from_raw("Status: OK — all systems nominal")
        assert s.status == CautreoStatus.HEALTHY

    def test_parse_keyword_error(self) -> None:
        s = RoomStatus.from_raw("SSD tier1 FAIL — check hardware")
        assert s.status == CautreoStatus.DEGRADED

    def test_offline_factory(self) -> None:
        s = RoomStatus.offline()
        assert s.status == CautreoStatus.OFFLINE
        assert s.raw == "binary_unavailable"


# ---------------------------------------------------------------------------
# 3. Status / version — degraded gracefully
# ---------------------------------------------------------------------------


class TestStatusGraceful:
    def test_status_offline_returns_offline(self, host_offline: VivyHost) -> None:
        s = host_offline.status()
        assert s.status == CautreoStatus.OFFLINE

    def test_version_offline(self, host_offline: VivyHost) -> None:
        assert host_offline.version() == "unavailable"

    def test_status_healthy_via_mock(self, host_mocked: VivyHost) -> None:
        payload = json.dumps({"status": "healthy", "ssd_tier1": True})
        with patch.object(host_mocked, "_run_cli", return_value=(payload, "", 0)):
            s = host_mocked.status()
        assert s.status == CautreoStatus.HEALTHY

    def test_status_nonzero_rc_is_degraded(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("", "error", 1)):
            s = host_mocked.status()
        assert s.status == CautreoStatus.DEGRADED


# ---------------------------------------------------------------------------
# 4. exec_directive
# ---------------------------------------------------------------------------


class TestExecDirective:
    def test_offline_returns_failure(self, host_offline: VivyHost) -> None:
        r = host_offline.exec_directive("DIRECTIVE: EXEC_CMD target=whoami")
        assert r.success is False
        assert "cautreo_unavailable" in r.stderr

    def test_success_via_mock(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("LENOVO", "", 0)):
            r = host_mocked.exec_directive("DIRECTIVE: EXEC_CMD target=whoami")
        assert r.success is True
        assert "LENOVO" in r.stdout

    def test_failure_via_mock(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("", "permission denied", 1)):
            r = host_mocked.exec_directive("DIRECTIVE: EXEC_CMD target=forbidden")
        assert r.success is False
        assert r.returncode == 1

    def test_elapsed_ms_tracked(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("ok", "", 0)):
            r = host_mocked.exec_directive("DIRECTIVE: EXEC_CMD target=echo")
        assert r.elapsed_ms >= 0.0


# ---------------------------------------------------------------------------
# 5. dream / sync
# ---------------------------------------------------------------------------


class TestDreamSync:
    def test_dream_offline_returns_false(self, host_offline: VivyHost) -> None:
        assert host_offline.dream() is False

    def test_dream_success(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("Dream complete", "", 0)):
            assert host_mocked.dream() is True

    def test_dream_fail(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("", "SVD error", 1)):
            assert host_mocked.dream() is False

    def test_sync_offline_returns_false(self, host_offline: VivyHost) -> None:
        assert host_offline.sync_2brain() is False

    def test_sync_success(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("Sync OK", "", 0)):
            assert host_mocked.sync_2brain() is True


# ---------------------------------------------------------------------------
# 6. query_knowledge / store_artifact
# ---------------------------------------------------------------------------


class TestKnowledgeStore:
    def test_query_offline_empty(self, host_offline: VivyHost) -> None:
        assert host_offline.query_knowledge("robot arm torque") == []

    def test_query_returns_entries_json(self, host_mocked: VivyHost) -> None:
        entry = json.dumps({"key": "k1", "content": "torque = 12Nm", "verified": True})
        with patch.object(host_mocked, "_run_cli", return_value=(entry, "", 0)):
            results = host_mocked.query_knowledge("robot arm torque")
        assert len(results) == 1
        assert results[0].key == "k1"
        assert results[0].verified is True

    def test_query_empty_response_is_empty_list(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("", "", 0)):
            results = host_mocked.query_knowledge("unknown topic")
        assert results == []

    def test_store_offline_returns_false(self, host_offline: VivyHost) -> None:
        assert host_offline.store_artifact("key", "content") is False

    def test_store_verified(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("stored", "", 0)) as mock_cli:
            result = host_mocked.store_artifact("k1", "my content", verified=True)
        assert result is True
        call_args = mock_cli.call_args[0][0]
        assert "--verified" in call_args

    def test_store_staging(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("staged", "", 0)) as mock_cli:
            result = host_mocked.store_artifact("k2", "raw content", verified=False)
        assert result is True
        call_args = mock_cli.call_args[0][0]
        assert "--staging" in call_args


# ---------------------------------------------------------------------------
# 7. Composite helpers & stats
# ---------------------------------------------------------------------------


class TestCompositeHelpers:
    def test_maybe_dream_below_threshold(self, host_mocked: VivyHost) -> None:
        """Below threshold → no dream triggered."""
        with patch.object(host_mocked, "dream") as mock_dream:
            host_mocked.maybe_dream(error_rate=0.05)
            mock_dream.assert_not_called()

    def test_maybe_dream_at_threshold(self, host_mocked: VivyHost) -> None:
        """At or above threshold → dream triggered."""
        with patch.object(host_mocked, "dream", return_value=True) as mock_dream:
            result = host_mocked.maybe_dream(error_rate=DREAM_TRIGGER_ERROR_RATE)
            mock_dream.assert_called_once()
            assert result is True

    def test_error_rate_zero_on_init(self, host_offline: VivyHost) -> None:
        assert host_offline.error_rate == 0.0

    def test_error_rate_tracks_failures(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("", "err", 1)):
            host_mocked.store_artifact("x", "y")  # 1 failure
        with patch.object(host_mocked, "_run_cli", return_value=("ok", "", 0)):
            host_mocked.store_artifact("a", "b")  # 1 success
        assert host_mocked.error_rate == pytest.approx(0.5)

    def test_stats_dict_structure(self, host_offline: VivyHost) -> None:
        s = host_offline.stats()
        assert "available" in s
        assert "call_count" in s
        assert "error_rate" in s

    def test_post_inference_store_high_confidence(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("stored", "", 0)) as mock_cli:
            host_mocked.post_inference_store("solve ODE", "# Result\n...", confidence=0.95)
        # Should store as verified
        call_args = mock_cli.call_args[0][0]
        assert "--verified" in call_args

    def test_post_inference_store_low_confidence(self, host_mocked: VivyHost) -> None:
        with patch.object(host_mocked, "_run_cli", return_value=("staged", "", 0)) as mock_cli:
            host_mocked.post_inference_store("solve ODE", "# Result\n...", confidence=0.60)
        call_args = mock_cli.call_args[0][0]
        assert "--staging" in call_args


# ---------------------------------------------------------------------------
# 8. _run_cli resilience
# ---------------------------------------------------------------------------


class TestRunCliResilience:
    def test_timeout_returns_gracefully(self, host_mocked: VivyHost) -> None:
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cautreo", 5)):
            out, err, rc = host_mocked._run_cli(["status"])
        assert rc == 1
        assert "timeout" in err

    def test_file_not_found_marks_unavailable(self, host_mocked: VivyHost) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            out, err, rc = host_mocked._run_cli(["status"])
        assert rc == 1
        assert host_mocked._available is False

    def test_os_error_returns_gracefully(self, host_mocked: VivyHost) -> None:
        with patch("subprocess.run", side_effect=OSError("permission denied")):
            out, err, rc = host_mocked._run_cli(["status"])
        assert rc == 1
        assert "permission denied" in err
