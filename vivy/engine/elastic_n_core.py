"""
Elastic N-Core Single-Pass Evaluator — ViVy Final V1.0 Sprint 1.

Triển khai Hardware-Adaptive Elastic N-Core theo ARCHITECTURE_V5.md Mục 5.2:
- Baseline: N=2 (1 luồng phân tích hành động + 1 luồng phản biện rủi ro).
- Scale: N ∈ [2, 16] theo VRAM/compute headroom thực tế.
- OOM Guard: nếu budget thấp, fallback về N=2 thay vì crash.
- Single-Pass: tất cả N luồng được evaluated trên cùng hidden_state trong 1 pass.

Design:
    hidden_state h_L (dim-vector) → [N parallel action heads] → N candidate actions
    Each core i evaluates: score_i = softmax(W_i @ h_L) where W_i is head weight.
    Winner selected by argmax(score).

IMPORTANT BOUNDARY & AUDIT NOTICE (2026-09-21, Codex Audit Alignment):
    ElasticNCore in this phase functions as an architectural Tensor Shape & GEMM Latency
    Benchmark (<2ms on CPU). The linear projections W_i evaluate candidate projections
    across N heads. Scores from random Gaussian projections MUST NOT be treated as
    epistemic proof, nor used to declare VERIFIED_RESULT or promote durable knowledge
    without independent grounded evidence (tests or deterministic invariants).

No GPU/CUDA required for this Python reference implementation.
Hardware detection is abstracted via detect_hardware_budget() so the real
engine can swap in an nvml-backed implementation without changing the API.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 1 — HOH-VIVY-FINAL-V1): Initial implementation.
    21/09/2026 (Antigravity IDE, Sync S3): Added CognitivePrimitive enum.
    21/09/2026 (Antigravity IDE, CEO Audit): Demystified random head weights as tensor
        benchmark primitive; banned ungrounded VERIFIED_RESULT promotion.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cognitive Primitive Decisions (Sync from vivyChatGPT, 2026-09-21)
# ---------------------------------------------------------------------------


class CognitivePrimitive(Enum):
    """Typed decision enum for ViVy cognitive state.

    Synced from vivyChatGPT CAUTREO cognitive primitives.
    Epistemic distinction:
      - FALSIFIED (graph edge) = wrong answer, action produced bad result
      - INCIDENT = operational failure, system/resource problem, NOT the model's fault

    These are emitted by NCoreSinglePassResult or recorded by record_incident().
    They feed into GraphBridge.record_falsified() (FALSIFIED) or
    GraphBridge.record_incident() (INCIDENT) separately.
    """

    EXECUTE = auto()    # EXECUTE_DIRECTLY: confidence HIGH, no unknowns
    FORAGE = auto()     # NEED_KNOWLEDGE_FORAGING: unknown entity detected
    DELEGATE = auto()   # Delegate to specialist / backup backend
    HALT = auto()       # Disagreement-gated stop: streams disagree, need more evidence
    INCIDENT = auto()   # Operational failure: crash, missing resource, OOM — NOT semantic


@dataclass
class IncidentRecord:
    """Record of an operational incident during N-Core evaluation.

    INCIDENT is distinct from FALSIFIED:
      - FALSIFIED: action was semantically wrong (model made bad decision)
      - INCIDENT: operational/system failure (missing file, OOM, timeout)

    Use GraphBridge.record_incident() to log this, NOT record_falsified().
    """

    incident_id: str
    core_index: int
    primitive_name: str        # Which engine primitive failed
    error_message: str
    recoverable: bool = True   # False = requires human intervention
    timestamp: float = field(default_factory=time.time)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N_MIN = 2       # Baseline guaranteed by Jev validation
_N_MAX = 16      # Hardware upper bound (ARCH §5.2)
_HIDDEN_DIM = 64 # Default hidden state dimension (h_L)

# VRAM thresholds for N scaling (approximate, Python reference impl)
_VRAM_PER_CORE_MB = 512  # Conservative estimate per active core


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class HardwareBudget:
    """Snapshot of available compute budget."""

    n_cores_available: int    # Number of logical CPU cores
    vram_estimate_mb: int     # Estimated available VRAM / RAM budget
    n_active: int             # Computed N (clamped to [n_min, n_max])
    is_compute_bound: bool    # True when N > 1 (shifts GPU from mem-bound)
    budget_source: str        # How budget was detected


@dataclass
class ActionCandidate:
    """A single action hypothesis evaluated by one core."""

    core_index: int
    action_vector: NDArray[np.float32]  # Softmax output
    score: float                         # Max probability (confidence)
    hypothesis: str = ""                 # Optional label
    hypothesis_id: str = ""
    state_hash: str = ""
    source: str = ""
    expected_evidence: str = ""
    evaluation_status: str = "unevaluated"


@dataclass
class NCoreSinglePassResult:
    """Result of one ElasticNCore forward pass."""

    n_active: int
    candidates: list[ActionCandidate]
    winner: ActionCandidate
    hidden_state: NDArray[np.float32]
    elapsed_ms: float
    is_compute_bound: bool


# ---------------------------------------------------------------------------
# Hardware budget detection
# ---------------------------------------------------------------------------


def detect_hardware_budget(
    n_min: int = _N_MIN,
    n_max: int = _N_MAX,
    vram_override_mb: int | None = None,
) -> HardwareBudget:
    """Estimate available hardware and compute the optimal N.

    This Python reference implementation uses logical CPU count as a proxy
    for parallelism capacity. A production GPU implementation would use
    nvidia-ml-py (nvml) or rocm-smi to read actual VRAM headroom.

    Parameters
    ----------
    n_min:
        Minimum N (always returns at least this value — OOM guard).
    n_max:
        Maximum N regardless of hardware.
    vram_override_mb:
        Manually override VRAM estimate (for testing / mock scenarios).

    Returns
    -------
    HardwareBudget
        n_active is clamped to [n_min, n_max].
    """
    try:
        import os
        cpu_count = os.cpu_count() or 2
    except Exception:  # noqa: BLE001
        cpu_count = 2

    # Estimate VRAM via override or heuristic (Python mock: use RAM proxy)
    if vram_override_mb is not None:
        vram_mb = vram_override_mb
        source = "override"
    else:
        # Heuristic: assume 4 GB effective budget on typical GPU
        # Real impl: nvml.nvmlDeviceGetMemoryInfo(handle).free >> 20
        vram_mb = 4096
        source = "heuristic_4gb"

    # OOM guard: if budget is very low, stay at n_min
    if vram_mb < _VRAM_PER_CORE_MB * n_min:
        n_active = n_min
        source = f"{source}_oom_guard"
        logger.warning(
            "detect_hardware_budget: low VRAM (%d MB) — clamping to N=%d (OOM guard)",
            vram_mb,
            n_active,
        )
    else:
        # Scale N proportionally to VRAM headroom
        n_from_vram = int(vram_mb // _VRAM_PER_CORE_MB)
        # Also constrain by CPU parallelism
        n_from_cpu = min(cpu_count, n_max)
        n_active = min(n_from_vram, n_from_cpu, n_max)
        n_active = max(n_active, n_min)

    return HardwareBudget(
        n_cores_available=cpu_count,
        vram_estimate_mb=vram_mb,
        n_active=n_active,
        is_compute_bound=(n_active > 1),
        budget_source=source,
    )


# ---------------------------------------------------------------------------
# ElasticNCore
# ---------------------------------------------------------------------------


class ElasticNCore:
    """Hardware-Adaptive Elastic N-Core Single-Pass Evaluator.

    Evaluates N action hypotheses in parallel over the same hidden_state
    vector h_L in a single matrix multiplication pass, shifting GPU from
    memory-bandwidth bound to compute-bound (Jev validation, ARCH §5.2).

    Parameters
    ----------
    n_min:
        Minimum number of active cores (baseline guarantee).
    n_max:
        Maximum number of active cores (hardware ceiling).
    hidden_dim:
        Dimension of the shared hidden state h_L.
    seed:
        Random seed for reproducible head weight initialisation.
    """

    # Audit Boundary Notice (Truth over Hype - Codex Review & CEO Decision):
    # ElasticNCore is a single-pass tensor benchmark primitive verifying parallel GEMM latency (<2ms on CPU).
    # Its softmax confidence over random weights/hidden states does NOT represent cognitive truth or task hypotheses.
    # It must NEVER be used to promote durable lessons or emit VERIFIED_RESULT without actual execution evidence.
    _AUDIT_NOTICE: str = (
        "ElasticNCore is a tensor shape & latency benchmark primitive. "
        "Score winner does not reflect cognitive hypothesis validity. "
        "Strictly prohibited from generating VERIFIED_RESULT."
    )

    def __init__(
        self,
        n_min: int = _N_MIN,
        n_max: int = _N_MAX,
        hidden_dim: int = _HIDDEN_DIM,
        seed: int = 42,
    ) -> None:
        if n_min < 2:
            raise ValueError(f"n_min must be ≥ 2 (Jev baseline), got {n_min}")
        if n_max > 64:
            raise ValueError(f"n_max must be ≤ 64, got {n_max}")
        if n_min > n_max:
            raise ValueError(f"n_min ({n_min}) must be ≤ n_max ({n_max})")

        self.n_min = n_min
        self.n_max = n_max
        self.hidden_dim = hidden_dim
        self._seed = seed

        # Initialise N_MAX head weight matrices W_i ∈ R^{hidden_dim × hidden_dim}
        # Each core i scores: logits_i = W_i @ h_L
        rng = np.random.default_rng(seed)
        self._head_weights: NDArray[np.float32] = rng.standard_normal(
            (n_max, hidden_dim, hidden_dim)
        ).astype(np.float32)
        # Normalise each head to prevent score explosion
        norms = np.linalg.norm(self._head_weights, axis=(1, 2), keepdims=True)
        self._head_weights = self._head_weights / np.maximum(norms, 1e-8)

        logger.debug(
            "ElasticNCore: initialised n_min=%d n_max=%d hidden_dim=%d",
            n_min,
            n_max,
            hidden_dim,
        )

    # ------------------------------------------------------------------
    # Hardware budget
    # ------------------------------------------------------------------

    def detect_hardware_budget(
        self, vram_override_mb: int | None = None
    ) -> HardwareBudget:
        """Detect available hardware and compute optimal N for this instance.

        Returns a HardwareBudget clamped to this instance's [n_min, n_max].
        """
        return detect_hardware_budget(
            n_min=self.n_min,
            n_max=self.n_max,
            vram_override_mb=vram_override_mb,
        )

    # ------------------------------------------------------------------
    # Single-Pass Evaluation
    # ------------------------------------------------------------------

    def forward(
        self,
        hidden_state: NDArray[np.float32] | None = None,
        n_override: int | None = None,
        vram_override_mb: int | None = None,
        hypotheses: list[str] | None = None,
        state_hash: str = "",
        hypothesis_ids: list[str] | None = None,
        source: str = "n_core",
        expected_evidence: str = "",
    ) -> NCoreSinglePassResult:
        """Evaluate N action candidates in a SINGLE matrix multiplication pass.

        Parameters
        ----------
        hidden_state:
            Shared hidden state h_L (1-D float32 vector of self.hidden_dim).
            Auto-generated as random unit vector if None (for testing).
        n_override:
            Force N to a specific value [n_min, n_max]. Bypasses auto-detect.
        vram_override_mb:
            Override VRAM estimate for budget detection.
        hypotheses:
            Optional hypothesis labels for each core (for diagnostics).

        Returns
        -------
        NCoreSinglePassResult
        """
        t0 = time.perf_counter()

        # --- hidden state ---
        if hidden_state is None:
            if state_hash:
                raise ValueError("grounded product N-Core calls require hidden_state")
            rng = np.random.default_rng()
            h = rng.standard_normal(self.hidden_dim).astype(np.float32)
            h = h / (np.linalg.norm(h) + 1e-8)
        else:
            h = np.asarray(hidden_state, dtype=np.float32).ravel()
            if h.shape[0] != self.hidden_dim:
                raise ValueError(
                    f"hidden_state dim mismatch: expected {self.hidden_dim}, got {h.shape[0]}"
                )
            norm = np.linalg.norm(h)
            if norm > 1e-8:
                h = h / norm

        # --- budget detection ---
        if n_override is not None:
            n_active = max(self.n_min, min(n_override, self.n_max))
            budget = HardwareBudget(
                n_cores_available=n_active,
                vram_estimate_mb=vram_override_mb or 4096,
                n_active=n_active,
                is_compute_bound=(n_active > 1),
                budget_source="override",
            )
        else:
            budget = self.detect_hardware_budget(vram_override_mb=vram_override_mb)
            n_active = budget.n_active

        # --- SINGLE-PASS GEMM: all N cores evaluated simultaneously ---
        # W_active: (N, D, D) batch of head weights
        W_active = self._head_weights[:n_active]  # (N, D, D)

        # Batched matmul: logits[i] = W_active[i] @ h  →  (N, D)
        logits = np.einsum("nij,j->ni", W_active, h, optimize=True)  # (N, D)

        # Softmax per core
        logits_shifted = logits - logits.max(axis=1, keepdims=True)  # numerical stability
        exp_logits = np.exp(logits_shifted)
        action_vectors = exp_logits / (exp_logits.sum(axis=1, keepdims=True) + 1e-8)  # (N, D)

        # Score: max softmax probability (confidence of best action)
        scores = action_vectors.max(axis=1)  # (N,)

        # --- Build candidates ---
        candidates: list[ActionCandidate] = []
        for i in range(n_active):
            label = (hypotheses[i] if hypotheses and i < len(hypotheses) else f"core_{i}")
            candidates.append(
                ActionCandidate(
                    core_index=i,
                    action_vector=action_vectors[i],
                    score=float(scores[i]),
                    hypothesis=label,
                    hypothesis_id=(hypothesis_ids[i] if hypothesis_ids and i < len(hypothesis_ids) else ""),
                    state_hash=state_hash,
                    source=source,
                    expected_evidence=expected_evidence,
                )
            )

        # Winner: highest-confidence action
        winner_idx = int(np.argmax(scores))
        winner = candidates[winner_idx]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "ElasticNCore.forward: n_active=%d winner=core_%d score=%.4f %.2fms",
            n_active,
            winner_idx,
            winner.score,
            elapsed_ms,
        )

        return NCoreSinglePassResult(
            n_active=n_active,
            candidates=candidates,
            winner=winner,
            hidden_state=h,
            elapsed_ms=elapsed_ms,
            is_compute_bound=budget.is_compute_bound,
        )
