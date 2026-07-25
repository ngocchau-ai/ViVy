"""Verify that all expected nps_core submodules are importable."""

import importlib

import pytest

_EXPECTED_MODULES = [
    "nps_core",
    "nps_core.codegraph",
    "nps_core.codegraph.indexer",
    "nps_core.evidence_assimilator",
    "nps_core.evidence_assimilator.errors",
    "nps_core.evidence_assimilator.impact",
    "nps_core.evidence_assimilator.packet",
    "nps_core.hypothesis_population",
    "nps_core.hypothesis_population.errors",
    "nps_core.hypothesis_population.lifecycle",
    "nps_core.hypothesis_population.lineage",
    "nps_core.hypothesis_population.serialization",
    "nps_core.hypothesis_population.thought_state",
    "nps_core.state_update",
    "nps_core.state_update.engine",
    "nps_core.state_update.errors",
    "nps_core.thought_ecology",
    "nps_core.thought_ecology.errors",
    "nps_core.thought_ecology.index",
    "nps_core.thought_ecology.relations",
]


@pytest.mark.parametrize("module_name", _EXPECTED_MODULES)
def test_module_importable(module_name: str) -> None:
    """Every expected module must be importable without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_package_version() -> None:
    """nps_core.__version__ must be a non-empty string."""
    import nps_core

    assert isinstance(nps_core.__version__, str)
    assert nps_core.__version__
