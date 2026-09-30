"""Engine — V5.0 Engine Primitives (file_io, exec, media_slice, cache_control, self_healer).

Sprint 1 (HOH-VIVY-FINAL-V1, 19/09/2026): Added primitives, elastic_n_core, mtp_directive.
"""

from .cache_control import (
    CacheChunk,
    CacheSnapshot,
    ContextCacheController,
    PurgeResult,
)
from .elastic_n_core import (
    ActionCandidate,
    ElasticNCore,
    HardwareBudget,
    NCoreSinglePassResult,
    detect_hardware_budget,
)
from .mtp_directive import (
    DirectiveExecutionTuple,
    DirectiveMTPHead,
    TargetComponent,
)
from .primitives import (
    CacheOp,
    FileAction,
    PrimitiveResult,
    engine_cache_control,
    engine_exec,
    engine_file_io,
    engine_media_slice,
)
from .self_healer import (
    HealingResult,
    Incident,
    RCAHypothesis,
    SelfHealingLoop,
)

__all__ = [
    # Sprint 2C (cache controller — original)
    "ContextCacheController",
    "CacheChunk",
    "CacheSnapshot",
    "PurgeResult",
    # Sprint 3B (self-healer — original)
    "SelfHealingLoop",
    "Incident",
    "HealingResult",
    "RCAHypothesis",
    # Sprint 1 — Engine Primitives (HOH-VIVY-FINAL-V1)
    "PrimitiveResult",
    "FileAction",
    "CacheOp",
    "engine_file_io",
    "engine_exec",
    "engine_media_slice",
    "engine_cache_control",
    # Sprint 1 — Elastic N-Core
    "ElasticNCore",
    "HardwareBudget",
    "ActionCandidate",
    "NCoreSinglePassResult",
    "detect_hardware_budget",
    # Sprint 1 — MTP Directive Head
    "DirectiveMTPHead",
    "DirectiveExecutionTuple",
    "TargetComponent",
]
