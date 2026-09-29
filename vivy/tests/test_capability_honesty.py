"""Gate 9 — capability honesty tripwire.  [NEW 29/09/2026 · WP-5 / O-12]

Nghiệm thu WP-5: **0 tuyên bố năng lực không có lời gọi model thật hoặc
receipt; mọi con số không đo được gắn `UNMEASURED`.**

This file is the enforcement, not the documentation.  ``docs/CAPABILITY_LEDGER.md``
records what is claimed; this file fails the build when a claim that was taken
out comes back, or when a number that was never measured starts being asserted
again as fact.

Scope of the source scan
------------------------
A claim counts as **live** when it appears in a Python *code* line — i.e. not
in a `#` comment and not in a docstring.  WP-5 deliberately quotes the old
claims in module docstrings and trailing `[ISOLATED]` comment blocks, per the
project rule "cô lập, không xóa".  Those quotes are history, not behaviour, so
the scanner skips them.  A string literal that is *returned, logged or sent to
a model* is code and is scanned.

INV-01: every patch carries a test.  If a test here fails, **fix the code, not
the test** (plan hard rule #4).  The assertions below are the spec.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

VIVY_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = VIVY_ROOT.parent
DOCS = REPO_ROOT / "docs"
SRC = VIVY_ROOT / "src"
MODELS = REPO_ROOT / "models"
MODELF_VY = VIVY_ROOT / "modelfiles" / "Modelfile.vivy-clairvoyance"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(VIVY_ROOT) not in sys.path:
    sys.path.insert(0, str(VIVY_ROOT))


# ---------------------------------------------------------------------------
# Source scanning helpers
# ---------------------------------------------------------------------------


def live_code_lines(text: str) -> str:
    """Return only Python code lines — comments and docstrings removed.

    Triple-quoted strings are treated as docstrings/comments throughout, which
    matches how WP-5 archived the old claims.
    """
    out: list[str] = []
    in_triple: str | None = None
    for line in text.splitlines():
        if in_triple:
            if in_triple in line:
                in_triple = None
            continue

        # Detect an opening triple-quote on this line.
        for q in ('"""', "'''"):
            if q in line:
                before, _, after = line.partition(q)
                if q in after:
                    # opens and closes on the same line — single-line string
                    line = before + after.partition(q)[2]
                    break
                in_triple = q
                line = before
                break

        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


def system_block(text: str) -> str:
    """Extract the live ``SYSTEM \"\"\"...\"\"\"`` body from a Modelfile."""
    m = re.search(r'SYSTEM\s+"""(.*?)"""', text, re.DOTALL)
    assert m, "Modelfile has no SYSTEM block"
    return m.group(1)


#: Phrases that assert an unmeasured capability *as a positive claim*.  The
#: words may appear in a denial ("do NOT claim zero-hallucination"); what must
#: not come back is the assertion form.
FORBIDDEN_LIVE_PHRASES = {
    "src/nps_core/vivy_interface/vision.py": [
        "width=1024",
        "height=1024",
        "width = 1024",
        "height = 1024",
    ],
    "src/nps_core/vivy_interface/reasoning_engine.py": [
        "has processed the image",
        "nhận diện được hình ảnh",
        "Fusing visual features",
        "Kết hợp đặc trưng thị giác",
        "equipped with Vision capability",
        "phân tích thị giác (Vision)",
    ],
    "src/vivy/core/moe_brain.py": [
        "70B MoE Quantum Core (1B Active)",
        "1B Active Parameters",
        "1B representational capacity",
    ],
    "src/nps_core/vivy_ollama/exporter.py": [
        "4-Level Self-Verification Filter Funnel",
        "1-Touch Intuition Retrieval",
        "Self-Verification: SVD spectral decomposition",
    ],
    "src/nps_core/multimodal_clairvoyance/clairvoyance_engine.py": [
        "Clairvoyance Direct Perception",
    ],
    "src/nps_core/vivy_ollama/server.py": [
        "parameter_size\": \"1.15B\"",
        "sha256:vivy1b",
        "2147483648",
    ],
}


# ---------------------------------------------------------------------------
# 1. Known lies must not be live code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("relpath", "phrases"), sorted(FORBIDDEN_LIVE_PHRASES.items())
)
def test_wp5_claims_are_not_live_code(relpath: str, phrases: list[str]) -> None:
    path = VIVY_ROOT / relpath
    assert path.exists(), f"missing source under test: {relpath}"

    live = live_code_lines(path.read_text(encoding="utf-8"))
    for phrase in phrases:
        assert phrase not in live, (
            f"{relpath}: {phrase!r} is LIVE CODE again. It was removed in "
            f"WP-5 because it had no receipt. Fix the code, not this test. "
            f"See docs/CAPABILITY_LEDGER.md."
        )


