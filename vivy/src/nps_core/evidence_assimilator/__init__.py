"""Evidence assimilation package.

Public API re-exports the evidence error taxonomy, value models, and
assimilation plan types used by downstream consumers.
"""

from nps_core.evidence_assimilator.errors import (
    EvidenceError,
    ImpactValidationError,
    PacketValidationError,
    PlanValidationError,
)
from nps_core.evidence_assimilator.impact import (
    IMPACT_CLASSIFICATIONS,
    AssimilationPlan,
    EvidenceImpact,
)
from nps_core.evidence_assimilator.packet import EvidencePacket, Reproducibility

__all__ = [
    # errors
    "EvidenceError",
    "PacketValidationError",
    "ImpactValidationError",
    "PlanValidationError",
    # models
    "Reproducibility",
    "EvidencePacket",
    "IMPACT_CLASSIFICATIONS",
    "EvidenceImpact",
    "AssimilationPlan",
]
