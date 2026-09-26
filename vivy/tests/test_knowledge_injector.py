"""Tests for the KnowledgeInjector domain-knowledge injection."""

from __future__ import annotations

from core.knowledge_injector import KnowledgeInjector
from llm_bridge.encoder import LogicForm


def _lf(propositions: list[str], query: str = "") -> LogicForm:
    return LogicForm(propositions=propositions, query=query)


def test_no_match_returns_empty() -> None:
    inj = KnowledgeInjector()
    streams = inj.inject(_lf(["The sky is blue."], "Is the sky blue?"))
    assert streams == []


def test_harmonic_oscillator_injects_energy_levels() -> None:
    inj = KnowledgeInjector()
    streams = inj.inject(
        _lf(
            ["A quantum harmonic oscillator has mass m and frequency omega."],
            "What is the ground-state energy?",
        )
    )
    assert len(streams) == 1
    s = streams[0]
    assert s["domain"] == "quantum.harmonic_oscillator"
    assert "E_n = (n + 1/2)" in s["interpretation"]
    assert s["singular_value"] > 0.9


def test_bell_inequality_injects_chsh() -> None:
    inj = KnowledgeInjector()
    streams = inj.inject(
        _lf(["Two entangled particles are measured."], "Does the CHSH inequality hold?")
    )
    assert len(streams) == 1
    assert streams[0]["domain"] == "quantum.bell"
    assert "2*sqrt(2)" in streams[0]["interpretation"]


def test_multiple_domains_dedup_to_highest_confidence() -> None:
    """When multiple domains match, only the highest-confidence stream survives."""
    inj = KnowledgeInjector()
    streams = inj.inject(
        _lf(
            ["The particle is in a box and has spin 1/2."],
            "Compute the ground-state energy.",
        )
    )
    # Dedup picks the highest singular_value — both are 0.95, so only one
    assert len(streams) == 1
    assert streams[0]["domain"] in ("quantum.particle_in_box", "quantum.spin")


def test_collatz_injects_conjecture() -> None:
    inj = KnowledgeInjector()
    streams = inj.inject(_lf([], "Is the Collatz conjecture true for all n?"))
    assert len(streams) == 1
    assert streams[0]["domain"] == "math.collatz"


def test_stream_shape_is_funnel_compatible() -> None:
    inj = KnowledgeInjector()
    streams = inj.inject(_lf(["A pendulum swings."], "What is its period?"))
    assert streams
    s = streams[0]
    for key in ("singular_value", "amplitude_ratio", "interpretation", "domain"):
        assert key in s
    assert 0.0 <= s["singular_value"] <= 1.0
    assert s["singular_value"] == s["amplitude_ratio"]
