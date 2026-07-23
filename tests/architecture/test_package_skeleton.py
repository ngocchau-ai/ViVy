import importlib
import pytest
import nps_core

MODULES = (
    "problem_compiler",
    "hypothesis_population",
    "thought_ecology",
    "adaptive_n",
    "experiment_designer",
    "contract_generator",
    "executor_router",
    "evidence_assimilator",
    "verification_tribunal",
    "state_update",
    "memory",
    "codegraph",
    "interfaces",
)

@pytest.mark.parametrize("module_name", MODULES)
def test_module_import(module_name):
    module = importlib.import_module(f"nps_core.{module_name}")
    assert module is not None

def test_nps_core_all():
    assert nps_core.__all__ == ["__version__"]
    assert isinstance(nps_core.__version__, str)
    assert len(nps_core.__version__) > 0
