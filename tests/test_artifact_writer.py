"""Tests for KnowledgeArtifactWriter — V5.0 Sprint 3A.

10 tests cho artifact_writer.py.

Changelog:
    19/09/2026 (Antigravity IDE, Sprint 3A tests): Initial implementation.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from forager.artifact_writer import (
    KnowledgeArtifactWriter,
    KnowledgeBriefContent,
)

_SCRATCH_BASE = Path("scratchpad/_test")


@pytest.fixture()
def tmp_path() -> Path:  # type: ignore[override]
    """Custom tmp_path fixture that uses workspace dir to avoid Windows PermissionError."""
    test_id = uuid.uuid4().hex[:8]
    p = _SCRATCH_BASE / test_id
    p.mkdir(parents=True, exist_ok=True)
    yield p
    shutil.rmtree(p, ignore_errors=True)


def _sample_content(**overrides: str) -> KnowledgeBriefContent:
    defaults = {
        "topic": "FFMPEG Video Slicing",
        "source_path": "https://ffmpeg.org/docs",
        "core_mechanics": "Use -ss and -t flags to extract video segments.",
        "invariants": "Always use -codec:v copy to avoid re-encoding.",
        "api_signatures": "ffmpeg -i input.mp4 -ss 00:01:00 -t 30 out.mp4",
        "gotchas": "Seeking with -ss before -i is faster (keyframe seek).",
        "lang": "bash",
    }
    defaults.update(overrides)
    return KnowledgeBriefContent(**defaults)


def test_write_brief_creates_file(tmp_path: Path) -> None:
    """write_brief() creates a .md file in scratchpad."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    result = writer.write_brief(_sample_content())
    assert Path(result.file_path).exists()
    assert result.file_path.endswith(".md")


def test_write_brief_result_is_complete(tmp_path: Path) -> None:
    """write_brief() with all sections produces is_complete=True."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    result = writer.write_brief(_sample_content())
    assert result.is_complete is True
    assert result.sections_complete == 4
    assert result.validation_errors == []


def test_written_brief_contains_all_sections(tmp_path: Path) -> None:
    """Written file contains all 4 required section headers."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    result = writer.write_brief(_sample_content())
    content = Path(result.file_path).read_text(encoding="utf-8")
    assert "Core Mechanics" in content
    assert "Hard Invariants" in content
    assert "Verified API Signatures" in content
    assert "Known Gotchas" in content


def test_written_brief_contains_topic(tmp_path: Path) -> None:
    """Written brief starts with the correct topic."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    result = writer.write_brief(_sample_content(topic="My Custom Topic"))
    content = Path(result.file_path).read_text(encoding="utf-8")
    assert "My Custom Topic" in content


def test_written_brief_has_source_and_confidence(tmp_path: Path) -> None:
    """Written brief includes source_path and confidence level."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    content_obj = _sample_content(source_path="docs/cuda.pdf", confidence="VERIFIED")
    result = writer.write_brief(content_obj)
    content = Path(result.file_path).read_text(encoding="utf-8")
    assert "docs/cuda.pdf" in content
    assert "VERIFIED" in content


def test_validate_completeness_passes_for_complete_brief(tmp_path: Path) -> None:
    """validate_completeness() returns empty errors for complete brief."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    result = writer.write_brief(_sample_content())
    errors = writer.validate_completeness(result.file_path)
    assert errors == []


def test_validate_completeness_fails_for_missing_section(tmp_path: Path) -> None:
    """validate_completeness() detects missing sections in a malformed file."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    malformed = tmp_path / "malformed_brief.md"
    malformed.write_text("# KNOWLEDGE BRIEF: Test\n\n## 1. Core Mechanics\nSome content.\n", encoding="utf-8")
    errors = writer.validate_completeness(str(malformed))
    # Should flag missing sections
    assert len(errors) > 0
    missing_labels = [e for e in errors if "Missing section" in e]
    assert len(missing_labels) > 0


def test_validate_completeness_file_not_found(tmp_path: Path) -> None:
    """validate_completeness() returns error for non-existent file."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    errors = writer.validate_completeness(str(tmp_path / "nonexistent.md"))
    assert len(errors) == 1
    assert "not found" in errors[0].lower() or "File" in errors[0]


def test_list_briefs_returns_created_files(tmp_path: Path) -> None:
    """list_briefs() returns paths to all created briefs."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    writer.write_brief(_sample_content(topic="Topic A"))
    writer.write_brief(_sample_content(topic="Topic B"))
    briefs = writer.list_briefs()
    assert len(briefs) == 2


def test_brief_id_in_result(tmp_path: Path) -> None:
    """BriefWriteResult has a non-empty brief_id."""
    writer = KnowledgeArtifactWriter(scratchpad_dir=tmp_path)
    result = writer.write_brief(_sample_content())
    assert isinstance(result.brief_id, str)
    assert len(result.brief_id) > 0
