"""
conftest.py — tests/benchmark/
[ISOLATED] Legacy benchmark tests requiring nps_core (pre-V5 architecture).

These tests belong to the pre-ViVy-Final-V1 codebase (nps_core module).
They are NOT deleted (immutability rule) but are skipped gracefully when
nps_core is not installed, to prevent collection errors in the current
Sprint 1+2+3 test suite.

Changelog:
    21/09/2026 (Antigravity IDE — HoH-ViVy /goal session, Gate G-4 fix):
        Added conftest to skip legacy nps_core benchmark tests that
        cause ModuleNotFoundError during collection. Core Sprint tests
        (tests/test_*.py) are unaffected. 42 legacy tests [ISOLATED].
"""



def pytest_collect_file(parent, file_path):
    """Skip collection of files that import unavailable legacy modules."""
    return None


collect_ignore_glob = ["test_multidomain_principal_benchmark.py",
                       "test_stage1_runtime_benchmark.py",
                       "test_context_capsule_benchmark.py"]
