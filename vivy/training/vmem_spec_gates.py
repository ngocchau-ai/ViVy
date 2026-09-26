"""C13.1 — VMEM spec-threshold quoting and VM-01…VM-11 measurement-shape gates.

Spec thresholds must be quoted verbatim with a version BEFORE any measurement
is accepted. A silent or unversioned spec is a GAP, never a PASS.

Changelog: 2026-09-24 (Claude Code — P5 C13)
    Initial. VM-01…VM-11 measurement contracts encode both the required
    fields from ANTIGRAVITY_IMPLEMENTATION_AND_REVIEW_ACCEPTANCE_PLAN §C13
    and the "Sai lầm cần tránh" shortcuts that must force FAIL.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

VM_IDS: tuple[str, ...] = tuple(f"VM-{i:02d}" for i in range(1, 12))

# Status labels that bind simulation vs live observation.
LIVE_LABEL = "LIVE_MODEL_OBSERVATION"
SIM_LABEL = "SIMULATED_PROTOCOL"
GAP_STATUS = "GAP"
QUOTED_STATUS = "QUOTED"

# Required measurement fields per VM (acceptance plan §C13 "Phép đo bắt buộc").
# A field listed here is MISSING when absent, empty, or (for *_labeled / flags)
# not literally True.
_REQUIRED: dict[str, tuple[str, ...]] = {
    "VM-01": (
        "ood_labeled",
        "in_domain_labeled",
        "sensitivity",
        "false_escalation_rate",
        "denominator",
    ),
    "VM-02": ("confusion_matrix", "inputs_include", "denominator"),
    "VM-03": ("traces", "source_required", "necessary_recall", "denominator"),
    "VM-04": (
        "bytes_eligible",
        "bytes_evicted",
        "memory_after_eviction_bytes",
        "reload_correct",
    ),
    "VM-05": ("schema", "provenance"),
    "VM-06": (
        "parse_ok",
        "bounded_target",
        "evidence_criteria",
        "criteria_met",
    ),
    "VM-07": (
        "seeded_faults",
        "blind_diagnosis",
        "diagnosed_root_cause",
        "fix_confirmed",
    ),
    "VM-08": (
        "sandbox_faults",
        "regressions",
        "rollback_ok",
        "success_denominator",
        "successes",
    ),
    "VM-09": (
        "ttft_cold_ms",
        "ttft_warm_ms",
        "total_cold_ms",
        "total_warm_ms",
        "hardware",
        "n_samples",
    ),
    "VM-10": ("paired", "oom_events", "fallback_taken", "denominator"),
    "VM-11": (
        "repeat_rate",
        "false_inhibition_rate",
        "status_label",
        "live",
        "denominator",
        "ci95",
    ),
}

# "Sai lầm cần tránh" — presence of these shortcut keys alone is never enough.
_SHORTCUT_ONLY: dict[str, tuple[str, ...]] = {
    "VM-01": ("n_forage",),  # every FORAGE is not automatically correct
    "VM-02": ("adapter_exists",),  # adapter exists ≠ accuracy
    "VM-03": ("n_tool_calls",),  # many tool calls ≠ good scan
    "VM-04": ("cache_entries",),  # entry count ≠ capacity/bytes
    "VM-05": ("lesson_text",),  # any lesson text ≠ 4-part schema
    "VM-06": ("parse_ok",),  # parse succeeded ≠ task correct (see also required)
    "VM-07": ("named_the_error",),  # naming the error ≠ root-cause analysis
    "VM-08": ("process_restarted",),  # process restart ≠ self-heal
    "VM-09": ("memory_get_ms",),  # memory microbenchmark ≠ TTFT
    "VM-10": ("n",),  # N increase alone does not prove intelligence
    "VM-11": ("status_label",),  # simulated ≠ production (checked below too)
}

# Presence is checked on the measurement key; *missing* reports this name so
# callers can match the acceptance-plan vocabulary ("false escalation").
_MISSING_NAMES = {
    "false_escalation_rate": "false_escalation",
}

_TRUE_FLAGS = frozenset(
    {
        "ood_labeled",
        "in_domain_labeled",
        "reload_correct",
        "source_required",
        "criteria_met",
        "blind_diagnosis",
        "fix_confirmed",
        "rollback_ok",
        "live",
    }
)

_SCHEMA_PARTS = ("claim", "evidence", "scope", "limits")
_INPUT_KINDS = ("real", "corrupt", "mixed")
_PAIRED_ARMS = ("N=1", "N=2", "N=3")


def quote_threshold(
    *,
    vm_id: str,
    spec_name: str,
    spec_version: str,
    verbatim: str,
) -> dict[str, Any]:
    """Record a spec threshold. Missing version or verbatim text is a GAP."""
    name = (spec_name or "").strip()
    version = (spec_version or "").strip()
    text = (verbatim or "").strip()
    quoted = bool(name and version and text)
    return {
        "vm_id": vm_id,
        "spec_name": name or None,
        "spec_version": version or None,
        "verbatim": text or None,
        "status": QUOTED_STATUS if quoted else GAP_STATUS,
        "note": (
            "quoted verbatim with version; measurement may proceed"
            if quoted
            else "spec silent or unversioned — GAP, not PASS"
        ),
    }


def evaluate_spec_thresholds(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate per-VM threshold quotes. Any GAP forces overall GAP.

    VM ids absent from *entries* are filled as GAP so a partial table can never
    look complete. Overall is never PASS: quoting a threshold is not a
    measurement.
    """
    thresholds: dict[str, dict[str, Any]] = {}
    for entry in entries:
        quoted = quote_threshold(
            vm_id=str(entry.get("vm_id", "")),
            spec_name=str(entry.get("spec_name", "") or ""),
            spec_version=str(entry.get("spec_version", "") or ""),
            verbatim=str(entry.get("verbatim", "") or ""),
        )
        thresholds[quoted["vm_id"]] = quoted
    for vm_id in VM_IDS:
        if vm_id not in thresholds:
            thresholds[vm_id] = quote_threshold(
                vm_id=vm_id,
                spec_name="",
                spec_version="",
                verbatim="",
            )
    gaps = sorted(k for k, v in thresholds.items() if v["status"] == GAP_STATUS)
    overall = GAP_STATUS if gaps else QUOTED_STATUS
    return {
        "thresholds": thresholds,
        "gaps": gaps,
        "n_quoted": sum(1 for v in thresholds.values() if v["status"] == QUOTED_STATUS),
        "n_gap": len(gaps),
        "overall": overall,
        "overall_is_never_pass": True,
        "note": (
            "threshold quoting is a prerequisite; overall=PASS would imply "
            "measurement, which this report does not perform"
        ),
    }


