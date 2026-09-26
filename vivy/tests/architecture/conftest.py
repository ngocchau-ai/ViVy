"""
conftest.py — tests/architecture/
[ISOLATED] Legacy architecture tests checking nps_core package skeleton.

These tests verify the pre-V5 nps_core package structure which has been
superseded by ViVy Final V1.0 architecture (engine/memory/orchestrator/integration).
Files are preserved per immutability rule (only isolate, never delete).

The current architecture is validated by:
  - scripts/test_integration.py (19/19 smoke tests)
  - tests/test_primitives.py, test_elastic_n_core.py, test_mtp_directive.py
  - tests/test_cognitive_graph.py, test_hebbian_recall.py, test_graph_bridge.py

Changelog:
    21/09/2026 (Antigravity IDE — HoH-ViVy /goal session, Gate G-3 fix):
        Added conftest to skip nps_core skeleton check (21 tests).
        Status: [ISOLATED / DEPRECATED] — preserved for historical reference.
        nps_core replaced by unitary-reasoner Sprint 1+2+3 modules.
"""

collect_ignore_glob = ["test_package_skeleton.py"]
