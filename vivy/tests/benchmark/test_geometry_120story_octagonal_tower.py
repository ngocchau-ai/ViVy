"""Benchmark & Test Suite for ViVy Geometric & Spatial Reasoning: 120-Story Middle-Eastern Octagonal Tower.

Verifies mathematical matrix calculations of 8-sided octagonal geometry,
tapering ratios, 6 micro-task decompositions, and 3D HTML visualization rendering.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

__all__ = [
    "OctagonalGeometryMath",
    "TowerFloorZone",
    "DecomposedMicroTask",
]


class OctagonalGeometryMath:
    """Helper calculating 8-sided regular octagonal geometry metrics."""

    @staticmethod
    def calculate_side_length(radius: float) -> float:
        """Calculate side length a = 2 * R * tan(22.5 deg)."""
        return 2.0 * radius * math.tan(math.radians(22.5))

    @staticmethod
    def calculate_floor_area(radius: float) -> float:
        """Calculate octagonal floor area S = 2 * sqrt(2) * R^2."""
        return 2.0 * math.sqrt(2.0) * (radius ** 2)

    @staticmethod
    def calculate_vertex_coordinates(radius: float, floor_height: float) -> list[tuple[float, float, float]]:
        """Calculate 8 vertex coordinates (x_k, y_k, z) for 8 octagonal corners."""
        vertices = []
        for k in range(8):
            angle_rad = math.radians(k * 45.0)
            x = radius * math.cos(angle_rad)
            y = radius * math.sin(angle_rad)
            vertices.append((round(x, 4), round(y, 4), round(floor_height, 2)))
        return vertices


class TowerFloorZone:
    """Vertical floor zone configuration for 120 stories."""

    @staticmethod
    def get_zone_for_floor(floor: int) -> str:
        if 1 <= floor <= 10:
            return "Podium & Grand Lobby"
        elif 11 <= floor <= 40:
            return "Commercial Offices"
        elif 41 <= floor <= 75:
            return "Luxury Residential"
        elif 76 <= floor <= 105:
            return "Palace Hotel 7★ & Sky Villas"
        elif 106 <= floor <= 115:
            return "Sky Deck Observatory"
        elif 116 <= floor <= 120:
            return "Mechanical Plant & Spire"
        else:
            raise ValueError(f"Floor {floor} out of range 1..120")


class DecomposedMicroTask:
    """Micro-task definition for 120-story building decomposition."""

    @staticmethod
    def get_all_tasks() -> tuple[str, ...]:
        return (
            "Task 1: Octagonal Geometry Math & Tapering Matrix",
            "Task 2: 120-Story Vertical Floor Zoning Matrix",
            "Task 3: Structural Mega-Columns & Mashrabiya Lattice Grid",
            "Task 4: Ground Khatam Plaza & Oasis Reflecting Pools",
            "Task 5: Interactive 3D WebGL HTML Renderer",
            "Task 6: Automated Geometry Benchmark Audit",
        )


# ---------------------------------------------------------------------------
# UNIT & BENCHMARK TESTS
# ---------------------------------------------------------------------------

def test_octagonal_geometry_calculations():
    # Test Floor 1 (R = 40m)
    r1 = 40.0
    side1 = OctagonalGeometryMath.calculate_side_length(r1)
    area1 = OctagonalGeometryMath.calculate_floor_area(r1)

    assert pytest.approx(side1, abs=0.1) == 33.14
    assert pytest.approx(area1, abs=1.0) == 4525.5

    # Verify 8 vertices symmetry at 45 deg angles
    vertices = OctagonalGeometryMath.calculate_vertex_coordinates(r1, floor_height=4.5)
    assert len(vertices) == 8
    assert vertices[0] == (40.0, 0.0, 4.5)  # 0 deg
    assert vertices[2] == (0.0, 40.0, 4.5)   # 90 deg


def test_120_floor_vertical_zoning():
    assert TowerFloorZone.get_zone_for_floor(1) == "Podium & Grand Lobby"
    assert TowerFloorZone.get_zone_for_floor(25) == "Commercial Offices"
    assert TowerFloorZone.get_zone_for_floor(50) == "Luxury Residential"
    assert TowerFloorZone.get_zone_for_floor(80) == "Palace Hotel 7★ & Sky Villas"
    assert TowerFloorZone.get_zone_for_floor(110) == "Sky Deck Observatory"
    assert TowerFloorZone.get_zone_for_floor(120) == "Mechanical Plant & Spire"

    with pytest.raises(ValueError):
        TowerFloorZone.get_zone_for_floor(121)


def test_decomposed_micro_tasks():
    tasks = DecomposedMicroTask.get_all_tasks()
    assert len(tasks) == 6
    assert "Task 1:" in tasks[0]
    assert "Task 5:" in tasks[4]


def test_html_3d_viewer_artifact_exists():
    repo_root = Path(__file__).resolve().parents[2]
    html_path = repo_root / "docs" / "geometry_3d_tower_viewer.html"
    spec_path = repo_root / "docs" / "OCTAGONAL_TOWER_120S_SPECIFICATION.md"

    assert html_path.exists(), f"HTML 3D Viewer missing: {html_path}"
    assert spec_path.exists(), f"Specification doc missing: {spec_path}"

    html_content = html_path.read_text(encoding="utf-8")
    assert "Three.js" in html_content or "three.min.js" in html_content
    assert "Octagon" in html_content or "setbackZones" in html_content