def _present(measurement: Mapping[str, Any], key: str) -> bool:
    if key not in measurement:
        return False
    value = measurement[key]
    if value is None:
        return False
    if key in _TRUE_FLAGS:
        return value is True
    if isinstance(value, (list, tuple, dict, set, str)) and len(value) == 0:
        return False
    return True


def _deep_validate(vm_id: str, measurement: Mapping[str, Any], missing: list[str]) -> None:
    """Extra shape checks beyond key presence."""
    if vm_id == "VM-02":
        kinds = measurement.get("inputs_include")
        if not isinstance(kinds, (list, tuple)) or not set(_INPUT_KINDS) <= set(kinds):
            missing.append("inputs_include(real|corrupt|mixed)")
        matrix = measurement.get("confusion_matrix")
        if not isinstance(matrix, dict) or not matrix:
            missing.append("confusion_matrix")
    elif vm_id == "VM-03":
        traces = measurement.get("traces")
        if not isinstance(traces, (list, tuple)) or not traces:
            missing.append("traces")
        elif not all(isinstance(t, Mapping) and t.get("source") for t in traces):
            missing.append("traces[].source")
    elif vm_id == "VM-05":
        schema = measurement.get("schema")
        if not isinstance(schema, Mapping):
            missing.append("schema")
        else:
            for part in _SCHEMA_PARTS:
                if not schema.get(part):
                    missing.append(f"schema.{part}")
        prov = measurement.get("provenance")
        if not isinstance(prov, Mapping) or not prov:
            missing.append("provenance")
    elif vm_id == "VM-06":
        criteria = measurement.get("evidence_criteria")
        if not isinstance(criteria, (list, tuple)) or not criteria:
            missing.append("evidence_criteria")
    elif vm_id == "VM-07":
        seeded = measurement.get("seeded_faults")
        if not isinstance(seeded, (list, tuple)) or not seeded:
            missing.append("seeded_faults")
        elif not all(isinstance(s, Mapping) and s.get("root_cause") for s in seeded):
            missing.append("seeded_faults[].root_cause")
    elif vm_id == "VM-10":
        paired = measurement.get("paired")
        if not isinstance(paired, Mapping):
            missing.append("paired")
        else:
            for arm in _PAIRED_ARMS:
                row = paired.get(arm)
                if not isinstance(row, Mapping):
                    missing.append(f"paired.{arm}")
                    continue
                if "quality" not in row or "resource" not in row:
                    missing.append(f"paired.{arm}.quality|resource")
    elif vm_id == "VM-11":
        if measurement.get("live") is not True:
            if "live" not in missing:
                missing.append("live")
        label = measurement.get("status_label")
        if label != LIVE_LABEL:
            missing.append("status_label=LIVE_MODEL_OBSERVATION")
        if label == SIM_LABEL:
            missing.append("simulation_is_not_production")


def judge_vm_measurement(vm_id: str, measurement: Mapping[str, Any]) -> dict[str, Any]:
    """Judge one VM measurement against the acceptance-plan shape.

    Returns verdict PASS only when every required field is present and valid.
    Shortcut-only payloads (the "Sai lầm cần tránh" mistakes) FAIL.
    """
    if vm_id not in _REQUIRED:
        return {
            "vm_id": vm_id,
            "verdict": "FAIL",
            "missing": ["unknown_vm_id"],
            "shortcut_only": [],
            "note": "unknown VM id",
        }

    required = _REQUIRED[vm_id]
    missing: list[str] = [
        _MISSING_NAMES.get(key, key) for key in required if not _present(measurement, key)
    ]
    _deep_validate(vm_id, measurement, missing)

    shortcut_only = [
        key
        for key in _SHORTCUT_ONLY.get(vm_id, ())
        if key in measurement and key not in required
    ]
    # VM-06 lists parse_ok as both required and a shortcut: parse alone is not
    # enough, so only flag it when the rest of the contract is absent.
    if vm_id == "VM-06" and set(measurement) <= {"parse_ok", "accuracy", "note", "label", "n"}:
        if "parse_ok" not in shortcut_only:
            shortcut_only.append("parse_ok")

    # A measurement that is only the known mistake keys can never pass.
    if shortcut_only and missing:
        pass  # already failing via missing
    elif shortcut_only and not any(k in measurement for k in required if k not in shortcut_only):
        missing.append("required_measurement_fields")

    verdict = "PASS" if not missing else "FAIL"
    return {
        "vm_id": vm_id,
        "verdict": verdict,
        "missing": missing,
        "shortcut_only": shortcut_only,
        "required": list(required),
        "note": (
            "shape contract only — not a numeric-threshold claim"
            if verdict == "PASS"
            else "measurement shape incomplete or uses a forbidden shortcut"
        ),
    }
