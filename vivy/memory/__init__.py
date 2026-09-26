"""Unitary Reasoner — Memory module (associative memory + query utilities).

Sprint 2 (HOH-VIVY-FINAL-V1, 19/09/2026): Added CognitiveStateGraph, HebbianRecall.
"""

from .associative import AssociativeMemory, QuantumAssociativeMemory
from .cognitive_graph import (
    CognitiveStateGraph,
    EdgeType,
    GraphEdge,
    GraphNode,
    GraphStats,
    NodeType,
)
from .hebbian_recall import HebbianRecall, RecallResult
from .query import analogical_reasoning, cosine_similarity

__all__ = [
    # Original
    "AssociativeMemory",
    "QuantumAssociativeMemory",
    "cosine_similarity",
    "analogical_reasoning",
    # Sprint 2 — Cognitive State Graph
    "CognitiveStateGraph",
    "GraphNode",
    "GraphEdge",
    "GraphStats",
    "NodeType",
    "EdgeType",
    # Sprint 2 — Hebbian Recall
    "HebbianRecall",
    "RecallResult",
]
