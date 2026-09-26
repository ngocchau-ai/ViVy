"""Interactive CLI for communicating with ViVy Multimodal Bilingual AI Model.

Usage:
  python scripts/chat_with_vivy.py --prompt "Chào ViVy!"
  python scripts/chat_with_vivy.py --prompt "Analyze this image" --image "path/to/img.png"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from nps_core.vivy_interface import ViVyChatSession  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Chat directly with ViVy Multimodal AI")
    parser.add_argument("--prompt", type=str, default="Chào ViVy, bạn hỗ trợ những ngôn ngữ và tính năng gì?", help="Text prompt")
    parser.add_argument("--image", type=str, default=None, help="Optional image path for visual analysis")
    args = parser.parse_args()

    session = ViVyChatSession()
    response = session.send_message(args.prompt, image_path=args.image)

    print("=" * 60)
    print(f"[LANG] Detected Language: {response.detected_language.upper()}")
    if response.visual_summary:
        print(f"[VISION] Visual Summary: {response.visual_summary}")

    print("\n[CHAIN OF THOUGHT REASONING]")
    for step in response.thought_chain:
        print(f"  {step}")

    print("\n[VIVY RESPONSE]")
    print(response.response_text)
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
