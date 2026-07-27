"""Script to package ViVy into Ollama format (Modelfile.vivy & ollama create vivy).

Usage:
  python scripts/package_vivy_ollama.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from nps_core.vivy_ollama import OllamaModelExporter


def main() -> int:
    print("=" * 60)
    print("[OLLAMA PACKAGING] Packaging ViVy AI Model for Ollama...")
    print("=" * 60)

    modelfile_path = REPO_ROOT / "modelfiles" / "Modelfile.vivy"
    saved_path = OllamaModelExporter.export_modelfile(modelfile_path)
    print(f"[OK] Exported Modelfile to: {saved_path}")

    create_cmd = OllamaModelExporter.get_create_command("vivy", str(saved_path))
    print("\n[INSTRUCTIONS TO PULL & RUN VIVY IN OLLAMA]")
    print("1. Build and register ViVy locally in Ollama:")
    print(f"   {create_cmd}")
    print("\n2. Interact with ViVy via Ollama CLI:")
    print("   ollama run vivy")
    print("\n3. Or communicate via Ollama HTTP API:")
    print("   curl http://localhost:11434/api/generate -d '{\"model\": \"vivy\", \"prompt\": \"Chào ViVy!\"}'")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
