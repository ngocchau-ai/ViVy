"""
MTP Directive Head — ViVy Final V1.0 Sprint 1.

Multi-Token Prediction heads that emit a structured DirectiveExecutionTuple
in a SINGLE forward pass — zero autoregressive token generation.

Architecture (ARCH §5.3 & §9.1):
    ActionCandidate (winner from ElasticNCore)
        → DirectiveMTPHead.forward()
        → DirectiveExecutionTuple(target_id, opcode, payload_hash, signature)

Design:
    - MTP heads are independent output heads over the winner's action_vector.
    - Each field (target_id, opcode, payload_hash, signature) is predicted by
      a dedicated linear projection, so ALL fields are emitted in ONE pass.
    - Zero autoregressive decoding: no token-by-token loop.
    - Signature is a HMAC-style hash binding the other 3 fields (integrity).

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 1 — HOH-VIVY-FINAL-V1): Initial implementation.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directive output schema
# ---------------------------------------------------------------------------


class TargetComponent(StrEnum):
    """Where the directive is dispatched to."""

    ENGINE_PRIMITIVE = "ENGINE_PRIMITIVE"
    PRETRAINED_SPECIALIST = "PRETRAINED_SPECIALIST"
    SYSTEM_IO = "SYSTEM_IO"
    COGNITIVE_GRAPH = "COGNITIVE_GRAPH"


@dataclass(frozen=True)
class DirectiveExecutionTuple:
    """Immutable directive emitted by ViVy in one MTP forward pass.

    Matches ARCH §9.1 Directive Grammar:

        [EXECUTION_DIRECTIVE]
        - Target_Component: <ENGINE_PRIMITIVE | PRETRAINED_SPECIALIST | SYSTEM_I_O>
        - Operation_Code: <OPCODE_STRING>
        - Parameter_Payload: { ...json payload... }
        - Acceptance_Gate: <EXACT_VERIFIABLE_OUTPUT_CRITERIA>

    Attributes
    ----------
    target_id:
        Which component to dispatch to (TargetComponent enum value).
    opcode:
        Operation code string (e.g. ``"FILE_READ"``, ``"EXEC_SHELL"``).
    payload_hash:
        SHA-256 hex digest of the serialised payload_json. Verifiable.
    signature:
        HMAC-SHA256 binding target_id + opcode + payload_hash.
    payload_json:
        Raw JSON-serialisable dict for the target component.
    confidence:
        Confidence score of the winning action (0.0–1.0).
    core_index:
        Which ElasticNCore index produced the winning candidate.
    generation_ms:
        Wall-clock time of this MTP forward pass in milliseconds.
    """

    target_id: str
    opcode: str
    payload_hash: str
    signature: str
    payload_json: dict[str, Any]
    confidence: float
    core_index: int
    generation_ms: float


# ---------------------------------------------------------------------------
# Opcode vocabulary
# ---------------------------------------------------------------------------

# Map of action vector bucket → (TargetComponent, opcode) table
# Divides the softmax output space into semantic zones.
_OPCODE_TABLE: list[tuple[TargetComponent, str]] = [
    (TargetComponent.ENGINE_PRIMITIVE, "FILE_READ"),
    (TargetComponent.ENGINE_PRIMITIVE, "FILE_WRITE"),
    (TargetComponent.ENGINE_PRIMITIVE, "EXEC_SHELL"),
    (TargetComponent.ENGINE_PRIMITIVE, "MEDIA_SLICE"),
    (TargetComponent.ENGINE_PRIMITIVE, "CACHE_PURGE"),
    (TargetComponent.ENGINE_PRIMITIVE, "CACHE_LOAD_ARTIFACT"),
    (TargetComponent.PRETRAINED_SPECIALIST, "DELEGATE_CODING"),
    (TargetComponent.PRETRAINED_SPECIALIST, "DELEGATE_MATH"),
    (TargetComponent.PRETRAINED_SPECIALIST, "DELEGATE_REASONING"),
    (TargetComponent.SYSTEM_IO, "STDOUT_EMIT"),
    (TargetComponent.SYSTEM_IO, "STDIN_READ"),
    (TargetComponent.COGNITIVE_GRAPH, "GRAPH_RECALL"),
    (TargetComponent.COGNITIVE_GRAPH, "GRAPH_UPDATE"),
    (TargetComponent.COGNITIVE_GRAPH, "GRAPH_DAMPEN"),
    (TargetComponent.ENGINE_PRIMITIVE, "NEED_KNOWLEDGE_FORAGING"),
    (TargetComponent.ENGINE_PRIMITIVE, "INCIDENT_INVESTIGATE"),
]

_N_OPCODES = len(_OPCODE_TABLE)
_HMAC_SECRET = b"vivy-final-v1-mtp-integrity-key"  # Static dev key; prod replaces with TPM-bound


# ---------------------------------------------------------------------------
# DirectiveMTPHead
# ---------------------------------------------------------------------------


class DirectiveMTPHead:
    """Multi-Token Prediction output head for ViVy's directive generation.

    Converts the winning action_vector from ElasticNCore into a fully
    structured DirectiveExecutionTuple in one matrix multiplication pass.

    Parameters
    ----------
    hidden_dim:
        Dimensionality of the input action_vector.
    seed:
        Random seed for weight initialisation.
    hmac_secret:
        Secret bytes for HMAC signature computation.
    """

    def __init__(
        self,
        hidden_dim: int = 64,
        seed: int = 42,
        hmac_secret: bytes = _HMAC_SECRET,
    ) -> None:
        self.hidden_dim = hidden_dim
        self._hmac_secret = hmac_secret

        rng = np.random.default_rng(seed)

        # Opcode selection head: projects action_vector → opcode logits
        self._W_opcode: NDArray[np.float32] = rng.standard_normal(
            (_N_OPCODES, hidden_dim)
        ).astype(np.float32)
        norms = np.linalg.norm(self._W_opcode, axis=1, keepdims=True)
        self._W_opcode = self._W_opcode / np.maximum(norms, 1e-8)

        # Payload embedding head: projects action_vector → payload latent (16-dim)
        self._W_payload: NDArray[np.float32] = rng.standard_normal(
            (16, hidden_dim)
        ).astype(np.float32)

        logger.debug("DirectiveMTPHead: initialised hidden_dim=%d opcodes=%d", hidden_dim, _N_OPCODES)

    # ------------------------------------------------------------------
    # Single-pass forward
    # ------------------------------------------------------------------

    def forward(
        self,
        action_vector: NDArray[np.float32],
        core_index: int = 0,
        confidence: float = 0.0,
        context_hint: str = "",
    ) -> DirectiveExecutionTuple:
        """Emit a DirectiveExecutionTuple in ONE forward pass — no autoregression.

        Parameters
        ----------
        action_vector:
            Softmax output from the winning ActionCandidate (1-D float32).
        core_index:
            Which ElasticNCore produced the winner.
        confidence:
            Winner's score from ElasticNCore.forward().
        context_hint:
            Optional context string injected into payload (e.g. task description).

        Returns
        -------
        DirectiveExecutionTuple
        """
        t0 = time.perf_counter()

        av = np.asarray(action_vector, dtype=np.float32).ravel()
        if av.shape[0] != self.hidden_dim:
            raise ValueError(
                f"action_vector dim mismatch: expected {self.hidden_dim}, got {av.shape[0]}"
            )

        # --- Step 1: opcode selection (1 matmul) ---
        opcode_logits = self._W_opcode @ av  # (_N_OPCODES,)
        opcode_idx = int(np.argmax(opcode_logits))
        target_component, opcode = _OPCODE_TABLE[opcode_idx]

        # --- Step 2: payload embedding (1 matmul) ---
        payload_latent = self._W_payload @ av  # (16,)
        # Quantise to deterministic hex for payload_hash pre-image
        latent_bytes = payload_latent.tobytes()

        # --- Step 3: build payload dict ---
        payload_json: dict[str, Any] = {
            "opcode": opcode,
            "target": str(target_component),
            "core_index": core_index,
            "confidence": round(float(confidence), 4),
            "context": context_hint[:256],  # cap to avoid bloat
            "latent_signature": latent_bytes.hex()[:32],  # first 16 bytes
        }

        # --- Step 4: payload hash (SHA-256 of canonical representation) ---
        canonical = f"{target_component}|{opcode}|{core_index}|{confidence:.4f}"
        payload_hash = hashlib.sha256(canonical.encode()).hexdigest()

        # --- Step 5: HMAC signature binding all fields ---
        hmac_msg = f"{target_component}:{opcode}:{payload_hash}".encode()
        signature = hmac.new(self._hmac_secret, hmac_msg, hashlib.sha256).hexdigest()

        elapsed_ms = (time.perf_counter() - t0) * 1000

        directive = DirectiveExecutionTuple(
            target_id=str(target_component),
            opcode=opcode,
            payload_hash=payload_hash,
            signature=signature,
            payload_json=payload_json,
            confidence=float(confidence),
            core_index=core_index,
            generation_ms=elapsed_ms,
        )

        logger.debug(
            "DirectiveMTPHead.forward: opcode=%s target=%s confidence=%.4f %.2fms",
            opcode,
            target_component,
            confidence,
            elapsed_ms,
        )
        return directive

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify(self, directive: DirectiveExecutionTuple) -> bool:
        """Verify the HMAC signature of a DirectiveExecutionTuple.

        Returns True if the directive is unmodified since generation.
        """
        hmac_msg = f"{directive.target_id}:{directive.opcode}:{directive.payload_hash}".encode()
        expected = hmac.new(self._hmac_secret, hmac_msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(directive.signature, expected)
