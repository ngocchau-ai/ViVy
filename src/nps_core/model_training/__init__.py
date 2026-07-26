"""Model training pipeline for NPS Core.

Provides bridge (ThoughtState -> TrainingExample), funnel (quality filtering),
config (1B-parameter transformer), and trainer (PyTorch training loop).

The bridge and funnel modules are standard-library-only.
The trainer module optionally imports PyTorch.
"""

from nps_core.model_training.bridge import (
    TASK_TYPES,
    BridgeConfig,
    TrainingExample,
    bridge_ecology,
    bridge_evidence_packet,
    bridge_snapshot,
    bridge_thought,
    bridge_thought_critique,
    bridge_thought_reasoning,
    bridge_thought_synthesis,
    bridge_thought_verification,
    examples_to_jsonl,
)
from nps_core.model_training.config import (
    MODEL_1B,
    MODEL_MOE_40B,
    DataConfig,
    ModelConfig,
    PipelineConfig,
    TrainingConfig,
)
from nps_core.model_training.errors import (
    BridgeError,
    ConfigError,
    FunnelError,
    ModelTrainingError,
    TrainerError,
)
from nps_core.model_training.funnel import (
    FunnelConfig,
    FunnelResult,
    QualityScore,
    deduplicate,
    funnel,
    rank_by_quality,
    score_example,
)
from nps_core.model_training.trainer import (
    TrainMetrics,
    TrainingState,
    create_optimizer,
    create_scheduler,
    get_learning_rate,
    load_checkpoint,
    save_checkpoint,
    train_step,
)

from nps_core.model_training.moe import (
    MoEConfig,
    MoERouter,
)
from nps_core.model_training.student import (
    LatencyEvaluator,
    StudentProposalEngine,
    StudentTrainingConfig,
)

__all__ = [
    # errors
    "ModelTrainingError",
    "BridgeError",
    "FunnelError",
    "ConfigError",
    "TrainerError",
    # moe
    "MoEConfig",
    "MoERouter",
    # student
    "StudentTrainingConfig",
    "StudentProposalEngine",
    "LatencyEvaluator",
    # config
    "ModelConfig",
    "TrainingConfig",
    "DataConfig",
    "PipelineConfig",
    "MODEL_1B",
    "MODEL_MOE_40B",
    # bridge
    "TASK_TYPES",
    "BridgeConfig",
    "TrainingExample",
    "bridge_thought",
    "bridge_thought_reasoning",
    "bridge_thought_verification",
    "bridge_thought_critique",
    "bridge_thought_synthesis",
    "bridge_snapshot",
    "bridge_ecology",
    "bridge_evidence_packet",
    "examples_to_jsonl",
    # funnel
    "FunnelConfig",
    "QualityScore",
    "FunnelResult",
    "score_example",
    "funnel",
    "deduplicate",
    "rank_by_quality",
    # trainer
    "TrainingState",
    "TrainMetrics",
    "create_optimizer",
    "create_scheduler",
    "get_learning_rate",
    "train_step",
    "save_checkpoint",
    "load_checkpoint",
]
