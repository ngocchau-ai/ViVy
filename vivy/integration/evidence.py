"""Validation boundary for promotion to durable knowledge."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

#: Verdict prefix :func:`build_evidence_packet` writes when a run has no
#: independent observation, or has a failed one.  A packet that records its own
#: rejection is **unverified output**, and Gate 7 says that cannot become
#: durable knowledge -- so it must never pass ``valid_for_promotion()``.
_REJECT_VERDICT = "REJECTED:"


@dataclass(frozen=True)
class EvidencePacket:
    claim: str
    evidence_ids: tuple[str, ...]
    source: str
    expected_evidence: str
    actual_observation: str
    acceptance: str
    confidence: float
    limits: str
    task_id: str
    session_id: str
    state_hash: str
    input_hash: str = ""
    output_hash: str = ""

    def valid_for_promotion(self) -> bool:
        # [REPLACED 29/09/2026] WP-8.  The old predicate only checked that
        # ``acceptance`` was *non-empty*, so a packet whose acceptance recorded
        # ``REJECTED: ...`` -- i.e. a run with zero or failed external
        # observations -- still looked promotable.  That is the Gate 7
        # violation "Unverified output cannot become durable knowledge",
        # reachable twice: through ``evaluate_multi_stream`` (VERIFIED_RESULT)
        # and through ``LessonStore.promote``.  The validation Gate 7 requires
        # the promotion to record has to be a validation that *passed*.
        #
        # Free-text acceptance stays legal (fixtures write "PASS" and
        # "ACCEPTED"); only an explicit rejection verdict blocks promotion.
        acceptance = self.acceptance.strip()
        return bool(self.claim.strip() and self.evidence_ids and self.source.strip()
                    and self.expected_evidence.strip() and self.actual_observation.strip()
                    and acceptance and not acceptance.startswith(_REJECT_VERDICT)
                    and self.limits.strip()
                    and self.task_id.strip() and self.session_id.strip()
                    and self.state_hash.strip() and 0.0 <= self.confidence <= 1.0)


def evidence_from_mapping(value: dict[str, Any]) -> EvidencePacket:
    return EvidencePacket(
        claim=str(value.get("claim", "")),
        evidence_ids=tuple(value.get("evidence_ids", ())),
        source=str(value.get("source", "")),
        expected_evidence=str(value.get("expected_evidence", "")),
        actual_observation=str(value.get("actual_observation", "")),
        acceptance=str(value.get("acceptance", "")),
        confidence=float(value.get("confidence", -1)),
        limits=str(value.get("limits", "")),
        task_id=str(value.get("task_id", "")),
        session_id=str(value.get("session_id", "")),
        state_hash=str(value.get("state_hash", "")),
        input_hash=str(value.get("input_hash", "")),
        output_hash=str(value.get("output_hash", "")),
    )


# ---------------------------------------------------------------------------
# WP-8 (F-B05) -- derive verification from observations, never from claims
# ---------------------------------------------------------------------------

#: Cap on how much of a single tool observation goes into the packet.  The
#: packet is a receipt, not a transcript; unbounded tool output would make it
#: unreadable and could smuggle a second claim past the gate.
_OBSERVATION_CAP = 400


def _tool_ok(tool: Any) -> bool:
    return bool(getattr(tool, "ok", False))


def derive_independent_verification(tool_results: Sequence[Any] | None) -> tuple[bool, str]:
    """Decide whether this run has *independent* evidence behind it.

    "Independent" is deliberately narrow: some process **outside the model**
    ran and returned an observation, and no such process failed.  The model
    never gets to assert this about itself -- this flag is computed from
    dispatch rows only.

    This does **not** mean the claim is semantically correct.  A tool
    returning ``ok`` is process success, not truth (Gate 7: *"Process success
    != semantic correctness != durable knowledge"*).  Semantic verification is
    the tribunal's job (WP-11).  This gate only refuses to promote a result
    that has nothing outside the model standing behind it.

    Returns
    -------
    (verified, reason) -- ``reason`` is a receipt string and is never blank.
    """
    rows = list(tool_results or ())
    if not rows:
        return False, "no external observation: zero tool results in this run"
    bad = [t for t in rows if not _tool_ok(t)]
    if bad:
        names = ", ".join(str(getattr(t, "tool_name", "?")) for t in bad[:3])
        return False, f"{len(bad)}/{len(rows)} external observation(s) failed ({names})"
    return True, f"{len(rows)}/{len(rows)} external observation(s) succeeded"


def _observation_text(tool_results: Sequence[Any]) -> str:
    parts: list[str] = []
    for tool in tool_results:
        if not _tool_ok(tool):
            continue
        name = str(getattr(tool, "tool_name", "?"))
        render = getattr(tool, "to_tool_response_content", None)
        body = render() if callable(render) else str(getattr(tool, "primitive_result", ""))
        body = " ".join(str(body).split())
        if len(body) > _OBSERVATION_CAP:
            body = body[:_OBSERVATION_CAP] + "…"
        parts.append(f"{name}={body}")
    return "; ".join(parts)


def build_evidence_packet(
    *,
    claim: str,
    expected_evidence: str,
    task_id: str,
    session_id: str,
    state_hash: str,
    tool_results: Sequence[Any] | None,
    confidence: float,
    limits: str,
    source: str = "tool_dispatch",
) -> tuple[EvidencePacket, bool]:
    """Assemble an :class:`EvidencePacket` from observations that really happened.

    ``evidence_ids`` and ``actual_observation`` are taken from ``tool_results``
    -- the external dispatch rows -- not from anything the model said about
    itself.  ``acceptance`` is derived by
    :func:`derive_independent_verification`, so a run with no external
    observation, or with any failed one, cannot present itself as accepted.

    Returns
    -------
    (packet, independently_verified)

    ``independently_verified`` is the second half of the Gate 7 input the
    caller must pass to ``evaluate_multi_stream``.  It is returned rather than
    read from the packet so the caller cannot forget to forward it (which is
    exactly the F-B05 hardcode this replaces).
    """
    rows = list(tool_results or ())
    independent, reason = derive_independent_verification(rows)
    ok_rows = [t for t in rows if _tool_ok(t)]
    evidence_ids = tuple(
        str(getattr(t, "tool_call_id", "") or getattr(t, "tool_name", "")) for t in ok_rows
    )
    packet = EvidencePacket(
        claim=claim,
        evidence_ids=evidence_ids,
        source=source,
        expected_evidence=expected_evidence,
        actual_observation=_observation_text(rows) or "(no external observation)",
        acceptance=(f"ACCEPTED: {reason}" if independent else f"REJECTED: {reason}"),
        confidence=confidence,
        limits=limits,
        task_id=task_id,
        session_id=session_id,
        state_hash=state_hash,
    )
    return packet, independent