# ---------------------------------------------------------------------------
# 2. Vision must never invent a resolution
# ---------------------------------------------------------------------------


def test_vision_module_never_writes_a_hardcoded_resolution() -> None:
    live = live_code_lines(
        (VIVY_ROOT / "src/nps_core/vivy_interface/vision.py").read_text(encoding="utf-8")
    )
    assert "1024" not in live, "vision.py code must not contain a literal resolution"
    assert "width=None" in live
    assert "height=None" in live


def test_vision_payload_marks_simulated_and_unknown(tmp_path) -> None:
    from nps_core.vivy_interface.vision import VisionEncoder

    with pytest.raises(FileNotFoundError):
        VisionEncoder.from_file(tmp_path / "absent.png")

    p = VisionEncoder.from_file(tmp_path / "absent.png", allow_simulated=True)
    assert p.simulated is True
    assert p.width is None and p.height is None

    real = tmp_path / "real.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\nreal-bytes")
    r = VisionEncoder.from_file(real)
    assert r.simulated is False
    assert r.width is None and r.height is None
    assert r.content_hash != p.content_hash


# ---------------------------------------------------------------------------
# 3. Modelfile / exporter must not assert unmeasured capabilities
# ---------------------------------------------------------------------------


def test_modelfile_system_prompt_is_honest() -> None:
    body = system_block(MODELF_VY.read_text(encoding="utf-8"))

    # The positive capability assertions are gone.
    assert "Self-Verification: SVD spectral decomposition" not in body
    assert "4-level filter funnel, zero-hallucination" not in body
    assert "Native Visual Perception:" not in body
    assert "Native Video Perception:" not in body
    assert "Native Audio Perception:" not in body
    # ...and the honest version is present.  The words may appear inside the
    # "NOT measured" denial list — that is the point of the list.
    assert "NOT measured" in body
    assert "do NOT present these as capabilities" in body


def test_exporter_modelfile_is_honest() -> None:
    from nps_core.vivy_ollama.exporter import OllamaModelExporter

    content = OllamaModelExporter.generate_modelfile_content()
    body = system_block(content)

    # Positive capability assertions are gone.
    assert "4-Level Self-Verification Filter Funnel" not in body
    assert "1-Touch Intuition Retrieval" not in body
    assert "Self-Verification: SVD spectral decomposition" not in body
    # And the honest version is present.
    assert "NOT measured" in body


# ---------------------------------------------------------------------------
# 4. Simulated modules must say so, and the atlas must refuse prompt injection
# ---------------------------------------------------------------------------


def test_clairvoyance_output_is_flagged_simulated() -> None:
    from nps_core.multimodal_clairvoyance.clairvoyance_engine import ClairvoyanceEngine

    res = ClairvoyanceEngine.process_multimodal_clairvoyance(
        "hello", image_path="missing.jpg", audio_path="missing.wav"
    )
    assert res.simulated is True
    assert res.pixels_read is False
    assert res.audio_samples_read is False
    assert res.video_frames_read is False
    assert "SIMULATED" in res.clairvoyance_perception_summary
    assert "Direct Perception" not in res.clairvoyance_perception_summary


def test_audio_video_payloads_never_invent_measurements() -> None:
    from nps_core.multimodal_clairvoyance.audio_video_perception import (
        AudioVideoEncoder,
    )

    with pytest.raises(FileNotFoundError):
        AudioVideoEncoder.encode_audio_file("missing.wav")

    a = AudioVideoEncoder.encode_audio_file("missing.wav", allow_simulated=True)
    assert a.sample_rate is None
    assert a.channels is None
    assert a.duration_sec is None
    assert a.spectrogram_is_synthetic is True
    assert a.samples_read is False

    with pytest.raises(FileNotFoundError):
        AudioVideoEncoder.encode_video_file("missing.mp4")

    v = AudioVideoEncoder.encode_video_file("missing.mp4", allow_simulated=True)
    assert v.width is None and v.height is None
    assert v.fps is None
    assert v.frame_count is None
    assert v.frames_read is False


def test_cautreo_atlas_refuses_prompt_injection() -> None:
    """[ADDED 29/09/2026 · WP-5 / F-C07] the ban is enforced in code."""
    from integration.cautreo_cartographer import CautreoCartographer

    atlas = CautreoCartographer().scan_model("fake-70b-model", total_layers=4)

    assert atlas.simulated is True
    assert atlas.weights_read is False
    assert atlas.prompt_injection_allowed is False
    assert all(n.simulated for n in atlas.nodes.values())
    assert all(n.weights_read is False for n in atlas.nodes.values())

    with pytest.raises(RuntimeError, match="must NOT be injected"):
        atlas.render_for_prompt()


