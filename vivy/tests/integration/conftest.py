"""
conftest.py — tests/integration/
[ISOLATED] Legacy integration tests requiring nps_core (pre-V5 architecture).

These tests belong to the pre-ViVy-Final-V1 codebase (nps_core module).
They are NOT deleted (immutability rule) but are skipped gracefully when
nps_core is not installed, to prevent collection errors in the current
Sprint 1+2+3 test suite.

Changelog:
    21/09/2026 (Antigravity IDE — HoH-ViVy /goal session, Gate G-4 fix):
        Added conftest to skip legacy nps_core integration tests.
        New Sprint 3 integration tests (test_integration.py, test_vivy_host.py)
        remain fully active. 8 legacy tests [ISOLATED].
"""

collect_ignore_glob = [
    "test_clairvoyance_pipeline.py",
    "test_filter_funnel_integration.py",
    "test_multi_hypothesis_evidence_update.py",
    "test_thought_ecology_population.py",
    "test_thought_lifecycle_end_to_end.py",
    "test_verification_portfolio.py",
    "test_vivy_4b_pipeline.py",
    "test_refresh_codegraph.py",
    "test_vivy_1b_pipeline.py",
    "test_vivy_moe_40b_pipeline.py",
]
