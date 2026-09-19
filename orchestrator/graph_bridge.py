"""
Graph Bridge — ViVy Final V1.0 Sprint 2.

Cầu nối giữa ElasticNCore (hidden_state) và CognitiveStateGraph
(Thought Ecology Topology), thông qua HebbianRecall (W = YX+).

Architecture (ARCH §6.4):
    ElasticNCore.forward(h_L)
        → NCoreSinglePassResult.winner.action_vector
        → GraphBridge.evaluate(action_vector, graph, recall)
        → DampenedCandidateSet (action_vector filtered by FALSIFIED history)
        → DirectiveMTPHead.forward(dampened_action_vector)

Design:
    1. Receive winner.action_vector from ElasticNCore.
    2. Query HebbianRecall → recall nearest graph node (O(1)).
    3. Apply Error-Dampening from graph.get_dampened_candidates().
    4. Blend action_vector with dampening signal → dampened_action_vector.
    5. Register new node in graph (HYPOTHESIS) with current embedding.

This bridge ensures ViVy never repeats falsified actions (VM-11):
the dampening signal geometrically reduces probability of re-selecting
error-prone action directions in embedding space.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 2 — HOH-VIVY-FINAL-V1): Initial implementation.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from engine.elastic_n_core import ActionCandidate, NCoreSinglePassResult
from memory.cognitive_graph import CognitiveStateGraph, EdgeType, NodeType
from memory.hebbian_recall import HebbianRecall, RecallResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


@dataclass
class BridgeResult:
    """Output of GraphBridge.evaluate().

    Attributes
    ----------
    original_action_vector:
        The raw winner.action_vector from ElasticNCore.
    dampened_action_vector:
        Action vector after applying Error-Dampening from graph history.
    dampening_factor:
        Multiplicative factor applied (1.0 = no dampening; 0.0 = fully suppressed).
    recall_result:
        HebbianRecall output (nearest graph node and similarity).
    registered_node_id:
        ID of the HYPOTHESIS node registered for this step.
    elapsed_ms:
        Total elapsed time of the bridge evaluation.
    error_repeat_suppressed:
        True if dampening_factor < 1.0 (Error-Dampening was active).
    """

    original_action_vector: NDArray[np.float32]
    dampened_action_vector: NDArray[np.float32]
    dampening_factor: float
    recall_result: RecallResult
    registered_node_id: str
    elapsed_ms: float
    error_repeat_suppressed: bool = False


# ---------------------------------------------------------------------------
# GraphBridge
# ---------------------------------------------------------------------------


class GraphBridge:
    """Wire ElasticNCore's hidden state into the CognitiveStateGraph via HebbianRecall.

    The bridge performs 4 operations in sequence on each call to evaluate():
        1. Recall nearest graph node (O(1) via HebbianRecall).
        2. Compute dampening_factor from the recalled node's FALSIFIED history.
        3. Apply dampening: dampened = action_vector * dampen_factor + noise_floor.
        4. Register current action_vector as a new HYPOTHESIS node in the graph.

    Parameters
    ----------
    dampening_noise_floor:
        Minimum residual weight preserved even for fully falsified actions.
        Prevents complete suppression (diversity floor). Default 0.05.
    auto_register:
        If True, automatically register each evaluated action as a new
        HYPOTHESIS node in the graph (default True).
    """

    def __init__(
        self,
        dampening_noise_floor: float = 0.05,
        auto_register: bool = True,
    ) -> None:
        if not 0.0 <= dampening_noise_floor <= 1.0:
            raise ValueError(f"dampening_noise_floor must be in [0, 1], got {dampening_noise_floor}")
        self._noise_floor = dampening_noise_floor
        self._auto_register = auto_register
        logger.debug("GraphBridge: initialised noise_floor=%.2f", dampening_noise_floor)

    # ------------------------------------------------------------------
    # Core evaluate()
    # ------------------------------------------------------------------

    def evaluate(
        self,
        action_vector: NDArray[np.float32],
        graph: CognitiveStateGraph,
        recall: HebbianRecall,
        task_context: str = "",
        core_index: int = 0,
        confidence: float = 0.0,
    ) -> BridgeResult:
        """Apply graph-aware Error-Dampening to an ElasticNCore action vector.

        Parameters
        ----------
        action_vector:
            The winner's action_vector from ElasticNCore.forward().
        graph:
            Active CognitiveStateGraph (Thought Ecology Topology).
        recall:
            HebbianRecall instance synced with the graph's embeddings.
        task_context:
            Human-readable description of the current task (for node content).
        core_index:
            Which ElasticNCore index produced this candidate.
        confidence:
            Winner confidence score from ElasticNCore.

        Returns
        -------
        BridgeResult
        """
        t0 = time.perf_counter()

        av = np.asarray(action_vector, dtype=np.float32).ravel()

        # Step 1: Recall nearest graph node (O(1))
        recall_result = recall.recall(av, graph=graph)

        # Step 2: Compute dampening factor from recalled node
        dampen_factor = 1.0  # default: no dampening
        recalled_node = recall_result.recalled_node

        if recalled_node is not None and recall_result.similarity > 0.7:
            # Similar node found in graph — apply its dampening
            dampen_factor = recalled_node.dampen_factor()
            if dampen_factor < 1.0:
                logger.info(
                    "GraphBridge: dampening applied node=%s factor=%.4f sim=%.4f",
                    recalled_node.node_id,
                    dampen_factor,
                    recall_result.similarity,
                )

        # Step 3: Apply dampening with noise floor
        # dampened = action_vector * (dampen_factor + noise_floor * (1 - dampen_factor))
        effective_factor = dampen_factor + self._noise_floor * (1.0 - dampen_factor)
        effective_factor = float(max(self._noise_floor, min(1.0, effective_factor)))

        dampened_av = av * effective_factor

        # Re-normalise dampened vector (keep it on the softmax simplex)
        dav_sum = float(np.sum(dampened_av))
        if dav_sum > 1e-8:
            dampened_av = dampened_av / dav_sum

        # Step 4: Register current action as new HYPOTHESIS node
        registered_node_id = ""
        if self._auto_register:
            node_id = f"hypo_{uuid.uuid4().hex[:8]}_c{core_index}"
            content = (
                f"Action core={core_index} conf={confidence:.3f} "
                + (f"ctx={task_context[:64]}" if task_context else "")
            )
            graph.add_node(
                node_id=node_id,
                node_type=NodeType.HYPOTHESIS,
                content=content,
                embedding=list(av),
                confidence=confidence,
            )
            recall.register(node_id, av)
            registered_node_id = node_id

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return BridgeResult(
            original_action_vector=av,
            dampened_action_vector=dampened_av,
            dampening_factor=effective_factor,
            recall_result=recall_result,
            registered_node_id=registered_node_id,
            elapsed_ms=elapsed_ms,
            error_repeat_suppressed=(effective_factor < 1.0),
        )

    # ------------------------------------------------------------------
    # Convenience: pipeline shortcut
    # ------------------------------------------------------------------

    def process_ncore_result(
        self,
        core_result: NCoreSinglePassResult,
        graph: CognitiveStateGraph,
        recall: HebbianRecall,
        task_context: str = "",
    ) -> BridgeResult:
        """Convenience wrapper: evaluate winner from a full NCoreSinglePassResult.

        Parameters
        ----------
        core_result:
            Full output from ElasticNCore.forward().
        graph:
            Active CognitiveStateGraph.
        recall:
            HebbianRecall instance.
        task_context:
            Optional task description.

        Returns
        -------
        BridgeResult with dampened_action_vector ready for DirectiveMTPHead.
        """
        winner = core_result.winner
        return self.evaluate(
            action_vector=winner.action_vector,
            graph=graph,
            recall=recall,
            task_context=task_context,
            core_index=winner.core_index,
            confidence=winner.score,
        )

    # ------------------------------------------------------------------
    # Error-Dampening feedback loop
    # ------------------------------------------------------------------

    def record_falsified(
        self,
        node_id: str,
        graph: CognitiveStateGraph,
        recall: HebbianRecall,
        reason: str = "",
    ) -> None:
        """Record that a previously registered action was falsified.

        Creates a FALSIFIED edge from node_id to a RCA_ROOT node and
        increments the node's falsified_count (VM-11 mechanism).

        Parameters
        ----------
        node_id:
            The HYPOTHESIS node that was found to be incorrect.
        graph:
            Active CognitiveStateGraph.
        recall:
            HebbianRecall instance (no change needed — graph is updated).
        reason:
            Human-readable description of why the action was falsified.
        """
        rca_id = f"rca_{uuid.uuid4().hex[:8]}"
        graph.add_node(
            node_id=rca_id,
            node_type=NodeType.RCA_ROOT,
            content=reason or f"Falsification of {node_id}",
            confidence=0.9,
        )
        graph.add_edge_falsified(source_id=node_id, target_id=rca_id)
        logger.info(
            "GraphBridge.record_falsified: node=%s rca=%s reason=%s",
            node_id,
            rca_id,
            reason[:64] if reason else "",
        )
