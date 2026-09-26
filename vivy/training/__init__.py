"""
ViVy Training & Evaluation Suite — Sprint R3.

Includes:
- dataset_extractor: Ingests Verdict 2.0, LLaVA, and Cautreo Activity logs into SFT datasets.
- teacher_critic: Online / post-session evaluator updating Cautreo Score Graph.
"""

from training.dataset_extractor import DatasetExtractor, TrainingSample
from training.teacher_critic import CriticEvaluation, TeacherCritic

__all__ = ["DatasetExtractor", "TrainingSample", "TeacherCritic", "CriticEvaluation"]