def test_scan_model_ignores_model_path() -> None:
    from integration.cautreo_cartographer import CautreoCartographer

    cart = CautreoCartographer()
    a = cart.scan_model("x", total_layers=3, model_path="/nonexistent/weights.gguf")
    b = cart.scan_model("x", total_layers=3, model_path="/also/nonexistent.bin")

    # model_path is never read — two different paths give the same atlas.
    assert a.simulated and b.simulated
    assert [n.dominant_domain for n in a.nodes.values()] == [
        n.dominant_domain for n in b.nodes.values()
    ]
    assert [n.high_salience_neuron_indices for n in a.nodes.values()] == [
        n.high_salience_neuron_indices for n in b.nodes.values()
    ]


# ---------------------------------------------------------------------------
# 5. Manifest: every unmeasured number is tagged
# ---------------------------------------------------------------------------


def test_model_manifest_tags_unmeasured_benchmarks() -> None:
    data = json.loads((MODELS / "model_manifest.json").read_text(encoding="utf-8"))
    assert data["capability_ledger_ref"] == "docs/CAPABILITY_LEDGER.md"
    assert "UNMEASURED" in data["unmeasured_claims_policy"]

    seen = 0
    for m in data["models"]:
        if "benchmark" not in m:
            continue
        seen += 1
        assert m["benchmark"].startswith("[UNMEASURED]"), (
            f"{m['id']}: benchmark must be prefixed [UNMEASURED] until a receipt exists"
        )
        assert m.get("benchmark_status") == "UNMEASURED"
        assert m.get("benchmark_receipt") is None
        assert m.get("benchmark_note")
    assert seen >= 4, "expected at least the 4 benchmark entries the review named"


# ---------------------------------------------------------------------------
# 6. The ledger itself must exist and cover the seed list
# ---------------------------------------------------------------------------

SEED_CLAIMS = [
    "Epistemic Rigor 99.2%",
    "MMBench 84.5",
    "DocVQA 94.2",
    "Zero-OOM",
    "Peak VRAM",
    "VM-11",
    "HebbianRecall",
    "70B MoE",
    "1B Active",
    "HumanEval",
    "tok/s",
    "zero-hallucination",
]


def test_capability_ledger_exists_and_is_live() -> None:
    ledger = DOCS / "CAPABILITY_LEDGER.md"
    assert ledger.exists(), "docs/CAPABILITY_LEDGER.md is the Gate 9 deliverable"
    text = ledger.read_text(encoding="utf-8")
    assert "UNMEASURED" in text
    assert "Gate 9" in text
    assert "RECEIPT" in text


@pytest.mark.parametrize("claim", SEED_CLAIMS)
def test_capability_ledger_covers_each_seed_claim(claim: str) -> None:
    text = (DOCS / "CAPABILITY_LEDGER.md").read_text(encoding="utf-8")
    assert claim in text, (
        f"claim {claim!r} is not on the ledger. Gate 9: every claim needs a "
        f"receipt or an UNMEASURED row."
    )


def test_zero_claims_in_the_ledger_are_always_status_marked() -> None:
    """A bare '0 ms' / '0%' is still a claim — it must sit in a marked row."""
    text = (DOCS / "CAPABILITY_LEDGER.md").read_text(encoding="utf-8")
    for m in re.finditer(r"`0 ms`|`0%`|zero-hallucination", text):
        window = text[max(0, m.start() - 400) : m.start() + 400]
        assert re.search(r"UNMEASURED|REPLACED|ISOLATED|SIMULATED", window), (
            f"unmarked zero-claim near offset {m.start()}: {m.group(0)!r}"
        )


def test_ledger_has_no_unmarked_unmeasured_row() -> None:
    """Every table row that names a number must name a status."""
    text = (DOCS / "CAPABILITY_LEDGER.md").read_text(encoding="utf-8")
    bad = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if not re.search(r"\d", line):
            continue
        # Header / separator rows.
        if re.match(r"^\|\s*:?-+:?\s*\|", line) or line.startswith("|:--"):
            continue
        if re.search(r"UNMEASURED|REPLACED|ISOLATED|SIMULATED|RECEIPT", line):
            continue
        # Rows that are pure column headers or section furniture.
        if re.search(r"\b(Trạng thái|Receipt|Nơi|Claim|Trạng)\b", line):
            continue
        bad.append(line)
    assert not bad, f"ledger rows with numbers but no status marker: {bad}"
